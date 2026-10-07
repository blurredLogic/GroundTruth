from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_INDEX_DIR = Path("data/index/bm25")
TOKEN_PATTERN = r"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*"
TOKEN_RE = re.compile(TOKEN_PATTERN)


class BM25RetrieverError(RuntimeError):
    """Raised when the BM25 retriever cannot initialize or search."""


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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise BM25RetrieverError(f"Missing file: {path}")

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BM25RetrieverError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise BM25RetrieverError(
                    f"{path}:{line_number}: expected JSON object."
                )

            records.append(value)

    return records


class BM25Retriever:
    def __init__(
        self,
        *,
        index_dir: Path = DEFAULT_INDEX_DIR,
        verify_hashes: bool = True,
    ) -> None:
        self.index_dir = Path(index_dir)
        self.manifest_path = self.index_dir / "index_manifest.json"
        self.index_path = self.index_dir / "inverted_index.json.gz"
        self.metadata_path = self.index_dir / "metadata.jsonl"

        if not self.manifest_path.exists():
            raise BM25RetrieverError(
                f"Missing BM25 manifest: {self.manifest_path}"
            )

        self.manifest = json.loads(
            self.manifest_path.read_text(encoding="utf-8")
        )

        if self.manifest.get("index_type") != "bm25":
            raise BM25RetrieverError(
                "BM25 manifest has unexpected index_type."
            )

        scoring = self.manifest.get("scoring", {})
        self.k1 = float(scoring.get("k1", 1.5))
        self.b = float(scoring.get("b", 0.75))

        if verify_hashes:
            artifacts = self.manifest.get("artifacts", {})
            expected_index = str(
                artifacts.get("index_sha256", "")
            ).removeprefix("sha256:")
            expected_metadata = str(
                artifacts.get("metadata_sha256", "")
            ).removeprefix("sha256:")

            if expected_index:
                actual = sha256_file(self.index_path)

                if actual != expected_index:
                    raise BM25RetrieverError(
                        "BM25 inverted-index SHA-256 mismatch."
                    )

            if expected_metadata:
                actual = sha256_file(self.metadata_path)

                if actual != expected_metadata:
                    raise BM25RetrieverError(
                        "BM25 metadata SHA-256 mismatch."
                    )

        self.metadata = load_jsonl(self.metadata_path)

        with gzip.open(
            self.index_path,
            mode="rt",
            encoding="utf-8",
        ) as file:
            payload = json.load(file)

        self.document_count = int(payload["document_count"])
        self.avgdl = float(payload["average_document_length"])
        self.document_lengths = [
            int(value)
            for value in payload["document_lengths"]
        ]
        self.terms = payload["terms"]

        if self.document_count != len(self.metadata):
            raise BM25RetrieverError(
                "BM25 index document count does not match metadata."
            )

        if len(self.document_lengths) != self.document_count:
            raise BM25RetrieverError(
                "BM25 document-length count does not match metadata."
            )

        for expected_row, record in enumerate(self.metadata):
            if int(record.get("row_index", -1)) != expected_row:
                raise BM25RetrieverError(
                    "BM25 metadata row_index is not contiguous."
                )

    def describe(self) -> dict[str, Any]:
        return {
            "index_type": "bm25",
            "implementation": self.manifest.get(
                "implementation",
                "groundtruth_native_bm25",
            ),
            "document_count": self.document_count,
            "vocabulary_size": len(self.terms),
            "average_document_length": self.avgdl,
            "k1": self.k1,
            "b": self.b,
            "tokenizer": self.manifest.get("tokenizer"),
        }

    def _allowed_rows(
        self,
        *,
        domains: set[str] | None = None,
        document_ids: set[str] | None = None,
    ) -> set[int] | None:
        if not domains and not document_ids:
            return None

        allowed: set[int] = set()

        for row_index, record in enumerate(self.metadata):
            if domains and str(record["domain"]) not in domains:
                continue

            if (
                document_ids
                and str(record["document_id"]) not in document_ids
            ):
                continue

            allowed.add(row_index)

        return allowed

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        domains: set[str] | None = None,
        document_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise BM25RetrieverError("top_k must be > 0.")

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        allowed_rows = self._allowed_rows(
            domains=domains,
            document_ids=document_ids,
        )

        scores: dict[int, float] = {}

        # Repeated query terms contribute repeatedly, matching a standard
        # bag-of-words BM25 query interpretation.
        for token in query_tokens:
            term = self.terms.get(token)

            if term is None:
                continue

            idf = float(term["idf"])

            for row_index_raw, tf_raw in term["postings"]:
                row_index = int(row_index_raw)

                if (
                    allowed_rows is not None
                    and row_index not in allowed_rows
                ):
                    continue

                tf = float(tf_raw)
                dl = float(self.document_lengths[row_index])

                denominator = (
                    tf
                    + self.k1
                    * (
                        1.0
                        - self.b
                        + self.b * (dl / self.avgdl)
                    )
                )

                contribution = (
                    idf
                    * (
                        tf
                        * (self.k1 + 1.0)
                        / denominator
                    )
                )

                scores[row_index] = (
                    scores.get(row_index, 0.0)
                    + contribution
                )

        if not scores:
            return []

        ranked = sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                str(self.metadata[item[0]]["chunk_id"]),
            ),
        )[:top_k]

        output: list[dict[str, Any]] = []

        for rank, (row_index, score) in enumerate(ranked, start=1):
            record = self.metadata[row_index]

            output.append(
                {
                    "rank": rank,
                    "score": float(score),
                    "chunk_id": record["chunk_id"],
                    "document_id": record["document_id"],
                    "section_id": record["section_id"],
                    "domain": record["domain"],
                    "heading_path": record["heading_path"],
                    "source_url": record["source_url"],
                    "text": record["text"],
                    "retrieval_text": record["retrieval_text"],
                }
            )

        return output


