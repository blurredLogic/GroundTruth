import copy
import hashlib
import json
import unittest
from pathlib import Path

from groundtruth.evaluation.multihop_closure_audit import (AuditError, FACETS, markdown_report, run, validate_and_assess)


class MultihopClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tests use a packaged, self-contained snapshot: no index or Ollama required.
        cls.path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "multihop_diagnostic_v07.json"
        cls.data = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.sha = hashlib.sha256(cls.path.read_bytes()).hexdigest()

    def assess(self, data=None):
        return validate_and_assess(data if data is not None else self.data, self.sha)

    def test_all_anchors_found(self):
        result = self.assess()
        self.assertTrue(result["all_facets_present"])
        self.assertEqual([c['facets_present'] for c in result['cases']], [5, 5])

    def test_provenance_survives(self):
        for row in self.assess()['cases']:
            self.assertEqual(row['manual_subqueries'], 3)
            self.assertEqual(row['retrieved_hits_including_duplicates'], 12)
            self.assertTrue(all(f['source_url'].startswith('https://kubernetes.io/') for f in row['facets']))

    def test_schema_rejection(self):
        data = copy.deepcopy(self.data); data['schema'] = 'unknown'
        with self.assertRaises(AuditError): self.assess(data)

    def test_test_split_rejected(self):
        data = copy.deepcopy(self.data); data['split'] = 'test'
        with self.assertRaises(AuditError): self.assess(data)

    def test_shadow_required(self):
        data = copy.deepcopy(self.data); data['shadow_only'] = False
        with self.assertRaises(AuditError): self.assess(data)

    def test_original_source_fingerprint_required(self):
        data = copy.deepcopy(self.data); data['source_sha256'] = '0' * 64
        with self.assertRaises(AuditError): self.assess(data)

    def test_frozen_weights_required(self):
        data = copy.deepcopy(self.data); data['retriever_description']['dense_weight'] = .5
        with self.assertRaises(AuditError): self.assess(data)

    def test_no_other_questions_allowed(self):
        data = copy.deepcopy(self.data); data['records'][0]['question_id'] = 'k8s-001'
        with self.assertRaises(AuditError): self.assess(data)

    def test_lost_anchor_not_counted(self):
        data = copy.deepcopy(self.data)
        for item in data['records'][0]['retrievals']:
            for s in item['sources']:
                if s['chunk_id'] == 'work-009-sec-033-ch-001':
                    s['text'] = 'Selector exists but the required-field statement is missing.'
        report = self.assess(data)
        self.assertFalse(report['all_facets_present'])
        self.assertEqual(report['cases'][0]['facets_present'], 4)

    def test_conflicting_duplicate_chunk_rejected(self):
        data = copy.deepcopy(self.data)
        data['records'][0]['retrievals'][1]['sources'][2]['text'] += ' mutated'
        with self.assertRaises(AuditError): self.assess(data)

    def test_missing_url_rejected(self):
        data = copy.deepcopy(self.data)
        data['records'][0]['retrievals'][0]['sources'][0]['source_url'] = ''
        with self.assertRaises(AuditError): self.assess(data)

    def test_markdown_never_implies_answer_accuracy(self):
        text = markdown_report(self.assess())
        self.assertIn('original answers for both questions remain **generation errors**', text)
        self.assertIn('manually designed targeted subqueries', text)


if __name__ == '__main__':
    unittest.main()
