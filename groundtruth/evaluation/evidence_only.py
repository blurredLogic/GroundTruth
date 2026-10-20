"""GroundTruth v0.5: deterministic evidence-only DEV shadow evaluation.

Uses previously retrieved passages as data; no LLM, HF Hub, API, or reretrieval.
Outputs strictly verbatim evidence with original source offsets and a BLIND
human-adjudication worksheet. Does not infer truth, factuality or abstention.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

VERSION = 'groundtruth_evidence_only_v0.5'
DEFAULT_INPUT = 'reports/generation/grounded_qa_dev.json'
DEFAULT_PREFIX = 'reports/evidence_only/dev_v05'
RELATIONS = {'supported', 'contradicted', 'partial', 'insufficient', 'unclear'}
STOPWORDS = frozenset('a an the and or how what which who why where when is are was were be been being of for on in as at to from by with it its these those this that can could would should do does did you your our does not means into than through their them each all every using use used about without while if such set field fields kubernetes pod pods cluster'.split())
TOKEN_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]*|\d+')
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])(?=\s+[A-Z`#*\[])')
PARAGRAPHS = re.compile(r'\S.*?(?=\n[ \t]*\n|\Z)', re.DOTALL)
REVIEW_COLUMNS = [
    'question_id', 'question', 'evidence_status', 'evidence_ids',
    'review_relation', 'review_confidence_0_2', 'review_notes', 'followup_needed',
]
CANDIDATE_COLUMNS = [
    'question_id', 'evidence_id', 'source_id', 'retrieval_rank', 'chunk_id',
    'section_id', 'heading_path', 'source_url', 'quote', 'source_start',
    'source_end', 'excerpt_truncated', 'lexical_overlap_terms', 'lexical_score',
]


class EvidenceError(ValueError):
    pass


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _csv_safe(value: Any) -> Any:
    """Prevent spreadsheet formula execution without mutating report quotes."""
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value


def _tokens(value: str) -> set[str]:
    pieces = set()
    for item in TOKEN_RE.findall(value):
        splits = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', item).replace('_', ' ').replace('-', ' ')
        for part in splits.split():
            t = part.lower()
            if len(t) >= 2 and t not in STOPWORDS:
                pieces.add(t)
    return pieces


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end-1].isspace():
        end -= 1
    return start, end


def _long_spans(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int, bool]]:
    """Split only along original positions; never concatenate fabricated text."""
    spans = []
    cursor = start
    while cursor < end:
        stop = min(cursor + max_chars, end)
        if stop < end:
            window = text[cursor:stop]
            cut = max(window.rfind('\n'), window.rfind(' '))
            if cut >= int(max_chars * .55):
                stop = cursor + cut + 1
        lo, hi = _trim_span(text, cursor, stop)
        if hi > lo:
            spans.append((lo, hi, lo > start or hi < end))
        cursor = stop
    return spans


def extract_spans(text: str, max_chars: int = 450) -> list[tuple[int, int, bool]]:
    """Return verbatim spans from markdown; offsets are into the ORIGINAL text."""
    if max_chars < 80:
        raise EvidenceError('max_chars must be >= 80')
    results: list[tuple[int, int, bool]] = []
    for match in PARAGRAPHS.finditer(text):
        st, en = _trim_span(text, match.start(), match.end())
        if en <= st:
            continue
        paragraph = text[st:en]
        if paragraph.startswith('```'):
            # Code may provide evidence, but avoid selecting entire fenced examples
            # as if they were explanatory prose. Other prose in the source remains.
            continue
        if len(paragraph) <= max_chars:
            candidates = [(st, en, False)]
        else:
            # First split on sentence boundaries, preserving exact original offsets.
            starts = [0] + [m.end() for m in SENTENCE_SPLIT.finditer(paragraph)]
            ends = [m.start() for m in SENTENCE_SPLIT.finditer(paragraph)] + [len(paragraph)]
            candidates = []
            for a, b in zip(starts, ends):
                lo, hi = _trim_span(text, st + a, st + b)
                if hi <= lo:
                    continue
                if hi - lo <= max_chars:
                    candidates.append((lo, hi, False))
                else:
                    candidates.extend(_long_spans(text, lo, hi, max_chars))
        for lo, hi, truncated in candidates:
            part = text[lo:hi]
            # Skip markdown-only headings, boilerplate and empty fragments.
            if len(part.strip()) < 24 or re.fullmatch(r'#{1,6}[^\n]*', part):
                continue
            results.append((lo, hi, truncated))
    if not results and text.strip():
        lo, hi = _trim_span(text, 0, min(max_chars, len(text)))
        if hi > lo:
            results.append((lo, hi, hi < len(text)))
    return results


def rank_evidence(record: dict[str, Any], *, top_k: int = 4,
                  max_snippets: int = 6, per_source: int = 2,
                  max_chars: int = 450) -> list[dict[str, Any]]:
    """Select excerpts by lexical overlap alone, without gold or generated answers."""
    if top_k < 1 or max_snippets < 1 or per_source < 1:
        raise EvidenceError('top_k, max_snippets, and per_source must be positive')
    sources = sorted(record.get('sources') or [], key=lambda s: (int(s.get('rank', 999)), str(s.get('chunk_id', ''))))[:top_k]
    questions_tokens = _tokens(str(record['question']))
    units: list[dict[str, Any]] = []
    for source in sources:
        text = source.get('text') or ''
        if not isinstance(text, str):
            raise EvidenceError('source text must be a string')
        for lo, hi, was_cut in extract_spans(text, max_chars=max_chars):
            quote = text[lo:hi]
            terms = sorted(questions_tokens & _tokens(quote))
            units.append({
                'source_id': str(source.get('id', '')), 'retrieval_rank': int(source.get('rank', 999)),
                'chunk_id': str(source.get('chunk_id', '')), 'section_id': str(source.get('section_id', '')),
                'heading_path': list(source.get('heading_path') or []),
                'source_url': str(source.get('source_url', '')), 'quote': quote,
                'source_start': lo, 'source_end': hi,
                'excerpt_truncated': bool(was_cut or '[TRUNCATED EXCERPT]' in text),
                'lexical_overlap_terms': terms,
                '_original': text,
            })
    # IDF over all candidates from this question: an explanatory passage with
    # distinctive matching terms outranks generic documentation boilerplate.
    frequencies: collections.Counter[str] = collections.Counter()
    for u in units:
        frequencies.update(set(u['lexical_overlap_terms']))
    total = max(len(units), 1)
    for u in units:
        score = sum(1.0 + math.log((total+1)/(frequencies[t]+1)) for t in u['lexical_overlap_terms'])
        score += .22 / max(u['retrieval_rank'], 1)
        if u['quote'].lstrip().startswith(('```', '| ', '[', '#### Note:')):
            score -= .3
        u['lexical_score'] = round(score, 5)
    units.sort(key=lambda x: (-x['lexical_score'], x['retrieval_rank'], x['source_start'], x['chunk_id']))
    selected = []
    counts: collections.Counter[str] = collections.Counter()
    seen = set()
    for u in units:
        key = (u['chunk_id'], u['source_start'], u['source_end'])
        if key in seen or counts[u['chunk_id']] >= per_source:
            continue
        seen.add(key)
        counts[u['chunk_id']] += 1
        assert u['quote'] == u['_original'][u['source_start']:u['source_end']]
        u = {k:v for k,v in u.items() if k != '_original'}
        u['evidence_id'] = 'E' + str(len(selected) + 1)
        selected.append(u)
        if len(selected) >= max_snippets:
            break
    return selected


def _validate_input(data: dict[str, Any], ids: set[str] | None) -> list[dict[str, Any]]:
    if data.get('split') != 'dev':
        raise EvidenceError('This experiment is DEV-only. Refusing non-DEV input.')
    originals = data.get('per_question')
    if not isinstance(originals, list) or not originals:
        raise EvidenceError('Input missing nonempty per_question array')
    if any(row.get('split') != 'dev' for row in originals):
        raise EvidenceError('Refusing records outside DEV')
    all_ids = [row.get('question_id') for row in originals]
    if len(set(all_ids)) != len(all_ids) or any(not isinstance(i, str) or not i.strip() for i in all_ids):
        raise EvidenceError('Question IDs must be unique, nonempty strings')
    if ids is not None:
        missing = ids - set(all_ids)
        if missing:
            raise EvidenceError('Unknown DEV question IDs: ' + ', '.join(sorted(missing)))
        originals = [o for o in originals if o['question_id'] in ids]
    return originals


def _paths(prefix: str | Path) -> dict[str, Path]:
    base = str(prefix)
    return {key: Path(base + suffix) for key, suffix in {
        'report': '_report.json', 'review': '_review.csv',
        'candidates': '_candidates.csv', 'packets': '_packets.md',
        'audit': '_audit.json', 'audit_details': '_audit_details.csv',
    }.items()}


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _csv_safe(row.get(c, '')) for c in headers})


def _fence(value: str) -> str:
    """Markdown fence guaranteed longer than any internal backtick run."""
    longest = max([2] + [len(m.group(0)) for m in re.finditer(r'`+', value)])
    return '`' * (longest + 1)


def _packet_md(records: list[dict[str, Any]]) -> str:
    out = [
        '# GroundTruth v0.5 — Evidence packets (DEV, shadow-only)', '',
        '**Important:** The excerpts are exact substrings of the saved retrieval report. '
        'They are candidate evidence, NOT answers, and no question has been adjudicated. '
        'A retrieved excerpt may be irrelevant or even contradict the assumption in the question.', '',
        'Use the accompanying blind review CSV to record whether the combined evidence '
        'supports, contradicts, partially addresses, or does not establish each question.', '',
    ]
    for record in records:
        out.extend([f"## {record['question_id']}", '', f"**Question:** {record['question']}", ''])
        if not record['selected']:
            out.extend(['**No retriever passages were recorded for this question.** '
                        'This does NOT establish that the question is unanswerable.', ''])
            continue
        for e in record['selected']:
            out.extend([
                f"### {e['evidence_id']} — {e['chunk_id']} (retrieval rank {e['retrieval_rank']})", '',
                f"Source: {e['source_url']}  ",
                f"Heading: {' > '.join(e['heading_path'])}  ",
                f"Original saved excerpt offsets: [{e['source_start']}, {e['source_end']})  ",
                f"Snippet cut or saved source already truncated: {e['excerpt_truncated']}", '',
                _fence(e['quote']) + 'text', e['quote'], _fence(e['quote']), '',
            ])
        out.extend(['---', ''])
    return '\n'.join(out)


def build(input_path: Path, prefix: str | Path, *, ids: set[str] | None = None,
          top_k: int = 4, max_snippets: int = 6,
          per_source: int = 2, max_chars: int = 450, force: bool = False) -> dict[str, Any]:
    raw = input_path.read_bytes()
    data = json.loads(raw)
    originals = _validate_input(data, ids)
    files = _paths(prefix)
    output_files = [files[k] for k in ('report', 'review', 'candidates', 'packets')]
    if not force and any(p.exists() for p in output_files):
        raise EvidenceError('Outputs already exist. Use a fresh --output-prefix to avoid overwriting review work.')
    config = {'top_k': top_k, 'max_snippets': max_snippets, 'per_source': per_source,
              'max_chars': max_chars, 'question_ids': sorted(ids) if ids is not None else None}
    records = []
    review_rows = []
    candidates_rows = []
    for original in originals:
        selected = rank_evidence(original, top_k=top_k, max_snippets=max_snippets,
                                 per_source=per_source, max_chars=max_chars)
        qid = original['question_id']
        records.append({'question_id': qid, 'question': original['question'],
                        'evidence_status': 'evidence_available' if selected else 'missing_saved_retrieval',
                        'selected': selected})
        review_rows.append({'question_id': qid, 'question': original['question'],
                            'evidence_status': 'evidence_available' if selected else 'missing_saved_retrieval',
                            'evidence_ids': '; '.join(e['evidence_id'] for e in selected),
                            'review_relation': '', 'review_confidence_0_2': '',
                            'review_notes': '', 'followup_needed': ''})
        for e in selected:
            candidates_rows.append({**e, 'question_id': qid,
                                    'heading_path': ' > '.join(e['heading_path']),
                                    'lexical_overlap_terms': '; '.join(e['lexical_overlap_terms'])})
    report = {
        'schema': VERSION, 'shadow_only': True, 'selection_is_not_truth_or_abstention': True,
        'input_sha256': _sha(raw), 'run_fingerprint': _sha(_json_bytes({'input_sha': _sha(raw), 'config': config, 'version': VERSION})),
        'split': 'dev', 'config': config,
        'summary': {'questions': len(records),
                    'with_saved_retrieval_evidence': sum(bool(r['selected']) for r in records),
                    'missing_saved_retrieval_evidence': sum(not r['selected'] for r in records),
                    'candidate_quotes': len(candidates_rows),
                    'automatically_supported_answers': None,
                    'human_adjudication_complete': False},
        'per_question': records,
        'limitations': [
            'Quotes are selected by lexical overlap with the question, not semantic entailment.',
            'No answerability prediction, assertion of truth or automatic abstention is made.',
            'Original source text is from the SAVED generation report, not a refreshed document crawl.',
            'Some saved source text is already truncated; quote offsets refer to the saved source.',
            'No retrieved evidence for generation-error records means unavailable context, not an unanswerable question.',
            'DEV only. Gold answerability labels and reference answers are excluded from extraction and blind reviewer files.',
        ],
    }
    files['report'].parent.mkdir(parents=True, exist_ok=True)
    files['report'].write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    _write_csv(files['review'], REVIEW_COLUMNS, review_rows)
    _write_csv(files['candidates'], CANDIDATE_COLUMNS, candidates_rows)
    files['packets'].write_text(_packet_md(records), encoding='utf-8')
    return report


def score_review(input_path: Path, prefix: str | Path) -> dict[str, Any]:
    """Only human-filled review labels are scored; never invent correctness."""
    paths = _paths(prefix)
    report = json.loads(paths['report'].read_text(encoding='utf-8'))
    if report.get('schema') != VERSION or report.get('split') != 'dev':
        raise EvidenceError('Incorrect or unsafe evidence-only report version/split')
    raw = input_path.read_bytes()
    if _sha(raw) != report.get('input_sha256'):
        raise EvidenceError('Input source report changed; cannot join human labels safely')
    originals = {r['question_id']: r for r in _validate_input(json.loads(raw), None)}
    questions = {r['question_id']: r for r in report['per_question']}
    with paths['review'].open(encoding='utf-8-sig', newline='') as fh:
        reviewer = list(csv.DictReader(fh))
    seen: set[str] = set()
    judged: list[dict[str, Any]] = []
    for row in reviewer:
        qid = row.get('question_id', '')
        if qid in seen or qid not in questions:
            raise EvidenceError('Duplicated or unknown review question ID: ' + qid)
        seen.add(qid)
        if row.get('question') != questions[qid]['question']:
            raise EvidenceError('Question text changed in reviewer CSV: ' + qid)
        relation = (row.get('review_relation') or '').strip().lower()
        if relation and relation not in RELATIONS:
            raise EvidenceError(f'Invalid review_relation for {qid}: {relation!r}')
        confidence = (row.get('review_confidence_0_2') or '').strip()
        if confidence and confidence not in {'0', '1', '2'}:
            raise EvidenceError(f'Invalid review_confidence_0_2 for {qid}')
        if relation and not confidence:
            raise EvidenceError(f'Supply confidence 0, 1, or 2 for reviewed question {qid}')
        if not relation and confidence:
            raise EvidenceError(f'Confidence given but no review_relation for {qid}')
        if questions[qid]['evidence_status'] == 'missing_saved_retrieval' and relation in ('supported', 'contradicted', 'partial'):
            raise EvidenceError(f'No evidence saved for {qid}; do not claim source-based support or contradiction')
        orig = originals[qid]
        judged.append({'question_id': qid, 'answerable_gold_for_aggregation_only': bool(orig['answerable']),
                       'evidence_status': questions[qid]['evidence_status'],
                       'review_relation': relation if relation else 'unreviewed',
                       'review_confidence_0_2': confidence,
                       'notes': row.get('review_notes', ''),
                       'followup_needed': row.get('followup_needed', '')})
    if seen != set(questions):
        raise EvidenceError('Missing review rows for: ' + ', '.join(sorted(set(questions) - seen)))
    done = [r for r in judged if r['review_relation'] != 'unreviewed']
    dist = collections.Counter(r['review_relation'] for r in done)
    positives = [r for r in done if r['answerable_gold_for_aggregation_only']]
    negatives = [r for r in done if not r['answerable_gold_for_aggregation_only']]
    summary = {
        'reviewed': len(done), 'unreviewed': len(judged) - len(done),
        'total_questions': len(judged), 'all_reviewed': len(done) == len(judged),
        'human_judgments': dict(sorted(dist.items())),
        'positive_reviewed': len(positives), 'negative_reviewed': len(negatives),
        'positive_supported': sum(r['review_relation'] == 'supported' for r in positives),
        'positive_partial': sum(r['review_relation'] == 'partial' for r in positives),
        'negative_contradicted': sum(r['review_relation'] == 'contradicted' for r in negatives),
        'negative_insufficient': sum(r['review_relation'] == 'insufficient' for r in negatives),
        'negative_supported_REVIEW_FOR_GOLD_LABEL_ERROR': sum(r['review_relation'] == 'supported' for r in negatives),
        'automatic_groundedness_score': None,
    }
    output = {'schema': VERSION + '_human_score', 'evidence_report_sha256': _sha(paths['report'].read_bytes()),
              'original_input_sha256': _sha(raw), 'summary': summary,
              'warning': 'These are HUMAN evidence-sufficiency judgments, not automatic answer correctness or generator groundedness.',
              'per_question': judged}
    paths['audit'].write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    _write_csv(paths['audit_details'], list(judged[0].keys()), judged)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='GroundTruth v0.5 offline DEV evidence-only audit, no model/API')
    parser.add_argument('--input', default=DEFAULT_INPUT, help='Existing DEV generation report JSON')
    parser.add_argument('--output-prefix', default=DEFAULT_PREFIX)
    parser.add_argument('--question-ids', help='Optional comma-separated DEV question IDs')
    parser.add_argument('--top-k', type=int, default=4)
    parser.add_argument('--max-snippets', type=int, default=6)
    parser.add_argument('--per-source', type=int, default=2)
    parser.add_argument('--max-chars', type=int, default=450)
    parser.add_argument('--score-review', action='store_true', help='Score hand-filled review CSV; do not rerun extraction')
    parser.add_argument('--force', action='store_true', help='Overwrite extraction outputs. WARNING: replaces human review entries.')
    args = parser.parse_args(argv)
    try:
        if args.score_review:
            result = score_review(Path(args.input), args.output_prefix)
            print('GroundTruth v0.5 HUMAN evidence review summary (not answer accuracy)')
            for key, value in result['summary'].items():
                print(f'  {key}: {value}')
            print('Audit:', _paths(args.output_prefix)['audit'])
        else:
            ids = set(x.strip() for x in args.question_ids.split(',') if x.strip()) if args.question_ids else None
            result = build(Path(args.input), args.output_prefix, ids=ids, top_k=args.top_k,
                           max_snippets=args.max_snippets, per_source=args.per_source,
                           max_chars=args.max_chars, force=args.force)
            print('GroundTruth v0.5 Evidence-Only DEV SHADOW summary')
            for key, value in result['summary'].items():
                print(f'  {key}: {value}')
            paths = _paths(args.output_prefix)
            print('Human review:', paths['review'])
            print('Evidence packets:', paths['packets'])
            print('Candidate excerpts:', paths['candidates'])
            print('Report:', paths['report'])
            print('Status: EVIDENCE EXTRACTED ONLY — no factual judgments or auto-abstentions')
        return 0
    except (EvidenceError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        parser.exit(2, f'GroundTruth v0.5 error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
