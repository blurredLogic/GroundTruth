import unittest
from groundtruth.evaluation.recover_missing_dev_evidence import targets, map_sources,RecoveryError
class RecoverTests(unittest.TestCase):
 def sample(self):
  ids=['k8s-022','k8s-034','k8s-068']+[f'other-{i}' for i in range(57)]
  return {'split':'dev','per_question':[{'question_id':x,'question':'Q',
   'status':'generation_error' if x.startswith('k8s') else 'answered',
   'split':'dev','sources':[]} for x in ids]}
 def test_three_only(self):self.assertEqual(len(targets(self.sample())),3)
 def test_refuses_test_split(self):
  o=self.sample();o['split']='test'
  with self.assertRaises(RecoveryError):targets(o)
 def test_refuses_source_modified(self):
  o=self.sample();o['per_question'][0]['sources']=[{'id':'C1'}]
  with self.assertRaises(RecoveryError):targets(o)
 def test_map_frozen_evidence(self):
  d=[{'rank':1,'chunk_id':'a','document_id':'doc','section_id':'sec',
      'heading_path':['Heading'],'source_url':'https://kubernetes.io/x','text':'x'*1700}]
  result=map_sources(d)
  self.assertTrue(result[0]['text'].endswith('[TRUNCATED EXCERPT]'))
  self.assertEqual(result[0]['id'],'C1')
  self.assertFalse(result[0]['cited'])
