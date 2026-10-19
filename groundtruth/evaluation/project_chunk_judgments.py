"""Project human-reviewed baseline chunk labels onto a new token-span chunking.

This is an APPROXIMATION, not new human relevance annotation. The human
judgments are tied to the original 512-token chunks, not minimal evidence spans.
For stronger comparisons, use section-level evaluation alongside this projection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


class ProjectionError(RuntimeError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ProjectionError(f"Missing input file: {path}")
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ProjectionError(f"{path}:{line_number}: {exc}") from exc
                if not isinstance(record, dict):
                    raise ProjectionError(f"{path}:{line_number}: expected JSON object")
                records.append(record)
    if not records:
        raise ProjectionError(f"No records in {path}")
    return records


def span(chunk: dict[str, Any]) -> tuple[int, int]:
    try:
        start = int(chunk["section_token_start"])
        end = int(chunk["section_token_end_exclusive"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"Missing or invalid token span: {chunk.get('chunk_id')}") from exc
    if not (0 <= start < end):
        raise ProjectionError(f"Invalid token span for {chunk.get('chunk_id')}: {start}:{end}")
    return start, end


def hash_text(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for data in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(data)
    return "sha256:" + digest.hexdigest()


def build_chunk_lookup(chunks: list[dict[str, Any]], label: str):
    by_id: dict[str, dict[str, Any]] = {}
    by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        cid = str(chunk["chunk_id"])
        if cid in by_id:
            raise ProjectionError(f"Duplicate {label} chunk_id: {cid}")
        span(chunk)
        by_id[cid] = chunk
        by_section[str(chunk["section_id"])].append(chunk)
    for rows in by_section.values():
        rows.sort(key=lambda c: (span(c)[0], span(c)[1], c["chunk_id"]))
    return by_id, by_section


def project(
    questions: list[dict[str, Any]],
    baseline_chunks: list[dict[str, Any]],
    target_chunks: list[dict[str, Any]],
    *,
    min_shorter_overlap: float = 0.5,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not (0 < min_shorter_overlap <= 1):
        raise ProjectionError("--min-shorter-overlap must be within (0, 1]")
    baseline_by_id, _ = build_chunk_lookup(baseline_chunks, "baseline")
    _, target_by_section = build_chunk_lookup(target_chunks, "target")

    projection_rows: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    expanded_evidence = 0
    no_candidates: list[str] = []
    source_grade_zero = 0
    for original in questions:
        q = dict(original)
        qid = str(q["question_id"])
        if qid in seen_questions:
            raise ProjectionError(f"Duplicate question ID: {qid}")
        seen_questions.add(qid)
        best_grades: dict[str, int] = {}
        sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for judged in original["relevance_judgments"]:
            cid = str(judged["chunk_id"])
            grade = int(judged["grade"])
            if grade == 0:
                source_grade_zero += 1
                continue  # absence from positive judgments is interpreted as zero
            old_chunk = baseline_by_id.get(cid)
            if old_chunk is None:
                raise ProjectionError(f"{qid}: baseline judgment missing chunk {cid}")
            old_start, old_end = span(old_chunk)
            section = str(old_chunk["section_id"])
            alternatives = target_by_section.get(section, [])
            matches: list[tuple[float, dict[str, Any], int]] = []
            for new_chunk in alternatives:
                if old_chunk.get("section_content_sha256") != new_chunk.get("section_content_sha256"):
                    raise ProjectionError(
                        f"{qid}: content hash mismatch between baseline and target section {section}"
                    )
                new_start, new_end = span(new_chunk)
                overlap = max(0, min(old_end, new_end) - max(old_start, new_start))
                if overlap == 0:
                    continue
                ratio = overlap / min(old_end - old_start, new_end - new_start)
                if ratio >= min_shorter_overlap:
                    matches.append((ratio, new_chunk, overlap))
            if not matches:
                no_candidates.append(f"{qid}: {cid} (grade {grade}, section {section})")
                continue
            expanded_evidence += max(0, len(matches) - 1)
            for ratio, target, overlap in matches:
                tid = str(target["chunk_id"])
                best_grades[tid] = max(best_grades.get(tid, 0), grade)
                sources[tid].append({
                    "baseline_chunk_id": cid,
                    "baseline_grade": grade,
                    "token_overlap": overlap,
                    "fraction_of_shorter_span": round(ratio, 6),
                })
        if bool(q["answerable"]) and not best_grades:
            no_candidates.append(f"{qid}: all positive evidence lost")
        if not bool(q["answerable"]) and best_grades:
            raise ProjectionError(f"{qid}: unanswerable question has positive labels")
        q["relevance_judgments"] = [
            {
                "chunk_id": cid,
                "grade": grade,
                "rationale": "Automatically projected from baseline section token-span overlap; requires human review.",
            }
            for cid, grade in sorted(best_grades.items())
        ]
        results.append(q)
        projection_rows.append({
            "question_id": qid,
            "answerable": bool(q["answerable"]),
            "baseline_positive_count": sum(int(j["grade"]) > 0 for j in original["relevance_judgments"]),
            "projected_positive_count": len(best_grades),
            "matches": [
                {"target_chunk_id": cid, "assigned_grade": best_grades[cid], "sources": sources[cid]}
                for cid in sorted(best_grades)
            ],
        })
    if no_candidates:
        summary = "\n".join(no_candidates[:30])
        raise ProjectionError(
            f"Unresolved evidence projections ({len(no_candidates)}). Nothing written.\n{summary}"
        )
    report = {
        "projection_version": "0.1.0",
        "status": "SUCCESS",
        "warning": (
            "Weak labels only: token-span overlap with an older judged chunk is not proof "
            "that a different chunk contains the exact answer. Use section-level evaluation "
            "as the more annotation-invariant primary comparison; manually audit before publishing."
        ),
        "method": "same-section token span; overlap / shorter_span >= threshold; max grade on collisions",
        "min_shorter_overlap": min_shorter_overlap,
        "questions": len(questions),
        "answerable": sum(bool(q["answerable"]) for q in questions),
        "negative": sum(not bool(q["answerable"]) for q in questions),
        "ignored_baseline_grade_zero_judgments": source_grade_zero,
        "additional_matches_from_one_to_many_projection": expanded_evidence,
        "per_question": projection_rows,
    }
    return results, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=Path("data/evaluation/golden_questions.jsonl"))
    parser.add_argument("--baseline-chunks", type=Path, default=Path("data/index/chunks_indexable.jsonl"))
    parser.add_argument("--target-chunks", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--min-shorter-overlap", type=float, default=0.5)
    args = parser.parse_args()
    if args.output.resolve() == args.golden.resolve():
        parser.error("Refusing to overwrite the human-reviewed baseline golden set")
    if args.target_chunks.resolve() == args.baseline_chunks.resolve():
        parser.error("Target indexable corpus must be distinct from baseline")
    try:
        questions = load_jsonl(args.golden)
        baseline = load_jsonl(args.baseline_chunks)
        target = load_jsonl(args.target_chunks)
        converted, report = project(
            questions, baseline, target, min_shorter_overlap=args.min_shorter_overlap
        )
        report["inputs"] = {
            "golden_sha256": hash_text(args.golden),
            "baseline_chunks_sha256": hash_text(args.baseline_chunks),
            "target_chunks_sha256": hash_text(args.target_chunks),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            "\n".join(json.dumps(q, sort_keys=True, ensure_ascii=False) for q in converted) + "\n",
            encoding="utf-8", newline="\n",
        )
        args.report_output.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        print(f"Projected {len(converted)} questions into {args.output}")
        print(f"Projection audit: {args.report_output}")
        print("WARNING: Projected judgments are weak labels, not human-reviewed ground truth.")
        return 0
    except (OSError, ValueError, KeyError, ProjectionError) as exc:
        print(f"Projection FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
