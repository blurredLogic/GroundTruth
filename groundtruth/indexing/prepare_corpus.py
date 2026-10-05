from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PREPARATION_VERSION = "0.1.0"

DEFAULT_INPUT_PATH = Path("data/processed/chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/index/chunks_indexable.jsonl")
DEFAULT_REPORT_PATH = Path("reports/corpus_preparation_report.json")

DEFAULT_MIN_HEADING_ONLY_TOKENS = 32

HEADING_ONLY_RE = re.compile(
    r"^\s*#{1,6}\s+\S.*?\s*$",
    flags=re.DOTALL,
)


class CorpusPreparationError(RuntimeError):
    """Raised when corpus preparation cannot be completed safely."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        temp_path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise CorpusPreparationError(
            f"Input file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CorpusPreparationError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise CorpusPreparationError(
                    f"{path}:{line_number}: each JSONL line must "
                    "contain an object."
                )

            records.append(value)

    if not records:
        raise CorpusPreparationError(
            f"No chunk records found in {path}"
        )

    return records


def validate_chunk_record(
    chunk: dict[str, Any],
) -> None:
    required_fields = {
        "chunk_id",
        "document_id",
        "section_id",
        "domain",
        "section_title",
        "heading_path",
        "chunk_index",
        "text",
        "token_count",
        "tokenizer",
        "source_url",
        "content_sha256",
        "section_content_sha256",
        "source_document_content_sha256",
        "chunking_config_sha256",
        "corpus_version",
    }

    missing = required_fields - set(chunk)

    if missing:
        raise CorpusPreparationError(
            "Chunk is missing required fields: "
            + ", ".join(sorted(missing))
        )

    chunk_id = chunk["chunk_id"]

    if not isinstance(chunk_id, str) or not chunk_id.strip():
        raise CorpusPreparationError(
            "Chunk has an invalid chunk_id."
        )

    text = chunk["text"]

    if not isinstance(text, str) or not text.strip():
        raise CorpusPreparationError(
            f"{chunk_id}: text must be a non-empty string."
        )

    token_count = chunk["token_count"]

    if not isinstance(token_count, int) or token_count < 0:
        raise CorpusPreparationError(
            f"{chunk_id}: token_count must be a non-negative integer."
        )

    heading_path = chunk["heading_path"]

    if (
        not isinstance(heading_path, list)
        or not heading_path
        or not all(
            isinstance(item, str) and item.strip()
            for item in heading_path
        )
    ):
        raise CorpusPreparationError(
            f"{chunk_id}: heading_path must be a non-empty "
            "list of non-empty strings."
        )

    content_sha256 = chunk["content_sha256"]

    if (
        not isinstance(content_sha256, str)
        or not content_sha256.startswith("sha256:")
    ):
        raise CorpusPreparationError(
            f"{chunk_id}: invalid content_sha256."
        )

    expected_hash = "sha256:" + sha256_text(text)

    if content_sha256 != expected_hash:
        raise CorpusPreparationError(
            f"{chunk_id}: content_sha256 does not match text."
        )


def is_heading_only(text: str) -> bool:
    """
    Return True only when the entire chunk contains exactly one Markdown
    heading and no body content.

    Examples:
        ## Services
        #### Note:

    Non-example:
        ## Services

        Services provide a stable network endpoint...
    """
    stripped = text.strip()

    if not stripped:
        return False

    nonempty_lines = [
        line.strip()
        for line in stripped.splitlines()
        if line.strip()
    ]

    if len(nonempty_lines) != 1:
        return False

    return HEADING_ONLY_RE.fullmatch(
        nonempty_lines[0]
    ) is not None


def build_quality_flags(
    *,
    chunk: dict[str, Any],
    minimum_heading_only_tokens: int,
) -> list[str]:
    flags: list[str] = []

    text = str(chunk["text"])
    token_count = int(chunk["token_count"])

    heading_only = is_heading_only(text)

    if heading_only:
        flags.append("heading_only")

    if token_count < minimum_heading_only_tokens:
        flags.append("very_short")

    return flags


def determine_indexable(
    *,
    chunk: dict[str, Any],
    quality_flags: list[str],
    minimum_heading_only_tokens: int,
) -> bool:
    """
    Current indexing policy:

    Exclude only chunks that are BOTH:
      - heading-only
      - below the configured token threshold

    Short chunks that contain meaningful body text remain indexable.
    """
    return not (
        "heading_only" in quality_flags
        and int(chunk["token_count"]) < minimum_heading_only_tokens
    )


def normalize_heading_path(
    heading_path: list[str],
) -> list[str]:
    result: list[str] = []

    for item in heading_path:
        cleaned = re.sub(
            r"\s+",
            " ",
            item,
        ).strip()

        if cleaned:
            result.append(cleaned)

    return result


def build_retrieval_text(
    *,
    chunk: dict[str, Any],
) -> str:
    """
    Enrich canonical chunk text with hierarchical heading context.

    Canonical chunk text remains untouched in `text`.

    Example:

        Service > Service type > ClusterIP

        ### ClusterIP

        For type: ClusterIP services...
    """
    heading_path = normalize_heading_path(
        list(chunk["heading_path"])
    )

    context_line = " > ".join(
        heading_path
    )

    chunk_text = str(chunk["text"]).strip()

    if context_line:
        retrieval_text = (
            f"{context_line}\n\n"
            f"{chunk_text}"
        )
    else:
        retrieval_text = chunk_text

    return retrieval_text.strip()


def prepare_chunk(
    *,
    chunk: dict[str, Any],
    minimum_heading_only_tokens: int,
) -> dict[str, Any]:
    quality_flags = build_quality_flags(
        chunk=chunk,
        minimum_heading_only_tokens=minimum_heading_only_tokens,
    )

    indexable = determine_indexable(
        chunk=chunk,
        quality_flags=quality_flags,
        minimum_heading_only_tokens=minimum_heading_only_tokens,
    )

    retrieval_text = build_retrieval_text(
        chunk=chunk,
    )

    prepared = dict(chunk)

    prepared["preparation_version"] = PREPARATION_VERSION
    prepared["quality_flags"] = quality_flags
    prepared["indexable"] = indexable
    prepared["retrieval_text"] = retrieval_text
    prepared["retrieval_text_sha256"] = (
        "sha256:" + sha256_text(retrieval_text)
    )

    return prepared


def canonical_json_line(
    record: dict[str, Any],
) -> str:
    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_indexable_chunks(
    *,
    output_path: Path,
    prepared_chunks: list[dict[str, Any]],
) -> str:
    indexable_chunks = [
        chunk
        for chunk in prepared_chunks
        if chunk["indexable"] is True
    ]

    ordered = sorted(
        indexable_chunks,
        key=lambda chunk: (
            str(chunk["document_id"]),
            str(chunk["section_id"]),
            int(chunk["chunk_index"]),
        ),
    )

    content = "\n".join(
        canonical_json_line(chunk)
        for chunk in ordered
    )

    if content:
        content += "\n"

    atomic_write_text(
        output_path,
        content,
    )

    return (
        "sha256:"
        + hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()
    )


def duplicate_groups(
    records: list[dict[str, Any]],
    field: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}

    for record in records:
        value = str(
            record.get(field, "")
        )

        grouped.setdefault(
            value,
            [],
        ).append(
            str(record["chunk_id"])
        )

    groups: list[dict[str, Any]] = []

    for value, chunk_ids in grouped.items():
        if len(chunk_ids) <= 1:
            continue

        groups.append(
            {
                "value": value,
                "count": len(chunk_ids),
                "chunk_ids": sorted(chunk_ids),
            }
        )

    return sorted(
        groups,
        key=lambda item: (
            -int(item["count"]),
            str(item["value"]),
        ),
    )


def build_report(
    *,
    input_path: Path,
    output_path: Path,
    output_sha256: str,
    prepared_chunks: list[dict[str, Any]],
    minimum_heading_only_tokens: int,
) -> dict[str, Any]:
    indexable = [
        chunk
        for chunk in prepared_chunks
        if chunk["indexable"]
    ]

    excluded = [
        chunk
        for chunk in prepared_chunks
        if not chunk["indexable"]
    ]

    all_token_counts = [
        int(chunk["token_count"])
        for chunk in prepared_chunks
    ]

    indexable_token_counts = [
        int(chunk["token_count"])
        for chunk in indexable
    ]

    flag_counts = Counter()

    for chunk in prepared_chunks:
        for flag in chunk["quality_flags"]:
            flag_counts[flag] += 1

    excluded_by_reason = Counter()

    for chunk in excluded:
        flags = tuple(
            sorted(chunk["quality_flags"])
        )

        reason = (
            "+".join(flags)
            if flags
            else "unspecified"
        )

        excluded_by_reason[reason] += 1

    excluded_records = [
        {
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "section_id": chunk["section_id"],
            "section_title": chunk["section_title"],
            "token_count": chunk["token_count"],
            "quality_flags": chunk["quality_flags"],
            "text": chunk["text"],
        }
        for chunk in excluded
    ]

    excluded_records.sort(
        key=lambda item: (
            int(item["token_count"]),
            str(item["chunk_id"]),
        )
    )

    indexable_duplicate_hashes = duplicate_groups(
        indexable,
        "content_sha256",
    )

    report = {
        "preparation_version": PREPARATION_VERSION,
        "status": "SUCCESS",

        "input": input_path.as_posix(),
        "output": output_path.as_posix(),
        "output_sha256": output_sha256,

        "policy": {
            "minimum_heading_only_tokens": (
                minimum_heading_only_tokens
            ),
            "exclusion_rule": (
                "Exclude a chunk only when it is heading-only "
                f"and token_count < {minimum_heading_only_tokens}."
            ),
            "retrieval_text_strategy": (
                "Prefix canonical chunk text with heading_path "
                "joined using ' > '."
            ),
            "canonical_text_modified": False,
        },

        "summary": {
            "input_chunks": len(prepared_chunks),
            "indexable_chunks": len(indexable),
            "excluded_chunks": len(excluded),
            "indexable_fraction": (
                round(
                    len(indexable)
                    / len(prepared_chunks),
                    6,
                )
                if prepared_chunks
                else 0.0
            ),
            "excluded_fraction": (
                round(
                    len(excluded)
                    / len(prepared_chunks),
                    6,
                )
                if prepared_chunks
                else 0.0
            ),
            "documents_in_input": len(
                {
                    str(chunk["document_id"])
                    for chunk in prepared_chunks
                }
            ),
            "documents_in_index": len(
                {
                    str(chunk["document_id"])
                    for chunk in indexable
                }
            ),
            "sections_in_input": len(
                {
                    str(chunk["section_id"])
                    for chunk in prepared_chunks
                }
            ),
            "sections_in_index": len(
                {
                    str(chunk["section_id"])
                    for chunk in indexable
                }
            ),
        },

        "quality_flags": dict(
            sorted(flag_counts.items())
        ),

        "excluded_by_reason": dict(
            sorted(excluded_by_reason.items())
        ),

        "token_statistics": {
            "input": {
                "minimum": min(
                    all_token_counts,
                    default=None,
                ),
                "maximum": max(
                    all_token_counts,
                    default=None,
                ),
                "mean": (
                    round(
                        statistics.fmean(
                            all_token_counts
                        ),
                        3,
                    )
                    if all_token_counts
                    else None
                ),
                "median": (
                    round(
                        statistics.median(
                            all_token_counts
                        ),
                        3,
                    )
                    if all_token_counts
                    else None
                ),
            },

            "indexable": {
                "minimum": min(
                    indexable_token_counts,
                    default=None,
                ),
                "maximum": max(
                    indexable_token_counts,
                    default=None,
                ),
                "mean": (
                    round(
                        statistics.fmean(
                            indexable_token_counts
                        ),
                        3,
                    )
                    if indexable_token_counts
                    else None
                ),
                "median": (
                    round(
                        statistics.median(
                            indexable_token_counts
                        ),
                        3,
                    )
                    if indexable_token_counts
                    else None
                ),
            },
        },

        "duplicate_content_hashes_in_index": {
            "group_count": len(
                indexable_duplicate_hashes
            ),
            "groups": indexable_duplicate_hashes,
        },

        "excluded_chunks": excluded_records,
    }

    return report


def validate_prepared_corpus(
    *,
    original_chunks: list[dict[str, Any]],
    prepared_chunks: list[dict[str, Any]],
) -> None:
    if len(original_chunks) != len(
        prepared_chunks
    ):
        raise CorpusPreparationError(
            "Prepared chunk count differs from input chunk count."
        )

    original_ids = [
        str(chunk["chunk_id"])
        for chunk in original_chunks
    ]

    prepared_ids = [
        str(chunk["chunk_id"])
        for chunk in prepared_chunks
    ]

    if original_ids != prepared_ids:
        raise CorpusPreparationError(
            "Chunk identity/order changed during preparation."
        )

    if len(prepared_ids) != len(
        set(prepared_ids)
    ):
        raise CorpusPreparationError(
            "Duplicate chunk IDs exist in prepared corpus."
        )

    for original, prepared in zip(
        original_chunks,
        prepared_chunks,
    ):
        chunk_id = str(
            original["chunk_id"]
        )

        if prepared["text"] != original["text"]:
            raise CorpusPreparationError(
                f"{chunk_id}: canonical text was modified."
            )

        if (
            prepared["content_sha256"]
            != original["content_sha256"]
        ):
            raise CorpusPreparationError(
                f"{chunk_id}: canonical content hash changed."
            )

        if not isinstance(
            prepared["quality_flags"],
            list,
        ):
            raise CorpusPreparationError(
                f"{chunk_id}: quality_flags must be a list."
            )

        if not isinstance(
            prepared["indexable"],
            bool,
        ):
            raise CorpusPreparationError(
                f"{chunk_id}: indexable must be boolean."
            )

        retrieval_text = prepared[
            "retrieval_text"
        ]

        if (
            not isinstance(
                retrieval_text,
                str,
            )
            or not retrieval_text.strip()
        ):
            raise CorpusPreparationError(
                f"{chunk_id}: retrieval_text is empty."
            )

        expected_retrieval_hash = (
            "sha256:"
            + sha256_text(
                retrieval_text
            )
        )

        if (
            prepared["retrieval_text_sha256"]
            != expected_retrieval_hash
        ):
            raise CorpusPreparationError(
                f"{chunk_id}: retrieval_text hash mismatch."
            )


def print_summary(
    report: dict[str, Any],
    report_path: Path,
) -> None:
    summary = report["summary"]
    flags = report["quality_flags"]

    print()
    print("-" * 76)
    print("Index Corpus Preparation")
    print("-" * 76)
    print(
        f"Input chunks:         "
        f"{summary['input_chunks']}"
    )
    print(
        f"Indexable chunks:     "
        f"{summary['indexable_chunks']}"
    )
    print(
        f"Excluded chunks:      "
        f"{summary['excluded_chunks']}"
    )
    print(
        f"Indexable fraction:   "
        f"{summary['indexable_fraction']:.2%}"
    )
    print(
        f"Heading-only flags:   "
        f"{flags.get('heading_only', 0)}"
    )
    print(
        f"Very-short flags:     "
        f"{flags.get('very_short', 0)}"
    )
    print(
        "Duplicate hashes "
        "remaining in index: "
        f"{report['duplicate_content_hashes_in_index']['group_count']}"
    )
    print(
        f"Output:               "
        f"{report['output']}"
    )
    print(
        f"Report:               "
        f"{report_path}"
    )
    print("Status:               SUCCESS")
    print("-" * 76)

    excluded = report["excluded_chunks"]

    if excluded:
        print()
        print("Excluded chunks:")
        print("-" * 76)

        for item in excluded[:50]:
            print(
                f"{item['token_count']:>4}  "
                f"{item['chunk_id']}  "
                f"[{', '.join(item['quality_flags'])}]"
            )
            cleaned_text = re.sub(
                r"\\s+",
                " ",
                str(item["text"]),
            ).strip()

            print(
                f"      {cleaned_text}"
            )

        if len(excluded) > 50:
            print(
                f"... {len(excluded) - 50} more "
                "excluded chunks are listed in the report."
            )

        print("-" * 76)


def run_preparation(
    *,
    input_path: Path,
    output_path: Path,
    report_path: Path,
    minimum_heading_only_tokens: int,
) -> int:
    print(
        f"Loading chunks: {input_path}"
    )

    chunks = load_jsonl(
        input_path
    )

    print(
        f"Loaded {len(chunks):,} chunks."
    )

    seen_ids: set[str] = set()

    for chunk in chunks:
        validate_chunk_record(
            chunk
        )

        chunk_id = str(
            chunk["chunk_id"]
        )

        if chunk_id in seen_ids:
            raise CorpusPreparationError(
                f"Duplicate chunk ID: {chunk_id}"
            )

        seen_ids.add(
            chunk_id
        )

    prepared_chunks = [
        prepare_chunk(
            chunk=chunk,
            minimum_heading_only_tokens=(
                minimum_heading_only_tokens
            ),
        )
        for chunk in chunks
    ]

    validate_prepared_corpus(
        original_chunks=chunks,
        prepared_chunks=prepared_chunks,
    )

    output_sha256 = write_indexable_chunks(
        output_path=output_path,
        prepared_chunks=prepared_chunks,
    )

    report = build_report(
        input_path=input_path,
        output_path=output_path,
        output_sha256=output_sha256,
        prepared_chunks=prepared_chunks,
        minimum_heading_only_tokens=(
            minimum_heading_only_tokens
        ),
    )

    atomic_write_text(
        report_path,
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    print_summary(
        report,
        report_path,
    )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare GroundTruth chunks for retrieval indexing by "
            "adding quality flags, applying an auditable indexability "
            "policy, and enriching retrieval text with heading context."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=(
            "Canonical chunks JSONL. "
            f"Default: {DEFAULT_INPUT_PATH}"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "Indexable chunks JSONL. "
            f"Default: {DEFAULT_OUTPUT_PATH}"
        ),
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=(
            "Preparation report JSON. "
            f"Default: {DEFAULT_REPORT_PATH}"
        ),
    )

    parser.add_argument(
        "--minimum-heading-only-tokens",
        type=int,
        default=DEFAULT_MIN_HEADING_ONLY_TOKENS,
        help=(
            "Heading-only chunks below this token count are excluded. "
            f"Default: {DEFAULT_MIN_HEADING_ONLY_TOKENS}"
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if (
        args.minimum_heading_only_tokens
        <= 0
    ):
        parser.error(
            "--minimum-heading-only-tokens must be > 0"
        )

    try:
        return run_preparation(
            input_path=args.input,
            output_path=args.output,
            report_path=args.report_output,
            minimum_heading_only_tokens=(
                args.minimum_heading_only_tokens
            ),
        )
    except CorpusPreparationError as exc:
        print(
            f"Preparation failed: {exc}"
        )
        return 1
    except Exception as exc:
        print(
            "Preparation failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
