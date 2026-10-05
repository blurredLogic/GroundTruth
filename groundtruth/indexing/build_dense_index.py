from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


INDEX_BUILDER_VERSION = "0.1.0"

DEFAULT_INPUT_PATH = Path("data/index/chunks_indexable.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/index/dense")

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_BATCH_SIZE = 32
DEFAULT_DEVICE = "cpu"

SIMILARITY_METRIC = "cosine"
NORMALIZE_EMBEDDINGS = True


class DenseIndexBuildError(RuntimeError):
    """Raised when the dense index cannot be built safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


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


def atomic_save_npy(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temp_path.open("wb") as file:
            np.save(file, array, allow_pickle=False)
            file.flush()
            os.fsync(file.fileno())

        temp_path.replace(path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def canonical_json_line(record: dict[str, Any]) -> str:
    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def package_version(package_name: str) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def resolve_device(requested: str) -> str:
    requested = requested.strip().lower()

    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"

    if requested == "cuda":
        if not torch.cuda.is_available():
            raise DenseIndexBuildError(
                "--device cuda was requested, but PyTorch does not report "
                "an available CUDA device."
            )
        return "cuda"

    if requested == "cpu":
        return "cpu"

    if requested == "mps":
        if (
            not hasattr(torch.backends, "mps")
            or not torch.backends.mps.is_available()
        ):
            raise DenseIndexBuildError(
                "--device mps was requested, but MPS is unavailable."
            )
        return "mps"

    raise DenseIndexBuildError(
        f"Unsupported device {requested!r}. Use cpu, cuda, mps, or auto."
    )


def device_description(device: str) -> str:
    if device == "cuda" and torch.cuda.is_available():
        return torch.cuda.get_device_name(0)

    if device == "mps":
        return "Apple Metal Performance Shaders"

    return platform.processor() or "CPU"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise DenseIndexBuildError(
            f"Input corpus does not exist: {path}"
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
                raise DenseIndexBuildError(
                    f"{path}:{line_number}: invalid JSON: {exc}"
                ) from exc

            if not isinstance(value, dict):
                raise DenseIndexBuildError(
                    f"{path}:{line_number}: every JSONL line must "
                    "contain an object."
                )

            records.append(value)

    if not records:
        raise DenseIndexBuildError(
            f"No records found in {path}"
        )

    return records


def validate_indexable_chunk(chunk: dict[str, Any]) -> None:
    required_fields = {
        "chunk_id",
        "document_id",
        "section_id",
        "domain",
        "section_title",
        "heading_path",
        "chunk_index",
        "text",
        "retrieval_text",
        "retrieval_text_sha256",
        "token_count",
        "source_url",
        "content_sha256",
        "section_content_sha256",
        "source_document_content_sha256",
        "chunking_config_sha256",
        "corpus_version",
        "quality_flags",
        "indexable",
    }

    missing = required_fields - set(chunk)

    if missing:
        raise DenseIndexBuildError(
            "Indexable chunk is missing required fields: "
            + ", ".join(sorted(missing))
        )

    chunk_id = chunk["chunk_id"]

    if not isinstance(chunk_id, str) or not chunk_id.strip():
        raise DenseIndexBuildError(
            "Chunk has an invalid chunk_id."
        )

    if chunk["indexable"] is not True:
        raise DenseIndexBuildError(
            f"{chunk_id}: chunks_indexable.jsonl contains indexable=false."
        )

    retrieval_text = chunk["retrieval_text"]

    if (
        not isinstance(retrieval_text, str)
        or not retrieval_text.strip()
    ):
        raise DenseIndexBuildError(
            f"{chunk_id}: retrieval_text must be non-empty."
        )

    expected_retrieval_hash = (
        "sha256:" + sha256_text(retrieval_text)
    )

    if (
        chunk["retrieval_text_sha256"]
        != expected_retrieval_hash
    ):
        raise DenseIndexBuildError(
            f"{chunk_id}: retrieval_text_sha256 mismatch."
        )

    text = chunk["text"]

    if not isinstance(text, str) or not text.strip():
        raise DenseIndexBuildError(
            f"{chunk_id}: canonical text is empty."
        )

    expected_content_hash = (
        "sha256:" + sha256_text(text)
    )

    if chunk["content_sha256"] != expected_content_hash:
        raise DenseIndexBuildError(
            f"{chunk_id}: content_sha256 mismatch."
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
        raise DenseIndexBuildError(
            f"{chunk_id}: invalid heading_path."
        )

    if not isinstance(chunk["quality_flags"], list):
        raise DenseIndexBuildError(
            f"{chunk_id}: quality_flags must be a list."
        )


def validate_input_corpus(
    chunks: list[dict[str, Any]],
) -> None:
    seen_ids: set[str] = set()

    for chunk in chunks:
        validate_indexable_chunk(chunk)
        chunk_id = str(chunk["chunk_id"])

        if chunk_id in seen_ids:
            raise DenseIndexBuildError(
                f"Duplicate chunk ID: {chunk_id}"
            )

        seen_ids.add(chunk_id)


def sort_chunks(
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        chunks,
        key=lambda chunk: (
            str(chunk["document_id"]),
            str(chunk["section_id"]),
            int(chunk["chunk_index"]),
            str(chunk["chunk_id"]),
        ),
    )


def load_embedding_model(
    *,
    model_name: str,
    device: str,
) -> SentenceTransformer:
    try:
        return SentenceTransformer(
            model_name,
            device=device,
        )
    except Exception as exc:
        raise DenseIndexBuildError(
            f"Failed to load embedding model {model_name!r}: {exc}"
        ) from exc


def encode_corpus(
    *,
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int,
) -> np.ndarray:
    try:
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=NORMALIZE_EMBEDDINGS,
        )
    except Exception as exc:
        raise DenseIndexBuildError(
            f"Embedding generation failed: {exc}"
        ) from exc

    array = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    if array.ndim != 2:
        raise DenseIndexBuildError(
            f"Expected 2D embedding matrix, got shape {array.shape}."
        )

    if array.shape[0] != len(texts):
        raise DenseIndexBuildError(
            "Embedding row count does not match corpus record count."
        )

    if array.shape[1] <= 0:
        raise DenseIndexBuildError(
            "Embedding dimension must be greater than zero."
        )

    if not np.isfinite(array).all():
        raise DenseIndexBuildError(
            "Embedding matrix contains NaN or infinite values."
        )

    return array


def validate_normalization(
    embeddings: np.ndarray,
    tolerance: float = 1e-4,
) -> dict[str, float]:
    norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    if not np.isfinite(norms).all():
        raise DenseIndexBuildError(
            "Embedding norms contain NaN or infinite values."
        )

    maximum_error = float(
        np.max(
            np.abs(norms - 1.0)
        )
    )

    if NORMALIZE_EMBEDDINGS and maximum_error > tolerance:
        raise DenseIndexBuildError(
            "Embeddings were expected to be L2 normalized, but the "
            f"maximum norm error is {maximum_error:.8f}."
        )

    return {
        "minimum_norm": float(np.min(norms)),
        "maximum_norm": float(np.max(norms)),
        "mean_norm": float(np.mean(norms)),
        "maximum_absolute_error_from_1": maximum_error,
    }


def build_metadata_record(
    *,
    row_index: int,
    chunk: dict[str, Any],
) -> dict[str, Any]:
    return {
        "row_index": row_index,
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "section_id": chunk["section_id"],
        "domain": chunk["domain"],
        "section_title": chunk["section_title"],
        "heading_path": chunk["heading_path"],
        "chunk_index": chunk["chunk_index"],
        "text": chunk["text"],
        "retrieval_text": chunk["retrieval_text"],
        "token_count": chunk["token_count"],
        "source_url": chunk["source_url"],
        "quality_flags": chunk["quality_flags"],
        "content_sha256": chunk["content_sha256"],
        "retrieval_text_sha256": chunk["retrieval_text_sha256"],
        "section_content_sha256": chunk["section_content_sha256"],
        "source_document_content_sha256": (
            chunk["source_document_content_sha256"]
        ),
        "chunking_config_sha256": chunk["chunking_config_sha256"],
        "corpus_version": chunk["corpus_version"],
    }


def write_metadata(
    *,
    path: Path,
    chunks: list[dict[str, Any]],
) -> str:
    content = "\n".join(
        canonical_json_line(
            build_metadata_record(
                row_index=index,
                chunk=chunk,
            )
        )
        for index, chunk in enumerate(chunks)
    )

    if content:
        content += "\n"

    atomic_write_text(
        path,
        content,
    )

    return "sha256:" + hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def unique_values(
    records: list[dict[str, Any]],
    field: str,
) -> list[str]:
    return sorted(
        {
            str(record[field])
            for record in records
        }
    )


def build_manifest(
    *,
    input_path: Path,
    input_sha256: str,
    embeddings_path: Path,
    embeddings_sha256: str,
    metadata_path: Path,
    metadata_sha256: str,
    model_name: str,
    model: SentenceTransformer,
    device: str,
    batch_size: int,
    chunks: list[dict[str, Any]],
    embeddings: np.ndarray,
    normalization_stats: dict[str, float],
    started_at: str,
    completed_at: str,
    duration_seconds: float,
) -> dict[str, Any]:
    dimension_method = getattr(
        model,
        "get_sentence_embedding_dimension",
        None,
    )

    model_dimension = (
        int(dimension_method())
        if callable(dimension_method)
        else int(embeddings.shape[1])
    )

    max_sequence_length = getattr(
        model,
        "max_seq_length",
        None,
    )

    max_sequence_length_value = (
        int(max_sequence_length)
        if isinstance(max_sequence_length, (int, float))
        else None
    )

    corpus_versions = unique_values(
        chunks,
        "corpus_version",
    )

    chunking_hashes = unique_values(
        chunks,
        "chunking_config_sha256",
    )

    if len(corpus_versions) != 1:
        raise DenseIndexBuildError(
            "Expected exactly one corpus_version; "
            f"found {corpus_versions}."
        )

    if len(chunking_hashes) != 1:
        raise DenseIndexBuildError(
            "Expected exactly one chunking_config_sha256; "
            f"found {chunking_hashes}."
        )

    return {
        "index_builder_version": INDEX_BUILDER_VERSION,
        "index_type": "dense",
        "created_at": completed_at,
        "started_at": started_at,
        "duration_seconds": round(duration_seconds, 3),
        "similarity": {
            "metric": SIMILARITY_METRIC,
            "embeddings_l2_normalized": NORMALIZE_EMBEDDINGS,
            "retrieval_operation": (
                "dot_product_equivalent_to_cosine_for_normalized_vectors"
            ),
        },
        "embedding_model": {
            "name": model_name,
            "sentence_embedding_dimension": model_dimension,
            "model_max_seq_length": max_sequence_length_value,
            "document_instruction": None,
            "query_instruction": (
                "Handled by the retriever, not during corpus embedding."
            ),
        },
        "runtime": {
            "device": device,
            "device_description": device_description(device),
            "batch_size": batch_size,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": package_version("numpy"),
            "torch": package_version("torch"),
            "sentence_transformers": package_version(
                "sentence-transformers"
            ),
            "transformers": package_version("transformers"),
            "huggingface_hub": package_version("huggingface-hub"),
        },
        "corpus": {
            "input": input_path.as_posix(),
            "input_sha256": f"sha256:{input_sha256}",
            "chunk_count": len(chunks),
            "document_count": len(
                {
                    str(chunk["document_id"])
                    for chunk in chunks
                }
            ),
            "section_count": len(
                {
                    str(chunk["section_id"])
                    for chunk in chunks
                }
            ),
            "corpus_version": corpus_versions[0],
            "chunking_config_sha256": chunking_hashes[0],
            "row_order": (
                "document_id, section_id, chunk_index, chunk_id"
            ),
            "embedded_field": "retrieval_text",
        },
        "embeddings": {
            "path": embeddings_path.as_posix(),
            "sha256": embeddings_sha256,
            "shape": [
                int(embeddings.shape[0]),
                int(embeddings.shape[1]),
            ],
            "dtype": str(embeddings.dtype),
            "normalization": normalization_stats,
        },
        "metadata": {
            "path": metadata_path.as_posix(),
            "sha256": metadata_sha256,
            "record_count": len(chunks),
        },
    }


def validate_written_artifacts(
    *,
    embeddings_path: Path,
    metadata_path: Path,
    expected_rows: int,
    expected_dimension: int,
) -> None:
    try:
        loaded_embeddings = np.load(
            embeddings_path,
            allow_pickle=False,
        )
    except Exception as exc:
        raise DenseIndexBuildError(
            f"Could not reload embeddings artifact: {exc}"
        ) from exc

    if loaded_embeddings.shape != (
        expected_rows,
        expected_dimension,
    ):
        raise DenseIndexBuildError(
            "Reloaded embedding matrix shape does not match expected shape."
        )

    metadata_count = 0

    with metadata_path.open("r", encoding="utf-8") as file:
        for line_number, raw_line in enumerate(file, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DenseIndexBuildError(
                    f"{metadata_path}:{line_number}: invalid JSON."
                ) from exc

            if record.get("row_index") != metadata_count:
                raise DenseIndexBuildError(
                    "Metadata row_index values are not contiguous "
                    f"at record {metadata_count}."
                )

            metadata_count += 1

    if metadata_count != expected_rows:
        raise DenseIndexBuildError(
            f"Metadata record count {metadata_count} does not match "
            f"embedding rows {expected_rows}."
        )


def run_build(
    *,
    input_path: Path,
    embeddings_path: Path,
    metadata_path: Path,
    manifest_path: Path,
    model_name: str,
    device_requested: str,
    batch_size: int,
) -> int:
    started_at = utc_now()
    started_monotonic = time.monotonic()

    print(f"Loading indexable corpus: {input_path}")

    chunks = load_jsonl(input_path)
    validate_input_corpus(chunks)
    chunks = sort_chunks(chunks)

    print(f"Validated {len(chunks):,} indexable chunks.")

    input_sha256 = sha256_file(input_path)
    device = resolve_device(device_requested)

    print()
    print(f"Embedding model: {model_name}")
    print(
        f"Device:          {device} "
        f"({device_description(device)})"
    )
    print(f"Batch size:      {batch_size}")
    print(
        "Similarity:      cosine "
        "(L2-normalized embeddings)"
    )
    print()
    print("Loading embedding model...")

    model = load_embedding_model(
        model_name=model_name,
        device=device,
    )

    texts = [
        str(chunk["retrieval_text"])
        for chunk in chunks
    ]

    print(f"Embedding {len(texts):,} retrieval texts...")

    embeddings = encode_corpus(
        model=model,
        texts=texts,
        batch_size=batch_size,
    )

    normalization_stats = validate_normalization(
        embeddings
    )

    print()
    print(
        "Embedding matrix: "
        f"{embeddings.shape[0]:,} x {embeddings.shape[1]}"
    )
    print(f"Embedding dtype:  {embeddings.dtype}")
    print(
        "Norm range:       "
        f"{normalization_stats['minimum_norm']:.6f} - "
        f"{normalization_stats['maximum_norm']:.6f}"
    )
    print()
    print(f"Writing embeddings: {embeddings_path}")

    atomic_save_npy(
        embeddings_path,
        embeddings,
    )

    embeddings_sha256 = (
        "sha256:" + sha256_file(embeddings_path)
    )

    print(f"Writing metadata:   {metadata_path}")

    metadata_sha256 = write_metadata(
        path=metadata_path,
        chunks=chunks,
    )

    validate_written_artifacts(
        embeddings_path=embeddings_path,
        metadata_path=metadata_path,
        expected_rows=embeddings.shape[0],
        expected_dimension=embeddings.shape[1],
    )

    completed_at = utc_now()
    duration_seconds = time.monotonic() - started_monotonic

    manifest = build_manifest(
        input_path=input_path,
        input_sha256=input_sha256,
        embeddings_path=embeddings_path,
        embeddings_sha256=embeddings_sha256,
        metadata_path=metadata_path,
        metadata_sha256=metadata_sha256,
        model_name=model_name,
        model=model,
        device=device,
        batch_size=batch_size,
        chunks=chunks,
        embeddings=embeddings,
        normalization_stats=normalization_stats,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
    )

    atomic_write_text(
        manifest_path,
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    manifest_sha256 = (
        "sha256:" + sha256_file(manifest_path)
    )

    print()
    print("-" * 76)
    print("Dense Index Build")
    print("-" * 76)
    print(f"Chunks embedded:     {embeddings.shape[0]:,}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Model:               {model_name}")
    print(f"Device:              {device}")
    print(f"Embeddings:          {embeddings_path}")
    print(f"Metadata:            {metadata_path}")
    print(f"Manifest:            {manifest_path}")
    print(f"Manifest SHA-256:    {manifest_sha256}")
    print(f"Duration:            {duration_seconds:.2f}s")
    print("Status:              SUCCESS")
    print("-" * 76)

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a deterministic dense embedding index from "
            "GroundTruth retrieval-ready chunks."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=(
            "Input indexable chunk JSONL. "
            f"Default: {DEFAULT_INPUT_PATH}"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=(
            "Dense-index output directory. "
            f"Default: {DEFAULT_OUTPUT_DIR}"
        ),
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=(
            "SentenceTransformers model name or local path. "
            f"Default: {DEFAULT_MODEL}"
        ),
    )

    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        choices=["cpu", "cuda", "mps", "auto"],
        help=(
            "Embedding device. CPU is the reproducibility-first default. "
            "Use --device cuda for an NVIDIA GPU. "
            f"Default: {DEFAULT_DEVICE}"
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "SentenceTransformers encoding batch size. "
            f"Default: {DEFAULT_BATCH_SIZE}"
        ),
    )

    parser.add_argument(
        "--embeddings-output",
        type=Path,
        default=None,
        help=(
            "Optional explicit embeddings.npy path. "
            "Defaults to <output-dir>/embeddings.npy."
        ),
    )

    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=None,
        help=(
            "Optional explicit metadata.jsonl path. "
            "Defaults to <output-dir>/metadata.jsonl."
        ),
    )

    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=None,
        help=(
            "Optional explicit index_manifest.json path. "
            "Defaults to <output-dir>/index_manifest.json."
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than 0")

    if not str(args.model).strip():
        parser.error("--model must not be empty")

    output_dir = args.output_dir

    embeddings_path = (
        args.embeddings_output
        if args.embeddings_output is not None
        else output_dir / "embeddings.npy"
    )

    metadata_path = (
        args.metadata_output
        if args.metadata_output is not None
        else output_dir / "metadata.jsonl"
    )

    manifest_path = (
        args.manifest_output
        if args.manifest_output is not None
        else output_dir / "index_manifest.json"
    )

    try:
        return run_build(
            input_path=args.input,
            embeddings_path=embeddings_path,
            metadata_path=metadata_path,
            manifest_path=manifest_path,
            model_name=str(args.model).strip(),
            device_requested=args.device,
            batch_size=args.batch_size,
        )

    except DenseIndexBuildError as exc:
        print()
        print(f"Dense index build failed: {exc}")
        return 1

    except KeyboardInterrupt:
        print()
        print("Dense index build interrupted.")
        return 130

    except Exception as exc:
        print()
        print(
            "Dense index build failed: "
            f"{type(exc).__name__}: {exc}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
