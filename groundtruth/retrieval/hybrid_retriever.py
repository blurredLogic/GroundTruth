from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from groundtruth.retrieval.bm25_retriever import (
    BM25Retriever,
    BM25RetrieverError,
)
from groundtruth.retrieval.dense_retriever import (
    DenseRetriever,
    DenseRetrieverError,
)


RETRIEVER_VERSION = "0.1.0"

DEFAULT_DENSE_INDEX_DIR = Path("data/index/dense")
DEFAULT_BM25_INDEX_DIR = Path("data/index/bm25")
DEFAULT_TOP_K = 5
DEFAULT_CANDIDATE_K = 50
DEFAULT_RRF_K = 60.0
DEFAULT_DENSE_WEIGHT = 1.0
DEFAULT_BM25_WEIGHT = 1.0


class HybridRetrieverError(RuntimeError):
    """Raised when hybrid retrieval cannot run safely."""


def normalize_optional_filters(
    values: Iterable[str] | None,
) -> set[str] | None:
    if values is None:
        return None

    cleaned = {
        value.strip()
        for value in values
        if value.strip()
    }

    return cleaned or None


def fuse_rrf(
    *,
    dense_results: list[dict[str, Any]],
    bm25_results: list[dict[str, Any]],
    top_k: int,
    rrf_k: float,
    dense_weight: float,
    bm25_weight: float,
) -> list[dict[str, Any]]:
    if top_k <= 0:
        raise HybridRetrieverError("top_k must be > 0.")

    if rrf_k <= 0:
        raise HybridRetrieverError("rrf_k must be > 0.")

    if dense_weight < 0 or bm25_weight < 0:
        raise HybridRetrieverError(
            "Retriever weights must be non-negative."
        )

    if dense_weight == 0 and bm25_weight == 0:
        raise HybridRetrieverError(
            "At least one retriever weight must be > 0."
        )

    fused: dict[str, dict[str, Any]] = {}

    def ensure_entry(
        result: dict[str, Any],
    ) -> dict[str, Any]:
        chunk_id = str(result["chunk_id"])

        if chunk_id not in fused:
            entry = dict(result)
            entry.pop("rank", None)
            entry.pop("score", None)
            entry["dense_rank"] = None
            entry["dense_score"] = None
            entry["bm25_rank"] = None
            entry["bm25_score"] = None
            entry["fusion_score"] = 0.0
            fused[chunk_id] = entry

        return fused[chunk_id]

    for result in dense_results:
        entry = ensure_entry(result)
        rank = int(result["rank"])
        entry["dense_rank"] = rank
        entry["dense_score"] = float(result["score"])
        entry["fusion_score"] += (
            dense_weight / (rrf_k + rank)
        )

    for result in bm25_results:
        entry = ensure_entry(result)
        rank = int(result["rank"])
        entry["bm25_rank"] = rank
        entry["bm25_score"] = float(result["score"])
        entry["fusion_score"] += (
            bm25_weight / (rrf_k + rank)
        )

    ranked = sorted(
        fused.values(),
        key=lambda item: (
            -float(item["fusion_score"]),
            min(
                item["dense_rank"]
                if item["dense_rank"] is not None
                else 10**9,
                item["bm25_rank"]
                if item["bm25_rank"] is not None
                else 10**9,
            ),
            str(item["chunk_id"]),
        ),
    )[:top_k]

    for rank, result in enumerate(ranked, start=1):
        result["rank"] = rank
        result["score"] = float(result["fusion_score"])

    return ranked


