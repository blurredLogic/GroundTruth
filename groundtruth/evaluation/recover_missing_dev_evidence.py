"""Recover saved retrieval passages for three DEV generation-error rows.

Separate output only. Does not rerun generation, edit the golden set, or open TEST.
Requires existing local frozen Hybrid RRF indexes; CPU supported.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

MISSING_IDS=('k8s-022','k8s-034','k8s-068')

class RecoveryError(ValueError):pass


def targets(source:dict[str,Any]) -> list[dict[str,Any]]:
    if source.get('split')!='dev':raise RecoveryError('Refusing non-DEV source')
    rows={r['question_id']:r for r in source.get('per_question',[])}
    if len(rows)!=60 or len(source.get('per_question',[]))!=60:raise RecoveryError('Expected 60 distinct DEV rows')
    out=[]
    for id in MISSING_IDS:
        r=rows.get(id)
        if not r or r.get('split')!='dev' or r.get('status')!='generation_error' or r.get('sources'):
            raise RecoveryError('Missing-evidence assumptions changed: '+id)
        out.append(r)
    return out


def map_sources(results:list[dict],max_chars:int=1500)->list[dict]:
    sources=[]
    for result in results:
        if not result.get('text'):continue
        t=str(result['text']).strip()
        snippet=t[:max_chars]
        if len(t)>max_chars:snippet+=' [TRUNCATED EXCERPT]'
        sources.append({'id':f'C{len(sources)+1}', 'rank':int(result['rank']),
            'chunk_id':str(result['chunk_id']), 'document_id':str(result['document_id']),
            'section_id':str(result['section_id']), 'heading_path':list(result.get('heading_path') or []),
            'source_url':str(result['source_url']), 'text':snippet, 'cited':False})
    return sources


def recover(source_path:Path,output_path:Path,*,device:str='cpu',
            dense_index_dir:Path=Path('data/index/dense'),
            bm25_index_dir:Path=Path('data/index/bm25')) -> dict:
    if output_path.exists():raise RecoveryError('Output exists; refusing overwrite: '+str(output_path))
    raw=source_path.read_bytes()
    original=json.loads(raw)
    records=targets(original)
    from groundtruth.retrieval.hybrid_retriever import HybridRetriever
    h=HybridRetriever(dense_index_dir=dense_index_dir,bm25_index_dir=bm25_index_dir,
                      device=device, candidate_k=20,rrf_k=20.0,dense_weight=1.0,bm25_weight=0.1,
                      verify_hashes=True)
    meta=h.describe()
    if any((meta.get('rrf_k')!=20.0,meta.get('candidate_k')!=20,meta.get('dense_weight')!=1.0,
            meta.get('bm25_weight')!=0.1)):
        raise RecoveryError('Frozen retriever settings differ')
    out=[]
    for r in records:
        found=h.search(r['question'],top_k=4)
        sources=map_sources(found)
        out.append({'question_id':r['question_id'],'question':r['question'],
                    'sources':sources,'recovered_count':len(sources)})
        print(f"{r['question_id']}: {len(sources)} retrieval passages recovered")
    record={'schema':'groundtruth_missing_dev_recovery_v0.6','split':'dev','source_input_sha256':hashlib.sha256(raw).hexdigest(),
            'frozen_hybrid_rrf_params':{'candidate_k':20,'rrf_k':20.0,'dense_weight':1.0,'bm25_weight':0.1},
            'retriever_description':meta,'records':out,
            'limitations':['Recovered passages were retrieved later, not recorded at original generation time.',
                           'Retrieval does not establish model answer correctness or human support.',
                           'No TEST queries or gold labels used.']}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    output_path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return record


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--source',default='reports/generation/grounded_qa_dev.json')
    p.add_argument('--output',default='reports/evidence_only/missing_dev_recovered_v06.json')
    p.add_argument('--device',default='cpu')
    p.add_argument('--dense-index-dir',default='data/index/dense')
    p.add_argument('--bm25-index-dir',default='data/index/bm25')
    args=p.parse_args(argv)
    try:
        recover(Path(args.source),Path(args.output),device=args.device,
                dense_index_dir=Path(args.dense_index_dir),bm25_index_dir=Path(args.bm25_index_dir))
        print('Status: DEV evidence recovery only; questions remain UNADJUDICATED')
        return 0
    except (RecoveryError,OSError,KeyError,ValueError) as exc:
        p.exit(2,'Missing DEV evidence recovery failed: '+str(exc)+'\n')

if __name__=='__main__':raise SystemExit(main())
