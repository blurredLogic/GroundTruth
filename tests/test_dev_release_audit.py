import csv
import json
from pathlib import Path
import tempfile
import unittest
from groundtruth.evaluation.dev_release_audit import audit, DevAuditError


class DevReleaseAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[1]
        cls.src=cls.root/'reports/generation/grounded_qa_dev.json'
        cls.evidence=cls.root/'reports/evidence_only/dev_v06_assistant_report.json'
        cls.review=cls.root/'reports/evidence_only/dev_v06_assistant_review.csv'
        cls.prov=cls.root/'reports/evidence_only/dev_v06_provenance.json'

    def test_missing_paths_raise(self):
        with self.assertRaises(FileNotFoundError):
            audit(Path('missing_source.json'),self.evidence,self.review,self.prov)

    def test_no_internal_report_self_certifies_as_truth(self):
        if not self.src.is_file():
            self.skipTest('Local user report must be supplied, no web fallback')
        result=audit(self.src,self.evidence,self.review,self.prov)
        self.assertFalse(result['release_gates']['base_v1_release_ready'])
        self.assertFalse(result['generation']['manual_factual_correctness_scored'])
        self.assertEqual(result['evidence']['assistant_reviewed_count'],57)
        self.assertEqual(result['evidence']['missing_saved_retrieval_ids'],['k8s-022','k8s-034','k8s-068'])
        self.assertEqual(result['generation']['negative_false_answers'],5)

    def test_provenance_alteration_rejected(self):
        if not self.src.is_file():
            self.skipTest('Local user report must be supplied')
        data=json.loads(self.prov.read_text(encoding='utf-8'))
        data['source_report_sha256']='0'*64
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'prov.json';p.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaisesRegex(DevAuditError,'SHA'):
                audit(self.src,self.evidence,self.review,p)

if __name__=='__main__':unittest.main()
