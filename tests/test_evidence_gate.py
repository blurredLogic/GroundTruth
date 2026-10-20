import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from groundtruth.evaluation import evidence_gate as eg


def record(qid='q1', answer='Kubernetes supports the documented operation [C1].',
           text='Kubernetes supports the documented operation.'):
    return {
        'question_id': qid, 'question': 'Does Kubernetes support the documented operation?',
        'answer': answer, 'answerable': True, 'status': 'answered',
        'citations': ['C1'], 'sources': [
            {'id': 'C1', 'cited': True, 'text': text, 'chunk_id': 'chunk-1'},
            {'id': 'C2', 'cited': False, 'text': 'An unrelated Kubernetes setting', 'chunk_id': 'chunk-2'},
        ]
    }


class EvidenceGateTests(unittest.TestCase):
    def test_normal_answer_rules_do_not_claim_support(self):
        r = eg.assess(record(), 'rules')
        self.assertEqual(r['verdict'], 'not_semantically_checked')
        self.assertFalse(r['would_block'])

    def test_placeholder_is_blocked_in_answer_stage(self):
        r = eg.assess(record(answer='The documented claim goes here [C1].'), 'rules')
        self.assertEqual(r['verdict'], 'structural_failure')
        self.assertTrue(r['would_block'])
        self.assertIn('placeholder_answer', r['hard_flags'])

    def test_question_stage_does_not_use_post_generation_placeholder_gate(self):
        r = eg.assess(record(answer='The documented claim goes here [C1].'), 'rules', stage='question')
        self.assertFalse(r['would_block'])

    def test_unmatched_identifiers_are_review_hints_not_fabrication_proof(self):
        r = eg.assess(record(answer='Set `madeUpField` on the Pod [C1].'), 'rules')
        self.assertFalse(r['would_block'])
        self.assertIn('unmatched_technical_identifier:madeUpField', r['review_flags'])

    def test_no_marker_blocked(self):
        r = eg.assess(record(answer='Kubernetes supports the operation.'), 'rules')
        self.assertTrue(r['would_block'])

    def test_verified_quote_allows_provisional_supported(self):
        raw = json.dumps({'verdict': 'supported', 'reason': 'evidence',
                          'quotes': [{'id': 'C1', 'quote': 'supports the documented operation'}],
                          'unsupported_claims': []})
        parsed = eg._parse_verifier(raw, eg.cited_sources(record()))
        self.assertEqual(parsed['verdict'], 'supported')
        self.assertEqual(len(parsed['verified_quotes']), 1)

    def test_fake_quote_downgrades_supported_to_uncertain(self):
        raw = json.dumps({'verdict': 'supported', 'reason': 'evidence',
                          'quotes': [{'id': 'C1', 'quote': 'totally made up sentence'}],
                          'unsupported_claims': []})
        parsed = eg._parse_verifier(raw, eg.cited_sources(record()))
        self.assertEqual(parsed['verdict'], 'uncertain')
        self.assertEqual(parsed['verified_quotes'], [])

    def test_contradiction_requires_quote(self):
        raw = json.dumps({'verdict': 'contradicted', 'reason': 'not supported',
                          'quotes': [], 'unsupported_claims': ['auto scaling']})
        parsed = eg._parse_verifier(raw, eg.cited_sources(record()))
        self.assertEqual(parsed['verdict'], 'uncertain')

    def test_ollama_verdict_can_shadow_block(self):
        raw = json.dumps({'verdict': 'unsupported', 'reason': 'source says nothing about it',
                          'quotes': [], 'unsupported_claims': ['automatic conversion']})
        with patch.object(eg, '_safe_post_ollama', return_value=raw):
            r = eg.assess(record(), 'ollama')
        self.assertTrue(r['would_block'])
        self.assertEqual(r['verdict'], 'unsupported')

    def test_question_verifier_payload_excludes_generated_answer_and_gold(self):
        raw = json.dumps({'verdict': 'unsupported', 'reason': 'evidence lacks answer',
                          'quotes': [], 'unsupported_claims': []})
        captured = []
        def fake(*args, **kwargs):
            captured.append((json.loads(args[2]), kwargs.get('system')))
            return raw
        with patch.object(eg, '_safe_post_ollama', side_effect=fake):
            r = eg.assess(record(), 'ollama', stage='question')
        self.assertEqual(r['verdict'], 'unsupported')
        sent = captured[0][0]
        self.assertNotIn('answer', sent)
        self.assertNotIn('answerable', sent)
        self.assertEqual(len(sent['passages']), 2)
        self.assertEqual(captured[0][1], eg.QUESTION_VERIFIER_SYSTEM)

    def test_model_failure_is_not_abstention(self):
        with patch.object(eg, '_safe_post_ollama', side_effect=eg.GateError('offline')):
            r = eg.assess(record(), 'ollama')
        self.assertEqual(r['verdict'], 'verifier_error')
        self.assertFalse(r['would_block'])

    def test_original_failure_not_counted_as_new_abstention(self):
        original = [record(), dict(record('q2'), answerable=False),
                    dict(record('q3'), status='generation_error', answerable=True)]
        result = [eg.assess(original[0], 'rules'),
                  eg.assess(original[1], 'rules'), eg.assess(original[2], 'rules')]
        summary = eg.summarize(original, result)
        self.assertEqual(summary['original_generation_errors_unchanged'], 1)
        self.assertEqual(summary['negative_false_answers_after_shadow_gate'], 1)

    def test_preexisting_abstention_no_verifier_call(self):
        r = dict(record(), status='abstained', answer='')
        with patch.object(eg, '_safe_post_ollama', side_effect=AssertionError('should not call')):
            result = eg.assess(r, 'ollama')
        self.assertEqual(result['verdict'], 'not_applicable')

    def test_reject_remote_endpoint(self):
        with self.assertRaises(eg.GateError):
            eg._safe_post_ollama('https://example.com', 'model', 'data', 1.)


if __name__ == '__main__':
    unittest.main()
