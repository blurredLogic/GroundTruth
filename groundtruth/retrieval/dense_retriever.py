from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: numpy\n"
        "Install dependencies with:\n"
        "  python -m pip install numpy sentence-transformers torch"
    ) from exc

try:
    import torch
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: torch\n"
        "Install dependencies with:\n"
        "  python -m pip install numpy sentence-transformers torch"
    ) from exc

try:
    from sentence_transformers import SentenceTransformer
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: sentence-transformers\n"
        "Install dependencies with:\n"
        "  python -m pip install numpy sentence-transformers torch"
    ) from exc


RETRIEVER_VERSION = "0.1.0"

DEFAULT_INDEX_DIR = Path("data/index/dense")
DEFAULT_TOP_K = 10
DEFAULT_DEVICE = "auto"
DEFAULT_PREVIEW_CHARS = 420

BGE_EN_QUERY_INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)


class DenseRetrieverError(RuntimeError):
    """Raised when a dense retrieval operation cannot be completed safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise DenseRetrieverError(
            f"JSON file does not exist: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        try:
            value = json.load(file)
        except json.JSONDecodeError as exc:
            raise DenseRetrieverError(
                f"Invalid JSON in {path}: {exc}"
            ) from exc

    if not isinstance(value, dict):
        raise DenseRetrieverError(
            f"Expected JSON object in {path}."
        )

    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise DenseRetrieverError(
            f"JSONL file does not exist: {path}"
        )

    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DenseRetrieverError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise DenseRetrieverError(
                    f"{path}:{line_number}: each JSONL record must "
                    "be an object."
                )

            records.append(record)

    if not records:
        raise DenseRetrieverError(
            f"No metadata records found in {path}."
        )

    return records


def resolve_device(requested: str) -> str:
    requested = requested.strip().lower()

    if requested == "auto":
        if torch.cuda.is_available():
            return "cuda"

        if (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            return "mps"

        return "cpu"

    if requested == "cuda":
        if not torch.cuda.is_available():
            raise DenseRetrieverError(
                "--device cuda was requested, but CUDA is unavailable."
            )

        return "cuda"

    if requested == "mps":
        if not (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            raise DenseRetrieverError(
                "--device mps was requested, but MPS is unavailable."
            )

        return "mps"

    if requested == "cpu":
        return "cpu"

    raise DenseRetrieverError(
        f"Unsupported device {requested!r}."
    )


def device_description(device: str) -> str:
    if device == "cuda" and torch.cuda.is_available():
        return torch.cuda.get_device_name(0)

    if device == "mps":
        return "Apple Metal Performance Shaders"

    return platform.processor() or "CPU"


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


def compact_text(
    text: str,
    limit: int,
) -> str:
    compact = " ".join(
        text.split()
    )

    if limit <= 0 or len(compact) <= limit:
        return compact

    return compact[: limit - 1] + "…"


def default_query_instruction_for_model(
    model_name: str,
) -> str:
    """
    Use the BGE English retrieval instruction for English BGE models.
    Other model families receive no automatic prefix.
    """
    normalized = model_name.lower().strip()

    if (
        normalized.startswith("baai/bge-")
        and "-en" in normalized
    ):
        return BGE_EN_QUERY_INSTRUCTION

    return ""


def validate_metadata(
    metadata: list[dict[str, Any]],
) -> None:
    seen_chunk_ids: set[str] = set()

    required_fields = {
        "row_index",
        "chunk_id",
        "document_id",
        "section_id",
        "domain",
        "section_title",
        "heading_path",
        "text",
        "retrieval_text",
        "source_url",
    }

    for expected_row, record in enumerate(metadata):
        missing = required_fields - set(record)

        if missing:
            raise DenseRetrieverError(
                f"Metadata row {expected_row} is missing fields: "
                + ", ".join(sorted(missing))
            )

        if record["row_index"] != expected_row:
            raise DenseRetrieverError(
                f"Metadata row {expected_row} has row_index="
                f"{record['row_index']!r}."
            )

        chunk_id = str(record["chunk_id"])

        if chunk_id in seen_chunk_ids:
            raise DenseRetrieverError(
                f"Duplicate chunk_id in metadata: {chunk_id}"
            )

        seen_chunk_ids.add(chunk_id)


def validate_manifest_and_artifacts(
    *,
    manifest: dict[str, Any],
    embeddings_path: Path,
    metadata_path: Path,
    embeddings: np.ndarray,
    metadata: list[dict[str, Any]],
    verify_hashes: bool,
) -> None:
    if manifest.get("index_type") != "dense":
        raise DenseRetrieverError(
            "Index manifest does not describe a dense index."
        )

    embedding_info = manifest.get("embeddings")
    metadata_info = manifest.get("metadata")
    model_info = manifest.get("embedding_model")
    similarity_info = manifest.get("similarity")

    if not isinstance(embedding_info, dict):
        raise DenseRetrieverError(
            "Manifest is missing embeddings metadata."
        )

    if not isinstance(metadata_info, dict):
        raise DenseRetrieverError(
            "Manifest is missing metadata metadata."
        )

    if not isinstance(model_info, dict):
        raise DenseRetrieverError(
            "Manifest is missing embedding_model metadata."
        )

    if not isinstance(similarity_info, dict):
        raise DenseRetrieverError(
            "Manifest is missing similarity metadata."
        )

    if similarity_info.get("metric") != "cosine":
        raise DenseRetrieverError(
            "This retriever expects a cosine-similarity dense index."
        )

    if similarity_info.get("embeddings_l2_normalized") is not True:
        raise DenseRetrieverError(
            "This retriever expects L2-normalized corpus embeddings."
        )

    if embeddings.ndim != 2:
        raise DenseRetrieverError(
            f"Embeddings must be a 2D matrix, got {embeddings.shape}."
        )

    if embeddings.shape[0] != len(metadata):
        raise DenseRetrieverError(
            "Embedding row count does not match metadata record count."
        )

    manifest_shape = embedding_info.get("shape")

    if (
        not isinstance(manifest_shape, list)
        or len(manifest_shape) != 2
        or list(embeddings.shape) != manifest_shape
    ):
        raise DenseRetrieverError(
            "Embedding matrix shape differs from the manifest."
        )

    if metadata_info.get("record_count") != len(metadata):
        raise DenseRetrieverError(
            "Metadata count differs from the manifest."
        )

    if not np.isfinite(embeddings).all():
        raise DenseRetrieverError(
            "Embedding matrix contains NaN or infinite values."
        )

    norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    maximum_norm_error = float(
        np.max(
            np.abs(norms - 1.0)
        )
    )

    if maximum_norm_error > 1e-4:
        raise DenseRetrieverError(
            "Corpus embeddings are not sufficiently L2-normalized. "
            f"Maximum norm error: {maximum_norm_error:.8f}"
        )

    if verify_hashes:
        expected_embeddings_hash = embedding_info.get(
            "sha256"
        )

        if isinstance(expected_embeddings_hash, str):
            actual_embeddings_hash = (
                "sha256:" + sha256_file(embeddings_path)
            )

            if actual_embeddings_hash != expected_embeddings_hash:
                raise DenseRetrieverError(
                    "embeddings.npy SHA-256 does not match manifest."
                )

        expected_metadata_hash = metadata_info.get(
            "sha256"
        )

        if isinstance(expected_metadata_hash, str):
            actual_metadata_hash = (
                "sha256:" + sha256_file(metadata_path)
            )

            if actual_metadata_hash != expected_metadata_hash:
                raise DenseRetrieverError(
                    "metadata.jsonl SHA-256 does not match manifest."
                )


class DenseRetriever:
    """
    Reusable dense retriever for GroundTruth.

    Corpus vectors are precomputed and L2-normalized. Query vectors are also
    L2-normalized, so matrix-vector dot product equals cosine similarity.
    """

    def __init__(
        self,
        *,
        manifest_path: Path,
        embeddings_path: Path,
        metadata_path: Path,
        device: str = DEFAULT_DEVICE,
        query_prefix: str | None = None,
        use_query_prefix: bool = True,
        verify_hashes: bool = True,
    ) -> None:
        self.manifest_path = manifest_path
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path
        self.device = resolve_device(
            device
        )

        self.manifest = load_json_object(
            manifest_path
        )

        try:
            self.embeddings = np.load(
                embeddings_path,
                allow_pickle=False,
            )
        except Exception as exc:
            raise DenseRetrieverError(
                f"Could not load {embeddings_path}: {exc}"
            ) from exc

        self.embeddings = np.asarray(
            self.embeddings,
            dtype=np.float32,
        )

        self.metadata = load_jsonl(
            metadata_path
        )

        validate_metadata(
            self.metadata
        )

        validate_manifest_and_artifacts(
            manifest=self.manifest,
            embeddings_path=embeddings_path,
            metadata_path=metadata_path,
            embeddings=self.embeddings,
            metadata=self.metadata,
            verify_hashes=verify_hashes,
        )

        model_info = self.manifest["embedding_model"]
        model_name = model_info.get("name")

        if not isinstance(model_name, str) or not model_name.strip():
            raise DenseRetrieverError(
                "Manifest embedding model name is missing."
            )

        self.model_name = model_name.strip()

        try:
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        except Exception as exc:
            raise DenseRetrieverError(
                f"Could not load embedding model {self.model_name!r}: "
                f"{exc}"
            ) from exc

        dimension_method = getattr(
            self.model,
            "get_sentence_embedding_dimension",
            None,
        )

        if callable(dimension_method):
            model_dimension = int(
                dimension_method()
            )

            if model_dimension != self.embeddings.shape[1]:
                raise DenseRetrieverError(
                    "Loaded model embedding dimension does not match "
                    "the index."
                )

        if not use_query_prefix:
            self.query_prefix = ""
        elif query_prefix is not None:
            self.query_prefix = query_prefix
        else:
            self.query_prefix = (
                default_query_instruction_for_model(
                    self.model_name
                )
            )

    @property
    def chunk_count(self) -> int:
        return int(
            self.embeddings.shape[0]
        )

    @property
    def embedding_dimension(self) -> int:
        return int(
            self.embeddings.shape[1]
        )

    def prepare_query(
        self,
        query: str,
    ) -> str:
        cleaned = " ".join(
            query.split()
        )

        if not cleaned:
            raise DenseRetrieverError(
                "Query must not be empty."
            )

        if self.query_prefix:
            return self.query_prefix + cleaned

        return cleaned

    def encode_query(
        self,
        query: str,
    ) -> np.ndarray:
        prepared_query = self.prepare_query(
            query
        )

        try:
            encoded = self.model.encode(
                [prepared_query],
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise DenseRetrieverError(
                f"Query embedding failed: {exc}"
            ) from exc

        vector = np.asarray(
            encoded,
            dtype=np.float32,
        )

        expected_shape = (
            1,
            self.embedding_dimension,
        )

        if vector.shape != expected_shape:
            raise DenseRetrieverError(
                "Unexpected query embedding shape: "
                f"{vector.shape}; expected {expected_shape}."
            )

        if not np.isfinite(vector).all():
            raise DenseRetrieverError(
                "Query embedding contains NaN or infinite values."
            )

        norm = float(
            np.linalg.norm(vector[0])
        )

        if abs(norm - 1.0) > 1e-4:
            raise DenseRetrieverError(
                "Query embedding is not sufficiently L2-normalized."
            )

        return vector[0]

    def _candidate_indices(
        self,
        *,
        domains: set[str] | None,
        document_ids: set[str] | None,
    ) -> np.ndarray:
        if domains is None and document_ids is None:
            return np.arange(
                self.chunk_count,
                dtype=np.int64,
            )

        indices: list[int] = []

        for index, record in enumerate(
            self.metadata
        ):
            if (
                domains is not None
                and str(record["domain"]) not in domains
            ):
                continue

            if (
                document_ids is not None
                and str(record["document_id"])
                not in document_ids
            ):
                continue

            indices.append(index)

        return np.asarray(
            indices,
            dtype=np.int64,
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        domains: Iterable[str] | None = None,
        document_ids: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise DenseRetrieverError(
                "top_k must be greater than zero."
            )

        domain_filter = normalize_optional_filters(
            domains
        )

        document_filter = normalize_optional_filters(
            document_ids
        )

        candidate_indices = self._candidate_indices(
            domains=domain_filter,
            document_ids=document_filter,
        )

        if candidate_indices.size == 0:
            return []

        query_vector = self.encode_query(
            query
        )

        candidate_embeddings = self.embeddings[
            candidate_indices
        ]

        scores = (
            candidate_embeddings
            @ query_vector
        )

        result_count = min(
            top_k,
            int(scores.shape[0]),
        )

        if result_count == int(scores.shape[0]):
            local_indices = np.argsort(
                -scores,
                kind="stable",
            )
        else:
            partition = np.argpartition(
                -scores,
                kth=result_count - 1,
            )[:result_count]

            local_indices = partition[
                np.argsort(
                    -scores[partition],
                    kind="stable",
                )
            ]

        results: list[dict[str, Any]] = []

        for rank, local_index_value in enumerate(
            local_indices,
            start=1,
        ):
            local_index = int(
                local_index_value
            )

            row_index = int(
                candidate_indices[
                    local_index
                ]
            )

            metadata = self.metadata[
                row_index
            ]

            result = dict(
                metadata
            )

            result["rank"] = rank
            result["score"] = float(
                scores[local_index]
            )

            results.append(
                result
            )

        return results

    def describe(self) -> dict[str, Any]:
        return {
            "retriever_version": RETRIEVER_VERSION,
            "index_type": "dense",
            "model": self.model_name,
            "device": self.device,
            "device_description": device_description(
                self.device
            ),
            "query_prefix": self.query_prefix,
            "chunk_count": self.chunk_count,
            "embedding_dimension": (
                self.embedding_dimension
            ),
            "similarity": "cosine",
        }


def result_for_json(
    result: dict[str, Any],
    *,
    include_retrieval_text: bool,
) -> dict[str, Any]:
    value = dict(
        result
    )

    if not include_retrieval_text:
        value.pop(
            "retrieval_text",
            None,
        )

    return value


def print_human_results(
    *,
    query: str,
    results: list[dict[str, Any]],
    retriever: DenseRetriever,
    preview_chars: int,
    show_full_text: bool,
) -> None:
    print()
    print("-" * 88)
    print("GroundTruth Dense Retrieval")
    print("-" * 88)
    print(
        f"Query:        {query}"
    )
    print(
        f"Model:        {retriever.model_name}"
    )
    print(
        f"Device:       {retriever.device}"
    )
    print(
        "Query prefix: "
        + (
            repr(retriever.query_prefix)
            if retriever.query_prefix
            else "<none>"
        )
    )
    print(
        f"Candidates:   {retriever.chunk_count:,}"
    )
    print(
        f"Results:      {len(results)}"
    )
    print("-" * 88)

    if not results:
        print(
            "No chunks matched the supplied filters."
        )
        print("-" * 88)
        return

    for result in results:
        heading_path = " > ".join(
            str(item)
            for item in result.get(
                "heading_path",
                []
            )
        )

        print()
        print(
            f"#{result['rank']}  "
            f"score={result['score']:.6f}"
        )
        print(
            f"Chunk:    {result['chunk_id']}"
        )
        print(
            f"Document: {result['document_id']}"
        )
        print(
            f"Domain:   {result['domain']}"
        )
        print(
            f"Path:     {heading_path}"
        )
        print(
            f"Source:   {result['source_url']}"
        )

        text = str(
            result["text"]
        )

        if show_full_text:
            rendered = text
        else:
            rendered = compact_text(
                text,
                preview_chars,
            )

        print(
            f"Text:     {rendered}"
        )

    print()
    print("-" * 88)


def print_json_results(
    *,
    query: str,
    results: list[dict[str, Any]],
    retriever: DenseRetriever,
    include_retrieval_text: bool,
) -> None:
    payload = {
        "query": query,
        "retriever": retriever.describe(),
        "result_count": len(results),
        "results": [
            result_for_json(
                result,
                include_retrieval_text=(
                    include_retrieval_text
                ),
            )
            for result in results
        ],
    }

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Search the GroundTruth dense Kubernetes index using "
            "cosine similarity over normalized SentenceTransformers "
            "embeddings."
        )
    )

    parser.add_argument(
        "query",
        type=str,
        help="Natural-language retrieval query.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=(
            "Number of ranked chunks to return. "
            f"Default: {DEFAULT_TOP_K}"
        ),
    )

    parser.add_argument(
        "--index-dir",
        type=Path,
        default=DEFAULT_INDEX_DIR,
        help=(
            "Dense index directory. "
            f"Default: {DEFAULT_INDEX_DIR}"
        ),
    )

    parser.add_argument(
        "--device",
        choices=[
            "auto",
            "cpu",
            "cuda",
            "mps",
        ],
        default=DEFAULT_DEVICE,
        help=(
            "Query embedding device. "
            f"Default: {DEFAULT_DEVICE}"
        ),
    )

    parser.add_argument(
        "--domain",
        action="append",
        default=None,
        help=(
            "Restrict results to a domain. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--document-id",
        action="append",
        default=None,
        help=(
            "Restrict results to a document ID. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--query-prefix",
        default=None,
        help=(
            "Override the model-specific retrieval query prefix."
        ),
    )

    parser.add_argument(
        "--no-query-prefix",
        action="store_true",
        help=(
            "Disable the model-specific retrieval query prefix."
        ),
    )

    parser.add_argument(
        "--format",
        choices=[
            "human",
            "json",
        ],
        default="human",
        help="Output format. Default: human",
    )

    parser.add_argument(
        "--preview-chars",
        type=int,
        default=DEFAULT_PREVIEW_CHARS,
        help=(
            "Maximum text preview length in human output. "
            f"Default: {DEFAULT_PREVIEW_CHARS}"
        ),
    )

    parser.add_argument(
        "--show-full-text",
        action="store_true",
        help=(
            "Show complete canonical chunk text in human output."
        ),
    )

    parser.add_argument(
        "--include-retrieval-text",
        action="store_true",
        help=(
            "Include enriched retrieval_text in JSON output."
        ),
    )

    parser.add_argument(
        "--skip-hash-verification",
        action="store_true",
        help=(
            "Skip SHA-256 verification of embeddings and metadata."
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    query = args.query.strip()

    if not query:
        parser.error(
            "query must not be empty"
        )

    if args.top_k <= 0:
        parser.error(
            "--top-k must be greater than 0"
        )

    if args.preview_chars < 0:
        parser.error(
            "--preview-chars must be >= 0"
        )

    if (
        args.no_query_prefix
        and args.query_prefix is not None
    ):
        parser.error(
            "--query-prefix and --no-query-prefix "
            "cannot be used together"
        )

    index_dir = args.index_dir

    embeddings_path = (
        index_dir / "embeddings.npy"
    )

    metadata_path = (
        index_dir / "metadata.jsonl"
    )

    manifest_path = (
        index_dir / "index_manifest.json"
    )

    try:
        retriever = DenseRetriever(
            manifest_path=manifest_path,
            embeddings_path=embeddings_path,
            metadata_path=metadata_path,
            device=args.device,
            query_prefix=args.query_prefix,
            use_query_prefix=(
                not args.no_query_prefix
            ),
            verify_hashes=(
                not args.skip_hash_verification
            ),
        )

        results = retriever.search(
            query,
            top_k=args.top_k,
            domains=args.domain,
            document_ids=args.document_id,
        )

        if args.format == "json":
            print_json_results(
                query=query,
                results=results,
                retriever=retriever,
                include_retrieval_text=(
                    args.include_retrieval_text
                ),
            )
        else:
            print_human_results(
                query=query,
                results=results,
                retriever=retriever,
                preview_chars=args.preview_chars,
                show_full_text=args.show_full_text,
            )

        return 0

    except DenseRetrieverError as exc:
        print()
        print(
            f"Dense retrieval failed: {exc}"
        )
        return 1

    except KeyboardInterrupt:
        print()
        print(
            "Dense retrieval interrupted."
        )
        return 130

    except Exception as exc:
        print()
        print(
            "Dense retrieval failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
