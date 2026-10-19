"""Fast dependency-free tests for frozen retrieval CI protection."""
from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from groundtruth.ci.check_golden import GoldenError, semantic_fingerprint, validate_golden
from groundtruth.ci.check_retrieval_regression import check_report


BASELINE_PATH = Path('configs/frozen_retrieval_v1.json')


def synthetic_golden():
    return [
        {'question_id': 'k8s-001', 'question': 'What is a PersistentVolume?',
         'category': 'direct_factual', 'difficulty': 'easy', 'split': 'dev',
         'answerable': True, 'relevance_judgments': [
             {'chunk_id': 'stor-003-sec-002-ch-001', 'grade': 3}]},
        {'question_id': 'k8s-012', 'question': 'Does this unsupported snapshot field exist?',
         'category': 'negative_near_miss', 'difficulty': 'hard', 'split': 'test',
         'answerable': False, 'relevance_judgments': []},
    ]


def clean_report(baseline):
    return {
        'selected_split': 'test',
        'overall': {
            'question_count': 40,
            'answerable_question_count': 36,
            **baseline['test_metrics'],
        },
        'retriever': {
            'index_type': 'hybrid_rrf',
            'fusion': 'reciprocal_rank_fusion',
            'rrf_k': 20.0,
            'candidate_k': 20,
            'dense_weight': 1.0,
            'bm25_weight': 0.1,
            'chunk_count': 1223,
            'dense': {'model': 'BAAI/bge-small-en-v1.5', 'query_prefix': '',
                      'embedding_dimension': 384, 'similarity': 'cosine'},
            'bm25': {'k1': 1.5, 'b': 0.75, 'document_count': 1223},
        },
    }


class GoldenGateTests(unittest.TestCase):
    def test_valid_subset(self):
        result = validate_golden(synthetic_golden(), strict_counts=False)
        self.assertEqual(result['questions'], 2)

    def test_fingerprint_independent_of_jsonl_order(self):
        rows = synthetic_golden()
        self.assertEqual(semantic_fingerprint(rows), semantic_fingerprint(list(reversed(rows))))

    def test_rejects_positive_evidence_for_negative(self):
        rows = synthetic_golden()
        rows[-1]['relevance_judgments'] = [{'chunk_id': 'stor-003-sec-002-ch-001', 'grade': 1}]
        with self.assertRaises(GoldenError):
            validate_golden(rows, strict_counts=False)

    def test_rejects_duplicate_question_ids(self):
        rows = synthetic_golden()
        rows[1]['question_id'] = rows[0]['question_id']
        with self.assertRaises(GoldenError):
            validate_golden(rows, strict_counts=False)


class FrozenRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))

    def test_frozen_metrics_pass(self):
        self.assertEqual(check_report(clean_report(self.baseline), self.baseline), [])

    def test_recall10_drop_fails(self):
        report = clean_report(self.baseline)
        report['overall']['Recall@10'] -= 0.03
        self.assertTrue(any('Recall@10' in e for e in check_report(report, self.baseline)))

    def test_wrong_hybrid_weight_fails(self):
        report = clean_report(self.baseline)
        report['retriever']['bm25_weight'] = 1.0
        self.assertTrue(any('bm25_weight' in e for e in check_report(report, self.baseline)))

    def test_wrong_split_fails(self):
        report = clean_report(self.baseline)
        report['selected_split'] = 'dev'
        self.assertTrue(any('selected_split' in e for e in check_report(report, self.baseline)))

    def test_missing_metric_fails(self):
        report = clean_report(self.baseline)
        del report['overall']['nDCG@10']
        self.assertTrue(any('nDCG@10' in e for e in check_report(report, self.baseline)))


if __name__ == '__main__':
    unittest.main()
