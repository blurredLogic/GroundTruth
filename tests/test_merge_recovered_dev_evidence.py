import csv
import json
import tempfile
import unittest
from pathlib import Path
from groundtruth.evaluation.merge_recovered_dev_evidence import reconcile

class RecoveredReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.base = self.root/'original.csv'
        self.gen = self.root/'gen.json'
        self.rec = self.root/'rec.json'
        self.add = self.root/'add.csv'
        fields = ['question_id','question','evidence_status','evidence_ids','review_relation','review_confidence_0_2','review_notes','followup_needed']
        ids=['k8s-022','k8s-034','k8s-068']
        rows=[]
        for i in range(60):
            qid=ids[i] if i<3 else 'other-%03d'%i
            missing=i<3
            rows.append({'question_id':qid,'question':qid,'evidence_status':'missing_saved_retrieval' if missing else 'evidence_available','evidence_ids':'' if missing else 'E1','review_relation':'' if missing else 'supported','review_confidence_0_2':'' if missing else '2','review_notes':'' if missing else 'reviewed','followup_needed':''})
        with self.base.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        self.gen.write_text(json.dumps({'split':'dev','per_question':[{'question_id':r['question_id'],'question':r['question'],'status':'generation_error' if i<3 else 'answered','sources':[],'answerable':True} for i,r in enumerate(rows)]}))
        import hashlib
        sha=hashlib.sha256(self.gen.read_bytes()).hexdigest()
        sources=[{'id':f'C{i}','rank':i,'chunk_id':f'chunk-{i}','text':'example passage','source_url':'https://kubernetes.io/docs/concepts/test/'} for i in range(1,5)]
        self.rec.write_text(json.dumps({'split':'dev','source_input_sha256':sha,'frozen_hybrid_rrf_params':{'candidate_k':20,'rrf_k':20.0,'dense_weight':1.0,'bm25_weight':0.1},'retriever_description':{'chunk_count':1223,'dense':{'model':'BAAI/bge-small-en-v1.5'}},'records':[{'question_id':i,'question':i,'recovered_count':4,'sources':sources} for i in ids]}))
        with self.add.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['question_id','review_relation','review_confidence_0_2','evidence_ids','review_notes','followup_needed']);w.writeheader()
            for i in ids:
                w.writerow({'question_id':i,'review_relation':'partial' if i!='k8s-022' else 'supported','review_confidence_0_2':'2','evidence_ids':'C1; C2','review_notes':'Grounded explanation','followup_needed':''})
    def tearDown(self):
        self.tmp.cleanup()
    def test_three_scored_keep_other_57_unchanged(self):
        merged,audit=reconcile(self.base,self.gen,self.rec,self.add)
        self.assertEqual(len(merged),60)
        self.assertEqual(audit['reviewed_count'],60)
        self.assertEqual(audit['evidence_relation_counts']['supported'],58)
        self.assertEqual(audit['evidence_relation_counts']['partial'],2)
        self.assertEqual(merged[3]['review_notes'],'reviewed')
        self.assertEqual(audit['generation_status_unchanged']['generation_error'],3)
    def test_source_mismatch_rejected(self):
        d=json.loads(self.rec.read_text());d['source_input_sha256']='a'*64;self.rec.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'not produced'):
            reconcile(self.base,self.gen,self.rec,self.add)
    def test_nonfrozen_params_rejected(self):
        d=json.loads(self.rec.read_text());d['frozen_hybrid_rrf_params']['bm25_weight']=0.2;self.rec.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'parameter mismatch'):
            reconcile(self.base,self.gen,self.rec,self.add)
    def test_unknown_citation_rejected(self):
        rows=[]
        with self.add.open(newline='') as f:
            r=csv.DictReader(f); columns=r.fieldnames;rows=list(r)
        rows[0]['evidence_ids']='C9'
        with self.add.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
        with self.assertRaisesRegex(ValueError,'grounded citation'):
            reconcile(self.base,self.gen,self.rec,self.add)
    def test_duplicate_recovery_rejected(self):
        d=json.loads(self.rec.read_text());d['records'][1]['question_id']=d['records'][0]['question_id'];self.rec.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'exactly the three'):
            reconcile(self.base,self.gen,self.rec,self.add)
    def test_original_sources_present_rejected(self):
        d=json.loads(self.gen.read_text());d['per_question'][0]['sources']=[{'id':'C1'}];self.gen.write_text(json.dumps(d))
        import hashlib
        rec=json.loads(self.rec.read_text());rec['source_input_sha256']=hashlib.sha256(self.gen.read_bytes()).hexdigest();self.rec.write_text(json.dumps(rec))
        with self.assertRaisesRegex(ValueError,'does not show missing evidence'):
            reconcile(self.base,self.gen,self.rec,self.add)

if __name__=='__main__':unittest.main()
