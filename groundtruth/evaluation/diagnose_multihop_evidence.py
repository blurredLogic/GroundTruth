"""DEV-only targeted subquery retrieval for k8s-034 and k8s-068.

Diagnostic only: frozen hybrid parameters/index, no generation, no TEST reads,
no merges or changes to the official v0.2 retrieval benchmark.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SUBQUERIES={
 'k8s-034':(
     'Deployment spec.selector requirement matches Pod template metadata labels immutable',
     'StatefulSet spec.selector Pod template matching labels immutable',
     'ReplicaSet DaemonSet Job pod selector requirement auto generated selector',
 ),
 'k8s-068':(
     'Kubernetes CSI driver VolumeSnapshot creation only CSI plugins snapshots',
     'Kubernetes clone PersistentVolumeClaim volume cloning CSI driver prerequisite',
     'Out of tree CSI volume plugins compared legacy in tree operations resize migration',
 ),
}
class DiagnosticError(ValueError):pass

def validate_source(original:dict)->None:
    if original.get('split')!='dev' or len(original.get('per_question',[]))!=60:
        raise DiagnosticError('Expected complete original DEV report; TEST not permitted')
    found={r.get('question_id'):r for r in original['per_question']}
    if len(found)!=60:raise DiagnosticError('Duplicate IDs')
    for k in SUBQUERIES:
        if k not in found or found[k]['status']!='generation_error':
            raise DiagnosticError('Expected generation_error '+k)

def _map(found:list[dict])->list[dict]:
    results=[]
    for i,r in enumerate(found,1):
        if not r.get('text'):continue
        results.append({'rank':i,'chunk_id':r['chunk_id'],'document_id':r['document_id'],
            'heading_path':r.get('heading_path',[]),'source_url':r['source_url'],
            'text':str(r['text'])[:2400]})
    return results

def diagnose(source_path:Path,output:Path,*,device='cpu',dense_index_dir=Path('data/index/dense'),bm25_index_dir=Path('data/index/bm25'),retriever=None)->dict:
    if output.exists():raise DiagnosticError('Refusing overwrite: '+str(output))
    src=source_path.read_bytes()
    original=json.loads(src)
    validate_source(original)
    if retriever is None:
        from groundtruth.retrieval.hybrid_retriever import HybridRetriever
        retriever=HybridRetriever(dense_index_dir=dense_index_dir,bm25_index_dir=bm25_index_dir,
           device=device,candidate_k=20,rrf_k=20.0,dense_weight=1.0,bm25_weight=0.1,verify_hashes=True)
    meta=retriever.describe()
    if (meta.get('index_type'),meta.get('candidate_k'),meta.get('rrf_k'),meta.get('dense_weight'),meta.get('bm25_weight'),meta.get('chunk_count')) != ('hybrid_rrf',20,20.0,1.0,0.1,1223):
        raise DiagnosticError('Retriever does not match frozen v0.2 benchmark settings')
    records=[]
    for id,qs in SUBQUERIES.items():
        runs=[]
        for q in qs:
            passages=_map(retriever.search(q,top_k=4))
            runs.append({'subquery':q,'sources':passages,'count':len(passages)})
            print(id,':',len(passages),'passages for',q[:60])
        records.append({'question_id':id,'retrievals':runs})
    result={'schema':'groundtruth_multihop_diagnostic_v0.7','split':'dev','shadow_only':True,
      'source_sha256':hashlib.sha256(src).hexdigest(),
      'retriever_description':meta,'records':records,
      'limitations':['These subqueries are a manually designed diagnostic, not baseline v0.2 question queries.',
         'They are evaluated only on DEV and must not be compared to frozen retrieval metrics.',
         'Retrieved text does not prove generation quality or entailment.']}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',default='reports/generation/grounded_qa_dev.json')
    parser.add_argument('--output',default='reports/factuality/multihop_diagnostic_v07.json')
    parser.add_argument('--device',default='cpu')
    parser.add_argument('--dense-index-dir',default='data/index/dense')
    parser.add_argument('--bm25-index-dir',default='data/index/bm25')
    a=parser.parse_args(argv)
    diagnose(Path(a.source),Path(a.output),device=a.device,dense_index_dir=Path(a.dense_index_dir),bm25_index_dir=Path(a.bm25_index_dir))
    print('Status: saved DEV-only diagnostic; frozen official retrieval results unchanged')

if __name__=='__main__':main()
