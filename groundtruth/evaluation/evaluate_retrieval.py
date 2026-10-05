from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from groundtruth.retrieval.dense_retriever import DenseRetriever, DenseRetrieverError

EVALUATOR_VERSION = "0.1.0"
DEFAULT_GOLD_PATH = Path("data/evaluation/golden_questions.jsonl")
DEFAULT_INDEX_DIR = Path("data/index/dense")
DEFAULT_REPORT_PATH = Path("reports/evaluation/dense_baseline.json")
VALID_CATEGORIES = {
    "direct_factual", "comparison", "scenario_application",
    "multi_hop", "troubleshooting", "negative_near_miss",
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_SPLITS = {"dev", "test"}


class EvaluationError(RuntimeError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise EvaluationError(f"Golden set does not exist: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvaluationError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(obj, dict):
                raise EvaluationError(f"{path}:{line_no}: record must be an object")
            rows.append(obj)
    if not rows:
        raise EvaluationError(f"No questions found in {path}")
    return rows


def validate_question(q: dict[str, Any]) -> None:
    required = {
        "schema_version", "question_id", "question", "category", "difficulty",
        "split", "answerable", "relevance_judgments", "notes",
    }
    missing = required - set(q)
    if missing:
        raise EvaluationError("Golden question missing fields: " + ", ".join(sorted(missing)))
    qid = str(q["question_id"])
    if not str(q["question"]).strip():
        raise EvaluationError(f"{qid}: empty question")
    if q["category"] not in VALID_CATEGORIES:
        raise EvaluationError(f"{qid}: invalid category")
    if q["difficulty"] not in VALID_DIFFICULTIES:
        raise EvaluationError(f"{qid}: invalid difficulty")
    if q["split"] not in VALID_SPLITS:
        raise EvaluationError(f"{qid}: invalid split")
    if not isinstance(q["answerable"], bool):
        raise EvaluationError(f"{qid}: answerable must be boolean")
    judgments = q["relevance_judgments"]
    if not isinstance(judgments, list):
        raise EvaluationError(f"{qid}: relevance_judgments must be a list")
    seen: set[str] = set()
    positives = 0
    for j in judgments:
        if not isinstance(j, dict):
            raise EvaluationError(f"{qid}: judgment must be an object")
        cid = j.get("chunk_id")
        grade = j.get("grade")
        if not isinstance(cid, str) or not cid:
            raise EvaluationError(f"{qid}: invalid chunk_id")
        if cid in seen:
            raise EvaluationError(f"{qid}: duplicate judgment for {cid}")
        seen.add(cid)
        if not isinstance(grade, int) or not 0 <= grade <= 3:
            raise EvaluationError(f"{qid}: grade for {cid} must be 0..3")
        positives += int(grade > 0)
    if q["answerable"] and positives == 0:
        raise EvaluationError(f"{qid}: answerable question has no positive judgments")
    if q["category"] == "negative_near_miss" and q["answerable"]:
        raise EvaluationError(f"{qid}: negative_near_miss must be answerable=false")


def validate_golden_set(rows: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for q in rows:
        validate_question(q)
        qid = str(q["question_id"])
        if qid in seen:
            raise EvaluationError(f"Duplicate question_id: {qid}")
        seen.add(qid)


def grades_for(q: dict[str, Any]) -> dict[str, int]:
    return {str(j["chunk_id"]): int(j["grade"]) for j in q["relevance_judgments"]}


def recall_at_k(ids: list[str], grades: dict[str, int], k: int) -> float:
    relevant = {cid for cid, grade in grades.items() if grade > 0}
    if not relevant:
        return 0.0
    return len(relevant.intersection(ids[:k])) / len(relevant)


def reciprocal_rank(ids: list[str], grades: dict[str, int]) -> float:
    for rank, cid in enumerate(ids, 1):
        if grades.get(cid, 0) > 0:
            return 1.0 / rank
    return 0.0


def dcg_at_k(ids: list[str], grades: dict[str, int], k: int) -> float:
    score = 0.0
    for rank, cid in enumerate(ids[:k], 1):
        grade = grades.get(cid, 0)
        if grade > 0:
            score += ((2 ** grade) - 1) / math.log2(rank + 1)
    return score


def ideal_dcg_at_k(grades: dict[str, int], k: int) -> float:
    ranked = sorted((g for g in grades.values() if g > 0), reverse=True)[:k]
    return sum(((2 ** g) - 1) / math.log2(rank + 1) for rank, g in enumerate(ranked, 1))


def ndcg_at_k(ids: list[str], grades: dict[str, int], k: int) -> float:
    ideal = ideal_dcg_at_k(grades, k)
    return 0.0 if ideal == 0 else dcg_at_k(ids, grades, k) / ideal


def first_relevant_rank(ids: list[str], grades: dict[str, int]) -> int | None:
    for rank, cid in enumerate(ids, 1):
        if grades.get(cid, 0) > 0:
            return rank
    return None


def mean_or_none(values: list[float]) -> float | None:
    return None if not values else round(statistics.fmean(values), 6)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [r for r in rows if r["answerable"]]
    return {
        "question_count": len(rows),
        "answerable_question_count": len(answerable),
        "Recall@5": mean_or_none([r["metrics"]["Recall@5"] for r in answerable]),
        "Recall@10": mean_or_none([r["metrics"]["Recall@10"] for r in answerable]),
        "MRR": mean_or_none([r["metrics"]["MRR"] for r in answerable]),
        "nDCG@5": mean_or_none([r["metrics"]["nDCG@5"] for r in answerable]),
        "nDCG@10": mean_or_none([r["metrics"]["nDCG@10"] for r in answerable]),
        "top1_hit_rate": mean_or_none([1.0 if r["first_relevant_rank"] == 1 else 0.0 for r in answerable]),
    }


def grouped(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {key: aggregate(value) for key, value in sorted(groups.items())}


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def run(args: argparse.Namespace) -> int:
    questions = load_jsonl(args.golden)
    validate_golden_set(questions)
    if args.split != "all":
        questions = [q for q in questions if q["split"] == args.split]
    if not questions:
        raise EvaluationError(f"No questions selected for split={args.split}")

    retriever = DenseRetriever(
        manifest_path=args.index_dir / "index_manifest.json",
        embeddings_path=args.index_dir / "embeddings.npy",
        metadata_path=args.index_dir / "metadata.jsonl",
        device=args.device,
        query_prefix=args.query_prefix,
        use_query_prefix=not args.no_query_prefix,
        verify_hashes=not args.skip_hash_verification,
    )

    indexed = {str(row["chunk_id"]) for row in retriever.metadata}
    missing = sorted({
        str(j["chunk_id"])
        for q in questions
        for j in q["relevance_judgments"]
        if int(j["grade"]) > 0 and str(j["chunk_id"]) not in indexed
    })
    if missing:
        raise EvaluationError("Positive judgments reference chunks absent from the dense index: " + ", ".join(missing))

    retrieval_k = max(args.top_k, 10)
    per_question: list[dict[str, Any]] = []

    for i, q in enumerate(questions, 1):
        qid = str(q["question_id"])
        text = str(q["question"])
        print(f"[{i:03d}/{len(questions):03d}] {qid}  {text}")
        results = retriever.search(text, top_k=retrieval_k)
        ids = [str(r["chunk_id"]) for r in results]
        grades = grades_for(q)

        if q["answerable"]:
            metrics = {
                "Recall@5": round(recall_at_k(ids, grades, 5), 6),
                "Recall@10": round(recall_at_k(ids, grades, 10), 6),
                "MRR": round(reciprocal_rank(ids, grades), 6),
                "nDCG@5": round(ndcg_at_k(ids, grades, 5), 6),
                "nDCG@10": round(ndcg_at_k(ids, grades, 10), 6),
            }
            first_rank = first_relevant_rank(ids, grades)
        else:
            metrics = {"Recall@5": None, "Recall@10": None, "MRR": None, "nDCG@5": None, "nDCG@10": None}
            first_rank = None

        per_question.append({
            "question_id": qid,
            "question": text,
            "category": q["category"],
            "difficulty": q["difficulty"],
            "split": q["split"],
            "answerable": q["answerable"],
            "positive_judgment_count": sum(g > 0 for g in grades.values()),
            "first_relevant_rank": first_rank,
            "metrics": metrics,
            "retrieved": [
                {
                    "rank": int(r["rank"]),
                    "chunk_id": str(r["chunk_id"]),
                    "score": round(float(r["score"]), 8),
                    "document_id": str(r["document_id"]),
                    "section_id": str(r["section_id"]),
                    "domain": str(r["domain"]),
                }
                for r in results[:args.top_k]
            ],
        })

    report = {
        "evaluator_version": EVALUATOR_VERSION,
        "run_name": args.run_name,
        "golden_set": args.golden.as_posix(),
        "index_dir": args.index_dir.as_posix(),
        "selected_split": args.split,
        "retrieval_top_k_recorded": args.top_k,
        "retriever": retriever.describe(),
        "question_distribution": {
            "category": dict(sorted(Counter(str(q["category"]) for q in questions).items())),
            "difficulty": dict(sorted(Counter(str(q["difficulty"]) for q in questions).items())),
            "split": dict(sorted(Counter(str(q["split"]) for q in questions).items())),
        },
        "overall": aggregate(per_question),
        "by_category": grouped(per_question, "category"),
        "by_difficulty": grouped(per_question, "difficulty"),
        "by_split": grouped(per_question, "split"),
        "per_question": per_question,
    }
    write_json_atomic(args.report_output, report)

    overall = report["overall"]
    print()
    print("-" * 76)
    print("GroundTruth Retrieval Evaluation")
    print("-" * 76)
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
    print("-" * 76)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evaluate GroundTruth dense retrieval against graded golden judgments.")
    p.add_argument("--golden", type=Path, default=DEFAULT_GOLD_PATH)
    p.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    p.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_PATH)
    p.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    p.add_argument("--split", choices=["all", "dev", "test"], default="all")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--query-prefix", default=None)
    p.add_argument("--no-query-prefix", action="store_true")
    p.add_argument("--skip-hash-verification", action="store_true")
    p.add_argument("--run-name", default="dense_baseline")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.top_k < 10:
        parser.error("--top-k must be at least 10 because Recall@10/nDCG@10 are benchmark metrics")
    if args.no_query_prefix and args.query_prefix is not None:
        parser.error("--query-prefix and --no-query-prefix cannot be used together")
    try:
        return run(args)
    except (EvaluationError, DenseRetrieverError) as exc:
        print()
        print(f"Evaluation failed: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nEvaluation interrupted.")
        return 130
    except Exception as exc:
        print()
        print(f"Evaluation failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
