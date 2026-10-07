from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from groundtruth.retrieval.bm25_retriever import BM25RetrieverError
from groundtruth.retrieval.dense_retriever import DenseRetrieverError
from groundtruth.retrieval.hybrid_retriever import (
    HybridRetriever,
    HybridRetrieverError,
)

RERANKER_VERSION = "0.1.0"
DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_DENSE_INDEX_DIR = Path("data/index/dense")
DEFAULT_BM25_INDEX_DIR = Path("data/index/bm25")


class RerankerError(RuntimeError):
    pass


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested

    import torch

    if torch.cuda.is_available():
        return "cuda"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    return "cpu"


def rerank_candidates(
    candidates: list[dict[str, Any]],
    scores: list[float],
    top_k: int,
) -> list[dict[str, Any]]:
    if len(candidates) != len(scores):
        raise RerankerError(
            "Candidate count does not match reranker score count."
        )

    rows: list[dict[str, Any]] = []

    for candidate, score in zip(candidates, scores):
        row = dict(candidate)
        row["hybrid_rank"] = int(candidate["rank"])
        row["hybrid_score"] = float(candidate["score"])
        row["reranker_score"] = float(score)
        rows.append(row)

    rows.sort(
        key=lambda row: (
            -row["reranker_score"],
            row["hybrid_rank"],
            str(row["chunk_id"]),
        )
    )

    rows = rows[:top_k]

    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["score"] = row["reranker_score"]

    return rows


class CrossEncoderReranker:
    def __init__(
        self,
        *,
        dense_index_dir: Path = DEFAULT_DENSE_INDEX_DIR,
        bm25_index_dir: Path = DEFAULT_BM25_INDEX_DIR,
        model_name: str = DEFAULT_MODEL,
        device: str = "auto",
        candidate_k: int = 20,
        batch_size: int = 32,
        max_length: int = 512,
        verify_hashes: bool = True,
    ) -> None:
        if candidate_k <= 0:
            raise RerankerError("candidate_k must be > 0.")

        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RerankerError(
                "sentence-transformers is required."
            ) from exc

        self.model_name = model_name
        self.device = resolve_device(device)
        self.candidate_k = int(candidate_k)
        self.batch_size = int(batch_size)
        self.max_length = int(max_length)

        # Frozen Hybrid Retrieval v0.2.
        self.hybrid = HybridRetriever(
            dense_index_dir=dense_index_dir,
            bm25_index_dir=bm25_index_dir,
            device=self.device,
            candidate_k=20,
            rrf_k=20.0,
            dense_weight=1.0,
            bm25_weight=0.1,
            verify_hashes=verify_hashes,
        )

        self.model = CrossEncoder(
            model_name,
            device=self.device,
            max_length=self.max_length,
        )

    def describe(self) -> dict[str, Any]:
        return {
            "reranker_version": RERANKER_VERSION,
            "architecture": "cross_encoder",
            "model": self.model_name,
            "device": self.device,
            "candidate_k": self.candidate_k,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "candidate_generator": self.hybrid.describe(),
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        candidate_k = max(self.candidate_k, top_k)

        candidates = self.hybrid.search(
            query,
            top_k=candidate_k,
        )

        if not candidates:
            return []

        pairs = [
            [query, str(candidate["retrieval_text"])]
            for candidate in candidates
        ]

        predictions = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        scores = [float(value) for value in predictions.reshape(-1)]

        return rerank_candidates(
            candidates,
            scores,
            top_k,
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rerank frozen Hybrid RRF v0.2 results."
    )
    parser.add_argument("query")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], default="auto")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--skip-hash-verification", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        reranker = CrossEncoderReranker(
            model_name=args.model,
            device=args.device,
            candidate_k=args.candidate_k,
            batch_size=args.batch_size,
            max_length=args.max_length,
            verify_hashes=not args.skip_hash_verification,
        )

        results = reranker.search(args.query, top_k=args.top_k)

        if args.json:
            print(json.dumps(
                {
                    "query": args.query,
                    "retriever": reranker.describe(),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ))
        else:
            print("-" * 92)
            print("GroundTruth Cross-Encoder Reranking")
            print("-" * 92)
            print(f"Query:          {args.query}")
            print(f"Model:          {reranker.model_name}")
            print(f"Device:         {reranker.device}")
            print(f"Candidate pool: Hybrid RRF v0.2 top {reranker.candidate_k}")
            print("-" * 92)

            for row in results:
                path = " > ".join(str(v) for v in row.get("heading_path", []))
                preview = " ".join(str(row["text"]).split())
                if len(preview) > 400:
                    preview = preview[:397] + "..."

                print()
                print(
                    f"#{row['rank']} "
                    f"reranker={row['reranker_score']:.6f} "
                    f"hybrid_rank={row['hybrid_rank']}"
                )
                print(f"Chunk:  {row['chunk_id']}")
                print(f"Path:   {path}")
                print(f"Text:   {preview}")

            print()
            print("-" * 92)

        return 0

    except (
        RerankerError,
        HybridRetrieverError,
        DenseRetrieverError,
        BM25RetrieverError,
    ) as exc:
        print(f"Reranking failed: {exc}")
        return 1

    except Exception as exc:
        print(f"Reranking failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
