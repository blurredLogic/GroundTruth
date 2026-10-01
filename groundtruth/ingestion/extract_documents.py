from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup, NavigableString, Tag

from .validate_manifest import ManifestValidationError, validate_manifest


SCHEMA_VERSION = "0.1"
EXTRACTION_VERSION = "0.1.0"

DEFAULT_RAW_DIR = Path("data/raw/documents")
DEFAULT_OUTPUT_DIR = Path("data/processed/extracted")
DEFAULT_REPORT_PATH = Path("reports/extraction_report.json")

MIN_EXTRACTED_CHARACTERS = 500
MIN_EXTRACTED_WORDS = 100

CONTENT_SELECTORS = (
    ".td-content",
    "main[role='main'] .td-content",
    "main[role='main']",
    "article",
    "main",
)

REMOVE_SELECTORS = (
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "nav",
    "footer",
    "form",
    "button",
    "input",
    "select",
    "textarea",
    ".td-sidebar",
    ".td-sidebar-nav",
    ".td-toc",
    ".td-toc-menu",
    ".td-page-meta",
    ".td-page-meta--child",
    ".td-feedback",
    ".feedback",
    ".page-feedback",
    ".td-print-footer",
    ".d-print-none",
    ".clipboard",
    ".btn-clipboard",
    ".copy-code",
    ".copy-to-clipboard",
    "[data-clipboard-target]",
    "[data-clipboard-text]",
)

DECORATIVE_SELECTORS = (
    "a.anchor",
    "a.headerlink",
    "a.heading-anchor",
    "a.td-heading-self-link",
    ".anchor-link",
    ".heading-anchor",
    "[aria-hidden='true']",
)

TAIL_STOP_HEADINGS = {"feedback"}


class ExtractionError(RuntimeError):
    pass


class RawDocumentMissingError(ExtractionError):
    pass


class ContentContainerNotFoundError(ExtractionError):
    pass


class ExtractedContentTooSmallError(ExtractionError):
    pass


