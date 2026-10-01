from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

try:
    import tiktoken
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: tiktoken\n"
        "Install it with:\n"
        "  python -m pip install tiktoken pyyaml"
    ) from exc


AUDIT_VERSION = "0.1.0"

DEFAULT_MANIFEST = Path("manifest/kubernetes_v0.1.yaml")
DEFAULT_SECTIONS = Path("data/processed/sections.jsonl")
DEFAULT_CHUNKS = Path("data/processed/chunks.jsonl")
DEFAULT_REPORT = Path("reports/chunk_quality_report.json")

DEFAULT_TOKENIZER = "cl100k_base"
DEFAULT_TARGET_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 64
DEFAULT_SMALLEST_COUNT = 20

CHUNK_ID_RE = re.compile(
    r"^(?P<section_id>[a-z0-9]+-[0-9]{3}-sec-[0-9]{3})"
    r"-ch-(?P<chunk_index>[0-9]{3})$"
)

TOKEN_BUCKETS = (
    ("0", 0, 0),
    ("1-9", 1, 9),
    ("10-31", 10, 31),
    ("32-63", 32, 63),
    ("64-127", 64, 127),
    ("128-255", 128, 255),
    ("256-383", 256, 383),
    ("384-511", 384, 511),
    ("512", 512, 512),
    (">512", 513, None),
)


