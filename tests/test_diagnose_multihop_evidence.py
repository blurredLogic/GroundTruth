import json
import tempfile
import unittest
from pathlib import Path
from groundtruth.evaluation.diagnose_multihop_evidence import diagnose,DiagnosticError,SUBQUERIES,validate_source

class FakeRetriever:
    def describe(self):return {'index_type':'hybrid_rrf','candidate_k':20,'rrf_k':20.,'dense_weight':1.,'bm25_weight':.1,'chunk_count':1223}
    def search(self,query,top_k=4):
        return [{'chunk_id':'c1','document_id':'d1','source_url':'https://kubernetes.io/docs/','text':'Example quote for '+query,'heading_path':['Example']}]

class SubqueryTests(unittest.TestCase):
    def source(self):
        rows=[{'question_id':f'k8s-{i:03d}','split':'dev','question':'example','status':'answered'} for i in range(1,61)]
        rows[33]['status']='generation_error'
        # k8s-068 is outside 60 IDs; replace a row to produce unique 60
        rows[-1]['question_id']='k8s-068';rows[-1]['status']='generation_error'
        return {'split':'dev','per_question':rows}
    def test_reject_test(self):
        r=self.source();r['split']='test'
        with self.assertRaises(DiagnosticError):validate_source(r)
    def test_queries(self):
        self.assertEqual(len(SUBQUERIES['k8s-034']),3)
        self.assertEqual(len(SUBQUERIES['k8s-068']),3)
    def test_fake_retrieval(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'src.json';p.write_text(json.dumps(self.source()))
            output=Path(d)/'out.json'
            r=diagnose(p,output,retriever=FakeRetriever())
            self.assertEqual(len(r['records']),2)
            self.assertEqual(len(r['records'][0]['retrievals']),3)
            self.assertEqual(len(r['records'][1]['retrievals']),3)
            self.assertTrue(output.exists())
            with self.assertRaises(DiagnosticError):diagnose(p,output,retriever=FakeRetriever())
    def test_reject_changed_params(self):
        class Bad(FakeRetriever):
            def describe(self):return {**super().describe(),'rrf_k':40}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'src.json';p.write_text(json.dumps(self.source()))
            with self.assertRaises(DiagnosticError):diagnose(p,Path(d)/'out.json',retriever=Bad())
if __name__=='__main__':unittest.main()
