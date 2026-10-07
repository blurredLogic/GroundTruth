from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BUILDER_VERSION = "0.1.0"

DEFAULT_INPUT = Path("data/index/chunks_indexable.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/index/bm25")

TOKEN_PATTERN = r"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*"
TOKEN_RE = re.compile(TOKEN_PATTERN)

DEFAULT_K1 = 1.5
DEFAULT_B = 0.75


class BM25BuildError(RuntimeError):
    """Raised when the BM25 index cannot be built safely."""


def tokenize(text: str) -> list[str]:
    return [
        match.group(0).lower()
        for match in TOKEN_RE.finditer(text)
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")

    try:
        temp.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        temp.replace(path)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


def atomic_write_gzip_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp.open("wb") as raw_file:
            with gzip.GzipFile(
                fileobj=raw_file,
                mode="wb",
                mtime=0,
            ) as gzip_file:
                payload = (
                    json.dumps(
                        value,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
                gzip_file.write(payload)

        temp.replace(path)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise BM25BuildError(f"Input corpus does not exist: {path}")

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BM25BuildError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise BM25BuildError(
                    f"{path}:{line_number}: record must be an object."
                )

            records.append(value)

    if not records:
        raise BM25BuildError(f"No chunks found in {path}")

    return records


def validate_chunk(chunk: dict[str, Any]) -> None:
    required = {
        "chunk_id",
        "document_id",
        "section_id",
        "domain",
        "heading_path",
        "source_url",
        "text",
        "retrieval_text",
        "content_sha256",
        "retrieval_text_sha256",
    }

    missing = required - set(chunk)

    if missing:
        raise BM25BuildError(
            "Chunk missing required fields: "
            + ", ".join(sorted(missing))
        )

    if not isinstance(chunk["chunk_id"], str) or not chunk["chunk_id"]:
        raise BM25BuildError("chunk_id must be a non-empty string.")

    if not isinstance(chunk["retrieval_text"], str):
        raise BM25BuildError(
            f"{chunk['chunk_id']}: retrieval_text must be a string."
        )

    if not isinstance(chunk["heading_path"], list):
        raise BM25BuildError(
            f"{chunk['chunk_id']}: heading_path must be a list."
        )


def normalized_metadata_record(
    row_index: int,
    chunk: dict[str, Any],
) -> dict[str, Any]:
    return {
        "row_index": row_index,
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "section_id": chunk["section_id"],
        "domain": chunk["domain"],
        "heading_path": chunk["heading_path"],
        "source_url": chunk["source_url"],
        "text": chunk["text"],
        "retrieval_text": chunk["retrieval_text"],
        "content_sha256": chunk["content_sha256"],
        "retrieval_text_sha256": chunk["retrieval_text_sha256"],
    }


def run_build(
    *,
    input_path: Path,
    output_dir: Path,
    k1: float,
    b: float,
) -> int:
    if k1 <= 0:
        raise BM25BuildError("k1 must be > 0.")

    if not 0 <= b <= 1:
        raise BM25BuildError("b must be between 0 and 1.")

    chunks = load_jsonl(input_path)

    for chunk in chunks:
        validate_chunk(chunk)

    chunks = sorted(
        chunks,
        key=lambda row: (
            str(row["document_id"]),
            str(row["section_id"]),
            int(row.get("chunk_index", 0)),
            str(row["chunk_id"]),
        ),
    )

    seen_ids: set[str] = set()
    postings: dict[str, list[list[int]]] = defaultdict(list)
    document_lengths: list[int] = []
    metadata: list[dict[str, Any]] = []

    for row_index, chunk in enumerate(chunks):
        chunk_id = str(chunk["chunk_id"])

        if chunk_id in seen_ids:
            raise BM25BuildError(f"Duplicate chunk_id: {chunk_id}")

        seen_ids.add(chunk_id)

        tokens = tokenize(str(chunk["retrieval_text"]))

        if not tokens:
            raise BM25BuildError(
                f"{chunk_id}: retrieval_text produced no BM25 tokens."
            )

        document_lengths.append(len(tokens))
        term_counts = Counter(tokens)

        for term, tf in sorted(term_counts.items()):
            postings[term].append([row_index, int(tf)])

        metadata.append(normalized_metadata_record(row_index, chunk))

    document_count = len(metadata)
    avgdl = sum(document_lengths) / document_count

    terms: dict[str, dict[str, Any]] = {}

    for term in sorted(postings):
        posting_rows = postings[term]
        df = len(posting_rows)
        idf = math.log(
            1.0
            + (
                (document_count - df + 0.5)
                / (df + 0.5)
            )
        )

        terms[term] = {
            "df": df,
            "idf": idf,
            "postings": posting_rows,
        }

    output_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = output_dir / "metadata.jsonl"
    index_path = output_dir / "inverted_index.json.gz"
    manifest_path = output_dir / "index_manifest.json"

    metadata_text = "\n".join(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for record in metadata
    ) + "\n"

    atomic_write_text(metadata_path, metadata_text)

    index_payload = {
        "format_version": "0.1",
        "document_count": document_count,
        "average_document_length": avgdl,
        "document_lengths": document_lengths,
        "terms": terms,
    }

    atomic_write_gzip_json(index_path, index_payload)

    manifest = {
        "builder_version": BUILDER_VERSION,
        "index_type": "bm25",
        "implementation": "groundtruth_native_bm25",
        "scoring": {
            "formula": "BM25Okapi",
            "k1": k1,
            "b": b,
            "idf": "log(1 + (N - df + 0.5) / (df + 0.5))",
        },
        "tokenizer": {
            "name": "groundtruth_regex_v0.1",
            "pattern": TOKEN_PATTERN,
            "lowercase": True,
        },
        "corpus": {
            "input_path": input_path.as_posix(),
            "input_sha256": "sha256:" + sha256_file(input_path),
            "document_count": document_count,
            "vocabulary_size": len(terms),
            "average_document_length": avgdl,
            "min_document_length": min(document_lengths),
            "max_document_length": max(document_lengths),
        },
        "artifacts": {
            "metadata_path": metadata_path.as_posix(),
            "metadata_sha256": "sha256:" + sha256_file(metadata_path),
            "index_path": index_path.as_posix(),
            "index_sha256": "sha256:" + sha256_file(index_path),
        },
    }

    atomic_write_text(
        manifest_path,
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n",
    )

    print("-" * 76)
    print("BM25 Index Build")
    print("-" * 76)
    print(f"Chunks indexed:       {document_count:,}")
    print(f"Vocabulary:           {len(terms):,}")
    print(f"Average doc length:   {avgdl:.2f} tokens")
    print(f"BM25 k1 / b:          {k1} / {b}")
    print(f"Index:                {index_path}")
    print(f"Metadata:             {metadata_path}")
    print(f"Manifest:             {manifest_path}")
    print("Status:               SUCCESS")
    print("-" * 76)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic BM25 lexical index from the "
            "GroundTruth retrieval-ready chunk corpus."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input chunks JSONL. Default: {DEFAULT_INPUT}",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )

    parser.add_argument(
        "--k1",
        type=float,
        default=DEFAULT_K1,
        help=f"BM25 k1 parameter. Default: {DEFAULT_K1}",
    )

    parser.add_argument(
        "--b",
        type=float,
        default=DEFAULT_B,
        help=f"BM25 b parameter. Default: {DEFAULT_B}",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        return run_build(
            input_path=args.input,
            output_dir=args.output_dir,
            k1=args.k1,
            b=args.b,
        )
    except BM25BuildError as exc:
        print()
        print(f"BM25 index build failed: {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("BM25 index build interrupted.")
        return 130
    except Exception as exc:
        print()
        print(
            "BM25 index build failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
