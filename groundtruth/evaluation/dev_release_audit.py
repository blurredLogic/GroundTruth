"""DEV-only GroundTruth release evidence audit, offline and fully reproducible.

DOES NOT assert model factual correctness or independent human agreement.
The evidence review is assistant-authored, using v0.5 verbatim snippets.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

class DevAuditError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(source: Path, evidence_report: Path, review_csv: Path, provenance: Path) -> dict:
    raw=json.loads(source.read_text(encoding='utf-8'))
    ev=json.loads(evidence_report.read_text(encoding='utf-8'))
    prov=json.loads(provenance.read_text(encoding='utf-8'))
    with review_csv.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if raw.get('split')!='dev' or ev.get('split')!='dev':
        raise DevAuditError('Refusing non-DEV source or evidence report')
    if prov.get('origin','').lower().find('assistant') < 0:
        raise DevAuditError('Provenance must disclose assistant annotation')
    if prov.get('source_report_sha256')!=_sha(source) or ev.get('input_sha256')!=_sha(source):
        raise DevAuditError('Source report SHA changed; refusing stale review')
    if prov.get('evidence_report_sha256')!=_sha(evidence_report):
        raise DevAuditError('Evidence report SHA changed')
    if prov.get('review_csv_sha256')!=_sha(review_csv):
        raise DevAuditError('Review CSV SHA changed; update provenance intentionally')
    original=raw.get('per_question',[])
    evidence=ev.get('per_question',[])
    if len(original)!=60 or len(evidence)!=60 or len(rows)!=60:
        raise DevAuditError('Expected exactly 60 original, evidence and review DEV rows')
    orig_by={x['question_id']:x for x in original}
    ev_by={x['question_id']:x for x in evidence}
    rev_by={x['question_id']:x for x in rows}
    if any(len(x)!=60 for x in (orig_by,ev_by,rev_by)) or not (orig_by.keys()==ev_by.keys()==rev_by.keys()):
        raise DevAuditError('Question IDs duplicated or mismatched')
    statuses=Counter()
    relations=Counter()
    positive=Counter()
    negative=Counter()
    missing=[]
    notes_missing=[]
    for qid,r in orig_by.items():
        e=ev_by[qid]; v=rev_by[qid]
        if r.get('split')!='dev' or r.get('question')!=e.get('question') or r.get('question')!=v.get('question'):
            raise DevAuditError('Question text or split mismatch: '+qid)
        relation=v['review_relation'].strip().lower()
        if relation and relation not in {'supported','partial','insufficient','contradicted','unclear'}:
            raise DevAuditError('Invalid evidence relation: '+qid)
        if relation:
            if v.get('review_confidence_0_2') not in ('0','1','2') or not v.get('review_notes','').strip():
                notes_missing.append(qid)
        elif v.get('review_confidence_0_2'):
            raise DevAuditError('Confidence on unreviewed record: '+qid)
        if e['evidence_status']=='missing_saved_retrieval':
            missing.append(qid)
            if relation:
                raise DevAuditError('Unscored missing evidence has a label: '+qid)
        elif not e.get('selected'):
            raise DevAuditError('Evidence_available record has no excerpts: '+qid)
        if r.get('status') not in {'answered','abstained','generation_error'}:
            raise DevAuditError('Unexpected generation status: '+qid)
        statuses[r['status']]+=1
        relations[relation or 'unreviewed']+=1
        (positive if r['answerable'] else negative)[relation or 'unreviewed']+=1
    if notes_missing:
        raise DevAuditError('Notes/confidence missing: '+', '.join(notes_missing))
    if sum(bool(r['answerable']) for r in original)!=54:
        raise DevAuditError('Expected frozen 54 DEV answerable questions')
    if sorted(missing)!=['k8s-022','k8s-034','k8s-068']:
        raise DevAuditError('Unexpected missing passage IDs: '+repr(sorted(missing)))
    # Preserve observed generation outcome rather than inferring success from sources.
    neg_false=sum((not r['answerable']) and r['status']=='answered' for r in original)
    neg_abstain=sum((not r['answerable']) and r['status']=='abstained' for r in original)
    result={
        'schema':'groundtruth_dev_release_audit_v0.6',
        'data_scope':'DEV ONLY; TEST data not used',
        'annotation_origin':prov['origin'],
        'source_sha256':_sha(source),
        'review_sha256':_sha(review_csv),
        'question_count':len(original),
        'generation':{'status_counts':dict(statuses), 'negative_false_answers':neg_false,
                      'negative_correct_abstentions':neg_abstain,
                      'answerable_answered':sum(r['answerable'] and r['status']=='answered' for r in original),
                      'manual_factual_correctness_scored':False},
        'evidence':{'relation_counts':dict(relations),'answerable_relations':dict(positive),
                    'negative_relations':dict(negative),'missing_saved_retrieval_ids':missing,
                    'assistant_reviewed_count':len(original)-len(missing),
                    'independently_human_adjudicated':False,
                    'generated_answer_groundedness_scored':False},
        'release_gates':{
            'frozen_retriever_regression':'PASSED IN USER LOCAL LOGS; NOT REEXECUTED HERE',
            'evidence_review_provenance':'COMPLETE_ASSISTANT_ONLY',
            'missing_evidence_recovered':False,
            'independent_factual_review_complete':False,
            'semantic_generator_reliability':'NOT_PASSED',
            'base_v1_release_ready':False,
        },
        'limitations':['Review uses up to six selected lexical excerpts, not exhaustive retrieved context.',
            'Evidence sufficiency is not the same as the correctness of the model answer.',
            'Assistant annotations are not independent human ground truth.',
            'Three generation-error questions lack saved source passages.',
            'All six gold-negative DEV questions were in an earlier probe; DEV should not be used as fresh independent confirmation.',
            'Held-out TEST set is untouched.']
    }
    return result


def render_markdown(s:dict)->str:
    gen=s['generation']; ev=s['evidence']
    return '\n'.join([
        '# GroundTruth v0.6 — DEV release evidence audit','',
        '**Status: EVALUATION SNAPSHOT, NOT RELEASE-READY.** No TEST questions are used.','',
        '## Grounded counts','',
        f"- Original DEV generation: {gen['status_counts'].get('answered',0)} answered, {gen['status_counts'].get('abstained',0)} abstained, {gen['status_counts'].get('generation_error',0)} errors.",
        f"- Unsupported answers on the six DEV negatives: {gen['negative_false_answers']}/6; correct abstentions {gen['negative_correct_abstentions']}/6.",
        f"- Saved evidence: {ev['assistant_reviewed_count']}/60, missing {len(ev['missing_saved_retrieval_ids'])}: {', '.join(ev['missing_saved_retrieval_ids'])}.",
        f"- Assistant review selected-excerpt relations: {', '.join(f'{k}={v}' for k,v in sorted(ev['relation_counts'].items()))}.",
        f"- For 54 answerable questions: {', '.join(f'{k}={v}' for k,v in sorted(ev['answerable_relations'].items()))}.",
        f"- For six negative questions: {', '.join(f'{k}={v}' for k,v in sorted(ev['negative_relations'].items()))}.",
        '', '## Critical distinctions','',
        '- `supported` means selected retrieved excerpts can answer the QUESTION. It is **not** model-answer accuracy.',
        '- `partial` often means the excerpt selector dropped one part of a multi-part question; see review notes for full-source follow-up.',
        '- `insufficient` means these selected excerpts do not establish the answer, not that the entire Kubernetes documentation cannot answer it.',
        '- Three missing cases are **unreviewed**, not negative questions and not insufficient evidence.',
        '- Six negative DEV questions were previously inspected for tuning/triage: results are diagnostic, not unbiased hold-out performance.',
        '', '## Release decision','',
        '**Do not release as a factuality-validated v1.0.** The frozen retrieval regression is green, but generator factual correctness/abstention and independent adjudication remain incomplete. Leave experimental semantic gates in shadow mode.','',
        'Next: (1) re-retrieve evidence for 022/034/068, (2) expand selected excerpts where partial, '
        '(3) perform an independent answer-versus-evidence factual review, '
        '(4) freeze criteria before a final untouched TEST evaluation.',
    ])+'\n'


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='reports/generation/grounded_qa_dev.json')
    p.add_argument('--evidence-report',default='reports/evidence_only/dev_v06_assistant_report.json')
    p.add_argument('--review',default='reports/evidence_only/dev_v06_assistant_review.csv')
    p.add_argument('--provenance',default='reports/evidence_only/dev_v06_provenance.json')
    p.add_argument('--output-prefix',default='reports/release/dev_v06')
    a=p.parse_args(argv)
    try:
        result=audit(Path(a.source),Path(a.evidence_report),Path(a.review),Path(a.provenance))
        base=Path(a.output_prefix)
        base.parent.mkdir(parents=True,exist_ok=True)
        (Path(str(base)+'_audit.json')).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        (Path(str(base)+'_audit.md')).write_text(render_markdown(result),encoding='utf-8')
        print(render_markdown(result))
        print('Status: NOT RELEASE READY — review remains assistant-authored')
        return 0
    except (DevAuditError,ValueError,KeyError,OSError) as exc:
        p.exit(2,'DEV release audit failed: '+str(exc)+'\n')

if __name__=='__main__':
    raise SystemExit(main())