class AuditInputError(RuntimeError):
    """Raised when an audit input cannot be loaded."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        temp_path.write_text(
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
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


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AuditInputError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        value = yaml.safe_load(file)

    if not isinstance(value, dict):
        raise AuditInputError(
            f"Expected YAML mapping at root: {path}"
        )

    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise AuditInputError(f"File not found: {path}")

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AuditInputError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise AuditInputError(
                    f"{path}:{line_number}: each JSONL line "
                    "must contain an object."
                )

            records.append(value)

    if not records:
        raise AuditInputError(f"No records found in {path}")

    return records


def get_encoding(name: str):
    try:
        return tiktoken.get_encoding(name)
    except Exception as exc:
        raise AuditInputError(
            f"Could not load tiktoken encoding {name!r}: {exc}"
        ) from exc


def token_bucket_name(token_count: int) -> str:
    for name, minimum, maximum in TOKEN_BUCKETS:
        if token_count < minimum:
            continue

        if maximum is None or token_count <= maximum:
            return name

    raise RuntimeError(
        f"Unable to bucket token count: {token_count}"
    )


def duplicate_groups(
    records: list[dict[str, Any]],
    field: str,
    id_field: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)

    for record in records:
        value = record.get(field)

        if value is None:
            continue

        grouped[str(value)].append(
            str(record.get(id_field, "<missing>"))
        )

    groups = [
        {
            "value": value,
            "count": len(ids),
            "record_ids": sorted(ids),
        }
        for value, ids in grouped.items()
        if len(ids) > 1
    ]

    return sorted(
        groups,
        key=lambda group: (
            -int(group["count"]),
            str(group["value"]),
        ),
    )


def text_preview(text: str, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", text).strip()

    if len(compact) <= limit:
        return compact

    return compact[: limit - 1] + "…"


def is_heading_only(text: str) -> bool:
    stripped = text.strip()

    if not stripped:
        return False

    lines = [
        line.strip()
        for line in stripped.splitlines()
        if line.strip()
    ]

    return (
        len(lines) == 1
        and re.fullmatch(r"#{1,6}\s+\S.*", lines[0]) is not None
    )


def add_issue(
    issues: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    chunk_id: str | None = None,
    section_id: str | None = None,
    document_id: str | None = None,
) -> None:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }

    if chunk_id is not None:
        issue["chunk_id"] = chunk_id

    if section_id is not None:
        issue["section_id"] = section_id

    if document_id is not None:
        issue["document_id"] = document_id

    issues.append(issue)


def audit(
    *,
    manifest_path: Path,
    sections_path: Path,
    chunks_path: Path,
    report_path: Path,
    tokenizer_name: str,
    target_tokens: int,
    overlap_tokens: int,
    smallest_count: int,
) -> tuple[dict[str, Any], int]:
    manifest = load_yaml_mapping(manifest_path)
    sections = load_jsonl(sections_path)
    chunks = load_jsonl(chunks_path)
    encoding = get_encoding(tokenizer_name)

    manifest_documents = manifest.get("documents")

    if not isinstance(manifest_documents, list):
        raise AuditInputError(
            "Manifest must contain a top-level documents list."
        )

    documents_by_id: dict[str, dict[str, Any]] = {}

    for document in manifest_documents:
        if not isinstance(document, dict) or "id" not in document:
            raise AuditInputError(
                "Manifest documents must be objects with an id."
            )

        documents_by_id[str(document["id"])] = document

    sections_by_id: dict[str, dict[str, Any]] = {}
    section_ids_in_order: list[str] = []

    for section in sections:
        section_id = str(section.get("section_id", ""))

        if section_id:
            section_ids_in_order.append(section_id)

            if section_id not in sections_by_id:
                sections_by_id[section_id] = section

    issues: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Duplicate IDs / hashes
    # ------------------------------------------------------------------

    duplicate_chunk_ids = duplicate_groups(
        chunks,
        field="chunk_id",
        id_field="chunk_id",
    )

    duplicate_section_ids = duplicate_groups(
        sections,
        field="section_id",
        id_field="section_id",
    )

    duplicate_content_hashes = duplicate_groups(
        chunks,
        field="content_sha256",
        id_field="chunk_id",
    )

    if duplicate_chunk_ids:
        add_issue(
            issues,
            severity="ERROR",
            code="duplicate_chunk_ids",
            message=(
                f"Found {len(duplicate_chunk_ids)} duplicated "
                "chunk ID value(s)."
            ),
        )

    if duplicate_section_ids:
        add_issue(
            issues,
            severity="ERROR",
            code="duplicate_section_ids",
            message=(
                f"Found {len(duplicate_section_ids)} duplicated "
                "section ID value(s)."
            ),
        )

    if duplicate_content_hashes:
        add_issue(
            issues,
            severity="WARNING",
            code="duplicate_chunk_content_hashes",
            message=(
                f"Found {len(duplicate_content_hashes)} content hash "
                "value(s) shared by multiple chunks. This can be legitimate "
                "for repeated headings, but should be reviewed."
            ),
        )

    # ------------------------------------------------------------------
    # Token statistics / smallest chunks
    # ------------------------------------------------------------------

    declared_token_counts: list[int] = []
    bucket_counts = Counter(
        {name: 0 for name, _, _ in TOKEN_BUCKETS}
    )

    smallest_rows: list[dict[str, Any]] = []
    token_count_mismatches: list[dict[str, Any]] = []
    oversized_chunks: list[dict[str, Any]] = []
    zero_token_chunks: list[dict[str, Any]] = []
    very_short_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id", "<missing>"))
        text = chunk.get("text")
        declared = chunk.get("token_count")

        if not isinstance(text, str):
            add_issue(
                issues,
                severity="ERROR",
                code="invalid_chunk_text",
                message="Chunk text is missing or not a string.",
                chunk_id=chunk_id,
            )
            continue

        if not isinstance(declared, int):
            add_issue(
                issues,
                severity="ERROR",
                code="invalid_token_count",
                message="token_count is missing or not an integer.",
                chunk_id=chunk_id,
            )
            continue

        actual = len(
            encoding.encode(
                text,
                disallowed_special=(),
            )
        )

        declared_token_counts.append(declared)
        bucket_counts[token_bucket_name(declared)] += 1

        row = {
            "chunk_id": chunk_id,
            "document_id": chunk.get("document_id"),
            "section_id": chunk.get("section_id"),
            "section_title": chunk.get("section_title"),
            "token_count": declared,
            "heading_only": is_heading_only(text),
            "preview": text_preview(text),
        }

        smallest_rows.append(row)

        if declared != actual:
            token_count_mismatches.append(
                {
                    "chunk_id": chunk_id,
                    "declared": declared,
                    "recomputed": actual,
                }
            )

        if declared == 0:
            zero_token_chunks.append(row)

        if declared < 32:
            very_short_chunks.append(row)

        if declared > target_tokens:
            oversized_chunks.append(row)

    smallest_rows = sorted(
        smallest_rows,
        key=lambda row: (
            int(row["token_count"]),
            str(row["chunk_id"]),
        ),
    )[:smallest_count]

    very_short_chunks = sorted(
        very_short_chunks,
        key=lambda row: (
            int(row["token_count"]),
            str(row["chunk_id"]),
        ),
    )

    if token_count_mismatches:
        add_issue(
            issues,
            severity="ERROR",
            code="token_count_mismatch",
            message=(
                f"{len(token_count_mismatches)} chunk(s) have a "
                "token_count that differs from recomputation."
            ),
        )

    if zero_token_chunks:
        add_issue(
            issues,
            severity="ERROR",
            code="zero_token_chunks",
            message=(
                f"{len(zero_token_chunks)} zero-token chunk(s) found."
            ),
        )

    if oversized_chunks:
        add_issue(
            issues,
            severity="ERROR",
            code="oversized_chunks",
            message=(
                f"{len(oversized_chunks)} chunk(s) exceed the "
                f"{target_tokens}-token target."
            ),
        )

    if very_short_chunks:
        add_issue(
            issues,
            severity="WARNING",
            code="very_short_chunks",
            message=(
                f"{len(very_short_chunks)} chunk(s) contain fewer "
                "than 32 tokens."
            ),
        )

    # ------------------------------------------------------------------
    # Group chunks by section
    # ------------------------------------------------------------------

    chunks_by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for chunk in chunks:
        section_id = str(chunk.get("section_id", ""))
        chunks_by_section[section_id].append(chunk)

    for section_chunks in chunks_by_section.values():
        section_chunks.sort(
            key=lambda chunk: (
                int(chunk.get("chunk_index", 0))
                if isinstance(chunk.get("chunk_index"), int)
                else 0,
                str(chunk.get("chunk_id", "")),
            )
        )

    # ------------------------------------------------------------------
    # Chunk -> section -> document referential checks
    # ------------------------------------------------------------------

    orphan_chunk_sections: list[str] = []
    section_document_mismatches: list[str] = []
    missing_manifest_documents: set[str] = set()
    document_domain_mismatches: list[str] = []
    source_url_mismatches: list[str] = []
    heading_path_mismatches: list[str] = []
    section_hash_mismatches: list[str] = []
    document_hash_mismatches: list[str] = []
    chunk_id_shape_errors: list[str] = []
    chunk_index_errors: list[str] = []

    for section in sections:
        section_id = str(section.get("section_id", "<missing>"))
        document_id = str(section.get("document_id", ""))

        if document_id not in documents_by_id:
            missing_manifest_documents.add(document_id)
            continue

        manifest_document = documents_by_id[document_id]

        if section.get("domain") != manifest_document.get("domain"):
            document_domain_mismatches.append(section_id)

        if section.get("source_url") != manifest_document.get("url"):
            source_url_mismatches.append(section_id)

    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id", "<missing>"))
        section_id = str(chunk.get("section_id", ""))
        document_id = str(chunk.get("document_id", ""))

        match = CHUNK_ID_RE.fullmatch(chunk_id)

        if match is None:
            chunk_id_shape_errors.append(chunk_id)
        else:
            if match.group("section_id") != section_id:
                chunk_id_shape_errors.append(chunk_id)

            chunk_index = chunk.get("chunk_index")

            if (
                not isinstance(chunk_index, int)
                or int(match.group("chunk_index")) != chunk_index
            ):
                chunk_index_errors.append(chunk_id)

        section = sections_by_id.get(section_id)

        if section is None:
            orphan_chunk_sections.append(chunk_id)
            continue

        section_document_id = str(section.get("document_id", ""))

        if document_id != section_document_id:
            section_document_mismatches.append(chunk_id)

        manifest_document = documents_by_id.get(document_id)

        if manifest_document is None:
            missing_manifest_documents.add(document_id)
            continue

        if (
            chunk.get("domain") != section.get("domain")
            or chunk.get("domain") != manifest_document.get("domain")
        ):
            document_domain_mismatches.append(chunk_id)

        if (
            chunk.get("source_url") != section.get("source_url")
            or chunk.get("source_url") != manifest_document.get("url")
        ):
            source_url_mismatches.append(chunk_id)

        if chunk.get("heading_path") != section.get("heading_path"):
            heading_path_mismatches.append(chunk_id)

        if (
            chunk.get("section_content_sha256")
            != section.get("content_sha256")
        ):
            section_hash_mismatches.append(chunk_id)

        if (
            chunk.get("source_document_content_sha256")
            != section.get("source_document_content_sha256")
        ):
            document_hash_mismatches.append(chunk_id)

    missing_chunk_sections = sorted(
        set(sections_by_id) - set(chunks_by_section)
    )

    manifest_docs_without_sections = sorted(
        set(documents_by_id)
        - {
            str(section.get("document_id", ""))
            for section in sections
        }
    )

    manifest_docs_without_chunks = sorted(
        set(documents_by_id)
        - {
            str(chunk.get("document_id", ""))
            for chunk in chunks
        }
    )

    referential_error_sets = {
        "chunk_ids_with_invalid_shape_or_section_prefix": sorted(
            set(chunk_id_shape_errors)
        ),
        "chunk_ids_with_chunk_index_mismatch": sorted(
            set(chunk_index_errors)
        ),
        "chunks_with_missing_section": sorted(
            set(orphan_chunk_sections)
        ),
        "chunks_with_document_mismatch": sorted(
            set(section_document_mismatches)
        ),
        "unknown_manifest_document_ids": sorted(
            item
            for item in missing_manifest_documents
            if item
        ),
        "domain_mismatches": sorted(
            set(document_domain_mismatches)
        ),
        "source_url_mismatches": sorted(
            set(source_url_mismatches)
        ),
        "heading_path_mismatches": sorted(
            set(heading_path_mismatches)
        ),
        "section_hash_mismatches": sorted(
            set(section_hash_mismatches)
        ),
        "document_hash_mismatches": sorted(
            set(document_hash_mismatches)
        ),
        "sections_without_chunks": missing_chunk_sections,
        "manifest_documents_without_sections": manifest_docs_without_sections,
        "manifest_documents_without_chunks": manifest_docs_without_chunks,
    }

    referential_error_count = sum(
        len(values)
        for values in referential_error_sets.values()
    )

    if referential_error_count:
        add_issue(
            issues,
            severity="ERROR",
            code="referential_integrity_failure",
            message=(
                f"Found {referential_error_count} chunk/section/document "
                "referential-integrity violation(s)."
            ),
        )

    # ------------------------------------------------------------------
    # Section split statistics
    # ------------------------------------------------------------------

    split_counts: dict[str, int] = {}

    for section_id in sections_by_id:
        split_counts[section_id] = len(
            chunks_by_section.get(section_id, [])
        )

    chunk_count_distribution = Counter(
        split_counts.values()
    )

    split_sections = [
        {
            "section_id": section_id,
            "document_id": sections_by_id[section_id].get("document_id"),
            "title": sections_by_id[section_id].get("title"),
            "chunk_count": chunk_count,
        }
        for section_id, chunk_count in split_counts.items()
        if chunk_count > 1
    ]

    split_sections.sort(
        key=lambda row: (
            -int(row["chunk_count"]),
            str(row["section_id"]),
        )
    )

    # ------------------------------------------------------------------
    # Overlap / exact token-span validation
    # ------------------------------------------------------------------

    overlap_errors: list[dict[str, Any]] = []
    token_span_errors: list[dict[str, Any]] = []
    config_hashes = Counter(
        str(chunk.get("chunking_config_sha256", "<missing>"))
        for chunk in chunks
    )

    tokenizer_values = Counter(
        str(chunk.get("tokenizer", "<missing>"))
        for chunk in chunks
    )

    for section_id, section in sections_by_id.items():
        section_chunks = chunks_by_section.get(section_id, [])

        if not section_chunks:
            continue

        section_text = section.get("text")

        if not isinstance(section_text, str):
            token_span_errors.append(
                {
                    "section_id": section_id,
                    "reason": "section text missing or invalid",
                }
            )
            continue

        section_token_ids = encoding.encode(
            section_text,
            disallowed_special=(),
        )

        previous_end: int | None = None

        for expected_index, chunk in enumerate(
            section_chunks,
            start=1,
        ):
            chunk_id = str(chunk.get("chunk_id", "<missing>"))
            chunk_index = chunk.get("chunk_index")
            start = chunk.get("section_token_start")
            end = chunk.get("section_token_end_exclusive")
            declared_overlap = chunk.get(
                "overlap_tokens_with_previous"
            )

            if chunk_index != expected_index:
                overlap_errors.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": "non-contiguous chunk_index",
                        "expected": expected_index,
                        "actual": chunk_index,
                    }
                )

            if not (
                isinstance(start, int)
                and isinstance(end, int)
                and 0 <= start < end <= len(section_token_ids)
            ):
                token_span_errors.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": "invalid token span",
                        "start": start,
                        "end_exclusive": end,
                        "section_token_count": len(section_token_ids),
                    }
                )
                continue

            expected_text = encoding.decode(
                section_token_ids[start:end]
            )

            if chunk.get("text") != expected_text:
                token_span_errors.append(
                    {
                        "chunk_id": chunk_id,
                        "reason": (
                            "chunk text does not equal section token span"
                        ),
                    }
                )

            if expected_index == 1:
                if start != 0:
                    overlap_errors.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": "first chunk does not start at token 0",
                            "actual_start": start,
                        }
                    )

                if declared_overlap != 0:
                    overlap_errors.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": "first chunk declares non-zero overlap",
                            "actual": declared_overlap,
                        }
                    )
            else:
                if previous_end is None:
                    overlap_errors.append(
                        {
                            "chunk_id": chunk_id,
                            "reason": "previous chunk end unavailable",
                        }
                    )
                else:
                    actual_overlap = previous_end - start

                    if actual_overlap != overlap_tokens:
                        overlap_errors.append(
                            {
                                "chunk_id": chunk_id,
                                "reason": "unexpected token overlap",
                                "expected": overlap_tokens,
                                "actual": actual_overlap,
                            }
                        )

                    if declared_overlap != actual_overlap:
                        overlap_errors.append(
                            {
                                "chunk_id": chunk_id,
                                "reason": "overlap metadata mismatch",
                                "declared": declared_overlap,
                                "actual": actual_overlap,
                            }
                        )

            previous_end = end

        final_end = section_chunks[-1].get(
            "section_token_end_exclusive"
        )

        if final_end != len(section_token_ids):
            overlap_errors.append(
                {
                    "section_id": section_id,
                    "reason": "final chunk does not reach section end",
                    "expected_end": len(section_token_ids),
                    "actual_end": final_end,
                }
            )

    if overlap_errors:
        add_issue(
            issues,
            severity="ERROR",
            code="overlap_validation_failure",
            message=(
                f"Found {len(overlap_errors)} overlap/sequence "
                "validation issue(s)."
            ),
        )

    if token_span_errors:
        add_issue(
            issues,
            severity="ERROR",
            code="token_span_validation_failure",
            message=(
                f"Found {len(token_span_errors)} exact token-span "
                "validation issue(s)."
            ),
        )

    if len(config_hashes) != 1:
        add_issue(
            issues,
            severity="ERROR",
            code="mixed_chunking_config_hashes",
            message=(
                "Expected one chunking_config_sha256 across the canonical "
                f"corpus, found {len(config_hashes)}."
            ),
        )

    if len(tokenizer_values) != 1:
        add_issue(
            issues,
            severity="ERROR",
            code="mixed_tokenizers",
            message=(
                f"Expected one tokenizer across the canonical corpus, "
                f"found {len(tokenizer_values)}."
            ),
        )

    # ------------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------------

    error_count = sum(
        issue["severity"] == "ERROR"
        for issue in issues
    )

    warning_count = sum(
        issue["severity"] == "WARNING"
        for issue in issues
    )

    if error_count:
        status = "FAIL"
        exit_code = 1
    elif warning_count:
        status = "WARN"
        exit_code = 0
    else:
        status = "PASS"
        exit_code = 0

    token_summary: dict[str, Any]

    if declared_token_counts:
        token_summary = {
            "count": len(declared_token_counts),
            "minimum": min(declared_token_counts),
            "maximum": max(declared_token_counts),
            "mean": round(
                statistics.fmean(declared_token_counts),
                3,
            ),
            "median": round(
                statistics.median(declared_token_counts),
                3,
            ),
        }
    else:
        token_summary = {
            "count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
        }

    report: dict[str, Any] = {
        "audit_version": AUDIT_VERSION,
        "status": status,
        "inputs": {
            "manifest": manifest_path.as_posix(),
            "sections": sections_path.as_posix(),
            "chunks": chunks_path.as_posix(),
        },
        "expected_chunking": {
            "tokenizer": tokenizer_name,
            "target_tokens": target_tokens,
            "overlap_tokens": overlap_tokens,
        },
        "summary": {
            "manifest_documents": len(documents_by_id),
            "sections": len(sections),
            "chunks": len(chunks),
            "unique_chunk_ids": len(
                {
                    str(chunk.get("chunk_id", ""))
                    for chunk in chunks
                }
            ),
            "unique_chunk_content_hashes": len(
                {
                    str(chunk.get("content_sha256", ""))
                    for chunk in chunks
                }
            ),
            "errors": error_count,
            "warnings": warning_count,
        },
        "token_statistics": token_summary,
        "token_buckets": {
            name: bucket_counts[name]
            for name, _, _ in TOKEN_BUCKETS
        },
        "smallest_chunks": smallest_rows,
        "very_short_chunks_under_32_tokens": {
            "count": len(very_short_chunks),
            "heading_only_count": sum(
                bool(row["heading_only"])
                for row in very_short_chunks
            ),
            "chunks": very_short_chunks,
        },
        "duplicates": {
            "duplicate_chunk_ids": {
                "group_count": len(duplicate_chunk_ids),
                "groups": duplicate_chunk_ids,
            },
            "duplicate_section_ids": {
                "group_count": len(duplicate_section_ids),
                "groups": duplicate_section_ids,
            },
            "duplicate_chunk_content_hashes": {
                "group_count": len(duplicate_content_hashes),
                "groups": duplicate_content_hashes,
            },
        },
        "token_count_validation": {
            "mismatch_count": len(token_count_mismatches),
            "mismatches": token_count_mismatches,
            "zero_token_chunk_count": len(zero_token_chunks),
            "oversized_chunk_count": len(oversized_chunks),
            "oversized_chunks": oversized_chunks,
        },
        "section_split_statistics": {
            "total_sections": len(sections_by_id),
            "sections_with_zero_chunks": sum(
                count == 0
                for count in split_counts.values()
            ),
            "sections_with_one_chunk": sum(
                count == 1
                for count in split_counts.values()
            ),
            "sections_with_multiple_chunks": sum(
                count > 1
                for count in split_counts.values()
            ),
            "maximum_chunks_for_one_section": max(
                split_counts.values(),
                default=0,
            ),
            "chunk_count_distribution": {
                str(chunk_count): count
                for chunk_count, count in sorted(
                    chunk_count_distribution.items()
                )
            },
            "most_split_sections": split_sections[:50],
        },
        "overlap_validation": {
            "expected_overlap_tokens": overlap_tokens,
            "issue_count": len(overlap_errors),
            "issues": overlap_errors,
            "token_span_issue_count": len(token_span_errors),
            "token_span_issues": token_span_errors,
        },
        "referential_integrity": {
            "issue_count": referential_error_count,
            **referential_error_sets,
        },
        "configuration_consistency": {
            "chunking_config_hashes": dict(
                sorted(config_hashes.items())
            ),
            "tokenizers": dict(
                sorted(tokenizer_values.items())
            ),
        },
        "issues": issues,
    }

    atomic_write_json(
        report_path,
        report,
    )

    return report, exit_code


def print_console_summary(
    report: dict[str, Any],
    report_path: Path,
) -> None:
    summary = report["summary"]
    token_stats = report["token_statistics"]
    split_stats = report["section_split_statistics"]
    duplicates = report["duplicates"]
    overlap = report["overlap_validation"]
    refs = report["referential_integrity"]

    print()
    print("-" * 78)
    print("Chunk Quality Audit")
    print("-" * 78)
    print(f"Documents:           {summary['manifest_documents']}")
    print(f"Sections:            {summary['sections']}")
    print(f"Chunks:              {summary['chunks']}")
    print(f"Unique chunk IDs:    {summary['unique_chunk_ids']}")
    print()
    print(
        "Token stats:         "
        f"min={token_stats['minimum']}  "
        f"mean={token_stats['mean']}  "
        f"median={token_stats['median']}  "
        f"max={token_stats['maximum']}"
    )
    print()
    print("Token buckets:")

    for name, count in report["token_buckets"].items():
        print(f"  {name:<9} {count:>6}")

    print()
    print(
        "Very short (<32):    "
        f"{report['very_short_chunks_under_32_tokens']['count']}"
    )
    print(
        "Duplicate IDs:       "
        f"{duplicates['duplicate_chunk_ids']['group_count']}"
    )
    print(
        "Duplicate hashes:    "
        f"{duplicates['duplicate_chunk_content_hashes']['group_count']}"
    )
    print(
        "Split sections:      "
        f"{split_stats['sections_with_multiple_chunks']}"
    )
    print(
        "Max chunks/section:  "
        f"{split_stats['maximum_chunks_for_one_section']}"
    )
    print(
        "Overlap issues:      "
        f"{overlap['issue_count']}"
    )
    print(
        "Token-span issues:   "
        f"{overlap['token_span_issue_count']}"
    )
    print(
        "Referential issues:  "
        f"{refs['issue_count']}"
    )
    print(f"Errors:              {summary['errors']}")
    print(f"Warnings:            {summary['warnings']}")
    print(f"Report:              {report_path}")
    print(f"Status:              {report['status']}")
    print("-" * 78)

    smallest = report["smallest_chunks"]

    if smallest:
        print()
        print("Smallest chunks:")
        print("-" * 78)

        for row in smallest:
            heading_flag = " [heading-only]" if row["heading_only"] else ""
            print(
                f"{row['token_count']:>4}  "
                f"{row['chunk_id']}"
                f"{heading_flag}"
            )
            print(f"      {row['preview']}")

        print("-" * 78)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit GroundTruth chunks for retrieval-quality and "
            "referential-integrity issues."
        )
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Manifest YAML. Default: {DEFAULT_MANIFEST}",
    )

    parser.add_argument(
        "--sections",
        type=Path,
        default=DEFAULT_SECTIONS,
        help=f"Sections JSONL. Default: {DEFAULT_SECTIONS}",
    )

    parser.add_argument(
        "--chunks",
        type=Path,
        default=DEFAULT_CHUNKS,
        help=f"Chunks JSONL. Default: {DEFAULT_CHUNKS}",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Audit report JSON. Default: {DEFAULT_REPORT}",
    )

    parser.add_argument(
        "--tokenizer",
        default=DEFAULT_TOKENIZER,
        help=f"Expected tiktoken encoding. Default: {DEFAULT_TOKENIZER}",
    )

    parser.add_argument(
        "--target-tokens",
        type=int,
        default=DEFAULT_TARGET_TOKENS,
        help=(
            "Maximum expected tokens per chunk. "
            f"Default: {DEFAULT_TARGET_TOKENS}"
        ),
    )

    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=DEFAULT_OVERLAP_TOKENS,
        help=(
            "Expected overlap between adjacent chunks. "
            f"Default: {DEFAULT_OVERLAP_TOKENS}"
        ),
    )

    parser.add_argument(
        "--smallest-count",
        type=int,
        default=DEFAULT_SMALLEST_COUNT,
        help=(
            "Number of smallest chunks to include in the report. "
            f"Default: {DEFAULT_SMALLEST_COUNT}"
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.target_tokens <= 0:
        parser.error("--target-tokens must be > 0")

    if args.overlap_tokens < 0:
        parser.error("--overlap-tokens must be >= 0")

    if args.overlap_tokens >= args.target_tokens:
        parser.error(
            "--overlap-tokens must be smaller than --target-tokens"
        )

    if args.smallest_count <= 0:
        parser.error("--smallest-count must be > 0")

    try:
        report, exit_code = audit(
            manifest_path=args.manifest,
            sections_path=args.sections,
            chunks_path=args.chunks,
            report_path=args.report_output,
            tokenizer_name=args.tokenizer,
            target_tokens=args.target_tokens,
            overlap_tokens=args.overlap_tokens,
            smallest_count=args.smallest_count,
        )
    except AuditInputError as exc:
        print(f"Audit input error: {exc}")
        return 1
    except Exception as exc:
        print(
            f"Audit failed: {type(exc).__name__}: {exc}"
        )
        return 1

    print_console_summary(
        report,
        args.report_output,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
