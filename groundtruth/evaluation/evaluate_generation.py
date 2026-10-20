"""DEV-first answer-generation evaluation with deterministic checks and human review CSV.

Does not pretend citation IDs prove semantic entailment or factual correctness.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any

from groundtruth.generation.grounded_qa import (
    GenerationError,
    RETRIEVER_CONFIG,
    add_backend_arguments,
    build_service,
)


def load_questions(path: Path, split: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise GenerationError(f"Golden set missing: {path}")
    questions: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as stream:
        for lineno, line in enumerate(stream, 1):
            if not line.strip():
                continue
            question = json.loads(line)
            for field in ("question", "question_id", "split", "answerable", "relevance_judgments"):
                if field not in question:
                    raise GenerationError(f"Golden line {lineno} missing {field}")
            if question["question_id"] in seen:
                raise GenerationError(f"Duplicate question ID {question['question_id']}")
            seen.add(question["question_id"])
            if question["split"] == split:
                questions.append(question)
    if not questions:
        raise GenerationError(f"No questions found with split={split}")
    return questions


def safe_fraction(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _status(row: dict[str, Any]) -> str:
    return str(row.get("status") or ("abstained" if row.get("abstained") else "answered"))


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    positive = [r for r in records if r["answerable"]]
    negative = [r for r in records if not r["answerable"]]
    answered = [r for r in records if _status(r) == "answered"]
    failures = [r for r in records if _status(r) == "generation_error"]
    return {
        "questions": len(records),
        "answerable": len(positive),
        "negative": len(negative),
        "successful_generations": len(records) - len(failures),
        "generation_failure_count": len(failures),
        "generation_failure_rate": safe_fraction(len(failures), len(records)),
        "answerable_answer_rate": safe_fraction(sum(_status(r) == "answered" for r in positive), len(positive)),
        "answerable_false_abstention_rate": safe_fraction(sum(_status(r) in ("abstained", "no_evidence") for r in positive), len(positive)),
        "answerable_generation_failure_rate": safe_fraction(sum(_status(r) == "generation_error" for r in positive), len(positive)),
        "negative_abstention_rate": safe_fraction(sum(_status(r) in ("abstained", "no_evidence") for r in negative), len(negative)),
        "negative_false_answer_rate": safe_fraction(sum(_status(r) == "answered" for r in negative), len(negative)),
        "negative_generation_failure_rate": safe_fraction(sum(_status(r) == "generation_error" for r in negative), len(negative)),
        "answers_with_valid_citation_syntax": safe_fraction(sum(bool(r.get("citations")) for r in answered), len(answered)),
        "retrieved_gold_hit_rate_answerable": safe_fraction(sum(bool(r.get("retrieved_gold_hit")) for r in positive), len(positive)),
        "cited_gold_hit_rate_answerable": safe_fraction(sum(bool(r.get("cited_gold_hit")) for r in positive), len(positive)),
        "manual_correctness_and_groundedness": "NOT_SCORED_REQUIRES_HUMAN_REVIEW",
    }


def evaluation_record(question: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    relevant = {
        str(judgment["chunk_id"])
        for judgment in question["relevance_judgments"]
        if int(judgment["grade"]) > 0
    }
    retrieved_ids = {passage["chunk_id"] for passage in output["sources"]}
    cited_ids = {passage["chunk_id"] for passage in output["sources"] if passage["cited"]}
    return {
        "question_id": question["question_id"],
        "question": question["question"],
        "split": question["split"],
        "category": question.get("category"),
        "answerable": bool(question["answerable"]),
        "reference_answer": question.get("reference_answer"),
        "status": output["status"],
        "error": None,
        "debug_trace_path": None,
        "abstained": bool(output["abstained"]),
        "answer": output["answer"],
        "citations": output["citations"],
        "cited_chunks": sorted(cited_ids),
        "retrieved_gold_hit": bool(relevant & retrieved_ids),
        "cited_gold_hit": bool(relevant & cited_ids),
        "sources": output["sources"],
        "generation": output["generation"],
    }


def write_human_review(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "question_id", "split", "answerable", "status", "error", "question", "reference_answer",
        "generated_answer", "cited_chunks", "cited_urls", "review_correct_0_1",
        "review_grounded_0_2", "review_citations_support_claims_0_2", "review_notes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "question_id": row["question_id"],
                "split": row["split"],
                "answerable": row["answerable"],
                "status": _status(row),
                "error": row.get("error") or "",
                "question": row["question"],
                "reference_answer": row["reference_answer"] or "",
                "generated_answer": row["answer"],
                "cited_chunks": "; ".join(row["cited_chunks"]),
                "cited_urls": "; ".join(dict.fromkeys(p["source_url"] for p in row["sources"] if p["cited"])),
                "review_correct_0_1": "",
                "review_grounded_0_2": "",
                "review_citations_support_claims_0_2": "",
                "review_notes": "",
            })


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def failure_record(question: dict[str, Any], exc: GenerationError, debug_path: Path) -> dict[str, Any]:
    return {
        "question_id": str(question["question_id"]),
        "question": question["question"],
        "split": question["split"],
        "category": question.get("category"),
        "answerable": bool(question["answerable"]),
        "reference_answer": question.get("reference_answer"),
        "status": "generation_error",
        "error": str(exc),
        "debug_trace_path": str(debug_path) if debug_path.exists() else None,
        "abstained": None,  # Failure is neither an answer nor an abstention.
        "answer": "",
        "citations": [],
        "cited_chunks": [],
        "retrieved_gold_hit": None,
        "cited_gold_hit": None,
        "sources": [],
        "generation": {},
    }


def run_fingerprint(questions: list[dict[str, Any]], qa: Any, args: Any) -> str:
    configuration = {
        "golden_sha256": hashlib.sha256(args.golden.read_bytes()).hexdigest(),
        "questions": [(q["question_id"], q["question"], q["answerable"]) for q in questions],
        "split": args.split,
        "backend": qa.backend_label,
        "model": qa.model_label,
        "top_k": qa.top_k,
        "validation_retries": qa.validation_retries,
        "device": args.device,
        "dense_index_dir": str(args.dense_index_dir.resolve()),
        "bm25_index_dir": str(args.bm25_index_dir.resolve()),
        "ollama_url": args.ollama_url if args.backend == "ollama" else None,
        "retriever_config": RETRIEVER_CONFIG,
    }
    return hashlib.sha256(json.dumps(configuration, sort_keys=True).encode("utf-8")).hexdigest()


def evaluate_with_checkpoint(
    questions: list[dict[str, Any]], qa: Any, checkpoint: Path,
    fingerprint: str, resume: bool, debug_dir: Path,
) -> list[dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    if resume:
        if not checkpoint.exists():
            raise GenerationError(f"Cannot --resume: checkpoint not found: {checkpoint}")
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if saved.get("fingerprint") != fingerprint:
            raise GenerationError("Checkpoint doesn't match selected model/questions/settings; rerun without --resume.")
        cache = {str(row["question_id"]): row for row in saved["per_question"]}

    for idx, question in enumerate(questions, 1):
        qid = str(question["question_id"])
        previous = cache.get(qid)
        if previous and _status(previous) != "generation_error":
            print(f"[{idx:03d}/{len(questions):03d}] {qid} CACHED", flush=True)
            continue
        print(f"[{idx:03d}/{len(questions):03d}] {qid}", flush=True)
        debug_path = debug_dir / f"{qid}_invalid.json"
        qa.debug_output = debug_path
        # Never report a stale trace from an older attempt as a new failure.
        if debug_path.exists():
            debug_path.unlink()
        try:
            record = evaluation_record(question, qa.ask(str(question["question"])))
        except GenerationError as exc:
            record = failure_record(question, exc, debug_path)
            print(f"  GENERATION FAILURE (recorded): {exc}", flush=True)
        cache[qid] = record
        ordered = [cache[str(q["question_id"])] for q in questions if str(q["question_id"]) in cache]
        atomic_json(checkpoint, {"schema_version": "generation_checkpoint_v0.2", "fingerprint": fingerprint, "per_question": ordered})
    return [cache[str(q["question_id"])] for q in questions]


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV-first GroundTruth cited-answer evaluation")
    parser.add_argument("--golden", type=Path, default=Path("data/evaluation/golden_questions.jsonl"))
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--limit", type=int, default=None, help="Smoke-test N questions; omit for complete split")
    parser.add_argument("--report-output", type=Path, default=Path("reports/generation/grounded_qa_dev.json"))
    parser.add_argument("--review-output", type=Path, default=Path("reports/generation/human_review_dev.csv"))
    parser.add_argument("--checkpoint-output", type=Path, default=None)
    parser.add_argument("--resume", action="store_true", help="Reuse valid question results; retry any errors")
    parser.add_argument("--debug-dir", type=Path, default=Path("reports/generation/debug_failures"))
    add_backend_arguments(parser)
    args = parser.parse_args()
    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be positive")

    try:
        questions = load_questions(args.golden, args.split)
        if args.limit is not None:
            questions = questions[:args.limit]
        qa = build_service(args)
        checkpoint = args.checkpoint_output or Path(f"reports/generation/checkpoint_{args.split}.json")
        fingerprint = run_fingerprint(questions, qa, args)
        rows = evaluate_with_checkpoint(questions, qa, checkpoint, fingerprint, args.resume, args.debug_dir)
        summary = summarize(rows)
        report = {
            "schema_version": "generation_eval_v0.2",
            "checkpoint": str(checkpoint),
            "run_fingerprint": fingerprint,
            "split": args.split,
            "limited_run": args.limit is not None,
            "model": qa.model_label,
            "backend": qa.backend_label,
            "top_k": args.top_k,
            "summary": summary,
            "per_question": rows,
            "limitations": [
                "Valid citation markers do not establish that claims are supported.",
                "Gold citation overlap is a proxy, not factual-answer correctness.",
                "Some reference answers are missing; manual review is required.",
                "Generation errors are counted separately, not as abstentions.",
                "The negative set is small and cannot calibrate production abstention.",
            ],
        }
        atomic_json(args.report_output, report)
        write_human_review(args.review_output, rows)
        print("\nGroundTruth generation DEV summary")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        print(f"Report: {args.report_output}")
        print(f"Manual review: {args.review_output}")
        print(f"Checkpoint: {checkpoint}")
        if summary["generation_failure_count"]:
            print("Status: PARTIAL (failures recorded; run again with --resume)")
            return 2
        print("Status: SUCCESS (automatic checks only; factual review pending)")
        return 0
    except (GenerationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Generation evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
