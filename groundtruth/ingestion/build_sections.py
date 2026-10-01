from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from .validate_manifest import ManifestValidationError, validate_manifest


# =============================================================================
# Configuration
# =============================================================================

SCHEMA_VERSION = "0.1"
SECTION_BUILDER_VERSION = "0.1.0"
DEFAULT_CORPUS_VERSION = "0.1.0"

DEFAULT_EXTRACTED_DIR = Path("data/processed/extracted")
DEFAULT_OUTPUT_PATH = Path("data/processed/sections.jsonl")
DEFAULT_REPORT_PATH = Path("reports/sections_report.json")

SECTION_ID_PATTERN = re.compile(
    r"^(?P<document_id>[a-z0-9]+-[0-9]{3})-sec-(?P<section_number>[0-9]{3})$"
)


# =============================================================================
# Exceptions
# =============================================================================


class SectionBuildError(RuntimeError):
    """Base exception for section-building errors."""


class ExtractedDocumentMissingError(SectionBuildError):
    """Raised when an extracted document JSON file is missing."""


class ExtractedDocumentValidationError(SectionBuildError):
    """Raised when extracted document JSON is malformed."""


class SectionValidationError(SectionBuildError):
    """Raised when generated section records are invalid."""


# =============================================================================
# Generic helpers
# =============================================================================


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    """
    Write UTF-8 text atomically.

    A temporary file is written in the same directory and then renamed over
    the target. This reduces the chance of leaving a partially written output.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    try:
        temporary_path.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Manifest does not exist: {path}")

    with path.open("r", encoding="utf-8") as file:
        manifest = yaml.safe_load(file)

    if not isinstance(manifest, dict):
        raise ValueError("Manifest root must be a YAML mapping.")

    return manifest


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file does not exist: {path}")

    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")

    return value


def normalize_text(text: str) -> str:
    """
    Normalize section text deterministically.

    The extractor already performs the main normalization, so this function
    only standardizes line endings and excessive blank lines.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def count_words(text: str) -> int:
    """
    Deterministic QA word count.

    This is not intended to match an LLM tokenizer.
    """
    return len(
        re.findall(
            r"\b[\w.-]+\b",
            text,
            flags=re.UNICODE,
        )
    )


def canonical_json_line(record: dict[str, Any]) -> str:
    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


# =============================================================================
# Extracted document validation
# =============================================================================


def validate_extracted_document(
    extracted: dict[str, Any],
    manifest_document: dict[str, Any],
) -> None:
    """
    Ensure the extracted document belongs to the manifest entry and contains
    the block structure required for deterministic section construction.
    """
    required_fields = {
        "document_id",
        "domain",
        "title",
        "source_url",
        "content_sha256",
        "blocks",
    }

    missing = required_fields - set(extracted)

    if missing:
        raise ExtractedDocumentValidationError(
            "Missing required extracted-document fields: "
            + ", ".join(sorted(missing))
        )

    expected_document_id = str(manifest_document["id"])

    if extracted["document_id"] != expected_document_id:
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: extracted document_id is "
            f"{extracted['document_id']!r}."
        )

    if extracted["domain"] != manifest_document["domain"]:
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: domain mismatch."
        )

    if extracted["title"] != manifest_document["title"]:
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: title mismatch."
        )

    if extracted["source_url"] != manifest_document["url"]:
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: source URL mismatch."
        )

    content_sha256 = extracted["content_sha256"]

    if (
        not isinstance(content_sha256, str)
        or not content_sha256.startswith("sha256:")
    ):
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: invalid content_sha256."
        )

    blocks = extracted["blocks"]

    if not isinstance(blocks, list):
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: blocks must be a list."
        )

    if not blocks:
        raise ExtractedDocumentValidationError(
            f"{expected_document_id}: blocks must not be empty."
        )

    for position, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ExtractedDocumentValidationError(
                f"{expected_document_id}: block {position} must be an object."
            )

        block_type = block.get("type")

        if not isinstance(block_type, str) or not block_type:
            raise ExtractedDocumentValidationError(
                f"{expected_document_id}: block {position} has no valid type."
            )

        block_index = block.get("block_index")

        if block_index != position:
            raise ExtractedDocumentValidationError(
                f"{expected_document_id}: block at list position {position} "
                f"has block_index={block_index!r}; expected {position}."
            )

        text = block.get("text")

        if text is not None and not isinstance(text, str):
            raise ExtractedDocumentValidationError(
                f"{expected_document_id}: block {position} has non-string text."
            )

        if block_type == "heading":
            level = block.get("level")

            if not isinstance(level, int) or not 1 <= level <= 6:
                raise ExtractedDocumentValidationError(
                    f"{expected_document_id}: heading block {position} "
                    f"has invalid level {level!r}."
                )

            if not isinstance(text, str) or not text.strip():
                raise ExtractedDocumentValidationError(
                    f"{expected_document_id}: heading block {position} "
                    "has empty text."
                )


