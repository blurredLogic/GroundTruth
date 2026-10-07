from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from groundtruth.retrieval.bm25_retriever import (
    BM25Retriever,
    BM25RetrieverError,
)


EVALUATOR_VERSION = "0.1.0"

DEFAULT_GOLD_PATH = Path("data/evaluation/golden_questions.jsonl")
DEFAULT_INDEX_DIR = Path("data/index/bm25")
DEFAULT_REPORT_PATH = Path("reports/evaluation/bm25_100.json")


class EvaluationError(RuntimeError):
    """Raised when the retrieval benchmark cannot run safely."""


VALID_CATEGORIES = {
    "direct_factual",
    "comparison",
    "scenario_application",
    "multi_hop",
    "troubleshooting",
    "negative_near_miss",
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_SPLITS = {"dev", "test"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise EvaluationError(f"Golden set does not exist: {path}")

    records: list[dict[str, Any]] = []

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

            if not isinstance(value, dict):
                raise EvaluationError(
                    f"{path}:{line_number}: each line must be an object."
                )

            records.append(value)

    if not records:
        raise EvaluationError(f"No questions found in {path}")

    return records


def validate_question(question: dict[str, Any]) -> None:
    required = {
        "question_id",
        "question",
        "category",
        "difficulty",
        "split",
        "answerable",
        "relevance_judgments",
    }

    missing = required - set(question)

    if missing:
        raise EvaluationError(
            "Golden question missing fields: "
            + ", ".join(sorted(missing))
        )

    question_id = str(question["question_id"])

    if question["category"] not in VALID_CATEGORIES:
        raise EvaluationError(
            f"{question_id}: invalid category."
        )

    if question["difficulty"] not in VALID_DIFFICULTIES:
        raise EvaluationError(
            f"{question_id}: invalid difficulty."
        )

    if question["split"] not in VALID_SPLITS:
        raise EvaluationError(
            f"{question_id}: invalid split."
        )

    if not isinstance(question["answerable"], bool):
        raise EvaluationError(
            f"{question_id}: answerable must be boolean."
        )

    judgments = question["relevance_judgments"]

    if not isinstance(judgments, list):
        raise EvaluationError(
            f"{question_id}: relevance_judgments must be a list."
        )

    positive = 0
    seen: set[str] = set()

    for judgment in judgments:
        chunk_id = str(judgment["chunk_id"])
        grade = int(judgment["grade"])

        if chunk_id in seen:
            raise EvaluationError(
                f"{question_id}: duplicate judgment for {chunk_id}"
            )

        seen.add(chunk_id)

        if not 0 <= grade <= 3:
            raise EvaluationError(
                f"{question_id}: grade must be in 0..3."
            )

        if grade > 0:
            positive += 1

    if question["answerable"] and positive == 0:
        raise EvaluationError(
            f"{question_id}: answerable question has no positive judgments."
        )

    if not question["answerable"] and positive > 0:
        raise EvaluationError(
            f"{question_id}: negative question has positive judgments."
        )


def validate_golden_set(
    questions: list[dict[str, Any]],
) -> None:
    seen: set[str] = set()

    for question in questions:
        validate_question(question)
        question_id = str(question["question_id"])

        if question_id in seen:
            raise EvaluationError(
                f"Duplicate question_id: {question_id}"
            )

        seen.add(question_id)


def judgments_by_chunk(
    question: dict[str, Any],
) -> dict[str, int]:
    return {
        str(judgment["chunk_id"]): int(judgment["grade"])
        for judgment in question["relevance_judgments"]
    }


def recall_at_k(
    retrieved_ids: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    relevant = {
        chunk_id
        for chunk_id, grade in grades.items()
        if grade > 0
    }

    if not relevant:
        return 0.0

    hits = len(relevant.intersection(retrieved_ids[:k]))
    return hits / len(relevant)


def reciprocal_rank(
    retrieved_ids: list[str],
    grades: dict[str, int],
) -> float:
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if grades.get(chunk_id, 0) > 0:
            return 1.0 / rank

    return 0.0


def dcg_at_k(
    retrieved_ids: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    total = 0.0

    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):
        grade = grades.get(chunk_id, 0)

        if grade <= 0:
            continue

        total += (
            ((2 ** grade) - 1)
            / math.log2(rank + 1)
        )

    return total


def ideal_dcg_at_k(
    grades: dict[str, int],
    k: int,
) -> float:
    ideal_grades = sorted(
        [grade for grade in grades.values() if grade > 0],
        reverse=True,
    )[:k]

    return sum(
        ((2 ** grade) - 1)
        / math.log2(rank + 1)
        for rank, grade in enumerate(ideal_grades, start=1)
    )


def ndcg_at_k(
    retrieved_ids: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    ideal = ideal_dcg_at_k(grades, k)

    if ideal == 0:
        return 0.0

    return dcg_at_k(retrieved_ids, grades, k) / ideal


def first_relevant_rank(
    retrieved_ids: list[str],
    grades: dict[str, int],
) -> int | None:
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if grades.get(chunk_id, 0) > 0:
            return rank

    return None


def mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None

    return round(statistics.fmean(values), 6)


def aggregate_metric_rows(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    answerable = [
        row for row in rows if row["answerable"]
    ]

    return {
        "question_count": len(rows),
        "answerable_question_count": len(answerable),
        "Recall@5": mean_or_none(
            [row["metrics"]["Recall@5"] for row in answerable]
        ),
        "Recall@10": mean_or_none(
            [row["metrics"]["Recall@10"] for row in answerable]
        ),
        "MRR": mean_or_none(
            [row["metrics"]["MRR"] for row in answerable]
        ),
        "nDCG@5": mean_or_none(
            [row["metrics"]["nDCG@5"] for row in answerable]
        ),
        "nDCG@10": mean_or_none(
            [row["metrics"]["nDCG@10"] for row in answerable]
        ),
        "top1_hit_rate": mean_or_none(
            [
                1.0 if row["first_relevant_rank"] == 1 else 0.0
                for row in answerable
            ]
        ),
    }


def group_aggregates(
    rows: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        grouped[str(row[field])].append(row)

    return {
        key: aggregate_metric_rows(value)
        for key, value in sorted(grouped.items())
    }


def run_evaluation(
    *,
    golden_path: Path,
    index_dir: Path,
    report_path: Path,
    split: str,
    top_k: int,
    verify_hashes: bool,
    run_name: str,
) -> int:
    questions = load_jsonl(golden_path)
    validate_golden_set(questions)

    if split != "all":
        questions = [
            question
            for question in questions
            if question["split"] == split
        ]

    if not questions:
        raise EvaluationError(
            f"No questions selected for split={split!r}."
        )

    retriever = BM25Retriever(
        index_dir=index_dir,
        verify_hashes=verify_hashes,
    )

    indexed_ids = {
        str(record["chunk_id"])
        for record in retriever.metadata
    }

    missing: set[str] = set()

    for question in questions:
        for judgment in question["relevance_judgments"]:
            if (
                int(judgment["grade"]) > 0
                and str(judgment["chunk_id"]) not in indexed_ids
            ):
                missing.add(str(judgment["chunk_id"]))

    if missing:
        raise EvaluationError(
            "Positive judgments reference chunks missing from the BM25 "
            "index: "
            + ", ".join(sorted(missing))
        )

    retrieval_k = max(10, top_k)
    per_question: list[dict[str, Any]] = []

    for index, question in enumerate(questions, start=1):
        question_id = str(question["question_id"])
        text = str(question["question"])

        print(
            f"[{index:03d}/{len(questions):03d}] "
            f"{question_id}  {text}"
        )

        results = retriever.search(
            text,
            top_k=retrieval_k,
        )

        retrieved_ids = [
            str(result["chunk_id"])
            for result in results
        ]

        grades = judgments_by_chunk(question)

        if question["answerable"]:
            metrics = {
                "Recall@5": round(
                    recall_at_k(retrieved_ids, grades, 5),
                    6,
                ),
                "Recall@10": round(
                    recall_at_k(retrieved_ids, grades, 10),
                    6,
                ),
                "MRR": round(
                    reciprocal_rank(retrieved_ids, grades),
                    6,
                ),
                "nDCG@5": round(
                    ndcg_at_k(retrieved_ids, grades, 5),
                    6,
                ),
                "nDCG@10": round(
                    ndcg_at_k(retrieved_ids, grades, 10),
                    6,
                ),
            }
            first_rank = first_relevant_rank(
                retrieved_ids,
                grades,
            )
        else:
            metrics = {
                "Recall@5": None,
                "Recall@10": None,
                "MRR": None,
                "nDCG@5": None,
                "nDCG@10": None,
            }
            first_rank = None

        per_question.append(
            {
                "question_id": question_id,
                "question": text,
                "category": question["category"],
                "difficulty": question["difficulty"],
                "split": question["split"],
                "answerable": question["answerable"],
                "positive_judgment_count": sum(
                    grade > 0
                    for grade in grades.values()
                ),
                "first_relevant_rank": first_rank,
                "metrics": metrics,
                "retrieved": [
                    {
                        "rank": int(result["rank"]),
                        "chunk_id": str(result["chunk_id"]),
                        "score": round(float(result["score"]), 8),
                        "document_id": str(result["document_id"]),
                        "section_id": str(result["section_id"]),
                        "domain": str(result["domain"]),
                    }
                    for result in results[:top_k]
                ],
            }
        )

    category_counts = Counter(
        str(question["category"])
        for question in questions
    )
    difficulty_counts = Counter(
        str(question["difficulty"])
        for question in questions
    )
    split_counts = Counter(
        str(question["split"])
        for question in questions
    )

    report = {
        "evaluator_version": EVALUATOR_VERSION,
        "run_name": run_name,
        "golden_set": golden_path.as_posix(),
        "index_dir": index_dir.as_posix(),
        "selected_split": split,
        "retrieval_top_k_recorded": top_k,
        "retriever": retriever.describe(),
        "question_distribution": {
            "category": dict(sorted(category_counts.items())),
            "difficulty": dict(sorted(difficulty_counts.items())),
            "split": dict(sorted(split_counts.items())),
        },
        "overall": aggregate_metric_rows(per_question),
        "by_category": group_aggregates(
            per_question,
            "category",
        ),
        "by_difficulty": group_aggregates(
            per_question,
            "difficulty",
        ),
        "by_split": group_aggregates(
            per_question,
            "split",
        ),
        "per_question": per_question,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    temp = report_path.with_suffix(report_path.suffix + ".tmp")

    try:
        temp.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temp.replace(report_path)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass

    overall = report["overall"]

    print()
    print("-" * 76)
    print("GroundTruth BM25 Retrieval Evaluation")
    print("-" * 76)
    print(f"Run:          {run_name}")
    print(f"Questions:    {overall['question_count']}")
    print(f"Answerable:   {overall['answerable_question_count']}")
    print(f"Recall@5:     {overall['Recall@5']}")
    print(f"Recall@10:    {overall['Recall@10']}")
    print(f"MRR:          {overall['MRR']}")
    print(f"nDCG@5:       {overall['nDCG@5']}")
    print(f"nDCG@10:      {overall['nDCG@10']}")
    print(f"Top-1 hit:    {overall['top1_hit_rate']}")
    print(f"Report:       {report_path}")
    print("Status:       SUCCESS")
    print("-" * 76)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the GroundTruth BM25 retriever against the "
            "graded golden question set."
        )
    )

    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLD_PATH,
        help=f"Golden JSONL. Default: {DEFAULT_GOLD_PATH}",
    )

    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f"BM25 index directory. Default: {DEFAULT_INDEX_DIR}",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Evaluation report path. Default: {DEFAULT_REPORT_PATH}",
    )

    parser.add_argument(
        "--split",
        choices=["all", "dev", "test"],
        default="all",
        help="Evaluate all, dev, or test questions. Default: all",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of retrieved results recorded. Must be >= 10.",
    )

    parser.add_argument(
        "--skip-hash-verification",
        action="store_true",
        help="Skip BM25 artifact SHA-256 verification.",
    )

    parser.add_argument(
        "--run-name",
        default="bm25_100",
        help="Label stored in the report.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.top_k < 10:
        parser.error(
            "--top-k must be at least 10 because Recall@10/nDCG@10 "
            "are benchmark metrics."
        )

    try:
        return run_evaluation(
            golden_path=args.golden,
            index_dir=args.index_dir,
            report_path=args.report_output,
            split=args.split,
            top_k=args.top_k,
            verify_hashes=not args.skip_hash_verification,
            run_name=args.run_name,
        )
    except (EvaluationError, BM25RetrieverError) as exc:
        print()
        print(f"BM25 evaluation failed: {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("BM25 evaluation interrupted.")
        return 130
    except Exception as exc:
        print()
        print(
            "BM25 evaluation failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
