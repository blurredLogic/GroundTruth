"""Validate the frozen GroundTruth golden set without ML dependencies.

Usage:
    python -m groundtruth.ci.check_golden
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_GOLDEN = Path('data/evaluation/golden_questions.jsonl')
DEFAULT_BASELINE = Path('configs/frozen_retrieval_v1.json')
QUESTION_ID = re.compile(r'^k8s-[0-9]{3}$')
CHUNK_ID = re.compile(r'^[a-z0-9]+-[0-9]{3}-sec-[0-9]{3}-ch-[0-9]{3}$')
CATEGORIES = {'direct_factual', 'comparison', 'scenario_application', 'multi_hop', 'troubleshooting', 'negative_near_miss'}
DIFFICULTIES = {'easy', 'medium', 'hard'}
SPLITS = {'dev', 'test'}


class GoldenError(ValueError):
    pass


def load_golden(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise GoldenError(f'Missing golden set: {path}. Commit data/evaluation/golden_questions.jsonl.')
    rows = []
    with path.open(encoding='utf-8') as source:
        for line_no, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GoldenError(f'{path}:{line_no}: {exc}') from exc
            if not isinstance(record, dict):
                raise GoldenError(f'{path}:{line_no}: expected JSON object')
            rows.append(record)
    return rows


def semantic_fingerprint(rows: list[dict[str, Any]]) -> str:
    """Semantic SHA256, insensitive to JSON whitespace and JSONL ordering."""
    payload = '\n'.join(
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        for row in sorted(rows, key=lambda row: str(row['question_id']))
    ) + '\n'
    return 'sha256:' + hashlib.sha256(payload.encode('utf-8')).hexdigest()


def validate_golden(rows: list[dict[str, Any]], *, strict_counts: bool = True) -> dict[str, Any]:
    if not rows:
        raise GoldenError('Golden set is empty')
    seen_qids = set()
    split_counts: Counter[str] = Counter()
    answerable_by_split: Counter[str] = Counter()
    negative_by_split: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()

    for row in rows:
        required = {'question_id', 'question', 'category', 'difficulty', 'split', 'answerable', 'relevance_judgments'}
        missing = required - row.keys()
        if missing:
            raise GoldenError(f'Question missing fields: {sorted(missing)}')
        qid = row['question_id']
        if not isinstance(qid, str) or not QUESTION_ID.fullmatch(qid):
            raise GoldenError(f'Invalid question_id: {qid!r}')
        if qid in seen_qids:
            raise GoldenError(f'Duplicate question_id: {qid}')
        seen_qids.add(qid)
        if not isinstance(row['question'], str) or not row['question'].strip():
            raise GoldenError(f'{qid}: empty question')
        if row['category'] not in CATEGORIES or row['difficulty'] not in DIFFICULTIES:
            raise GoldenError(f'{qid}: invalid category or difficulty')
        if row['split'] not in SPLITS or type(row['answerable']) is not bool:
            raise GoldenError(f'{qid}: invalid split or answerable flag')
        if not isinstance(row['relevance_judgments'], list):
            raise GoldenError(f'{qid}: relevance_judgments must be a list')
        judged_chunks = set()
        positive = 0
        for judgment in row['relevance_judgments']:
            if not isinstance(judgment, dict) or 'chunk_id' not in judgment or 'grade' not in judgment:
                raise GoldenError(f'{qid}: malformed judgment')
            cid, grade = judgment['chunk_id'], judgment['grade']
            if not isinstance(cid, str) or not CHUNK_ID.fullmatch(cid):
                raise GoldenError(f'{qid}: invalid chunk_id {cid!r}')
            if cid in judged_chunks:
                raise GoldenError(f'{qid}: duplicate judgment for {cid}')
            judged_chunks.add(cid)
            if type(grade) is not int or not 0 <= grade <= 3:
                raise GoldenError(f'{qid}: judgment grade must be an integer 0..3')
            positive += grade > 0
        if row['answerable'] and positive == 0:
            raise GoldenError(f'{qid}: answerable question lacks positive evidence')
        if not row['answerable'] and positive > 0:
            raise GoldenError(f'{qid}: negative question has positive evidence')
        if (row['category'] == 'negative_near_miss') != (not row['answerable']):
            raise GoldenError(f'{qid}: negative_near_miss/answerable mismatch')
        split = row['split']
        split_counts[split] += 1
        category_counts[row['category']] += 1
        difficulty_counts[row['difficulty']] += 1
        if row['answerable']:
            answerable_by_split[split] += 1
        else:
            negative_by_split[split] += 1

    summary = {
        'questions': len(rows),
        'split_counts': dict(sorted(split_counts.items())),
        'answerable_by_split': dict(sorted(answerable_by_split.items())),
        'negative_by_split': dict(sorted(negative_by_split.items())),
        'category_counts': dict(sorted(category_counts.items())),
        'difficulty_counts': dict(sorted(difficulty_counts.items())),
        'semantic_sha256': semantic_fingerprint(rows),
    }
    if strict_counts and (
        len(rows) != 100
        or dict(split_counts) != {'dev': 60, 'test': 40}
        or dict(answerable_by_split) != {'dev': 54, 'test': 36}
        or dict(negative_by_split) != {'dev': 6, 'test': 4}
    ):
        raise GoldenError(f'Golden distribution changed: {summary}')
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate the frozen GroundTruth golden set.')
    parser.add_argument('--golden', type=Path, default=DEFAULT_GOLDEN)
    parser.add_argument('--baseline', type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args()
    try:
        summary = validate_golden(load_golden(args.golden))
        baseline = json.loads(args.baseline.read_text(encoding='utf-8'))
        expected = baseline['golden_semantic_sha256']
        if summary['semantic_sha256'] != expected:
            raise GoldenError('Golden set changed relative to frozen baseline. Re-review judgments and create a new baseline rather than silently tuning the test set.')
    except (GoldenError, OSError, ValueError, KeyError) as exc:
        print(f'GOLDEN GATE: FAILED — {exc}', file=sys.stderr)
        return 1
    print('GOLDEN GATE: PASSED')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
