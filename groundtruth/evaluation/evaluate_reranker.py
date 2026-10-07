from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from groundtruth.retrieval.bm25_retriever import BM25RetrieverError
from groundtruth.retrieval.dense_retriever import DenseRetrieverError
from groundtruth.retrieval.hybrid_retriever import HybridRetrieverError
from groundtruth.retrieval.reranker import (
    CrossEncoderReranker,
    RerankerError,
)

DEFAULT_GOLD = Path("data/evaluation/golden_questions.jsonl")
DEFAULT_REPORT = Path("reports/evaluation/reranker_dev_v0_1.json")


class EvaluationError(RuntimeError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvaluationError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            rows.append(value)

    return rows


def grades_for(question: dict[str, Any]) -> dict[str, int]:
    return {
        str(judgment["chunk_id"]): int(judgment["grade"])
        for judgment in question["relevance_judgments"]
    }


def recall_at_k(
    retrieved: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    relevant = {
        cid
        for cid, grade in grades.items()
        if grade > 0
    }

    if not relevant:
        return 0.0

    return len(relevant.intersection(retrieved[:k])) / len(relevant)


def reciprocal_rank(
    retrieved: list[str],
    grades: dict[str, int],
) -> float:
    for rank, cid in enumerate(retrieved, start=1):
        if grades.get(cid, 0) > 0:
            return 1.0 / rank

    return 0.0


def dcg_at_k(
    retrieved: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    total = 0.0

    for rank, cid in enumerate(retrieved[:k], start=1):
        grade = grades.get(cid, 0)

        if grade > 0:
            total += ((2 ** grade) - 1) / math.log2(rank + 1)

    return total


def ndcg_at_k(
    retrieved: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    ideal_grades = sorted(
        [grade for grade in grades.values() if grade > 0],
        reverse=True,
    )[:k]

    ideal = sum(
        ((2 ** grade) - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(ideal_grades, start=1)
    )

    if ideal == 0:
        return 0.0

    return dcg_at_k(retrieved, grades, k) / ideal


def first_relevant_rank(
    retrieved: list[str],
    grades: dict[str, int],
) -> int | None:
    for rank, cid in enumerate(retrieved, start=1):
        if grades.get(cid, 0) > 0:
            return rank

    return None


def mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if row["answerable"]]

    return {
        "question_count": len(rows),
        "answerable_question_count": len(answerable),
        "Recall@5": mean([row["metrics"]["Recall@5"] for row in answerable]),
        "Recall@10": mean([row["metrics"]["Recall@10"] for row in answerable]),
        "MRR": mean([row["metrics"]["MRR"] for row in answerable]),
        "nDCG@5": mean([row["metrics"]["nDCG@5"] for row in answerable]),
        "nDCG@10": mean([row["metrics"]["nDCG@10"] for row in answerable]),
        "top1_hit_rate": mean([
            1.0 if row["first_relevant_rank"] == 1 else 0.0
            for row in answerable
        ]),
    }


def grouped(
    rows: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        buckets[str(row[field])].append(row)

    return {
        key: aggregate(values)
        for key, values in sorted(buckets.items())
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate cross-encoder reranking over Hybrid RRF v0.2."
    )

    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument(
        "--model",
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
    )
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--run-name", default="reranker_dev_v0_1")
    parser.add_argument("--skip-hash-verification", action="store_true")
    args = parser.parse_args()

    if args.top_k < 10:
        parser.error("--top-k must be at least 10.")

    if args.candidate_k < args.top_k:
        parser.error("--candidate-k must be >= --top-k.")

    try:
        questions = load_jsonl(args.golden)

        if args.split != "all":
            questions = [
                q for q in questions
                if q["split"] == args.split
            ]

        reranker = CrossEncoderReranker(
            model_name=args.model,
            device=args.device,
            candidate_k=args.candidate_k,
            batch_size=args.batch_size,
            max_length=args.max_length,
            verify_hashes=not args.skip_hash_verification,
        )

        rows: list[dict[str, Any]] = []

        for index, question in enumerate(questions, start=1):
            qid = str(question["question_id"])
            query = str(question["question"])

            print(
                f"[{index:03d}/{len(questions):03d}] "
                f"{qid}"
            )

            results = reranker.search(
                query,
                top_k=max(10, args.top_k),
            )

            retrieved = [
                str(result["chunk_id"])
                for result in results
            ]

            grades = grades_for(question)

            if question["answerable"]:
                metrics = {
                    "Recall@5": round(recall_at_k(retrieved, grades, 5), 6),
                    "Recall@10": round(recall_at_k(retrieved, grades, 10), 6),
                    "MRR": round(reciprocal_rank(retrieved, grades), 6),
                    "nDCG@5": round(ndcg_at_k(retrieved, grades, 5), 6),
                    "nDCG@10": round(ndcg_at_k(retrieved, grades, 10), 6),
                }
                first_rank = first_relevant_rank(retrieved, grades)
            else:
                metrics = {
                    "Recall@5": None,
                    "Recall@10": None,
                    "MRR": None,
                    "nDCG@5": None,
                    "nDCG@10": None,
                }
                first_rank = None

            rows.append(
                {
                    "question_id": qid,
                    "question": query,
                    "category": question["category"],
                    "difficulty": question["difficulty"],
                    "split": question["split"],
                    "answerable": question["answerable"],
                    "first_relevant_rank": first_rank,
                    "metrics": metrics,
                    "retrieved": [
                        {
                            "rank": int(result["rank"]),
                            "chunk_id": str(result["chunk_id"]),
                            "reranker_score": round(
                                float(result["reranker_score"]),
                                8,
                            ),
                            "hybrid_rank": int(result["hybrid_rank"]),
                        }
                        for result in results[:args.top_k]
                    ],
                }
            )

        report = {
            "evaluator_version": "0.1.0",
            "run_name": args.run_name,
            "split": args.split,
            "reranker": reranker.describe(),
            "overall": aggregate(rows),
            "by_category": grouped(rows, "category"),
            "by_difficulty": grouped(rows, "difficulty"),
            "per_question": rows,
        }

        args.report_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.report_output.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        overall = report["overall"]

        print()
        print("-" * 84)
        print("GroundTruth Cross-Encoder Reranker Evaluation")
        print("-" * 84)
        print(f"Run:          {args.run_name}")
        print(f"Questions:    {overall['question_count']}")
        print(f"Answerable:   {overall['answerable_question_count']}")
        print(f"Recall@5:     {overall['Recall@5']}")
        print(f"Recall@10:    {overall['Recall@10']}")
        print(f"MRR:          {overall['MRR']}")
        print(f"nDCG@5:       {overall['nDCG@5']}")
        print(f"nDCG@10:      {overall['nDCG@10']}")
        print(f"Top-1 hit:    {overall['top1_hit_rate']}")
        print(f"Report:       {args.report_output}")
        print("Status:       SUCCESS")
        print("-" * 84)

        return 0

    except (
        EvaluationError,
        RerankerError,
        HybridRetrieverError,
        DenseRetrieverError,
        BM25RetrieverError,
    ) as exc:
        print(f"Reranker evaluation failed: {exc}")
        return 1

    except Exception as exc:
        print(
            "Reranker evaluation failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
