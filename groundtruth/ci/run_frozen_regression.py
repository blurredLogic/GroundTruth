"""Rebuild frozen 512/64 pipeline in isolation and run held-out regression gate.

Invoke from GroundTruth repository root:
    python -m groundtruth.ci.run_frozen_regression --device cuda

GitHub Actions can use --device cpu. No existing model indexes are touched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


class PipelineError(RuntimeError):
    pass


def discover_module(filename: str) -> str:
    matches = sorted(Path('groundtruth').rglob(filename))
    if len(matches) != 1:
        raise PipelineError(
            f'Expected exactly one groundtruth/**/{filename}; found {len(matches)}: {matches}'
        )
    return '.'.join(matches[0].with_suffix('').parts)


def run_module(module: str, *args: object) -> None:
    command = [sys.executable, '-m', module, *[str(arg) for arg in args]]
    print('\n$ ' + ' '.join(command), flush=True)
    subprocess.run(command, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description='Full frozen Hybrid RRF v0.2 quality regression')
    parser.add_argument('--device', choices=['cpu', 'cuda', 'auto', 'mps'], default='cpu')
    parser.add_argument('--sections', type=Path, default=Path('data/processed/sections.jsonl'))
    parser.add_argument('--manifest', type=Path, default=Path('manifest/kubernetes_v0.1.yaml'))
    parser.add_argument('--golden', type=Path, default=Path('data/evaluation/golden_questions.jsonl'))
    parser.add_argument('--workspace', type=Path, default=Path('data/ci/frozen_retrieval'))
    parser.add_argument('--skip-chunk-determinism-check', action='store_true')
    parser.add_argument('--preflight-only', action='store_true', help='Verify inputs, module discovery, and golden set; do not rebuild indexes')
    args = parser.parse_args()

    try:
        for path in [args.sections, args.manifest, args.golden]:
            if not path.is_file():
                raise PipelineError(
                    f'Missing required input {path}. In GitHub Actions, source sections and manifest '
                    'must be tracked or produced in an earlier checkout step.'
                )

        modules = {
            'chunks': discover_module('build_chunks.py'),
            'prepare': discover_module('prepare_corpus.py'),
            'dense': discover_module('build_dense_index.py'),
            'bm25': discover_module('build_bm25_index.py'),
            'hybrid': discover_module('evaluate_hybrid.py'),
        }
        print('Discovered project modules: ' + json.dumps(modules, sort_keys=True), flush=True)

        run_module('groundtruth.ci.check_golden', '--golden', args.golden)
        if args.preflight_only:
            print('FULL REGRESSION PREFLIGHT: PASSED (no models loaded)', flush=True)
            return 0

        workspace = args.workspace.resolve()
        # Explicitly confine destructive cleanup to the dedicated CI area.
        ci_root = Path('data/ci').resolve()
        if workspace == ci_root or not workspace.is_relative_to(ci_root):
            raise PipelineError(
                'For safety, --workspace must be a named child of data/ci/. '
                'Frozen data/index and reports/evaluation are never deleted.'
            )
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True)
        chunks = workspace / 'chunks.jsonl'
        chunks_report = workspace / 'chunks_report.json'
        prepared = workspace / 'chunks_indexable.jsonl'
        prep_report = workspace / 'corpus_preparation_report.json'
        dense_dir = workspace / 'dense'
        bm25_dir = workspace / 'bm25'
        report = workspace / 'hybrid_rrf_v0_2_test.json'

        chunk_arguments = [
            args.manifest, '--sections', args.sections,
            '--target-tokens', 512, '--overlap-tokens', 64,
        ]
        run_module(
            modules['chunks'], *chunk_arguments,
            '--output', chunks, '--report-output', chunks_report,
        )
        if not args.skip_chunk_determinism_check:
            repeat = workspace / 'chunks_repeat.jsonl'
            run_module(
                modules['chunks'], *chunk_arguments,
                '--output', repeat, '--report-output', workspace / 'repeat_report.json',
            )
            if sha256(chunks) != sha256(repeat):
                raise PipelineError('Chunk builder is nondeterministic: different output bytes on identical input')
            repeat.unlink()
            print('CHUNK DETERMINISM: PASSED', flush=True)

        run_module(
            modules['prepare'], '--input', chunks, '--output', prepared,
            '--report-output', prep_report,
        )
        run_module(
            modules['dense'], '--input', prepared,
            '--output-dir', dense_dir,
            '--model', 'BAAI/bge-small-en-v1.5',
            '--device', args.device, '--batch-size', 16,
        )
        run_module(
            modules['bm25'], '--input', prepared,
            '--output-dir', bm25_dir, '--k1', 1.5, '--b', 0.75,
        )
        run_module(
            modules['hybrid'], '--golden', args.golden,
            '--dense-index-dir', dense_dir, '--bm25-index-dir', bm25_dir,
            '--device', args.device, '--split', 'test', '--top-k', 10,
            '--candidate-k', 20, '--rrf-k', 20,
            '--dense-weight', 1.0, '--bm25-weight', 0.1,
            '--run-name', 'ci_hybrid_v1_test', '--report-output', report,
        )
        run_module(
            'groundtruth.ci.check_retrieval_regression',
            '--golden', args.golden, '--report', report,
        )
        print(f'FULL REGRESSION: PASSED\nFresh report: {report}', flush=True)
        return 0
    except (PipelineError, OSError, subprocess.CalledProcessError) as exc:
        print(f'FULL REGRESSION: FAILED — {exc}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