# =============================================================================
# Block rendering
# =============================================================================


def render_block(block: dict[str, Any]) -> str:
    """
    Re-render one extractor block into the same Markdown-like representation
    used for section text.
    """
    block_type = str(block.get("type", ""))
    text = str(block.get("text", "")).strip()

    if not text:
        return ""

    if block_type == "heading":
        level = int(block["level"])
        level = min(max(level, 1), 6)
        return f"{'#' * level} {text}"

    if block_type == "code":
        language = str(block.get("language") or "")
        return f"```{language}\n{text}\n```"

    return text


def render_section_text(
    blocks: list[dict[str, Any]],
    block_start: int,
    block_end: int,
) -> str:
    parts: list[str] = []

    for block in blocks[block_start : block_end + 1]:
        rendered = render_block(block)

        if rendered:
            parts.append(rendered)

    return normalize_text("\n\n".join(parts))


# =============================================================================
# Section construction
# =============================================================================


def make_section_id(
    document_id: str,
    section_order: int,
) -> str:
    return f"{document_id}-sec-{section_order:03d}"


def find_heading_positions(
    blocks: list[dict[str, Any]],
) -> list[int]:
    return [
        index
        for index, block in enumerate(blocks)
        if block.get("type") == "heading"
    ]


def build_sections_for_document(
    extracted: dict[str, Any],
    corpus_version: str,
) -> list[dict[str, Any]]:
    """
    Build deterministic, non-overlapping sections.

    Each heading starts a new section. The section ends immediately before
    the next heading of any level.

    Hierarchy is preserved separately using:
      - heading_path
      - parent_section_id

    Example:

        # Service
        intro

        ## Service types
        intro

        ### ClusterIP
        details

    becomes three non-overlapping section records:
      Service
      Service types
      ClusterIP

    rather than copying child text into parent sections.
    """
    document_id = str(extracted["document_id"])
    domain = str(extracted["domain"])
    source_url = str(extracted["source_url"])
    source_content_sha256 = str(extracted["content_sha256"])
    blocks = extracted["blocks"]

    heading_positions = find_heading_positions(blocks)

    if not heading_positions:
        raise SectionBuildError(
            f"{document_id}: extracted document contains no headings."
        )

    sections: list[dict[str, Any]] = []

    # Stack contains the active ancestor chain.
    # Example:
    # [
    #   {"level": 1, "title": "Service", "section_id": "..."},
    #   {"level": 2, "title": "Service types", "section_id": "..."},
    # ]
    hierarchy_stack: list[dict[str, Any]] = []

    for zero_based_heading_number, heading_index in enumerate(
        heading_positions
    ):
        section_order = zero_based_heading_number + 1
        heading_block = blocks[heading_index]

        heading_level = int(heading_block["level"])
        heading_title = str(heading_block["text"]).strip()

        # Pop headings that are not ancestors of the new heading.
        while (
            hierarchy_stack
            and int(hierarchy_stack[-1]["level"]) >= heading_level
        ):
            hierarchy_stack.pop()

        section_id = make_section_id(
            document_id,
            section_order,
        )

        parent_section_id = (
            str(hierarchy_stack[-1]["section_id"])
            if hierarchy_stack
            else None
        )

        heading_path = [
            str(item["title"])
            for item in hierarchy_stack
        ] + [heading_title]

        # Sections are deliberately non-overlapping.
        # The current section owns blocks from this heading up to immediately
        # before the next heading.
        if zero_based_heading_number + 1 < len(heading_positions):
            block_end = (
                heading_positions[zero_based_heading_number + 1] - 1
            )
        else:
            block_end = len(blocks) - 1

        block_start = heading_index

        section_text = render_section_text(
            blocks,
            block_start,
            block_end,
        )

        if not section_text:
            raise SectionBuildError(
                f"{section_id}: generated empty section text."
            )

        section_content_hash = sha256_text(section_text)

        record = {
            "schema_version": SCHEMA_VERSION,
            "section_builder_version": SECTION_BUILDER_VERSION,
            "corpus_version": corpus_version,

            "section_id": section_id,
            "document_id": document_id,
            "domain": domain,

            "title": heading_title,
            "heading_path": heading_path,
            "heading_level": heading_level,
            "section_order": section_order,
            "parent_section_id": parent_section_id,

            "block_start": block_start,
            "block_end": block_end,
            "block_count": block_end - block_start + 1,

            "text": section_text,
            "character_count": len(section_text),
            "word_count": count_words(section_text),

            "source_url": source_url,

            "source_document_content_sha256": source_content_sha256,
            "content_sha256": f"sha256:{section_content_hash}",
        }

        sections.append(record)

        hierarchy_stack.append(
            {
                "level": heading_level,
                "title": heading_title,
                "section_id": section_id,
            }
        )

    return sections


