"""Offline DEV answer-factuality review and scoring; Python 3.10+ stdlib only.

Review data is assistant-prepared and not an independent human evaluation.
Never calls an LLM, changes retrieval, reads TEST, or equates valid citations with entailment.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

OUTCOMES = {'correct_complete', 'correct_incomplete', 'incorrect', 'needs_review', 'not_applicable'}
CITATION = {'fully_supported', 'partially_supported', 'unsupported', 'needs_review', 'not_applicable'}
COLUMNS = ['question_id','question','generation_status','generated_answer','inline_citations',
           'cited_chunk_ids','cited_source_urls','cited_passages','reference_excerpts_NOT_a_ground_truth_answer',
           'assistant_factuality','assistant_citation_support','assistant_review_note','assistant_review_confidence_0_2',
           'review_provenance','independent_review_factuality','independent_review_citation_support',
           'independent_reviewer_notes','independent_review_status']

class AuditError(ValueError):
    pass

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_dev(path: Path) -> dict:
    obj=json.loads(path.read_text(encoding='utf-8'))
    records=obj.get('per_question',[])
    ids=[str(r.get('question_id','')) for r in records]
    if obj.get('split')!='dev' or len(ids)!=60 or len(set(ids))!=60 or any(r.get('split')!='dev' for r in records):
        raise AuditError('Expected original, complete, unique 60-question DEV report; TEST is prohibited')
    if sum(bool(r.get('answerable')) for r in records)!=54:
        raise AuditError('DEV answerability composition differs from baseline')
    return obj

def _padded_sources(record: dict) -> str:
    cited=set(record.get('citations') or [])
    chunks=[]
    for s in record.get('sources') or []:
        text=str(s.get('text','')).strip()
        if not text: continue
        chunks.append(f"[{s.get('id','')}] {s.get('chunk_id','')}: {text[:1800]}")
    return '\n\n-----\n\n'.join(chunks)

def make_rows(source: dict, curated: dict | None = None) -> list[dict]:
    curated=curated or {}
    original=source['per_question']
    extras=set(curated)-{r['question_id'] for r in original}
    if extras: raise AuditError('Unrecognized curated IDs: '+str(sorted(extras)))
    rows=[]
    for r in original:
        selected=[s for s in r.get('sources',[]) if s.get('id') in set(r.get('citations') or [])]
        row=dict.fromkeys(COLUMNS,'')
        row.update(question_id=r['question_id'],question=r.get('question',''),generation_status=r['status'],
            generated_answer=r.get('answer') or '',inline_citations=';'.join(r.get('citations') or []),
            cited_chunk_ids=';'.join(s.get('chunk_id','') for s in selected),
            cited_source_urls=';'.join(s.get('source_url','') for s in selected),
            cited_passages='\n\n-----\n\n'.join(f"[{s.get('id','')}] {s.get('chunk_id','')}: {s.get('text','')}" for s in selected),
            reference_excerpts_NOT_a_ground_truth_answer=_padded_sources(r),
            assistant_factuality='needs_review',assistant_citation_support='needs_review',
            assistant_review_confidence_0_2='', review_provenance='unreviewed',
            independent_review_status='UNREVIEWED')
        if r['status']!='answered':
            row.update(assistant_factuality='not_applicable',assistant_citation_support='not_applicable',
                       assistant_review_note='Operational status only: '+r['status']+'. Not a generated-answer factuality judgment.',
                       review_provenance='operational_only')
        if r['question_id'] in curated:
            label,cite,note,confidence=curated[r['question_id']]
            if r['status']!='answered':raise AuditError('Cannot curate non-answer: '+r['question_id'])
            if label not in OUTCOMES or cite not in CITATION or not note or str(confidence) not in ('0','1','2'):
                raise AuditError('Invalid curated judgment for '+r['question_id'])
            row.update(assistant_factuality=label,assistant_citation_support=cite,
                       assistant_review_note=note,assistant_review_confidence_0_2=str(confidence),
                       review_provenance='assistant_first_pass_NOT_independent')
        rows.append(row)
    return rows

def read_review(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=COLUMNS:
            raise AuditError('Unexpected review columns, do not remove provenance or status fields')
        return list(reader)

def write_review(path: Path,rows:list[dict]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=COLUMNS)
        writer.writeheader();writer.writerows(rows)

def score(source: Path, review: Path, expected_source_sha256: str | None=None)->dict:
    raw=load_dev(source)
    if expected_source_sha256 and sha256(source)!=expected_source_sha256:
        raise AuditError('Original DEV source fingerprint mismatch; cannot reuse annotations')
    rows=read_review(review)
    orig={r['question_id']:r for r in raw['per_question']}
    if len(rows)!=60 or len({r['question_id'] for r in rows})!=60 or set(orig)!={r['question_id'] for r in rows}:
        raise AuditError('Review must contain all 60 DEV questions exactly once')
    reviewed=Counter();cited=Counter();independent=Counter(); statuses=Counter()
    errors=[]
    for row in rows:
        q=orig[row['question_id']];id=q['question_id'];status=q['status']
        if row['question']!=q['question'] or row['generation_status']!=status or row['generated_answer']!=(q.get('answer') or ''):
            raise AuditError('Review modified source content/status for '+id)
        if row['inline_citations']!=';'.join(q.get('citations') or []):
            raise AuditError('Review modified citation IDs for '+id)
        if row['assistant_factuality'] not in OUTCOMES or row['assistant_citation_support'] not in CITATION:
            raise AuditError('Unknown answer or citation label at '+id)
        if status!='answered' and (row['assistant_factuality']!='not_applicable' or row['assistant_citation_support']!='not_applicable'):
            raise AuditError('Non-answer may not be graded as generated answer at '+id)
        if status=='answered' and (row['assistant_factuality']=='not_applicable' or row['assistant_citation_support']=='not_applicable'):
            raise AuditError('Answered response cannot be not_applicable at '+id)
        if row['review_provenance'].startswith('assistant_first_pass') and not row['assistant_review_note'].strip():
            raise AuditError('Missing assistant review justification at '+id)
        status_ind=row['independent_review_status']
        if status_ind not in ('UNREVIEWED','REVIEWED'):
            raise AuditError('Unknown independent review status at '+id)
        if status_ind=='REVIEWED':
            if not row['independent_reviewer_notes'].strip() or row['independent_review_factuality'] not in OUTCOMES or row['independent_review_citation_support'] not in CITATION:
                raise AuditError('Independent completed review missing justification at '+id)
            independent['reviewed']+=1
        statuses[status]+=1
        if status=='answered':
            reviewed[row['assistant_factuality']]+=1
            cited[row['assistant_citation_support']]+=1
        elif status=='generation_error':errors.append(id)
    assessed=sum(reviewed[k] for k in ('correct_complete','correct_incomplete','incorrect'))
    correct=reviewed['correct_complete'];incomplete=reviewed['correct_incomplete'];wrong=reviewed['incorrect']
    return {'schema':'groundtruth_answer_factuality_audit_v0.7',
      'dataset':'DEV ONLY; original 60-question saved generation report',
      'source_sha256':sha256(source),'review_csv_sha256':sha256(review),
      'generation_status_counts':dict(statuses),
      'generated_answer_count':statuses['answered'],
      'assistant_assessed_answer_count':assessed,
      'assistant_unreviewed_answer_count':reviewed['needs_review'],
      'assistant_reviewed_assessment_counts':{'correct_complete':correct,'correct_incomplete':incomplete,'incorrect':wrong},
      'assistant_citation_counts':dict(cited),
      'assistant_assessed_accuracy_complete_only':round(correct/assessed,6) if assessed else None,
      'assistant_assessed_accuracy_allow_incomplete':round((correct+incomplete)/assessed,6) if assessed else None,
      'independent_reviewed_question_count':independent['reviewed'],
      'negative_false_answer_count_from_operational_labels':sum((not bool(r['answerable'])) and r['status']=='answered' for r in orig.values()),
      'negative_correct_abstention_count_from_operational_labels':sum((not bool(r['answerable'])) and r['status']=='abstained' for r in orig.values()),
      'generation_error_ids':errors,
      'groundedness_claim_level_independently_verified':False,
      'limitations':['Assistant review is not an independent human judgment.',
         'Assistant-assessed accuracy denominators exclude unanswered/unassessed answers; do not call them model accuracy.',
         'Source label correctness depends on saved excerpt completeness and reviewer assessment.',
         'Citation syntax and gold overlap do not prove semantic entailment.',
         'Generation errors and abstentions are scored separately; held-out TEST is not used.']}

def render_markdown(r: dict)->str:
    cc=r['assistant_reviewed_assessment_counts']; gc=r['generation_status_counts']
    s=['# GroundTruth v0.7 — DEV generated-answer factuality audit','',
      '**Provenance: assistant first-pass review, not independent adjudication.**','',
      f"- DEV questions: {sum(gc.values())}; answered: {r['generated_answer_count']}; generation errors: {gc.get('generation_error',0)}; abstentions: {gc.get('abstained',0)}.",
      f"- Assistant-assessed generated answers: {r['assistant_assessed_answer_count']} / {r['generated_answer_count']}.",
      f"- Correct and complete: {cc['correct_complete']}; factually correct but incomplete: {cc['correct_incomplete']}; incorrect: {cc['incorrect']}.",
      f"- Unassessed generated answers: {r['assistant_unreviewed_answer_count']}.",
      f"- Citation support judgments: {r['assistant_citation_counts']}.",
      f"- Negative question false answers in original output: {r['negative_false_answer_count_from_operational_labels']}; correct negative abstentions: {r['negative_correct_abstention_count_from_operational_labels']}.",
      f"- Independent human review: {r['independent_reviewed_question_count']} / 60.",
      '', '## Interpretation','',
      'Assistant-assessed fractions are **subset statistics**, not full 60-question answer accuracy or a deployed groundedness guarantee.',
      'For defensible release claims, obtain a separate human review of the relevant answer claims and citations, resolve unassessed cases, and report full-DEV denominators.',
      'Retain retrieval metrics as frozen and report generation failures and negative false answers alongside factuality.',
      '', '## Generation errors','',', '.join(r['generation_error_ids']),'',
      '## Provenance','',f"- Source SHA256: `{r['source_sha256']}`",f"- Review SHA256: `{r['review_csv_sha256']}`",'']
    return '\n'.join(s)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',default='reports/generation/grounded_qa_dev.json')
    ap.add_argument('--review',default='reports/factuality/dev_v07_assistant_review.csv')
    ap.add_argument('--expected-source-sha256',default='')
    ap.add_argument('--output-prefix',default='reports/factuality/dev_v07_assistant')
    args=ap.parse_args(argv)
    result=score(Path(args.source),Path(args.review),args.expected_source_sha256 or None)
    prefix=Path(args.output_prefix);prefix.parent.mkdir(parents=True,exist_ok=True)
    prefix.with_name(prefix.name+'_audit.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    prefix.with_name(prefix.name+'_audit.md').write_text(render_markdown(result),encoding='utf-8')
    print(render_markdown(result))
    return result

if __name__=='__main__': main()
