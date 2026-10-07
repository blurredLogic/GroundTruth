from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

from groundtruth.retrieval.bm25_retriever import BM25RetrieverError
from groundtruth.retrieval.dense_retriever import DenseRetrieverError
from groundtruth.retrieval.hybrid_retriever import (
    HybridRetriever,
    HybridRetrieverError,
)


EVALUATOR_VERSION = "0.1.0"

DEFAULT_GOLD = Path("data/evaluation/golden_questions.jsonl")
DEFAULT_DENSE_INDEX = Path("data/index/dense")
DEFAULT_BM25_INDEX = Path("data/index/bm25")
DEFAULT_REPORT = Path("reports/evaluation/abstention_v0_1.json")

TOP_K = 2


class AbstentionEvaluationError(RuntimeError):
    """Raised when answerability / abstention evaluation cannot run."""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise AbstentionEvaluationError(
            f"Golden set does not exist: {path}"
        )

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AbstentionEvaluationError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise AbstentionEvaluationError(
                    f"{path}:{line_number}: expected a JSON object."
                )

            rows.append(value)

    if not rows:
        raise AbstentionEvaluationError(
            f"No questions found in {path}"
        )

    return rows


def validate_golden(questions: list[dict[str, Any]]) -> None:
    seen: set[str] = set()

    for question in questions:
        required = {
            "question_id",
            "question",
            "split",
            "answerable",
            "category",
            "relevance_judgments",
        }

        missing = required - set(question)

        if missing:
            raise AbstentionEvaluationError(
                "Golden question missing fields: "
                + ", ".join(sorted(missing))
            )

        question_id = str(question["question_id"])

        if question_id in seen:
            raise AbstentionEvaluationError(
                f"Duplicate question_id: {question_id}"
            )

        seen.add(question_id)

        if question["split"] not in {"dev", "test"}:
            raise AbstentionEvaluationError(
                f"{question_id}: split must be dev or test."
            )

        if not isinstance(question["answerable"], bool):
            raise AbstentionEvaluationError(
                f"{question_id}: answerable must be boolean."
            )

        if question["category"] == "negative_near_miss":
            if question["answerable"]:
                raise AbstentionEvaluationError(
                    f"{question_id}: negative_near_miss must be unanswerable."
                )

            if any(
                int(judgment["grade"]) > 0
                for judgment in question["relevance_judgments"]
            ):
                raise AbstentionEvaluationError(
                    f"{question_id}: negative query has positive gold."
                )


def auc_pairwise(
    rows: list[dict[str, Any]],
) -> float | None:
    positives = [
        float(row["confidence"])
        for row in rows
        if row["answerable"]
    ]

    negatives = [
        float(row["confidence"])
        for row in rows
        if not row["answerable"]
    ]

    if not positives or not negatives:
        return None

    wins = 0.0
    pairs = len(positives) * len(negatives)

    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5

    return round(wins / pairs, 6)