# =============================================================================
# Per-document validation
# =============================================================================


def validate_sections_for_document(
    *,
    document_id: str,
    sections: list[dict[str, Any]],
    source_blocks: list[dict[str, Any]],
) -> None:
    if not sections:
        raise SectionValidationError(
            f"{document_id}: no sections generated."
        )

    section_ids = [
        str(section["section_id"])
        for section in sections
    ]

    if len(section_ids) != len(set(section_ids)):
        raise SectionValidationError(
            f"{document_id}: duplicate section IDs generated."
        )

    sections_by_id = {
        str(section["section_id"]): section
        for section in sections
    }

    previous_block_end = -1

    for expected_order, section in enumerate(
        sections,
        start=1,
    ):
        section_id = str(section["section_id"])

        match = SECTION_ID_PATTERN.fullmatch(section_id)

        if not match:
            raise SectionValidationError(
                f"{document_id}: invalid section ID {section_id!r}."
            )

        if match.group("document_id") != document_id:
            raise SectionValidationError(
                f"{section_id}: section ID document prefix is incorrect."
            )

        if int(match.group("section_number")) != expected_order:
            raise SectionValidationError(
                f"{section_id}: ID sequence does not match section order."
            )

        if section["section_order"] != expected_order:
            raise SectionValidationError(
                f"{section_id}: expected section_order {expected_order}, "
                f"got {section['section_order']}."
            )

        title = section["title"]

        if not isinstance(title, str) or not title.strip():
            raise SectionValidationError(
                f"{section_id}: empty section title."
            )

        heading_level = section["heading_level"]

        if not isinstance(heading_level, int) or not 1 <= heading_level <= 6:
            raise SectionValidationError(
                f"{section_id}: invalid heading level {heading_level!r}."
            )

        heading_path = section["heading_path"]

        if (
            not isinstance(heading_path, list)
            or not heading_path
            or heading_path[-1] != title
        ):
            raise SectionValidationError(
                f"{section_id}: invalid heading_path."
            )

        parent_id = section["parent_section_id"]

        if parent_id is not None:
            if parent_id not in sections_by_id:
                raise SectionValidationError(
                    f"{section_id}: parent section {parent_id!r} not found."
                )

            parent = sections_by_id[parent_id]

            if parent["section_order"] >= section["section_order"]:
                raise SectionValidationError(
                    f"{section_id}: parent must occur before child."
                )

            if parent["heading_level"] >= heading_level:
                raise SectionValidationError(
                    f"{section_id}: parent heading level must be lower "
                    "than child heading level."
                )

            expected_path_prefix = parent["heading_path"]

            if heading_path[:-1] != expected_path_prefix:
                raise SectionValidationError(
                    f"{section_id}: heading_path does not match parent."
                )

        block_start = section["block_start"]
        block_end = section["block_end"]

        if not isinstance(block_start, int) or not isinstance(block_end, int):
            raise SectionValidationError(
                f"{section_id}: block range must contain integers."
            )

        if block_start < 0:
            raise SectionValidationError(
                f"{section_id}: block_start cannot be negative."
            )

        if block_end < block_start:
            raise SectionValidationError(
                f"{section_id}: block_end precedes block_start."
            )

        if block_end >= len(source_blocks):
            raise SectionValidationError(
                f"{section_id}: block_end exceeds source block count."
            )

        # Every section must begin at a heading.
        first_source_block = source_blocks[block_start]

        if first_source_block.get("type") != "heading":
            raise SectionValidationError(
                f"{section_id}: block_start does not point to a heading."
            )

        if first_source_block.get("text") != title:
            raise SectionValidationError(
                f"{section_id}: source heading text does not match title."
            )

        if first_source_block.get("level") != heading_level:
            raise SectionValidationError(
                f"{section_id}: source heading level does not match."
            )

        # Non-overlap check.
        if block_start <= previous_block_end:
            raise SectionValidationError(
                f"{section_id}: section block range overlaps a previous section."
            )

        previous_block_end = block_end

        expected_block_count = block_end - block_start + 1

        if section["block_count"] != expected_block_count:
            raise SectionValidationError(
                f"{section_id}: incorrect block_count."
            )

        text = section["text"]

        if not isinstance(text, str) or not text.strip():
            raise SectionValidationError(
                f"{section_id}: empty section text."
            )

        if section["character_count"] != len(text):
            raise SectionValidationError(
                f"{section_id}: character_count does not match text."
            )

        if section["word_count"] != count_words(text):
            raise SectionValidationError(
                f"{section_id}: word_count does not match text."
            )

        expected_hash = "sha256:" + sha256_text(text)

        if section["content_sha256"] != expected_hash:
            raise SectionValidationError(
                f"{section_id}: content SHA-256 mismatch."
            )


