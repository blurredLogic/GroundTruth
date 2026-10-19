"""Audit BGE-small-en-v1.5 embedding-token truncation WITHOUT importing torch.

Uses the exact Hugging Face tokenizer.json through the standalone Rust-backed
`tokenizers` library and model_max_length from tokenizer_config.json.

Run from the GroundTruth repository root:
    python -m groundtruth.evaluation.audit_embedding_truncation

Dependencies (usually already installed with sentence-transformers):
    python -m pip install tokenizers huggingface-hub
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_ROOT = Path("data/experiments/chunk_sizes")
DEFAULT_OUTPUT = Path(
    "reports/experiments/chunk_sizes/tokenizer_truncation_audit.json"
)


class AuditError(RuntimeError):
    """Input, tokenizer, or model metadata could not be validated."""


def load_model_tokenizer(
    *,
    model_name: str,
    tokenizer_json: Path | None,
    max_length_override: int | None,
    offline: bool,
):
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise AuditError(
            "Missing dependency 'tokenizers'. Run: "
            "python -m pip install tokenizers huggingface-hub"
        ) from exc

    tokenizer_source: Path
    limit_source: str

    if tokenizer_json is not None:
        tokenizer_source = tokenizer_json
        if not tokenizer_source.is_file():
            raise AuditError(f"Tokenizer file not found: {tokenizer_source}")
    else:
        try:
            from huggingface_hub import hf_hub_download
        except ImportError as exc:
            raise AuditError(
                "Missing dependency 'huggingface-hub'. Run: "
                "python -m pip install huggingface-hub"
            ) from exc

        try:
            tokenizer_source = Path(
                hf_hub_download(
                    repo_id=model_name,
                    filename="tokenizer.json",
                    local_files_only=offline,
                )
            )
        except Exception as exc:
            raise AuditError(
                f"Cannot load tokenizer.json for {model_name!r}: {exc}. "
                "For a local tokenizer use --tokenizer-json and "
                "--max-length 512."
            ) from exc

    tokenizer = Tokenizer.from_file(str(tokenizer_source))

    if max_length_override is not None:
        maximum = max_length_override
        limit_source = "--max-length CLI override"
    elif tokenizer_json is not None:
        raise AuditError(
            "--tokenizer-json also requires --max-length (usually 512 "
            "for BAAI/bge-small-en-v1.5)."
        )
    else:
        try:
            # `hf_hub_download` is available in this branch.
            config_file = Path(
                hf_hub_download(
                    repo_id=model_name,
                    filename="tokenizer_config.json",
                    local_files_only=offline,
                )
            )
            metadata = json.loads(config_file.read_text(encoding="utf-8"))
            maximum = metadata["model_max_length"]
            limit_source = str(config_file)
        except Exception as exc:
            raise AuditError(
                f"Could not determine model_max_length from {model_name}: {exc}. "
                "Specify --max-length 512 after verifying the model's limit."
            ) from exc

    if (
        not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum <= 0
        or maximum > 1_000_000
    ):
        raise AuditError(f"Invalid model max length: {maximum!r}")

    # From-file tokenization preserves Hugging Face tokenizer post-processing,
    # including CLS/SEP for this BERT-based embedding model.
    return tokenizer, int(maximum), tokenizer_source, limit_source


def read_input_rows(path: Path):
    if not path.is_file():
        raise AuditError(
            f"Missing indexable chunk file: {path}. "
            "Generate the experiment variants first."
        )

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise AuditError(
                    f"Invalid JSONL at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(item, dict) or not isinstance(
                item.get("retrieval_text"), str
            ):
                raise AuditError(
                    f"Missing retrieval_text string at {path}:{line_number}"
                )
            yield item


def audit_corpus(path: Path, tokenizer, maximum: int, batch_size: int) -> dict[str, Any]:
    lengths: list[int] = []
    batch: list[str] = []

    def process_batch() -> None:
        if not batch:
            return
        # No truncation during auditing: count the complete input length.
        encodings = tokenizer.encode_batch(batch, add_special_tokens=True)
        lengths.extend(len(encoding.ids) for encoding in encodings)
        batch.clear()

    for item in read_input_rows(path):
        batch.append(item["retrieval_text"])
        if len(batch) >= batch_size:
            process_batch()
    process_batch()

    if not lengths:
        raise AuditError(f"No indexable chunks in {path}")

    truncated_lengths = [n for n in lengths if n > maximum]

    return {
        "corpus_path": path.as_posix(),
        "total_chunks": len(lengths),
        "would_truncate_chunks": len(truncated_lengths),
        "would_truncate_fraction": round(len(truncated_lengths) / len(lengths), 6),
        "model_tokens_lost_to_truncation": sum(n - maximum for n in truncated_lengths),
        "maximum_model_tokenized_length": max(lengths),
        "mean_model_tokenized_length": round(statistics.fmean(lengths), 2),
        "median_model_tokenized_length": round(statistics.median(lengths), 2),
        "minimum_model_tokenized_length": min(lengths),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument(
        "--tokenizer-json", type=Path, default=None,
        help="Optional local tokenizer.json; requires --max-length",
    )
    parser.add_argument(
        "--max-length", type=int, default=None,
        help="Override model input limit (normally read from tokenizer_config.json)",
    )
    parser.add_argument(
        "--offline", action="store_true",
        help="Only use Hugging Face files already in the local cache",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("--batch-size must be > 0")
    if args.max_length is not None and args.max_length <= 0:
        parser.error("--max-length must be > 0")

    try:
        tokenizer, maximum, tokenizer_source, limit_source = load_model_tokenizer(
            model_name=args.model,
            tokenizer_json=args.tokenizer_json,
            max_length_override=args.max_length,
            offline=args.offline,
        )

        print(f"Model:             {args.model}")
        print(f"Tokenizer:         {tokenizer_source}")
        print(f"Maximum tokens:    {maximum}")
        print(f"Limit source:      {limit_source}")
        print("Imports torch:     NO")
        print()

        payload: dict[str, Any] = {
            "model": args.model,
            "embedding_tokenizer_max_length": maximum,
            "tokenizer_source": str(tokenizer_source),
            "model_length_source": limit_source,
            "auditor": "standalone tokenizers; no torch or transformers imports",
            "variants": {},
        }

        for size in (256, 512, 1024):
            input_path = (
                Path("data/index/chunks_indexable.jsonl")
                if size == 512
                else args.experiment_root / f"chunk_{size}" / "chunks_indexable.jsonl"
            )
            result = audit_corpus(input_path, tokenizer, maximum, args.batch_size)
            payload["variants"][str(size)] = result
            print(
                f"{size:>4}/overlap: "
                f"{result['would_truncate_chunks']:>4}/{result['total_chunks']:<5} "
                f"would truncate ({result['would_truncate_fraction']:.2%}); "
                f"model-token mean={result['mean_model_tokenized_length']}; "
                f"max={result['maximum_model_tokenized_length']}"
            )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"\nReport: {args.output}")
        print("Status: SUCCESS")
        return 0
    except AuditError as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Audit failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