class HybridRetriever:
    def __init__(
        self,
        *,
        dense_index_dir: Path = DEFAULT_DENSE_INDEX_DIR,
        bm25_index_dir: Path = DEFAULT_BM25_INDEX_DIR,
        device: str = "auto",
        candidate_k: int = DEFAULT_CANDIDATE_K,
        rrf_k: float = DEFAULT_RRF_K,
        dense_weight: float = DEFAULT_DENSE_WEIGHT,
        bm25_weight: float = DEFAULT_BM25_WEIGHT,
        verify_hashes: bool = True,
    ) -> None:
        if candidate_k <= 0:
            raise HybridRetrieverError(
                "candidate_k must be > 0."
            )

        self.dense_index_dir = Path(dense_index_dir)
        self.bm25_index_dir = Path(bm25_index_dir)
        self.candidate_k = int(candidate_k)
        self.rrf_k = float(rrf_k)
        self.dense_weight = float(dense_weight)
        self.bm25_weight = float(bm25_weight)

        # Dense Baseline v0.1 is frozen with BGE query prefix OFF.
        self.dense = DenseRetriever(
            manifest_path=self.dense_index_dir / "index_manifest.json",
            embeddings_path=self.dense_index_dir / "embeddings.npy",
            metadata_path=self.dense_index_dir / "metadata.jsonl",
            device=device,
            use_query_prefix=False,
            verify_hashes=verify_hashes,
        )

        self.bm25 = BM25Retriever(
            index_dir=self.bm25_index_dir,
            verify_hashes=verify_hashes,
        )

        dense_ids = {
            str(record["chunk_id"])
            for record in self.dense.metadata
        }
        bm25_ids = {
            str(record["chunk_id"])
            for record in self.bm25.metadata
        }

        if dense_ids != bm25_ids:
            raise HybridRetrieverError(
                "Dense and BM25 indexes do not contain identical chunk IDs."
            )

        self.chunk_count = len(dense_ids)

    def describe(self) -> dict[str, Any]:
        return {
            "retriever_version": RETRIEVER_VERSION,
            "index_type": "hybrid_rrf",
            "fusion": "reciprocal_rank_fusion",
            "rrf_k": self.rrf_k,
            "candidate_k": self.candidate_k,
            "dense_weight": self.dense_weight,
            "bm25_weight": self.bm25_weight,
            "chunk_count": self.chunk_count,
            "dense": self.dense.describe(),
            "bm25": self.bm25.describe(),
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        domains: Iterable[str] | None = None,
        document_ids: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise HybridRetrieverError(
                "top_k must be > 0."
            )

        domain_filter = normalize_optional_filters(domains)
        document_filter = normalize_optional_filters(document_ids)

        candidate_k = max(
            self.candidate_k,
            top_k,
        )

        dense_results = self.dense.search(
            query,
            top_k=candidate_k,
            domains=domain_filter,
            document_ids=document_filter,
        )

        bm25_results = self.bm25.search(
            query,
            top_k=candidate_k,
            domains=domain_filter,
            document_ids=document_filter,
        )

        return fuse_rrf(
            dense_results=dense_results,
            bm25_results=bm25_results,
            top_k=top_k,
            rrf_k=self.rrf_k,
            dense_weight=self.dense_weight,
            bm25_weight=self.bm25_weight,
        )


def display_results(
    query: str,
    retriever: HybridRetriever,
    results: list[dict[str, Any]],
) -> None:
    print("-" * 94)
    print("GroundTruth Hybrid Retrieval — Dense + BM25 RRF")
    print("-" * 94)
    print(f"Query:           {query}")
    print(f"Candidates:      {retriever.chunk_count:,}")
    print(f"Candidate depth: {retriever.candidate_k}")
    print(f"RRF k:           {retriever.rrf_k}")
    print(
        "Weights:         "
        f"dense={retriever.dense_weight} "
        f"bm25={retriever.bm25_weight}"
    )
    print("Dense prefix:    <none>")
    print(f"Results:         {len(results)}")
    print("-" * 94)

    for result in results:
        heading = " > ".join(
            str(value)
            for value in result.get("heading_path", [])
        )
        preview = " ".join(str(result["text"]).split())

        if len(preview) > 450:
            preview = preview[:447] + "..."

        dense_rank = (
            result["dense_rank"]
            if result["dense_rank"] is not None
            else "-"
        )
        bm25_rank = (
            result["bm25_rank"]
            if result["bm25_rank"] is not None
            else "-"
        )

        print()
        print(
            f"#{result['rank']} "
            f"rrf={result['fusion_score']:.8f} "
            f"dense_rank={dense_rank} "
            f"bm25_rank={bm25_rank}"
        )
        print(f"Chunk:    {result['chunk_id']}")
        print(f"Document: {result['document_id']}")
        print(f"Domain:   {result['domain']}")
        print(f"Path:     {heading}")
        print(f"Source:   {result['source_url']}")
        print(f"Text:     {preview}")

    print()
    print("-" * 94)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Search GroundTruth using Reciprocal Rank Fusion over "
            "Dense v0.1 and BM25."
        )
    )

    parser.add_argument("query")
    parser.add_argument(
        "--dense-index-dir",
        type=Path,
        default=DEFAULT_DENSE_INDEX_DIR,
    )
    parser.add_argument(
        "--bm25-index-dir",
        type=Path,
        default=DEFAULT_BM25_INDEX_DIR,
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda", "mps"],
        default="auto",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
    )
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=DEFAULT_CANDIDATE_K,
    )
    parser.add_argument(
        "--rrf-k",
        type=float,
        default=DEFAULT_RRF_K,
    )
    parser.add_argument(
        "--dense-weight",
        type=float,
        default=DEFAULT_DENSE_WEIGHT,
    )
    parser.add_argument(
        "--bm25-weight",
        type=float,
        default=DEFAULT_BM25_WEIGHT,
    )
    parser.add_argument(
        "--domain",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--document-id",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--json",
        action="store_true",
    )
    parser.add_argument(
        "--skip-hash-verification",
        action="store_true",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        retriever = HybridRetriever(
            dense_index_dir=args.dense_index_dir,
            bm25_index_dir=args.bm25_index_dir,
            device=args.device,
            candidate_k=args.candidate_k,
            rrf_k=args.rrf_k,
            dense_weight=args.dense_weight,
            bm25_weight=args.bm25_weight,
            verify_hashes=not args.skip_hash_verification,
        )

        results = retriever.search(
            args.query,
            top_k=args.top_k,
            domains=args.domain,
            document_ids=args.document_id,
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
                args.query,
                retriever,
                results,
            )

        return 0

    except (
        HybridRetrieverError,
        DenseRetrieverError,
        BM25RetrieverError,
    ) as exc:
        print()
        print(f"Hybrid retrieval failed: {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("Hybrid retrieval interrupted.")
        return 130
    except Exception as exc:
        print()
        print(
            "Hybrid retrieval failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