# =============================================================================
# Corpus-level validation
# =============================================================================


def validate_corpus_sections(
    *,
    sections: list[dict[str, Any]],
    expected_document_ids: set[str],
) -> None:
    all_section_ids = [
        str(section["section_id"])
        for section in sections
    ]

    if len(all_section_ids) != len(set(all_section_ids)):
        raise SectionValidationError(
            "Duplicate section IDs exist across the corpus."
        )

    actual_document_ids = {
        str(section["document_id"])
        for section in sections
    }

    missing_documents = (
        expected_document_ids - actual_document_ids
    )

    unexpected_documents = (
        actual_document_ids - expected_document_ids
    )

    if missing_documents:
        raise SectionValidationError(
            "No sections generated for expected documents: "
            + ", ".join(sorted(missing_documents))
        )

    if unexpected_documents:
        raise SectionValidationError(
            "Sections generated for unexpected documents: "
            + ", ".join(sorted(unexpected_documents))
        )

    section_id_set = set(all_section_ids)

    for section in sections:
        parent_id = section["parent_section_id"]

        if (
            parent_id is not None
            and parent_id not in section_id_set
        ):
            raise SectionValidationError(
                f"{section['section_id']}: orphan parent "
                f"{parent_id!r}."
            )


# =============================================================================
# Output and reporting
# =============================================================================


def write_sections_jsonl(
    output_path: Path,
    sections: list[dict[str, Any]],
) -> None:
    ordered_sections = sorted(
        sections,
        key=lambda section: (
            str(section["document_id"]),
            int(section["section_order"]),
        ),
    )

    lines = [
        canonical_json_line(section)
        for section in ordered_sections
    ]

    content = "\n".join(lines)

    if content:
        content += "\n"

    atomic_write_text(
        output_path,
        content,
    )