def display_results(
    *,
    query: str,
    retriever: BM25Retriever,
    results: list[dict[str, Any]],
) -> None:
    print("-" * 88)
    print("GroundTruth BM25 Retrieval")
    print("-" * 88)
    print(f"Query:        {query}")
    print(f"Candidates:   {retriever.document_count:,}")
    print(f"Results:      {len(results)}")
    print(f"BM25 k1 / b: {retriever.k1} / {retriever.b}")
    print("-" * 88)

    for result in results:
        heading_path = " > ".join(
            str(value)
            for value in result["heading_path"]
        )

        preview = " ".join(
            str(result["text"]).split()
        )

        if len(preview) > 450:
            preview = preview[:447] + "..."

        print()
        print(
            f"#{result['rank']}  score={result['score']:.6f}"
        )
        print(f"Chunk:    {result['chunk_id']}")
        print(f"Document: {result['document_id']}")
        print(f"Domain:   {result['domain']}")
        print(f"Path:     {heading_path}")
        print(f"Source:   {result['source_url']}")
        print(f"Text:     {preview}")

    print()
    print("-" * 88)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search the GroundTruth BM25 lexical index."
    )

    parser.add_argument(
        "query",
        help="Natural-language search query.",
    )

    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=f"BM25 index directory. Default: {DEFAULT_INDEX_DIR}",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results. Default: 5",
    )

    parser.add_argument(
        "--domain",
        action="append",
        default=[],
        help="Restrict to a domain. Can be repeated.",
    )

    parser.add_argument(
        "--document-id",
        action="append",
        default=[],
        help="Restrict to a document_id. Can be repeated.",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable output.",
    )

    parser.add_argument(
        "--skip-hash-verification",
        action="store_true",
        help="Skip artifact SHA-256 checks.",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        retriever = BM25Retriever(
            index_dir=args.index_dir,
            verify_hashes=not args.skip_hash_verification,
        )

        results = retriever.search(
            args.query,
            top_k=args.top_k,
            domains=set(args.domain) or None,
            document_ids=set(args.document_id) or None,
        )

        if args.json:
            print(
                json.dumps(
                    {
                        "query": args.query,
                        "retriever": retriever.describe(),
                        "results": results,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            display_results(
                query=args.query,
                retriever=retriever,
                results=results,
            )

        return 0

    except BM25RetrieverError as exc:
        print()
        print(f"BM25 retrieval failed: {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("BM25 retrieval interrupted.")
        return 130
    except Exception as exc:
        print()
        print(
            "BM25 retrieval failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
