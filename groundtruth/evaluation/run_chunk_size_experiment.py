"""Controlled GroundTruth chunk-size experiment (Python 3.10).

Phases:
  build   Rechunk, prepare/index, and weak-label project 256/1024 variants.
  dev     Run the frozen hybrid retriever on DEV for 256/512/1024.
  compare Compare DEV runs; report section-level and weak chunk-level metrics.

No command here evaluates the test split or overwrites the frozen 512 artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


VARIANTS = {256: 32, 512: 64, 1024: 128}


def call(arguments: list[str]) -> None:
    print("\n$ " + subprocess.list2cmdline(arguments), flush=True)
    subprocess.run(arguments, check=True)


def variant_path(root: Path, size: int) -> Path:
    return root / f"chunk_{size}"


def build(args: argparse.Namespace) -> None:
    root = args.experiment_root
    manifest = args.manifest
    golden = args.golden
    baseline = args.baseline_chunks
    if not golden.is_file() or not baseline.is_file():
        raise FileNotFoundError("Missing golden or baseline indexable chunks input")
    if not Path("data/processed/sections.jsonl").is_file():
        raise FileNotFoundError("Missing data/processed/sections.jsonl")
    for size, overlap in VARIANTS.items():
        if size == 512:
            print("512/64: retaining original frozen baseline chunks and indexes")
            continue
        dest = variant_path(root, size)
        chunks = dest / "chunks.jsonl"
        prepared = dest / "chunks_indexable.jsonl"
        dense = dest / "dense"
        bm25 = dest / "bm25"
        projected = dest / "golden_projected.jsonl"
        report_dir = args.report_root / f"chunk_{size}"
        required_outputs = [
            chunks, prepared, dense / "embeddings.npy", dense / "metadata.jsonl",
            dense / "index_manifest.json", bm25 / "inverted_index.json.gz",
            bm25 / "metadata.jsonl", bm25 / "index_manifest.json", projected,
        ]
        if all(path.exists() for path in required_outputs) and not args.rebuild:
            print(f"{size}/{overlap}: complete variant found, skipping (use --rebuild to rerun)")
            continue
        if any(path.exists() for path in required_outputs) and not args.rebuild:
            raise RuntimeError(
                f"Partial variant exists in {dest}. Review it and rerun with --rebuild "
                "if you intend to replace experiment artifacts. Baseline is never modified."
            )
        report_dir.mkdir(parents=True, exist_ok=True)
        call([
            sys.executable, "-m", "groundtruth.ingestion.build_chunks", str(manifest),
            "--target-tokens", str(size), "--overlap-tokens", str(overlap),
            "--output", str(chunks),
            "--report-output", str(report_dir / "chunks_report.json"),
        ])
        call([
            sys.executable, "-m", "groundtruth.indexing.prepare_corpus",
            "--input", str(chunks), "--output", str(prepared),
            "--report-output", str(report_dir / "preparation_report.json"),
        ])
        call([
            sys.executable, "-m", "groundtruth.indexing.build_dense_index",
            "--input", str(prepared), "--output-dir", str(dense),
            "--device", args.device, "--model", "BAAI/bge-small-en-v1.5",
        ])
        call([
            sys.executable, "-m", "groundtruth.indexing.build_bm25_index",
            "--input", str(prepared), "--output-dir", str(bm25),
            "--k1", "1.5", "--b", "0.75",
        ])
        call([
            sys.executable, "-m", "groundtruth.evaluation.project_chunk_judgments",
            "--golden", str(golden), "--baseline-chunks", str(baseline),
            "--target-chunks", str(prepared), "--output", str(projected),
            "--report-output", str(report_dir / "projection_report.json"),
        ])
        print(f"\nBuilt {size}/{overlap} in {dest}")


def evaluate_dev(args: argparse.Namespace) -> None:
    for size in VARIANTS:
        if size == 512:
            gold = args.golden
            dense = Path("data/index/dense")
            bm25 = Path("data/index/bm25")
        else:
            dest = variant_path(args.experiment_root, size)
            gold = dest / "golden_projected.jsonl"
            dense = dest / "dense"
            bm25 = dest / "bm25"
        for path in (gold, dense / "index_manifest.json", bm25 / "index_manifest.json"):
            if not path.is_file():
                raise FileNotFoundError(f"Build step incomplete: {path}")
        report = args.report_root / f"chunk_{size}" / "hybrid_dev.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        if report.exists() and not args.rebuild:
            print(f"DEV results already exist: {report}; skipping")
            continue
        call([
            sys.executable, "-m", "groundtruth.evaluation.evaluate_hybrid",
            "--device", args.device, "--split", "dev",
            "--golden", str(gold),
            "--dense-index-dir", str(dense),
            "--bm25-index-dir", str(bm25),
            "--dense-weight", "1.0", "--bm25-weight", "0.1",
            "--rrf-k", "20", "--candidate-k", "20", "--top-k", "10",
            "--run-name", f"chunk_{size}_hybrid_dev",
            "--report-output", str(report),
        ])


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def section_gold(golden: list[dict[str, Any]], baseline_chunks: list[dict[str, Any]]):
    lookup = {str(chunk["chunk_id"]): str(chunk["section_id"]) for chunk in baseline_chunks}
    output = {}
    for q in golden:
        grades: dict[str, int] = {}
        for judgment in q["relevance_judgments"]:
            if int(judgment["grade"]) <= 0:
                continue
            cid = str(judgment["chunk_id"])
            if cid not in lookup:
                raise ValueError(f"Baseline gold chunk not found: {cid}")
            sec = lookup[cid]
            grades[sec] = max(grades.get(sec, 0), int(judgment["grade"]))
        output[str(q["question_id"])] = grades
    return output


def section_metrics(rows: list[dict[str, Any]], gold: dict[str, dict[str, int]]):
    metrics = defaultdict(list)
    for q in rows:
        if not q["answerable"]:
            continue
        qid = str(q["question_id"])
        relevant = gold[qid]
        if not relevant:
            raise ValueError(f"Answerable question has no section evidence: {qid}")
        seen_sections = set()
        unique_at_rank: dict[int, str] = {}
        for item in q["retrieved"]:
            sec = str(item["section_id"])
            rank = int(item["rank"])
            if sec not in seen_sections:
                seen_sections.add(sec)
                unique_at_rank[rank] = sec
        ranked = [(rank, sec) for rank, sec in sorted(unique_at_rank.items())]
        for k in (5, 10):
            matched = {sec for rank, sec in ranked if rank <= k and sec in relevant}
            metrics[f"SectionRecall@{k}"].append(len(matched) / len(relevant))
            dcg = sum(
                ((2 ** relevant[sec]) - 1) / math.log2(rank + 1)
                for rank, sec in ranked if rank <= k and sec in relevant
            )
            ideal = sum(
                ((2 ** grade) - 1) / math.log2(i + 1)
                for i, grade in enumerate(sorted(relevant.values(), reverse=True)[:k], start=1)
            )
            metrics[f"SectionnDCG@{k}"].append(dcg / ideal if ideal else 0.0)
        first = next((rank for rank, sec in ranked if sec in relevant), None)
        metrics["SectionMRR"].append(1 / first if first else 0.0)
    return {key: round(statistics.fmean(values), 6) for key, values in sorted(metrics.items())}


def compare_dev(args: argparse.Namespace) -> None:
    golden = load_jsonl(args.golden)
    baseline_chunks = load_jsonl(args.baseline_chunks)
    gold = section_gold(golden, baseline_chunks)
    results = {}
    for size in VARIANTS:
        path = args.report_root / f"chunk_{size}" / "hybrid_dev.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing dev evaluation result: {path}")
        report = json.loads(path.read_text(encoding="utf-8"))
        rows = report["per_question"]
        if set(q["question_id"] for q in rows) != set(q["question_id"] for q in golden if q["split"] == "dev"):
            raise ValueError(f"DEV question IDs mismatch for size {size}")
        results[str(size)] = {
            "chunk_size": size,
            "overlap_tokens": VARIANTS[size],
            "section_metrics_on_original_gold": section_metrics(rows, gold),
            "chunk_metrics_on_size_specific_gold": report["overall"],
            "gold_origin": "human-reviewed" if size == 512 else "token-span projected; weak label",
            "report": str(path),
        }
    comparison = {
        "protocol": "DEV only; frozen Hybrid RRF v0.2; 256/32,512/64,1024/128",
        "primary_metric_note": "Section metrics use baseline human labels collapsed to sections and rank positions from each top-10 chunk list (deduplicated sections; duplicate chunks consume rank budget).",
        "secondary_metric_note": "Projected chunk-level relevance is approximate and may overlabel chunks: NOT direct human-reviewed evidence at new chunk sizes.",
        "model_limit_note": "BGE-small may truncate 1024 cl100k token inputs at its transformer maximum; report this confound and inspect actual encoder truncation before interpreting 1024 vs smaller chunks.",
        "test_split_used": False,
        "results": results,
    }
    output = args.report_root / "comparison_dev.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(comparison, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("\nControlled chunk-size DEV comparison")
    print("size  sec_R@5   sec_R@10  sec_MRR   sec_nDCG@5  sec_nDCG@10  projected_chunk_nDCG@10")
    for size in VARIANTS:
        result = results[str(size)]
        metrics = result["section_metrics_on_original_gold"]
        weak = result["chunk_metrics_on_size_specific_gold"]
        print(f"{size:>4}  {metrics['SectionRecall@5']:.6f}  {metrics['SectionRecall@10']:.6f}  {metrics['SectionMRR']:.6f}  {metrics['SectionnDCG@5']:.6f}  {metrics['SectionnDCG@10']:.6f}     {weak['nDCG@10']:.6f}")
    print(f"Report: {output}")
    print("WARNING: 1024 may be model-truncated. Test split remains untouched.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["build", "dev", "compare"])
    parser.add_argument("--manifest", type=Path, default=Path("manifest/kubernetes_v0.1.yaml"))
    parser.add_argument("--golden", type=Path, default=Path("data/evaluation/golden_questions.jsonl"))
    parser.add_argument("--baseline-chunks", type=Path, default=Path("data/index/chunks_indexable.jsonl"))
    parser.add_argument("--experiment-root", type=Path, default=Path("data/experiments/chunk_sizes"))
    parser.add_argument("--report-root", type=Path, default=Path("reports/experiments/chunk_sizes"))
    parser.add_argument("--device", choices=["cuda", "cpu", "auto", "mps"], default="cuda")
    parser.add_argument("--rebuild", action="store_true", help="Explicitly allow replacing variant experiment outputs and reports (NEVER frozen baseline)")
    args = parser.parse_args()
    try:
        if args.phase == "build":
            build(args)
        elif args.phase == "dev":
            evaluate_dev(args)
        else:
            compare_dev(args)
        print("Experiment phase: SUCCESS")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, KeyError) as exc:
        print(f"Experiment phase FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
