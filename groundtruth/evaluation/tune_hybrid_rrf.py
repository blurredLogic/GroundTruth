from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from groundtruth.retrieval.bm25_retriever import BM25RetrieverError
from groundtruth.retrieval.dense_retriever import DenseRetrieverError
from groundtruth.retrieval.hybrid_retriever import (
    HybridRetriever,
    HybridRetrieverError,
    fuse_rrf,
)

DEFAULT_GOLD = Path("data/evaluation/golden_questions.jsonl")
DEFAULT_DENSE_INDEX = Path("data/index/dense")
DEFAULT_BM25_INDEX = Path("data/index/bm25")
DEFAULT_REPORT = Path("reports/evaluation/hybrid_rrf_dev_tuning.json")

TOP_K = 10
BM25_WEIGHTS = [0.0, 0.10, 0.20, 0.35, 0.50, 0.75, 1.00]
RRF_K_VALUES = [20.0, 60.0, 100.0]
CANDIDATE_K_VALUES = [20, 50, 100]
MAX_RECALL10_REGRESSION = 0.01


class TuningError(RuntimeError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise TuningError(f"Golden set not found: {path}")

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TuningError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc
            if not isinstance(value, dict):
                raise TuningError(
                    f"{path}:{line_number}: expected JSON object."
                )
            rows.append(value)
    return rows


def grades_for(question: dict[str, Any]) -> dict[str, int]:
    return {
        str(j["chunk_id"]): int(j["grade"])
        for j in question["relevance_judgments"]
    }


def recall_at_k(
    retrieved: list[str],
    grades: dict[str, int],
    k: int,
) -> float:
    relevant = {cid for cid, grade in grades.items() if grade > 0}
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
    if ideal == 0.0:
        return 0.0
    return dcg_at_k(retrieved, grades, k) / ideal


def top1_hit(
    retrieved: list[str],
    grades: dict[str, int],
) -> float:
    if not retrieved:
        return 0.0
    return 1.0 if grades.get(retrieved[0], 0) > 0 else 0.0


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def evaluate_rankings(
    question_rows: list[dict[str, Any]],
    rankings: dict[str, list[str]],
) -> dict[str, float]:
    recall5: list[float] = []
    recall10: list[float] = []
    mrr: list[float] = []
    ndcg5: list[float] = []
    ndcg10: list[float] = []
    top1: list[float] = []

    for question in question_rows:
        if not question["answerable"]:
            continue

        qid = str(question["question_id"])
        retrieved = rankings[qid]
        grades = grades_for(question)

        recall5.append(recall_at_k(retrieved, grades, 5))
        recall10.append(recall_at_k(retrieved, grades, 10))
        mrr.append(reciprocal_rank(retrieved, grades))
        ndcg5.append(ndcg_at_k(retrieved, grades, 5))
        ndcg10.append(ndcg_at_k(retrieved, grades, 10))
        top1.append(top1_hit(retrieved, grades))

    return {
        "Recall@5": round(mean(recall5), 6),
        "Recall@10": round(mean(recall10), 6),
        "MRR": round(mean(mrr), 6),
        "nDCG@5": round(mean(ndcg5), 6),
        "nDCG@10": round(mean(ndcg10), 6),
        "Top-1": round(mean(top1), 6),
    }


def config_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    m = row["metrics"]
    return (
        0 if row["eligible"] else 1,
        -m["nDCG@10"],
        -m["MRR"],
        -m["nDCG@5"],
        -m["Recall@10"],
        row["bm25_weight"],
        row["rrf_k"],
        row["candidate_k"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Tune weighted Dense + BM25 RRF on the GroundTruth dev split only."
        )
    )
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--dense-index-dir", type=Path, default=DEFAULT_DENSE_INDEX)
    parser.add_argument("--bm25-index-dir", type=Path, default=DEFAULT_BM25_INDEX)
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda", "mps"],
        default="auto",
    )
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--skip-hash-verification", action="store_true")
    args = parser.parse_args()

    try:
        all_questions = load_jsonl(args.golden)
        dev_questions = [q for q in all_questions if q.get("split") == "dev"]
        answerable_dev = [q for q in dev_questions if q.get("answerable") is True]

        if not dev_questions:
            raise TuningError("No dev questions found.")
        if not answerable_dev:
            raise TuningError("No answerable dev questions found.")

        max_candidate_k = max(CANDIDATE_K_VALUES)

        retriever = HybridRetriever(
            dense_index_dir=args.dense_index_dir,
            bm25_index_dir=args.bm25_index_dir,
            device=args.device,
            candidate_k=max_candidate_k,
            rrf_k=60.0,
            dense_weight=1.0,
            bm25_weight=1.0,
            verify_hashes=not args.skip_hash_verification,
        )

        cache: dict[str, dict[str, list[dict[str, Any]]]] = {}

        print("-" * 80)
        print("GroundTruth Hybrid RRF Dev Tuning")
        print("-" * 80)
        print(f"Dev questions:        {len(dev_questions)}")
        print(f"Answerable dev:       {len(answerable_dev)}")
        print(f"Max candidate depth:  {max_candidate_k}")
        print("Dense query prefix:   OFF")
        print("Caching dense + BM25 rankings once per question...")
        print("-" * 80)

        for index, question in enumerate(dev_questions, start=1):
            qid = str(question["question_id"])
            text = str(question["question"])
            print(f"[{index:02d}/{len(dev_questions):02d}] {qid}")

            cache[qid] = {
                "dense": retriever.dense.search(
                    text,
                    top_k=max_candidate_k,
                ),
                "bm25": retriever.bm25.search(
                    text,
                    top_k=max_candidate_k,
                ),
            }

        dense_rankings = {
            qid: [str(r["chunk_id"]) for r in value["dense"][:TOP_K]]
            for qid, value in cache.items()
        }
        dense_metrics = evaluate_rankings(dev_questions, dense_rankings)
        recall10_floor = max(
            0.0,
            dense_metrics["Recall@10"] - MAX_RECALL10_REGRESSION,
        )

        results: list[dict[str, Any]] = []

        for candidate_k in CANDIDATE_K_VALUES:
            for rrf_k in RRF_K_VALUES:
                for bm25_weight in BM25_WEIGHTS:
                    rankings: dict[str, list[str]] = {}

                    for question in dev_questions:
                        qid = str(question["question_id"])
                        cached = cache[qid]

                        fused = fuse_rrf(
                            dense_results=cached["dense"][:candidate_k],
                            bm25_results=cached["bm25"][:candidate_k],
                            top_k=TOP_K,
                            rrf_k=rrf_k,
                            dense_weight=1.0,
                            bm25_weight=bm25_weight,
                        )

                        rankings[qid] = [
                            str(result["chunk_id"])
                            for result in fused
                        ]

                    metrics = evaluate_rankings(dev_questions, rankings)

                    results.append(
                        {
                            "dense_weight": 1.0,
                            "bm25_weight": bm25_weight,
                            "rrf_k": rrf_k,
                            "candidate_k": candidate_k,
                            "metrics": metrics,
                            "eligible": metrics["Recall@10"] >= recall10_floor,
                            "recall10_delta_vs_dense": round(
                                metrics["Recall@10"] - dense_metrics["Recall@10"],
                                6,
                            ),
                            "mrr_delta_vs_dense": round(
                                metrics["MRR"] - dense_metrics["MRR"],
                                6,
                            ),
                            "ndcg10_delta_vs_dense": round(
                                metrics["nDCG@10"] - dense_metrics["nDCG@10"],
                                6,
                            ),
                        }
                    )

        ranked = sorted(results, key=config_sort_key)
        best = ranked[0]
        eligible_count = sum(1 for row in ranked if row["eligible"])

        report = {
            "tuning_version": "0.1.0",
            "selection_protocol": {
                "split": "dev",
                "test_split_used_for_tuning": False,
                "dense_weight_fixed": 1.0,
                "bm25_weights": BM25_WEIGHTS,
                "rrf_k_values": RRF_K_VALUES,
                "candidate_k_values": CANDIDATE_K_VALUES,
                "max_recall10_regression": MAX_RECALL10_REGRESSION,
                "selection_order": [
                    "Recall@10 regression <= 0.01",
                    "maximize nDCG@10",
                    "maximize MRR",
                    "maximize nDCG@5",
                    "maximize Recall@10",
                    "prefer lower BM25 weight on exact tie",
                ],
            },
            "dev_question_count": len(dev_questions),
            "answerable_dev_question_count": len(answerable_dev),
            "dense_dev_baseline": dense_metrics,
            "recall10_floor": round(recall10_floor, 6),
            "eligible_configuration_count": eligible_count,
            "best_configuration": best,
            "all_configurations_ranked": ranked,
        }

        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        print()
        print("-" * 80)
        print("Dense dev baseline")
        print("-" * 80)
        for key, value in dense_metrics.items():
            print(f"{key:12s} {value}")

        print()
        print(f"Recall@10 eligibility floor: {recall10_floor:.6f}")
        print(f"Eligible configs: {eligible_count}/{len(ranked)}")

        print()
        print("-" * 80)
        print("Top 10 weighted-RRF dev configurations")
        print("-" * 80)
        print(
            "Rank  BM25w  RRFk  Cand  Elig  "
            "R@5      R@10     MRR      nDCG5    nDCG10   Top1"
        )

        for rank, row in enumerate(ranked[:10], start=1):
            m = row["metrics"]
            print(
                f"{rank:>4}  "
                f"{row['bm25_weight']:>5.2f}  "
                f"{row['rrf_k']:>4.0f}  "
                f"{row['candidate_k']:>4}  "
                f"{'Y' if row['eligible'] else 'N':>4}  "
                f"{m['Recall@5']:.6f} "
                f"{m['Recall@10']:.6f} "
                f"{m['MRR']:.6f} "
                f"{m['nDCG@5']:.6f} "
                f"{m['nDCG@10']:.6f} "
                f"{m['Top-1']:.6f}"
            )

        print()
        print("-" * 80)
        print("Selected dev configuration")
        print("-" * 80)
        print(f"Dense weight:  {best['dense_weight']}")
        print(f"BM25 weight:   {best['bm25_weight']}")
        print(f"RRF k:         {best['rrf_k']}")
        print(f"Candidate k:   {best['candidate_k']}")
        print(f"Eligible:      {best['eligible']}")
        print(f"Recall@5:      {best['metrics']['Recall@5']}")
        print(f"Recall@10:     {best['metrics']['Recall@10']}")
        print(f"MRR:           {best['metrics']['MRR']}")
        print(f"nDCG@5:        {best['metrics']['nDCG@5']}")
        print(f"nDCG@10:       {best['metrics']['nDCG@10']}")
        print(f"Top-1:         {best['metrics']['Top-1']}")
        print(f"Report:        {args.report_output}")
        print("Status:        SUCCESS")
        print("-" * 80)

        return 0

    except (
        TuningError,
        HybridRetrieverError,
        DenseRetrieverError,
        BM25RetrieverError,
    ) as exc:
        print()
        print(f"Hybrid tuning failed: {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("Hybrid tuning interrupted.")
        return 130
    except Exception as exc:
        print()
        print(f"Hybrid tuning failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