class ExistingOutputConflictError(ExtractionError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(content)
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
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Manifest root must be a YAML mapping.")
    return data


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize_inline_whitespace(text: str) -> str:
    text = normalize_unicode(text).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", text).strip()


def normalize_code(text: str) -> str:
    text = normalize_unicode(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def normalize_document_text(text: str) -> str:
    text = normalize_unicode(text).replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w.-]+\b", text, flags=re.UNICODE))


def select_content_container(soup: BeautifulSoup) -> tuple[Tag, str]:
    for selector in CONTENT_SELECTORS:
        match = soup.select_one(selector)
        if isinstance(match, Tag):
            visible = normalize_inline_whitespace(match.get_text(" ", strip=True))
            if len(visible) >= MIN_EXTRACTED_CHARACTERS:
                return match, selector
    raise ContentContainerNotFoundError(
        "Could not locate a sufficiently large documentation content container."
    )


def remove_boilerplate(container: Tag) -> None:
    for selector in REMOVE_SELECTORS:
        for match in list(container.select(selector)):
            match.decompose()
    for selector in DECORATIVE_SELECTORS:
        for match in list(container.select(selector)):
            match.decompose()
    for string in list(container.find_all(string=True)):
        if string.__class__.__name__ == "Comment":
            string.extract()


def render_inline(node: Tag, source_url: str) -> str:
    def walk(child: Any) -> str:
        if isinstance(child, NavigableString):
            return str(child)
        if not isinstance(child, Tag):
            return ""

        name = child.name.lower()

        if name == "br":
            return "\n"
        if name == "code":
            raw = normalize_inline_whitespace(child.get_text(" ", strip=False))
            if not raw:
                return ""
            return f"``{raw}``" if "`" in raw else f"`{raw}`"
        if name == "a":
            label = normalize_inline_whitespace(
                "".join(walk(grandchild) for grandchild in child.children)
            )
            href = child.get("href")
            if not label:
                return ""
            if label in {"#", "¶", "§"}:
                return ""
            if href in (None, "", "#"):
                return label
            return f"[{label}]({urljoin(source_url, str(href).strip())})"
        if name in {"strong", "b"}:
            inner = normalize_inline_whitespace(
                "".join(walk(grandchild) for grandchild in child.children)
            )
            return f"**{inner}**" if inner else ""
        if name in {"em", "i"}:
            inner = normalize_inline_whitespace(
                "".join(walk(grandchild) for grandchild in child.children)
            )
            return f"*{inner}*" if inner else ""
        if name in {"del", "s"}:
            inner = normalize_inline_whitespace(
                "".join(walk(grandchild) for grandchild in child.children)
            )
            return f"~~{inner}~~" if inner else ""
        if name == "img":
            alt = normalize_inline_whitespace(str(child.get("alt", "")))
            return f"[Image: {alt}]" if alt else ""

        return "".join(walk(grandchild) for grandchild in child.children)

    rendered = "".join(walk(child) for child in node.children)
    rendered = normalize_unicode(rendered)
    rendered_lines = [
        re.sub(r"[ \t\f\v]+", " ", line).strip()
        for line in rendered.split("\n")
    ]
    return "\n".join(line for line in rendered_lines if line).strip()


def detect_code_language(pre: Tag) -> str | None:
    candidates: list[str] = []
    code = pre.find("code")
    for element in (pre, code, pre.parent):
        if not isinstance(element, Tag):
            continue
        classes = element.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        candidates.extend(str(item) for item in classes)

    for candidate in candidates:
        lower = candidate.lower()
        for prefix in ("language-", "lang-"):
            if lower.startswith(prefix):
                language = candidate[len(prefix):].strip()
                if language:
                    return language
    return None


def render_code_block(pre: Tag) -> dict[str, Any] | None:
    code = pre.find("code")
    text = code.get_text("", strip=False) if isinstance(code, Tag) else pre.get_text("", strip=False)
    text = normalize_code(text)
    if not text:
        return None
    return {
        "type": "code",
        "language": detect_code_language(pre),
        "text": text,
    }


def render_list_item_text(li: Tag, source_url: str) -> str:
    pieces: list[str] = []
    for child in li.children:
        if isinstance(child, Tag) and child.name.lower() in {"ul", "ol"}:
            continue
        if isinstance(child, NavigableString):
            pieces.append(str(child))
        elif isinstance(child, Tag):
            pieces.append(render_inline(child, source_url))
    return normalize_inline_whitespace(" ".join(pieces))


def render_list(list_tag: Tag, source_url: str, depth: int = 0) -> str:
    ordered = list_tag.name.lower() == "ol"
    lines: list[str] = []
    direct_items = list_tag.find_all("li", recursive=False)

    for item_index, li in enumerate(direct_items, start=1):
        prefix = f"{item_index}." if ordered else "-"
        indent = "  " * depth
        text = render_list_item_text(li, source_url)
        if text:
            lines.append(f"{indent}{prefix} {text}")
        for nested in li.find_all(["ul", "ol"], recursive=False):
            nested_text = render_list(nested, source_url, depth + 1)
            if nested_text:
                lines.append(nested_text)

    return "\n".join(lines).strip()


def render_table(table: Tag, source_url: str) -> dict[str, Any] | None:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        if not cells:
            continue
        row = [render_inline(cell, source_url).strip() for cell in cells]
        if any(row):
            rows.append(row)

    if not rows:
        return None

    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]

    def esc(value: str) -> str:
        return value.replace("|", r"\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(esc(cell) for cell in padded[0]) + " |",
        "| " + " | ".join("---" for _ in range(width)) + " |",
    ]
    lines.extend(
        "| " + " | ".join(esc(cell) for cell in row) + " |"
        for row in padded[1:]
    )

    return {"type": "table", "rows": padded, "text": "\n".join(lines)}


def render_definition_list(dl: Tag, source_url: str) -> str:
    lines: list[str] = []
    for child in dl.find_all(["dt", "dd"], recursive=False):
        text = render_inline(child, source_url)
        if not text:
            continue
        lines.append(f"**{text}**" if child.name.lower() == "dt" else f": {text}")
    return "\n".join(lines).strip()


