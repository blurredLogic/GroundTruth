import copy
import json
import unittest
from pathlib import Path
from groundtruth.evaluation.release_readiness_audit import build_readiness
from groundtruth.evaluation.multihop_closure_audit import AuditError


class ReleaseReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures'
        cls.factuality = json.loads((root / 'dev_v07_assistant_audit.json').read_text(encoding='utf-8'))
        cls.closure = json.loads((root / 'multihop_closure_v071_audit.json').read_text(encoding='utf-8'))

    def test_v1_blocked_and_report_honest(self):
        out = build_readiness(self.factuality, self.closure)
        self.assertFalse(out['factuality_validated_v1_release_ready'])
        self.assertTrue(out['research_preview_documentation_possible'])
        self.assertTrue(any('negative' in g['name'].lower() and g['status']=='blocked' for g in out['gates']))

    def test_independent_review_not_invented(self):
        out = build_readiness(self.factuality, self.closure)
        self.assertTrue(any('0/56' in g['actual'] for g in out['gates']))

    def test_changed_source_rejected(self):
        other = copy.deepcopy(self.closure)
        other['source_sha256']='a'*64
        with self.assertRaises(AuditError): build_readiness(self.factuality, other)

    def test_unreviewed_changed_totals_rejected(self):
        other = copy.deepcopy(self.factuality)
        other['generation_status_counts']['answered']=55
        with self.assertRaises(AuditError): build_readiness(other, self.closure)

    def test_audit_does_not_represent_test_run(self):
        out = build_readiness(self.factuality, self.closure)
        self.assertTrue(any('TEST' in g['name'] and g['status']=='not_run_by_this_workflow' for g in out['gates']))


if __name__ == '__main__':
    unittest.main()
