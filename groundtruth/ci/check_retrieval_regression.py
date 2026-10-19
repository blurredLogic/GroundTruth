"""Quality gate for a *freshly evaluated* frozen hybrid test report.

This does not run retrieval. It verifies its result and fails when performance
regresses beyond thresholds in configs/frozen_retrieval_v1.json.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from groundtruth.ci.check_golden import load_golden, validate_golden, GoldenError


class RegressionError(ValueError):
    pass


def check_report(report: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = baseline['expected']

    if report.get('selected_split') != expected['split']:
        errors.append(f"Expected selected_split={expected['split']!r}, got {report.get('selected_split')!r}")
    overall = report.get('overall')
    if not isinstance(overall, dict):
        return errors + ['Missing overall metrics object']
    for field, expected_value in [('question_count', expected['question_count']),
                                  ('answerable_question_count', expected['answerable_question_count'])]:
        if overall.get(field) != expected_value:
            errors.append(f'{field}: expected {expected_value}, got {overall.get(field)}')

    retriever = report.get('retriever', {})
    if not isinstance(retriever, dict):
        return errors + ['Missing retriever configuration']
    checks = {
        'index_type': 'hybrid_rrf',
        'fusion': 'reciprocal_rank_fusion',
        'rrf_k': 20.0,
        'candidate_k': 20,
        'dense_weight': 1.0,
        'bm25_weight': 0.1,
        'chunk_count': 1223,
    }
    for key, wanted in checks.items():
        if retriever.get(key) != wanted:
            errors.append(f'retriever.{key}: expected {wanted!r}, got {retriever.get(key)!r}')
    dense = retriever.get('dense', {})
    bm25 = retriever.get('bm25', {})
    if not isinstance(dense, dict) or not isinstance(bm25, dict):
        errors.append('Missing dense/BM25 retriever metadata')
    else:
        for key, wanted in {'model': 'BAAI/bge-small-en-v1.5', 'query_prefix': '',
                            'embedding_dimension': 384, 'similarity': 'cosine'}.items():
            if dense.get(key) != wanted:
                errors.append(f'retriever.dense.{key}: expected {wanted!r}, got {dense.get(key)!r}')
        for key, wanted in {'k1': 1.5, 'b': 0.75, 'document_count': 1223}.items():
            if bm25.get(key) != wanted:
                errors.append(f'retriever.bm25.{key}: expected {wanted!r}, got {bm25.get(key)!r}')

    for metric, reference in baseline['test_metrics'].items():
        measured = overall.get(metric)
        if type(measured) not in (int, float) or not math.isfinite(measured):
            errors.append(f'{metric}: missing or non-finite metric {measured!r}')
            continue
        minimum = reference - baseline['max_absolute_regression'][metric]
        status = 'PASS' if measured >= minimum - 1e-9 else 'FAIL'
        print(f'  {metric:<15} measured={measured:.6f} frozen={reference:.6f} floor={minimum:.6f} {status}')
        if status == 'FAIL':
            errors.append(f'{metric}: {measured:.6f} fell below {minimum:.6f}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Check a fresh test-split hybrid report against frozen thresholds.')
    parser.add_argument('--report', type=Path, default=Path('reports/evaluation/ci_hybrid_v1_test.json'))
    parser.add_argument('--baseline', type=Path, default=Path('configs/frozen_retrieval_v1.json'))
    parser.add_argument('--golden', type=Path, default=Path('data/evaluation/golden_questions.jsonl'))
    args = parser.parse_args()
    try:
        if not args.report.is_file():
            raise RegressionError(f'Missing fresh evaluation report: {args.report}. Run the evaluator before this gate.')
        baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
        golden_summary = validate_golden(load_golden(args.golden))
        if golden_summary['semantic_sha256'] != baseline['golden_semantic_sha256']:
            raise RegressionError('Frozen golden-set fingerprint mismatch')
        report = json.loads(args.report.read_text(encoding='utf-8'))
        print('GroundTruth Frozen Hybrid Test Regression Gate')
        errors = check_report(report, baseline)
        if errors:
            raise RegressionError('; '.join(errors))
    except (GoldenError, RegressionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'REGRESSION GATE: FAILED — {exc}', file=sys.stderr)
        return 1
    print('REGRESSION GATE: PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