def confusion_at_threshold(
    rows: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    tp = 0
    fn = 0
    tn = 0
    fp = 0

    for row in rows:
        predicted_answerable = (
            float(row["confidence"]) >= threshold
        )

        if row["answerable"]:
            if predicted_answerable:
                tp += 1
            else:
                fn += 1
        else:
            if predicted_answerable:
                fp += 1
            else:
                tn += 1

    positive_count = tp + fn
    negative_count = tn + fp

    tpr = (
        tp / positive_count
        if positive_count
        else 0.0
    )

    tnr = (
        tn / negative_count
        if negative_count
        else 0.0
    )

    balanced_accuracy = (tpr + tnr) / 2.0

    accuracy = (
        (tp + tn) / len(rows)
        if rows
        else 0.0
    )

    return {
        "threshold": threshold,
        "tp_answerable": tp,
        "fn_answerable": fn,
        "tn_negative": tn,
        "fp_negative": fp,
        "answerable_recall": round(tpr, 6),
        "negative_rejection_rate": round(tnr, 6),
        "negative_false_positive_rate": round(1.0 - tnr, 6),
        "balanced_accuracy": round(balanced_accuracy, 6),
        "accuracy": round(accuracy, 6),
    }


def candidate_thresholds(
    rows: list[dict[str, Any]],
) -> list[float]:
    scores = sorted(
        {
            float(row["confidence"])
            for row in rows
        }
    )

    if not scores:
        return []

    thresholds: list[float] = [
        scores[0] - 1e-12,
    ]

    for left, right in zip(
        scores,
        scores[1:],
    ):
        thresholds.append(
            (left + right) / 2.0
        )

    thresholds.append(
        scores[-1] + 1e-12
    )

    return thresholds


def select_threshold(
    dev_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    thresholds = candidate_thresholds(
        dev_rows
    )

    if not thresholds:
        raise AbstentionEvaluationError(
            "No dev confidence scores available."
        )

    evaluated = [
        confusion_at_threshold(
            dev_rows,
            threshold,
        )
        for threshold in thresholds
    ]

    # Selection is dev-only:
    # 1. Maximize balanced accuracy.
    # 2. Prefer better rejection of unsupported queries.
    # 3. Prefer better recall on answerable queries.
    # 4. Prefer the higher threshold on exact ties.
    best = max(
        evaluated,
        key=lambda row: (
            row["balanced_accuracy"],
            row["negative_rejection_rate"],
            row["answerable_recall"],
            row["threshold"],
        ),
    )

    return best


def score_summary(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    answerable = [
        float(row["confidence"])
        for row in rows
        if row["answerable"]
    ]

    negatives = [
        float(row["confidence"])
        for row in rows
        if not row["answerable"]
    ]

    def summarize(
        values: list[float],
    ) -> dict[str, float | None]:
        if not values:
            return {
                "min": None,
                "mean": None,
                "median": None,
                "max": None,
            }

        return {
            "min": round(min(values), 8),
            "mean": round(statistics.fmean(values), 8),
            "median": round(statistics.median(values), 8),
            "max": round(max(values), 8),
        }

    return {
        "answerable": summarize(answerable),
        "negative_near_miss": summarize(negatives),
    }


def evaluate_system(
    *,
    system_name: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dev_rows = [
        row
        for row in rows
        if row["split"] == "dev"
    ]

    test_rows = [
        row
        for row in rows
        if row["split"] == "test"
    ]

    dev_selection = select_threshold(
        dev_rows
    )

    threshold = float(
        dev_selection["threshold"]
    )

    test_metrics = confusion_at_threshold(
        test_rows,
        threshold,
    )

    all_metrics = confusion_at_threshold(
        rows,
        threshold,
    )

    negative_test_details = []

    for row in test_rows:
        if row["answerable"]:
            continue

        rejected = (
            float(row["confidence"])
            < threshold
        )

        negative_test_details.append(
            {
                "question_id": row["question_id"],
                "question": row["question"],
                "confidence": round(
                    float(row["confidence"]),
                    8,
                ),
                "threshold": round(
                    threshold,
                    8,
                ),
                "rejected_as_unanswerable": rejected,
                "top1_chunk_id": row["top1_chunk_id"],
                "top1_document_id": row["top1_document_id"],
                "top1_domain": row["top1_domain"],
            }
        )

    negative_test_details.sort(
        key=lambda row: (
            -float(row["confidence"]),
            row["question_id"],
        )
    )

    return {
        "system": system_name,
        "confidence_signal": "top1_retrieval_score",
        "dev": {
            "question_count": len(dev_rows),
            "answerable_count": sum(
                row["answerable"]
                for row in dev_rows
            ),
            "negative_count": sum(
                not row["answerable"]
                for row in dev_rows
            ),
            "auroc": auc_pairwise(dev_rows),
            "score_summary": score_summary(dev_rows),
            "selected_threshold": dev_selection,
        },
        "test": {
            "question_count": len(test_rows),
            "answerable_count": sum(
                row["answerable"]
                for row in test_rows
            ),
            "negative_count": sum(
                not row["answerable"]
                for row in test_rows
            ),
            "auroc": auc_pairwise(test_rows),
            "score_summary": score_summary(test_rows),
            "threshold_from_dev": round(threshold, 10),
            "threshold_metrics": test_metrics,
            "negative_queries": negative_test_details,
        },
        "all_questions_at_dev_threshold": all_metrics,
    }


def top_result_fields(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    if not results:
        return {
            "confidence": 0.0,
            "top1_chunk_id": None,
            "top1_document_id": None,
            "top1_domain": None,
        }

    top = results[0]

    return {
        "confidence": float(top["score"]),
        "top1_chunk_id": str(top["chunk_id"]),
        "top1_document_id": str(top["document_id"]),
        "top1_domain": str(top["domain"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate answerability / abstention behavior for "
            "GroundTruth Dense v0.1, BM25 v0.1, and Hybrid RRF v0.2."
        )
    )

    parser.add_argument(
        "--golden",
        type=Path,
        default=DEFAULT_GOLD,
    )

    parser.add_argument(
        "--dense-index-dir",
        type=Path,
        default=DEFAULT_DENSE_INDEX,
    )

    parser.add_argument(
        "--bm25-index-dir",
        type=Path,
        default=DEFAULT_BM25_INDEX,
    )

    parser.add_argument(
        "--device",
        choices=[
            "auto",
            "cpu",
            "cuda",
            "mps",
        ],
        default="auto",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT,
    )

    parser.add_argument(
        "--skip-hash-verification",
        action="store_true",
    )

    args = parser.parse_args()

    try:
        questions = load_jsonl(
            args.golden
        )

        validate_golden(
            questions
        )

        dev_negative_count = sum(
            question["split"] == "dev"
            and not question["answerable"]
            for question in questions
        )

        test_negative_count = sum(
            question["split"] == "test"
            and not question["answerable"]
            for question in questions
        )

        print("-" * 80)
        print("GroundTruth Answerability / Abstention Evaluation")
        print("-" * 80)
        print(f"Questions:          {len(questions)}")
        print(f"Dev negatives:      {dev_negative_count}")
        print(f"Test negatives:     {test_negative_count}")
        print("Dense prefix:       OFF")
        print("Hybrid config:      dense=1.0, bm25=0.1, RRF k=20, candidate_k=20")
        print("Confidence signal:  top-1 retrieval score")
        print("-" * 80)

        # Instantiate the frozen hybrid once, then reuse its component
        # retrievers so Dense, BM25, and Hybrid use exactly the same indexes.
        hybrid = HybridRetriever(
            dense_index_dir=args.dense_index_dir,
            bm25_index_dir=args.bm25_index_dir,
            device=args.device,
            candidate_k=20,
            rrf_k=20.0,
            dense_weight=1.0,
            bm25_weight=0.1,
            verify_hashes=not args.skip_hash_verification,
        )

        system_rows: dict[
            str,
            list[dict[str, Any]],
        ] = {
            "dense_v0_1": [],
            "bm25_v0_1": [],
            "hybrid_rrf_v0_2": [],
        }

        for index, question in enumerate(
            questions,
            start=1,
        ):
            question_id = str(
                question["question_id"]
            )

            query = str(
                question["question"]
            )

            print(
                f"[{index:03d}/{len(questions):03d}] "
                f"{question_id}"
            )

            dense_results = hybrid.dense.search(
                query,
                top_k=TOP_K,
            )

            bm25_results = hybrid.bm25.search(
                query,
                top_k=TOP_K,
            )

            hybrid_results = hybrid.search(
                query,
                top_k=TOP_K,
            )

            for system_name, results in (
                ("dense_v0_1", dense_results),
                ("bm25_v0_1", bm25_results),
                ("hybrid_rrf_v0_2", hybrid_results),
            ):
                row = {
                    "question_id": question_id,
                    "question": query,
                    "split": question["split"],
                    "category": question["category"],
                    "answerable": question["answerable"],
                }

                row.update(
                    top_result_fields(
                        results
                    )
                )

                system_rows[
                    system_name
                ].append(
                    row
                )

        systems = {
            name: evaluate_system(
                system_name=name,
                rows=rows,
            )
            for name, rows in system_rows.items()
        }

        report = {
            "evaluator_version": EVALUATOR_VERSION,
            "task": "answerability_abstention",
            "confidence_signal": "top1_retrieval_score",
            "threshold_protocol": {
                "threshold_selected_on": "dev",
                "test_used_for_threshold_selection": False,
                "selection_metric": "balanced_accuracy",
                "tie_breakers": [
                    "negative_rejection_rate",
                    "answerable_recall",
                    "higher_threshold",
                ],
                "prediction_rule": (
                    "answerable if top1 retrieval score >= threshold"
                ),
            },
            "benchmark": {
                "question_count": len(questions),
                "answerable_count": sum(
                    question["answerable"]
                    for question in questions
                ),
                "negative_count": sum(
                    not question["answerable"]
                    for question in questions
                ),
                "dev_negative_count": dev_negative_count,
                "test_negative_count": test_negative_count,
            },
            "systems": systems,
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

        print()
        print("-" * 100)
        print("Held-out TEST abstention results")
        print("-" * 100)
        print(
            "System             "
            "AUROC     Threshold     AnsRecall   NegReject   NegFPR      BalAcc"
        )

        for system_name in (
            "dense_v0_1",
            "bm25_v0_1",
            "hybrid_rrf_v0_2",
        ):
            result = systems[
                system_name
            ]

            test = result[
                "test"
            ]

            metrics = test[
                "threshold_metrics"
            ]

            threshold = test[
                "threshold_from_dev"
            ]

            print(
                f"{system_name:18s} "
                f"{str(test['auroc']):>8s} "
                f"{threshold:>13.8f} "
                f"{metrics['answerable_recall']:>11.6f} "
                f"{metrics['negative_rejection_rate']:>11.6f} "
                f"{metrics['negative_false_positive_rate']:>11.6f} "
                f"{metrics['balanced_accuracy']:>11.6f}"
            )

        print()
        print("-" * 100)
        print("Held-out negative queries")
        print("-" * 100)

        for system_name in (
            "dense_v0_1",
            "bm25_v0_1",
            "hybrid_rrf_v0_2",
        ):
            print()
            print(system_name)

            for row in systems[
                system_name
            ]["test"]["negative_queries"]:
                decision = (
                    "REJECT"
                    if row[
                        "rejected_as_unanswerable"
                    ]
                    else "FALSE POSITIVE"
                )

                print(
                    f"  {row['question_id']} "
                    f"score={row['confidence']:.8f} "
                    f"threshold={row['threshold']:.8f} "
                    f"{decision} "
                    f"top1={row['top1_chunk_id']}"
                )

        print()
        print(f"Report: {args.report_output}")
        print("Status: SUCCESS")
        print("-" * 100)

        return 0

    except (
        AbstentionEvaluationError,
        HybridRetrieverError,
        DenseRetrieverError,
        BM25RetrieverError,
    ) as exc:
        print()
        print(
            f"Abstention evaluation failed: {exc}"
        )
        return 1

    except KeyboardInterrupt:
        print()
        print(
            "Abstention evaluation interrupted."
        )
        return 130

    except Exception as exc:
        print()
        print(
            "Abstention evaluation failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
