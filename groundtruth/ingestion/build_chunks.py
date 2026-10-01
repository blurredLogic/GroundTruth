from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import tiktoken
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: tiktoken\n"
        "Install it with:\n"
        "  python -m pip install tiktoken"
    ) from exc

from .validate_manifest import ManifestValidationError, validate_manifest


SCHEMA_VERSION = "0.1"
CHUNK_BUILDER_VERSION = "0.1.0"

DEFAULT_SECTIONS = Path("data/processed/sections.jsonl")
DEFAULT_OUTPUT = Path("data/processed/chunks.jsonl")
DEFAULT_REPORT = Path("reports/chunks_report.json")

DEFAULT_TOKENIZER = "cl100k_base"
DEFAULT_TARGET_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 64

BOUNDARY_SEARCH_FRACTION = 0.25
MIN_BOUNDARY_SEARCH_TOKENS = 32

SECTION_ID_RE = re.compile(
    r"^(?P<doc>[a-z0-9]+-[0-9]{3})-sec-(?P<section>[0-9]{3})$"
)

CHUNK_ID_RE = re.compile(
    r"^(?P<section>[a-z0-9]+-[0-9]{3}-sec-[0-9]{3})"
    r"-ch-(?P<chunk>[0-9]{3})$"
)

SENTENCE_END_RE = re.compile(r"""[.!?](?:["')\]]+)?\s*$""")


class ChunkBuildError(RuntimeError):
    pass


class SectionsValidationError(ChunkBuildError):
    pass


class ChunkValidationError(ChunkBuildError):
    pass


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        temp_path.write_text(content, encoding="utf-8", newline="\n")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest does not exist: {path}")

    with path.open("r", encoding="utf-8") as file:
        value = yaml.safe_load(file)

    if not isinstance(value, dict):
        raise ValueError("Manifest root must be a YAML mapping.")

    return value