def write_report(
    *,
    report_path: Path,
    manifest_path: Path,
    output_path: Path,
    requested_document_count: int,
    results: list[dict[str, Any]],
    sections: list[dict[str, Any]],
) -> None:
    successful = [
        result
        for result in results
        if result["status"] == "success"
    ]

    failed = [
        result
        for result in results
        if result["status"] == "failed"
    ]

    complete = len(results) == requested_document_count

    report = {
        "schema_version": SCHEMA_VERSION,
        "stage": "build_sections",
        "section_builder_version": SECTION_BUILDER_VERSION,

        "manifest": manifest_path.as_posix(),
        "output": output_path.as_posix(),

        "status": (
            "SUCCESS"
            if not failed and complete
            else "FAILED"
        ),

        "documents_requested": requested_document_count,
        "documents_processed": len(results),
        "documents_successful": len(successful),
        "documents_failed": len(failed),

        "total_sections": len(sections),

        "root_sections": sum(
            section["parent_section_id"] is None
            for section in sections
        ),

        "total_characters": sum(
            int(section["character_count"])
            for section in sections
        ),

        "total_words": sum(
            int(section["word_count"])
            for section in sections
        ),

        "maximum_heading_level": max(
            (
                int(section["heading_level"])
                for section in sections
            ),
            default=0,
        ),

        "documents": results,
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
    results: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    output_path: Path,
    report_path: Path,
) -> None:
    successful = [
        result
        for result in results
        if result["status"] == "success"
    ]

    failed = [
        result
        for result in results
        if result["status"] == "failed"
    ]

    print()
    print("-" * 72)
    print(f"Documents processed: {len(results)}")
    print(f"Successful:          {len(successful)}")
    print(f"Failed:              {len(failed)}")
    print(f"Sections generated:  {len(sections)}")
    print(
        "Root sections:       "
        f"{sum(s['parent_section_id'] is None for s in sections)}"
    )
    print(f"Output:              {output_path}")
    print(f"Report:              {report_path}")
    print(
        "Status:              "
        f"{'SUCCESS' if not failed else 'FAILED'}"
    )
    print("-" * 72)


# =============================================================================
# Pipeline orchestration
# =============================================================================