def extract_blocks(
    container: Tag,
    source_url: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    blocks: list[dict[str, Any]] = []
    links: list[dict[str, str]] = []
    seen_links: set[tuple[str, str]] = set()

    semantic_tags = {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "pre", "ul", "ol", "table", "blockquote", "dl", "hr",
    }

    def collect_links(node: Tag) -> None:
        for anchor in node.find_all("a", href=True):
            label = normalize_inline_whitespace(anchor.get_text(" ", strip=True))
            href = str(anchor.get("href", "")).strip()
            if not label or not href or href == "#" or label in {"#", "¶", "§"}:
                continue
            absolute = urljoin(source_url, href)
            key = (label, absolute)
            if key not in seen_links:
                seen_links.add(key)
                links.append({"text": label, "url": absolute})

    def append_block(block: dict[str, Any] | None) -> None:
        if not block:
            return
        text = block.get("text", "")
        if isinstance(text, str) and not text.strip():
            return
        if blocks and blocks[-1].get("type") == block.get("type") and blocks[-1].get("text") == block.get("text"):
            return
        block["block_index"] = len(blocks)
        blocks.append(block)

    def walk(node: Tag) -> None:
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            name = child.name.lower()
            if name in {"script", "style", "noscript", "template"}:
                continue

            if name in semantic_tags:
                collect_links(child)

                if re.fullmatch(r"h[1-6]", name):
                    text = normalize_inline_whitespace(render_inline(child, source_url))
                    if text:
                        append_block({"type": "heading", "level": int(name[1]), "text": text})
                    continue

                if name == "p":
                    text = render_inline(child, source_url).strip()
                    if text:
                        append_block({"type": "paragraph", "text": text})
                    continue

                if name == "pre":
                    append_block(render_code_block(child))
                    continue

                if name in {"ul", "ol"}:
                    text = render_list(child, source_url)
                    if text:
                        append_block({"type": "list", "ordered": name == "ol", "text": text})
                    continue

                if name == "table":
                    append_block(render_table(child, source_url))
                    continue

                if name == "blockquote":
                    text = render_inline(child, source_url).strip()
                    if text:
                        quoted = "\n".join(f"> {line}" for line in text.splitlines() if line.strip())
                        append_block({"type": "blockquote", "text": quoted})
                    continue

                if name == "dl":
                    text = render_definition_list(child, source_url)
                    if text:
                        append_block({"type": "definition_list", "text": text})
                    continue

                if name == "hr":
                    append_block({"type": "separator", "text": "---"})
                    continue

            walk(child)

    walk(container)

    trimmed: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") == "heading":
            heading = normalize_inline_whitespace(str(block.get("text", ""))).casefold()
            if heading in TAIL_STOP_HEADINGS:
                break
        trimmed.append(block)

    for index, block in enumerate(trimmed):
        block["block_index"] = index

    # Keep only links that remain in the final retained content. This avoids
    # carrying feedback/page-metadata links into the extracted document when
    # a tail section was trimmed.
    retained_text = "\n".join(str(block.get("text", "")) for block in trimmed)
    retained_links: list[dict[str, str]] = []
    for link in links:
        markdown_link = f"[{link['text']}]({link['url']})"
        if markdown_link in retained_text:
            retained_links.append(link)

    return trimmed, retained_links


def render_document(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in blocks:
        block_type = block["type"]
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        if block_type == "heading":
            level = min(max(int(block["level"]), 1), 6)
            parts.append(f"{'#' * level} {text}")
        elif block_type == "code":
            language = block.get("language") or ""
            parts.append(f"```{language}\n{text}\n```")
        else:
            parts.append(text)
    return normalize_document_text("\n\n".join(parts))


def build_heading_summary(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"level": block["level"], "text": block["text"], "block_index": block["block_index"]}
        for block in blocks
        if block.get("type") == "heading"
    ]


def build_statistics(
    content: str,
    blocks: list[dict[str, Any]],
    links: list[dict[str, str]],
) -> dict[str, int]:
    return {
        "character_count": len(content),
        "word_count": count_words(content),
        "block_count": len(blocks),
        "heading_count": sum(block.get("type") == "heading" for block in blocks),
        "paragraph_count": sum(block.get("type") == "paragraph" for block in blocks),
        "list_count": sum(block.get("type") == "list" for block in blocks),
        "code_block_count": sum(block.get("type") == "code" for block in blocks),
        "table_count": sum(block.get("type") == "table" for block in blocks),
        "link_count": len(links),
    }


def extract_document(
    *,
    manifest_document: dict[str, Any],
    raw_dir: Path,
) -> dict[str, Any]:
    document_id = str(manifest_document["id"])
    source_url = str(manifest_document["url"])
    raw_path = raw_dir / f"{document_id}.html"

    if not raw_path.exists():
        raise RawDocumentMissingError(f"Raw HTML not found for {document_id}: {raw_path}")

    raw_bytes = raw_path.read_bytes()
    if not raw_bytes:
        raise ExtractionError(f"Raw HTML is empty for {document_id}: {raw_path}")

    raw_sha256 = sha256_bytes(raw_bytes)
    soup = BeautifulSoup(raw_bytes, "html.parser")
    container, selector_used = select_content_container(soup)
    remove_boilerplate(container)

    blocks, links = extract_blocks(container, source_url)
    if not blocks:
        raise ExtractionError(f"No semantic blocks extracted from {document_id}.")

    content = render_document(blocks)
    statistics = build_statistics(content, blocks, links)

    if statistics["character_count"] < MIN_EXTRACTED_CHARACTERS:
        raise ExtractedContentTooSmallError(
            f"{document_id} produced only {statistics['character_count']} characters; "
            f"minimum is {MIN_EXTRACTED_CHARACTERS}."
        )
    if statistics["word_count"] < MIN_EXTRACTED_WORDS:
        raise ExtractedContentTooSmallError(
            f"{document_id} produced only {statistics['word_count']} words; "
            f"minimum is {MIN_EXTRACTED_WORDS}."
        )

    content_sha256 = sha256_bytes(content.encode("utf-8"))

    return {
        "schema_version": SCHEMA_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "document_id": document_id,
        "domain": manifest_document["domain"],
        "title": manifest_document["title"],
        "source_url": source_url,
        "raw_path": raw_path.as_posix(),
        "raw_sha256": f"sha256:{raw_sha256}",
        "content_selector": selector_used,
        "content_sha256": f"sha256:{content_sha256}",
        "statistics": statistics,
        "headings": build_heading_summary(blocks),
        "links": links,
        "blocks": blocks,
        "content": content,
    }


def canonical_json(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_extracted_document(
    *,
    record: dict[str, Any],
    output_dir: Path,
    overwrite_changed: bool,
) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{record['document_id']}.json"
    serialized = canonical_json(record)
    new_hash = sha256_bytes(serialized.encode("utf-8"))

    if output_path.exists():
        existing_hash = sha256_bytes(output_path.read_bytes())
        if existing_hash == new_hash:
            return output_path, "unchanged"
        if not overwrite_changed:
            raise ExistingOutputConflictError(
                f"{output_path} already exists but differs from the newly extracted result.\n"
                f"Existing output SHA-256: {existing_hash}\n"
                f"New output SHA-256:      {new_hash}\n\n"
                "Refusing to silently replace extracted corpus data. "
                "Use --overwrite-changed if this change is intentional."
            )
        atomic_write_text(output_path, serialized)
        return output_path, "overwritten"

    atomic_write_text(output_path, serialized)
    return output_path, "new"


def write_report(
    *,
    report_path: Path,
    manifest_path: Path,
    selected_count: int,
    results: list[dict[str, Any]],
) -> None:
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    report = {
        "schema_version": SCHEMA_VERSION,
        "stage": "extraction",
        "extraction_version": EXTRACTION_VERSION,
        "manifest": manifest_path.as_posix(),
        "status": "SUCCESS" if not failed and len(results) == selected_count else "FAILED",
        "documents_requested": selected_count,
        "successful": len(successful),
        "failed": len(failed),
        "outputs": {
            "new": sum(r.get("output_status") == "new" for r in successful),
            "unchanged": sum(r.get("output_status") == "unchanged" for r in successful),
            "overwritten": sum(r.get("output_status") == "overwritten" for r in successful),
        },
        "totals": {
            "characters": sum(int(r.get("statistics", {}).get("character_count", 0)) for r in successful),
            "words": sum(int(r.get("statistics", {}).get("word_count", 0)) for r in successful),
            "blocks": sum(int(r.get("statistics", {}).get("block_count", 0)) for r in successful),
            "headings": sum(int(r.get("statistics", {}).get("heading_count", 0)) for r in successful),
            "code_blocks": sum(int(r.get("statistics", {}).get("code_block_count", 0)) for r in successful),
            "tables": sum(int(r.get("statistics", {}).get("table_count", 0)) for r in successful),
        },
        "documents": results,
    }

    atomic_write_text(
        report_path,
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def print_summary(
    *,
    results: list[dict[str, Any]],
    output_dir: Path,
    report_path: Path,
) -> None:
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    print()
    print("-" * 72)
    print(f"Documents processed: {len(results)}")
    print(f"Successful:          {len(successful)}")
    print(f"Failed:              {len(failed)}")
    print(f"New outputs:         {sum(r.get('output_status') == 'new' for r in successful)}")
    print(f"Unchanged outputs:   {sum(r.get('output_status') == 'unchanged' for r in successful)}")
    print(f"Overwritten:         {sum(r.get('output_status') == 'overwritten' for r in successful)}")
    print(f"Output directory:    {output_dir}")
    print(f"Report:              {report_path}")
    print(f"Status:              {'SUCCESS' if not failed else 'FAILED'}")
    print("-" * 72)


def run_extraction(
    *,
    manifest_path: Path,
    raw_dir: Path,
    output_dir: Path,
    report_path: Path,
    document_id: str | None,
    limit: int | None,
    overwrite_changed: bool,
    continue_on_error: bool,
) -> int:
    print(f"Validating manifest: {manifest_path}")

    try:
        manifest = load_manifest(manifest_path)
        validate_manifest(manifest)
    except ManifestValidationError as exc:
        print("\nManifest validation failed.")
        print(exc)
        return 1
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print("\nFailed to load manifest.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    print("Manifest validation: PASSED\n")

    documents = list(manifest["documents"])

    if document_id is not None:
        documents = [d for d in documents if d["id"] == document_id]
        if not documents:
            print(f"ERROR: document ID {document_id!r} was not found in the manifest.")
            return 1

    if limit is not None:
        documents = documents[:limit]

    if not documents:
        print("ERROR: no documents selected for extraction.")
        return 1

    results: list[dict[str, Any]] = []
    total = len(documents)

    for index, document in enumerate(documents, start=1):
        doc_id = str(document["id"])
        print(f"[{index:03d}/{total:03d}] {doc_id:<12} {document['title']}")

        try:
            record = extract_document(manifest_document=document, raw_dir=raw_dir)
            output_path, output_status = write_extracted_document(
                record=record,
                output_dir=output_dir,
                overwrite_changed=overwrite_changed,
            )
            stats = record["statistics"]
            results.append(
                {
                    "document_id": doc_id,
                    "status": "success",
                    "output_status": output_status,
                    "output_path": output_path.as_posix(),
                    "raw_sha256": record["raw_sha256"],
                    "content_sha256": record["content_sha256"],
                    "content_selector": record["content_selector"],
                    "statistics": stats,
                    "error": None,
                }
            )
            print(
                f"    {stats['word_count']:,} words  "
                f"{stats['heading_count']} headings  "
                f"{stats['code_block_count']} code  "
                f"{stats['table_count']} tables  "
                f"{output_status:<11} "
                f"{record['content_sha256'][:19]}...  OK"
            )
        except Exception as exc:
            results.append(
                {
                    "document_id": doc_id,
                    "status": "failed",
                    "output_status": None,
                    "output_path": None,
                    "statistics": {},
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"    FAILED: {type(exc).__name__}: {exc}")
            if not continue_on_error:
                print("\nStopping because fail-fast mode is enabled.")
                break

    write_report(
        report_path=report_path,
        manifest_path=manifest_path,
        selected_count=len(documents),
        results=results,
    )
    print_summary(results=results, output_dir=output_dir, report_path=report_path)

    failed = any(r["status"] == "failed" for r in results)
    incomplete = len(results) != len(documents)
    return 1 if failed or incomplete else 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract and deterministically normalize Kubernetes documentation "
            "from GroundTruth raw HTML snapshots."
        )
    )
    parser.add_argument("manifest", type=Path, help="Path to the YAML corpus manifest.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help=f"Directory containing raw {{document_id}}.html files. Default: {DEFAULT_RAW_DIR}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for extracted JSON documents. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Extraction report JSON path. Default: {DEFAULT_REPORT_PATH}",
    )
    parser.add_argument(
        "--document-id",
        type=str,
        default=None,
        help="Extract only one manifest document. Example: --document-id net-002",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Extract only the first N selected documents.",
    )
    parser.add_argument(
        "--overwrite-changed",
        action="store_true",
        help="Allow an existing extracted JSON file to be replaced if extraction changed.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing later documents after an extraction failure.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be greater than 0")

    return run_extraction(
        manifest_path=args.manifest,
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        report_path=args.report_output,
        document_id=args.document_id,
        limit=args.limit,
        overwrite_changed=args.overwrite_changed,
        continue_on_error=args.continue_on_error,
    )


if __name__ == "__main__":
    sys.exit(main())