def load_sections(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Sections file does not exist: {path}")

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SectionsValidationError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise SectionsValidationError(
                    f"{path}:{line_number}: JSONL record must be an object."
                )

            records.append(record)

    if not records:
        raise SectionsValidationError(
            f"No section records found in {path}."
        )

    return records


def get_encoding(name: str):
    try:
        return tiktoken.get_encoding(name)
    except Exception as exc:
        raise ChunkBuildError(
            f"Could not load tiktoken encoding {name!r}: {exc}"
        ) from exc


def get_tiktoken_version() -> str:
    try:
        return importlib.metadata.version("tiktoken")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def manifest_by_id(
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(document["id"]): document
        for document in manifest["documents"]
    }


def validate_sections(
    sections: list[dict[str, Any]],
    manifest: dict[str, Any],
    require_full_corpus: bool,
) -> None:
    docs = manifest_by_id(manifest)

    required = {
        "section_id",
        "document_id",
        "domain",
        "title",
        "heading_path",
        "heading_level",
        "section_order",
        "text",
        "source_url",
        "source_document_content_sha256",
        "content_sha256",
        "corpus_version",
    }

    ids: list[str] = []
    orders_by_doc: dict[str, list[int]] = {}

    for section in sections:
        missing = required - set(section)

        if missing:
            raise SectionsValidationError(
                "Section missing required fields: "
                + ", ".join(sorted(missing))
            )

        section_id = str(section["section_id"])
        document_id = str(section["document_id"])

        match = SECTION_ID_RE.fullmatch(section_id)

        if not match:
            raise SectionsValidationError(
                f"Invalid section_id: {section_id!r}"
            )

        if match.group("doc") != document_id:
            raise SectionsValidationError(
                f"{section_id}: section/document ID mismatch."
            )

        if document_id not in docs:
            raise SectionsValidationError(
                f"{section_id}: unknown document {document_id!r}."
            )

        manifest_document = docs[document_id]

        if section["domain"] != manifest_document["domain"]:
            raise SectionsValidationError(
                f"{section_id}: domain does not match manifest."
            )

        if section["source_url"] != manifest_document["url"]:
            raise SectionsValidationError(
                f"{section_id}: source_url does not match manifest."
            )

        title = section["title"]

        if not isinstance(title, str) or not title.strip():
            raise SectionsValidationError(
                f"{section_id}: invalid title."
            )

        heading_path = section["heading_path"]

        if (
            not isinstance(heading_path, list)
            or not heading_path
            or heading_path[-1] != title
        ):
            raise SectionsValidationError(
                f"{section_id}: invalid heading_path."
            )

        text = section["text"]

        if not isinstance(text, str) or not text:
            raise SectionsValidationError(
                f"{section_id}: empty text."
            )

        expected_hash = "sha256:" + sha256_text(text)

        if section["content_sha256"] != expected_hash:
            raise SectionsValidationError(
                f"{section_id}: content hash mismatch."
            )

        order = section["section_order"]

        if not isinstance(order, int) or order < 1:
            raise SectionsValidationError(
                f"{section_id}: invalid section_order."
            )

        ids.append(section_id)
        orders_by_doc.setdefault(document_id, []).append(order)

    if len(ids) != len(set(ids)):
        raise SectionsValidationError(
            "Duplicate section IDs found."
        )

    for document_id, orders in orders_by_doc.items():
        expected = list(range(1, len(orders) + 1))

        if sorted(orders) != expected:
            raise SectionsValidationError(
                f"{document_id}: section_order is not contiguous."
            )

    if require_full_corpus:
        expected_docs = set(docs)
        actual_docs = set(orders_by_doc)

        missing_docs = expected_docs - actual_docs

        if missing_docs:
            raise SectionsValidationError(
                "Sections missing manifest documents: "
                + ", ".join(sorted(missing_docs))
            )


def build_chunking_config(
    tokenizer_name: str,
    target_tokens: int,
    overlap_tokens: int,
) -> dict[str, Any]:
    boundary_search_tokens = max(
        MIN_BOUNDARY_SEARCH_TOKENS,
        round(target_tokens * BOUNDARY_SEARCH_FRACTION),
    )

    boundary_search_tokens = min(
        boundary_search_tokens,
        target_tokens - overlap_tokens - 1,
    )

    return {
        "strategy": "recursive_boundary",
        "tokenizer": tokenizer_name,
        "tiktoken_version": get_tiktoken_version(),
        "target_tokens": target_tokens,
        "overlap_tokens": overlap_tokens,
        "respect_section_boundaries": True,
        "boundary_search_tokens": boundary_search_tokens,
        "boundary_priority": [
            "blank_line",
            "line_break",
            "sentence_end",
            "whitespace",
            "hard_token_cut",
        ],
    }


def config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return "sha256:" + sha256_text(payload)


def boundary_priority(text_tail: str) -> int:
    if text_tail.endswith("\n\n"):
        return 4

    if text_tail.endswith("\n"):
        return 3

    if SENTENCE_END_RE.search(text_tail):
        return 2

    if text_tail and text_tail[-1].isspace():
        return 1

    return 0


def choose_end(
    *,
    encoding,
    token_ids: list[int],
    start: int,
    target_tokens: int,
    overlap_tokens: int,
    boundary_search_tokens: int,
) -> int:
    total = len(token_ids)
    desired_end = min(start + target_tokens, total)

    if desired_end >= total:
        return total

    earliest = max(
        start + overlap_tokens + 1,
        desired_end - boundary_search_tokens,
    )

    if earliest >= desired_end:
        return desired_end

    for priority in (4, 3, 2, 1):
        for candidate in range(
            desired_end,
            earliest - 1,
            -1,
        ):
            tail_start = max(start, candidate - 16)
            tail = encoding.decode(
                token_ids[tail_start:candidate]
            )

            if boundary_priority(tail) == priority:
                return candidate

    return desired_end


def split_token_spans(
    *,
    encoding,
    text: str,
    target_tokens: int,
    overlap_tokens: int,
    boundary_search_tokens: int,
) -> tuple[list[int], list[tuple[int, int]]]:
    token_ids = encoding.encode(
        text,
        disallowed_special=(),
    )

    if not token_ids:
        raise ChunkBuildError(
            "Section encoded to zero tokens."
        )

    if len(token_ids) <= target_tokens:
        return token_ids, [(0, len(token_ids))]

    spans: list[tuple[int, int]] = []
    start = 0

    while start < len(token_ids):
        end = choose_end(
            encoding=encoding,
            token_ids=token_ids,
            start=start,
            target_tokens=target_tokens,
            overlap_tokens=overlap_tokens,
            boundary_search_tokens=boundary_search_tokens,
        )

        if end <= start:
            raise ChunkBuildError(
                f"Chunker made no progress: {start=} {end=}."
            )

        spans.append((start, end))

        if end >= len(token_ids):
            break

        next_start = end - overlap_tokens

        if next_start <= start:
            raise ChunkBuildError(
                "Overlap prevents forward progress."
            )

        start = next_start

    return token_ids, spans


def make_chunk_id(
    section_id: str,
    chunk_index: int,
) -> str:
    return f"{section_id}-ch-{chunk_index:03d}"


def build_chunks_for_section(
    *,
    section: dict[str, Any],
    encoding,
    config: dict[str, Any],
    chunk_config_hash: str,
) -> list[dict[str, Any]]:
    section_id = str(section["section_id"])

    token_ids, spans = split_token_spans(
        encoding=encoding,
        text=str(section["text"]),
        target_tokens=int(config["target_tokens"]),
        overlap_tokens=int(config["overlap_tokens"]),
        boundary_search_tokens=int(config["boundary_search_tokens"]),
    )

    chunks: list[dict[str, Any]] = []
    previous_end: int | None = None

    for chunk_index, (start, end) in enumerate(
        spans,
        start=1,
    ):
        chunk_text = encoding.decode(
            token_ids[start:end]
        )

        token_count = len(
            encoding.encode(
                chunk_text,
                disallowed_special=(),
            )
        )

        overlap = (
            0
            if previous_end is None
            else max(0, previous_end - start)
        )

        chunks.append(
            {
                "schema_version": SCHEMA_VERSION,
                "chunk_builder_version": CHUNK_BUILDER_VERSION,
                "corpus_version": section["corpus_version"],

                "chunk_id": make_chunk_id(
                    section_id,
                    chunk_index,
                ),
                "document_id": section["document_id"],
                "section_id": section_id,
                "domain": section["domain"],

                "section_title": section["title"],
                "heading_path": section["heading_path"],
                "chunk_index": chunk_index,

                "text": chunk_text,
                "token_count": token_count,
                "tokenizer": config["tokenizer"],

                "section_token_start": start,
                "section_token_end_exclusive": end,
                "overlap_tokens_with_previous": overlap,

                "source_url": section["source_url"],

                "source_document_content_sha256": (
                    section["source_document_content_sha256"]
                ),
                "section_content_sha256": section["content_sha256"],
                "content_sha256": "sha256:" + sha256_text(chunk_text),

                "chunking_config_sha256": chunk_config_hash,
            }
        )

        previous_end = end

    return chunks


def validate_chunks_for_section(
    *,
    section: dict[str, Any],
    chunks: list[dict[str, Any]],
    encoding,
    config: dict[str, Any],
    chunk_config_hash: str,
) -> None:
    if not chunks:
        raise ChunkValidationError(
            f"{section['section_id']}: no chunks generated."
        )

    target = int(config["target_tokens"])
    expected_overlap = int(config["overlap_tokens"])

    section_tokens = encoding.encode(
        str(section["text"]),
        disallowed_special=(),
    )

    previous_end: int | None = None

    for expected_index, chunk in enumerate(chunks, start=1):
        chunk_id = str(chunk["chunk_id"])
        match = CHUNK_ID_RE.fullmatch(chunk_id)

        if not match:
            raise ChunkValidationError(
                f"Invalid chunk_id: {chunk_id!r}"
            )

        if match.group("section") != section["section_id"]:
            raise ChunkValidationError(
                f"{chunk_id}: section ID mismatch."
            )

        if int(match.group("chunk")) != expected_index:
            raise ChunkValidationError(
                f"{chunk_id}: chunk sequence mismatch."
            )

        start = chunk["section_token_start"]
        end = chunk["section_token_end_exclusive"]

        if not (
            isinstance(start, int)
            and isinstance(end, int)
            and 0 <= start < end <= len(section_tokens)
        ):
            raise ChunkValidationError(
                f"{chunk_id}: invalid token span {start}:{end}."
            )

        expected_text = encoding.decode(
            section_tokens[start:end]
        )

        if chunk["text"] != expected_text:
            raise ChunkValidationError(
                f"{chunk_id}: text does not match section span."
            )

        actual_count = len(
            encoding.encode(
                chunk["text"],
                disallowed_special=(),
            )
        )

        if chunk["token_count"] != actual_count:
            raise ChunkValidationError(
                f"{chunk_id}: token_count mismatch."
            )

        if actual_count > target:
            raise ChunkValidationError(
                f"{chunk_id}: {actual_count} tokens exceeds target {target}."
            )

        if chunk["content_sha256"] != (
            "sha256:" + sha256_text(chunk["text"])
        ):
            raise ChunkValidationError(
                f"{chunk_id}: content hash mismatch."
            )

        if chunk["chunking_config_sha256"] != chunk_config_hash:
            raise ChunkValidationError(
                f"{chunk_id}: config hash mismatch."
            )

        if expected_index == 1:
            if start != 0:
                raise ChunkValidationError(
                    f"{chunk_id}: first chunk must start at token 0."
                )

            if chunk["overlap_tokens_with_previous"] != 0:
                raise ChunkValidationError(
                    f"{chunk_id}: first chunk cannot have overlap."
                )
        else:
            if previous_end is None:
                raise ChunkValidationError(
                    f"{chunk_id}: previous chunk tracking failed."
                )

            actual_overlap = previous_end - start

            if actual_overlap != expected_overlap:
                raise ChunkValidationError(
                    f"{chunk_id}: expected {expected_overlap} overlap "
                    f"tokens, got {actual_overlap}."
                )

            if (
                chunk["overlap_tokens_with_previous"]
                != actual_overlap
            ):
                raise ChunkValidationError(
                    f"{chunk_id}: overlap metadata mismatch."
                )

        previous_end = end

    if chunks[-1]["section_token_end_exclusive"] != len(section_tokens):
        raise ChunkValidationError(
            f"{section['section_id']}: final chunk does not reach section end."
        )


def validate_chunk_corpus(
    chunks: list[dict[str, Any]],
    selected_sections: list[dict[str, Any]],
) -> None:
    chunk_ids = [
        str(chunk["chunk_id"])
        for chunk in chunks
    ]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ChunkValidationError(
            "Duplicate chunk IDs found."
        )

    expected_sections = {
        str(section["section_id"])
        for section in selected_sections
    }

    actual_sections = {
        str(chunk["section_id"])
        for chunk in chunks
    }

    if expected_sections != actual_sections:
        missing = expected_sections - actual_sections
        extra = actual_sections - expected_sections

        raise ChunkValidationError(
            "Chunk/section referential mismatch. "
            f"Missing={sorted(missing)} Extra={sorted(extra)}"
        )


def write_chunks(
    path: Path,
    chunks: list[dict[str, Any]],
) -> str:
    ordered = sorted(
        chunks,
        key=lambda chunk: (
            str(chunk["document_id"]),
            str(chunk["section_id"]),
            int(chunk["chunk_index"]),
        ),
    )

    content = "\n".join(
        json.dumps(
            chunk,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for chunk in ordered
    )

    if content:
        content += "\n"

    atomic_write_text(path, content)

    return "sha256:" + sha256_bytes(
        content.encode("utf-8")
    )


def percentile(
    values: list[int],
    fraction: float,
) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)

    if len(ordered) == 1:
        return float(ordered[0])

    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower

    return (
        ordered[lower] * (1 - weight)
        + ordered[upper] * weight
    )


def write_report(
    *,
    report_path: Path,
    manifest_path: Path,
    sections_path: Path,
    output_path: Path,
    output_hash: str | None,
    config: dict[str, Any],
    chunk_config_hash: str,
    selected_sections: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    results: list[dict[str, Any]],
    success: bool,
) -> None:
    token_counts = [
        int(chunk["token_count"])
        for chunk in chunks
    ]

    report = {
        "schema_version": SCHEMA_VERSION,
        "stage": "build_chunks",
        "chunk_builder_version": CHUNK_BUILDER_VERSION,

        "manifest": manifest_path.as_posix(),
        "sections_input": sections_path.as_posix(),
        "output": output_path.as_posix(),
        "output_sha256": output_hash,

        "status": "SUCCESS" if success else "FAILED",

        "chunking_config": config,
        "chunking_config_sha256": chunk_config_hash,

        "documents_selected": len(
            {
                str(section["document_id"])
                for section in selected_sections
            }
        ),
        "sections_selected": len(selected_sections),
        "sections_processed": len(results),
        "sections_failed": sum(
            result["status"] == "failed"
            for result in results
        ),
        "sections_single_chunk": sum(
            result.get("chunk_count") == 1
            for result in results
            if result["status"] == "success"
        ),
        "sections_split": sum(
            (result.get("chunk_count") or 0) > 1
            for result in results
            if result["status"] == "success"
        ),

        "chunks_generated": len(chunks),

        "token_statistics": {
            "total_including_overlap": sum(token_counts),
            "minimum": min(token_counts, default=0),
            "maximum": max(token_counts, default=0),
            "mean": (
                round(statistics.fmean(token_counts), 3)
                if token_counts
                else 0.0
            ),
            "median": (
                round(statistics.median(token_counts), 3)
                if token_counts
                else 0.0
            ),
            "p90": round(percentile(token_counts, 0.90), 3),
            "p95": round(percentile(token_counts, 0.95), 3),
        },

        "sections": results,
    }

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


def print_summary(
    *,
    selected_sections: list[dict[str, Any]],
    results: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    config: dict[str, Any],
    chunk_config_hash: str,
    output_path: Path,
    report_path: Path,
    success: bool,
) -> None:
    token_counts = [
        int(chunk["token_count"])
        for chunk in chunks
    ]

    print()
    print("-" * 76)
    print(
        f"Documents selected:  "
        f"{len({s['document_id'] for s in selected_sections})}"
    )
    print(f"Sections selected:   {len(selected_sections)}")
    print(f"Sections processed:  {len(results)}")
    print(
        "Sections failed:     "
        f"{sum(r['status'] == 'failed' for r in results)}"
    )
    print(f"Chunks generated:    {len(chunks)}")
    print(
        "Target / overlap:    "
        f"{config['target_tokens']} / "
        f"{config['overlap_tokens']} tokens"
    )
    print(f"Tokenizer:           {config['tokenizer']}")

    if token_counts:
        print(
            "Chunk tokens:        "
            f"min={min(token_counts)}  "
            f"mean={statistics.fmean(token_counts):.1f}  "
            f"max={max(token_counts)}"
        )

    print(f"Config hash:         {chunk_config_hash}")
    print(f"Output:              {output_path}")
    print(f"Report:              {report_path}")
    print(
        "Status:              "
        f"{'SUCCESS' if success else 'FAILED'}"
    )
    print("-" * 76)


def run(
    *,
    manifest_path: Path,
    sections_path: Path,
    output_path: Path,
    report_path: Path,
    tokenizer_name: str,
    target_tokens: int,
    overlap_tokens: int,
    document_id: str | None,
    section_id: str | None,
    limit_sections: int | None,
    continue_on_error: bool,
) -> int:
    print(f"Validating manifest: {manifest_path}")

    try:
        manifest = load_manifest(manifest_path)
        validate_manifest(manifest)
    except ManifestValidationError as exc:
        print("Manifest validation failed.")
        print(exc)
        return 1
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Failed to load manifest: {exc}")
        return 1

    print("Manifest validation: PASSED")

    try:
        sections = load_sections(sections_path)

        full_run = (
            document_id is None
            and section_id is None
            and limit_sections is None
        )

        validate_sections(
            sections,
            manifest,
            require_full_corpus=full_run,
        )
    except (
        OSError,
        ValueError,
        SectionsValidationError,
    ) as exc:
        print("Sections validation failed.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print(
        f"Sections validation: PASSED "
        f"({len(sections):,} records)"
    )

    selected = list(sections)

    if document_id is not None:
        selected = [
            section
            for section in selected
            if section["document_id"] == document_id
        ]

        if not selected:
            print(
                f"ERROR: no sections found for document {document_id!r}."
            )
            return 1

    if section_id is not None:
        selected = [
            section
            for section in selected
            if section["section_id"] == section_id
        ]

        if not selected:
            print(
                f"ERROR: section {section_id!r} was not found."
            )
            return 1

    selected = sorted(
        selected,
        key=lambda section: (
            str(section["document_id"]),
            int(section["section_order"]),
        ),
    )

    if limit_sections is not None:
        selected = selected[:limit_sections]

    if not selected:
        print("ERROR: no sections selected.")
        return 1

    try:
        encoding = get_encoding(tokenizer_name)
    except ChunkBuildError as exc:
        print(exc)
        return 1

    config = build_chunking_config(
        tokenizer_name,
        target_tokens,
        overlap_tokens,
    )

    chunk_config_hash = config_hash(config)

    print()
    print("Chunking configuration:")
    print(f"  tokenizer:       {config['tokenizer']}")
    print(f"  target tokens:   {config['target_tokens']}")
    print(f"  overlap tokens:  {config['overlap_tokens']}")
    print(f"  boundary search: {config['boundary_search_tokens']}")
    print(f"  config hash:     {chunk_config_hash}")
    print()

    all_chunks: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    total = len(selected)

    for index, section in enumerate(selected, start=1):
        sid = str(section["section_id"])

        print(
            f"[{index:04d}/{total:04d}] "
            f"{sid:<24} {section['title']}"
        )

        try:
            chunks = build_chunks_for_section(
                section=section,
                encoding=encoding,
                config=config,
                chunk_config_hash=chunk_config_hash,
            )

            validate_chunks_for_section(
                section=section,
                chunks=chunks,
                encoding=encoding,
                config=config,
                chunk_config_hash=chunk_config_hash,
            )

            all_chunks.extend(chunks)

            section_tokens = len(
                encoding.encode(
                    section["text"],
                    disallowed_special=(),
                )
            )

            max_chunk_tokens = max(
                int(chunk["token_count"])
                for chunk in chunks
            )

            results.append(
                {
                    "section_id": sid,
                    "document_id": section["document_id"],
                    "status": "success",
                    "section_token_count": section_tokens,
                    "chunk_count": len(chunks),
                    "error": None,
                }
            )

            print(
                f"    {section_tokens} section tokens  "
                f"{len(chunks)} chunk(s)  "
                f"max={max_chunk_tokens}  OK"
            )

        except Exception as exc:
            results.append(
                {
                    "section_id": sid,
                    "document_id": section["document_id"],
                    "status": "failed",
                    "section_token_count": 0,
                    "chunk_count": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

            print(
                f"    FAILED: {type(exc).__name__}: {exc}"
            )

            if not continue_on_error:
                print(
                    "Stopping because fail-fast mode is enabled."
                )
                break

    failed = any(
        result["status"] == "failed"
        for result in results
    )

    incomplete = len(results) != len(selected)
    success = not failed and not incomplete

    output_hash: str | None = None

    if success:
        try:
            validate_chunk_corpus(
                all_chunks,
                selected,
            )

            output_hash = write_chunks(
                output_path,
                all_chunks,
            )
        except ChunkValidationError as exc:
            success = False
            print(
                f"Corpus-level validation failed: {exc}"
            )

    write_report(
        report_path=report_path,
        manifest_path=manifest_path,
        sections_path=sections_path,
        output_path=output_path,
        output_hash=output_hash,
        config=config,
        chunk_config_hash=chunk_config_hash,
        selected_sections=selected,
        chunks=all_chunks,
        results=results,
        success=success,
    )

    print_summary(
        selected_sections=selected,
        results=results,
        chunks=all_chunks,
        config=config,
        chunk_config_hash=chunk_config_hash,
        output_path=output_path,
        report_path=report_path,
        success=success,
    )

    return 0 if success else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic section-bounded chunks from "
            "GroundTruth sections.jsonl."
        )
    )

    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to corpus manifest YAML.",
    )

    parser.add_argument(
        "--sections",
        type=Path,
        default=DEFAULT_SECTIONS,
        help=f"Input sections JSONL. Default: {DEFAULT_SECTIONS}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output chunks JSONL. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Chunk report JSON. Default: {DEFAULT_REPORT}",
    )

    parser.add_argument(
        "--tokenizer",
        default=DEFAULT_TOKENIZER,
        help=f"tiktoken encoding. Default: {DEFAULT_TOKENIZER}",
    )

    parser.add_argument(
        "--target-tokens",
        type=int,
        default=DEFAULT_TARGET_TOKENS,
        help=f"Maximum tokens per chunk. Default: {DEFAULT_TARGET_TOKENS}",
    )

    parser.add_argument(
        "--overlap-tokens",
        type=int,
        default=DEFAULT_OVERLAP_TOKENS,
        help=f"Adjacent chunk overlap. Default: {DEFAULT_OVERLAP_TOKENS}",
    )

    parser.add_argument(
        "--document-id",
        default=None,
        help="Process one document only, e.g. net-002.",
    )

    parser.add_argument(
        "--section-id",
        default=None,
        help="Process one exact section only.",
    )

    parser.add_argument(
        "--limit-sections",
        type=int,
        default=None,
        help="Process only the first N selected sections.",
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue after a section failure.",
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

    if args.target_tokens - args.overlap_tokens < 16:
        parser.error(
            "target minus overlap must leave at least 16 new tokens"
        )

    if (
        args.limit_sections is not None
        and args.limit_sections <= 0
    ):
        parser.error("--limit-sections must be > 0")

    return run(
        manifest_path=args.manifest,
        sections_path=args.sections,
        output_path=args.output,
        report_path=args.report_output,
        tokenizer_name=args.tokenizer,
        target_tokens=args.target_tokens,
        overlap_tokens=args.overlap_tokens,
        document_id=args.document_id,
        section_id=args.section_id,
        limit_sections=args.limit_sections,
        continue_on_error=args.continue_on_error,
    )


if __name__ == "__main__":
    sys.exit(main())