def run_section_build(
    *,
    manifest_path: Path,
    extracted_dir: Path,
    output_path: Path,
    report_path: Path,
    corpus_version: str,
    document_id: str | None,
    limit: int | None,
    continue_on_error: bool,
) -> int:
    print(f"Validating manifest: {manifest_path}")

    try:
        manifest = load_manifest(manifest_path)

        # validate_manifest() in this project expects the already-loaded
        # YAML dictionary rather than a Path object.
        validate_manifest(manifest)

    except ManifestValidationError as exc:
        print()
        print("Manifest validation failed.")
        print(exc)
        return 1

    except (OSError, ValueError, yaml.YAMLError) as exc:
        print()
        print("Failed to load manifest.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print("Manifest validation: PASSED")
    print()

    documents = list(manifest["documents"])

    # Development mode: select one document.
    if document_id is not None:
        documents = [
            document
            for document in documents
            if document["id"] == document_id
        ]

        if not documents:
            print(
                f"ERROR: document ID {document_id!r} "
                "was not found in the manifest."
            )
            return 1

    # Optional small-batch development mode.
    if limit is not None:
        documents = documents[:limit]

    if not documents:
        print("ERROR: no documents selected.")
        return 1

    all_sections: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    total = len(documents)

    for index, manifest_document in enumerate(
        documents,
        start=1,
    ):
        document_id_value = str(
            manifest_document["id"]
        )

        extracted_path = (
            extracted_dir
            / f"{document_id_value}.json"
        )

        print(
            f"[{index:03d}/{total:03d}] "
            f"{document_id_value:<12} "
            f"{manifest_document['title']}"
        )

        try:
            if not extracted_path.exists():
                raise ExtractedDocumentMissingError(
                    f"Extracted JSON not found: {extracted_path}"
                )

            extracted = load_json_object(
                extracted_path
            )

            validate_extracted_document(
                extracted,
                manifest_document,
            )

            sections = build_sections_for_document(
                extracted,
                corpus_version=corpus_version,
            )

            validate_sections_for_document(
                document_id=document_id_value,
                sections=sections,
                source_blocks=extracted["blocks"],
            )

            all_sections.extend(sections)

            root_count = sum(
                section["parent_section_id"] is None
                for section in sections
            )

            maximum_heading_level = max(
                int(section["heading_level"])
                for section in sections
            )

            results.append(
                {
                    "document_id": document_id_value,
                    "status": "success",
                    "extracted_path": extracted_path.as_posix(),
                    "section_count": len(sections),
                    "root_section_count": root_count,
                    "maximum_heading_level": maximum_heading_level,
                    "error": None,
                }
            )

            print(
                f"    {len(sections)} sections  "
                f"{root_count} roots  "
                f"max H{maximum_heading_level}  OK"
            )

        except Exception as exc:
            results.append(
                {
                    "document_id": document_id_value,
                    "status": "failed",
                    "extracted_path": extracted_path.as_posix(),
                    "section_count": 0,
                    "root_section_count": 0,
                    "maximum_heading_level": 0,
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

            print(
                f"    FAILED: "
                f"{type(exc).__name__}: {exc}"
            )

            if not continue_on_error:
                print()
                print(
                    "Stopping because fail-fast mode "
                    "is enabled."
                )
                break

    failed = any(
        result["status"] == "failed"
        for result in results
    )

    incomplete = len(results) != len(documents)

    # Do not write a canonical sections corpus if the selected run failed or
    # stopped early. This prevents partial data from looking valid.
    if not failed and not incomplete:
        expected_document_ids = {
            str(document["id"])
            for document in documents
        }

        validate_corpus_sections(
            sections=all_sections,
            expected_document_ids=expected_document_ids,
        )

        write_sections_jsonl(
            output_path,
            all_sections,
        )

    write_report(
        report_path=report_path,
        manifest_path=manifest_path,
        output_path=output_path,
        requested_document_count=len(documents),
        results=results,
        sections=all_sections,
    )

    print_summary(
        results=results,
        sections=all_sections,
        output_path=output_path,
        report_path=report_path,
    )

    return 1 if failed or incomplete else 0


# =============================================================================
# CLI
# =============================================================================


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic hierarchical sections from "
            "GroundTruth extracted-document JSON files."
        )
    )

    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to the corpus manifest YAML file.",
    )

    parser.add_argument(
        "--extracted-dir",
        type=Path,
        default=DEFAULT_EXTRACTED_DIR,
        help=(
            "Directory containing extracted "
            "{document_id}.json files. "
            f"Default: {DEFAULT_EXTRACTED_DIR}"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=(
            "Sections JSONL output path. "
            f"Default: {DEFAULT_OUTPUT_PATH}"
        ),
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=(
            "Section build report output path. "
            f"Default: {DEFAULT_REPORT_PATH}"
        ),
    )

    parser.add_argument(
        "--corpus-version",
        type=str,
        default=DEFAULT_CORPUS_VERSION,
        help=(
            "Corpus version stamped into every section. "
            f"Default: {DEFAULT_CORPUS_VERSION}"
        ),
    )

    parser.add_argument(
        "--document-id",
        type=str,
        default=None,
        help=(
            "Build sections for one document only. "
            "Example: --document-id net-002"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Build sections for only the first N "
            "selected documents."
        ),
    )

    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help=(
            "Continue after a document fails. "
            "Default behaviour is fail-fast."
        ),
    )

    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error(
            "--limit must be greater than 0"
        )

    if not args.corpus_version.strip():
        parser.error(
            "--corpus-version must not be empty"
        )

    return run_section_build(
        manifest_path=args.manifest,
        extracted_dir=args.extracted_dir,
        output_path=args.output,
        report_path=args.report_output,
        corpus_version=args.corpus_version.strip(),
        document_id=args.document_id,
        limit=args.limit,
        continue_on_error=args.continue_on_error,
    )


if __name__ == "__main__":
    sys.exit(main())
