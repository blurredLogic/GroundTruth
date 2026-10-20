"""Reconcile 3 later-retrieved DEV evidence packets with the immutable v0.6 review.

No model calls, TEST access, claim-entailment inference, or modification to original files.
Python 3.10+; standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

EXPECTED_IDS = ('k8s-022', 'k8s-034', 'k8s-068')
RELATIONS = {'supported', 'partial', 'insufficient', 'contradicted'}
COLUMNS = (
    'question_id', 'question', 'evidence_status', 'evidence_ids',
    'review_relation', 'review_confidence_0_2', 'review_notes', 'followup_needed',
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def csv_rows(path: Path):
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = reader.fieldnames
    return columns, rows

def reconcile(base_review: Path, source_report: Path, recovery: Path, addendum: Path):
    base_cols, base_rows = csv_rows(base_review)
    if base_cols != list(COLUMNS) or len(base_rows) != 60:
        raise ValueError('Expected unchanged 60-question v0.6 review schema')
    base_ids = [r['question_id'] for r in base_rows]
    if len(set(base_ids)) != 60:
        raise ValueError('Duplicate question ID in baseline review')

    src = json.loads(source_report.read_text(encoding='utf-8'))
    src_rows = {r['question_id']: r for r in src['per_question']}
    if src.get('split') != 'dev' or len(src_rows) != 60:
        raise ValueError('Source must be full 60-question DEV generation report')

    rec = json.loads(recovery.read_text(encoding='utf-8'))
    if rec.get('split') != 'dev' or rec.get('source_input_sha256') != sha256(source_report):
        raise ValueError('Recovered evidence was not produced from the supplied DEV report')
    params = rec.get('frozen_hybrid_rrf_params', {})
    for name, expected in {'candidate_k':20, 'rrf_k':20.0, 'dense_weight':1.0, 'bm25_weight':0.1}.items():
        if params.get(name) != expected:
            raise ValueError('Frozen retrieval parameter mismatch: '+name)
    description = rec.get('retriever_description', {})
    if description.get('chunk_count') != 1223 or description.get('dense', {}).get('model') != 'BAAI/bge-small-en-v1.5':
        raise ValueError('Index metadata differs from frozen v0.6 retrieval baseline')
    recovered_rows = rec.get('records', [])
    recovered_by_id = {r['question_id']: r for r in recovered_rows}
    if len(recovered_rows) != 3 or set(recovered_by_id) != set(EXPECTED_IDS):
        raise ValueError('Expected exactly the three original missing DEV IDs')

    ad_cols, annotated = csv_rows(addendum)
    required = {'question_id','review_relation','review_confidence_0_2','evidence_ids','review_notes','followup_needed'}
    if not required.issubset(set(ad_cols or [])) or len(annotated) != 3:
        raise ValueError('Recovery annotations need exactly three completed rows')
    annotation_by_id = {r['question_id']: r for r in annotated}
    if set(annotation_by_id) != set(EXPECTED_IDS):
        raise ValueError('Recovery annotation IDs mismatch')

    for qid in EXPECTED_IDS:
        item = recovered_by_id[qid]
        orig = src_rows[qid]
        if orig.get('status') != 'generation_error' or orig.get('sources'):
            raise ValueError('The original source report does not show missing evidence for '+qid)
        if orig.get('question') != item.get('question'):
            raise ValueError('Recovered question text differs: '+qid)
        sources = item.get('sources', [])
        if len(sources) != 4 or item.get('recovered_count') != 4:
            raise ValueError('Expected top-four recovered sources: '+qid)
        ids = set()
        for i, passage in enumerate(sources, start=1):
            if passage.get('id') != f'C{i}' or passage.get('rank') != i:
                raise ValueError('Passage provenance IDs/ranks malformed for '+qid)
            if not passage.get('chunk_id') or not passage.get('text') or not passage.get('source_url','').startswith('https://kubernetes.io/docs/'):
                raise ValueError('Recovered source missing text/URL/chunk provenance: '+qid)
            ids.add(passage['id'])
        a = annotation_by_id[qid]
        if a['review_relation'] not in RELATIONS or a['review_confidence_0_2'] not in {'0','1','2'}:
            raise ValueError('Invalid review relation or confidence for '+qid)
        cited_ids = [s.strip() for s in a['evidence_ids'].split(';') if s.strip()]
        if not cited_ids or not set(cited_ids).issubset(ids) or not a['review_notes'].strip():
            raise ValueError('Annotation requires grounded citation IDs and notes for '+qid)

    merged = []
    for row in base_rows:
        row = dict(row)
        qid = row['question_id']
        if qid in recovered_by_id:
            if row['evidence_status'] != 'missing_saved_retrieval' or row['review_relation']:
                raise ValueError('Cannot overwrite existing scored evidence: '+qid)
            a = annotation_by_id[qid]
            row.update({
                'evidence_status': 'recovered_retrieval_later_run',
                'evidence_ids': a['evidence_ids'],
                'review_relation': a['review_relation'],
                'review_confidence_0_2': a['review_confidence_0_2'],
                'review_notes': a['review_notes'],
                'followup_needed': a['followup_needed'],
            })
        merged.append(row)
    count = Counter(r['review_relation'] for r in merged)
    if set(count) - RELATIONS or sum(count.values()) != 60:
        raise ValueError('Merged review still has unscored rows')

    breakdown = {'answerable': Counter(), 'negative': Counter()}
    for row in merged:
        bucket = 'answerable' if src_rows[row['question_id']]['answerable'] else 'negative'
        breakdown[bucket][row['review_relation']] += 1
    result = {
        'schema':'groundtruth_dev_recovery_addendum_v0.6.1',
        'scope':'DEV_ONLY; original TEST untouched',
        'assistant_reviewed_not_independently_adjudicated':True,
        'source_generation_sha256':sha256(source_report),
        'original_review_sha256':sha256(base_review),
        'recovery_file_sha256':sha256(recovery),
        'recovery_annotations_sha256':sha256(addendum),
        'recovery_run_is_later_not_original': True,
        'newly_reviewed_ids':list(EXPECTED_IDS),
        'evidence_relation_counts':dict(count),
        'answerable_evidence_relations':dict(breakdown['answerable']),
        'negative_evidence_relations':dict(breakdown['negative']),
        'reviewed_count':60,
        'generation_status_unchanged':dict(Counter(r['status'] for r in src['per_question'])),
        'generated_answer_correctness_independently_scored':False,
        'v1_release_ready':False,
        'limitations':[
            'Assistant-authored relations evaluate evidence sufficiency, not answer accuracy.',
            'Three evidence packets were retrieved later, after the original generation errors.',
            'k8s-034 omits Deployment and StatefulSet selector requirements in top-four chunks.',
            'k8s-068 omits CSI-only snapshot/restore and cloning evidence in top-four chunks.',
            'Earlier 57 reviews used selected excerpts; these 3 use full recovered top-four chunks.',
            'The previously frozen retriever quality metrics are unaffected.',
            'Independent claim-level review and an untouched TEST evaluation remain required.',
        ],
    }
    return merged, result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-review', type=Path, default=Path('reports/evidence_only/dev_v06_assistant_review.csv'))
    ap.add_argument('--source-report', type=Path, default=Path('reports/generation/grounded_qa_dev.json'))
    ap.add_argument('--recovery', type=Path, default=Path('reports/evidence_only/missing_dev_recovered_v06.json'))
    ap.add_argument('--annotations', type=Path, default=Path('reports/evidence_only/dev_v06_recovery_assistant_addendum.csv'))
    ap.add_argument('--output-prefix', type=Path, default=Path('reports/evidence_only/dev_v06_recovered_assistant'))
    args = ap.parse_args()
    output_csv = Path(str(args.output_prefix) + '_review.csv')
    output_json = Path(str(args.output_prefix) + '_audit.json')
    for p in [args.base_review, args.source_report, args.recovery, args.annotations]:
        if not p.exists():
            ap.error('Required file missing: '+str(p))
    if output_csv.resolve() in {p.resolve() for p in [args.base_review,args.source_report,args.recovery,args.annotations]} or output_json.resolve() in {p.resolve() for p in [args.base_review,args.source_report,args.recovery,args.annotations]}:
        ap.error('Output must not overwrite original inputs')
    merged, audit = reconcile(args.base_review, args.source_report, args.recovery, args.annotations)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open('w',encoding='utf-8',newline='') as f:
        writer = csv.DictWriter(f,fieldnames=COLUMNS,lineterminator='\n')
        writer.writeheader()
        writer.writerows(merged)
    output_json.write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('GroundTruth v0.6.1 recovered-evidence addendum (DEV, assistant-reviewed)')
    print('  recovered: 3 / 3')
    print('  supported:',audit['evidence_relation_counts'].get('supported',0))
    print('  partial:',audit['evidence_relation_counts'].get('partial',0))
    print('  insufficient:',audit['evidence_relation_counts'].get('insufficient',0))
    print('  contradicted:',audit['evidence_relation_counts'].get('contradicted',0))
    print('  independent answer accuracy: NOT SCORED')
    print('  original generation failures: UNCHANGED')
    print('Review:',output_csv)
    print('Audit:',output_json)

if __name__ == '__main__':
    main()
