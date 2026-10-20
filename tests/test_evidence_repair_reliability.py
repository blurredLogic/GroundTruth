"""Strict-format retry checks. Mocked only; no network, Ollama or GPU."""
import json
import unittest
from unittest.mock import patch

from groundtruth.evaluation import evidence_gate as eg
from groundtruth.evaluation import evidence_repair as er


def record():
    return {
        'question_id': 'k8s-test', 'question': 'How does a Pod get scheduled?',
        'answerable': True, 'status': 'answered', 'answer': 'Incorrect [C1].',
        'citations': ['C1'],
        'sources': [
            {'id': 'C1', 'chunk_id': 'a-sec-1', 'cited': True,
             'text': 'Kubernetes schedules Pods to Nodes.', 'source_url': 'https://kubernetes.io/docs/'},
            {'id': 'C2', 'chunk_id': 'b-sec-2', 'cited': False,
             'text': 'The scheduler checks Node resources.', 'source_url': 'https://kubernetes.io/docs/'},
        ],
    }


def verdict(kind):
    return {'verdict': kind, 'would_block': kind in ('unsupported', 'contradicted'),
            'verifier_reason': 'Old answer unsupported', 'verified_quotes': [],
            'unsupported_claims': ['incorrect statement'] if kind == 'unsupported' else [],
            'hard_flags': [], 'error': None}


def raw(abstain=False, answer='', citations=None):
    return json.dumps({'abstain': abstain, 'answer': answer, 'citations': citations or []})


class RepairReliabilityTests(unittest.TestCase):
    def test_one_format_retry_recovers_supported_inline_citation(self):
        responses = [raw(answer='Kubernetes schedules Pods to Nodes.', citations=['C1']),
                     raw(answer='Kubernetes schedules Pods to Nodes [C1].', citations=['C1'])]
        with patch.object(er, '_verify_once', side_effect=[(verdict('unsupported'), 1),
                                                          (verdict('supported'), 1)]), \
             patch.object(eg, '_safe_post_ollama', side_effect=responses) as calls:
            out = er.assess_and_repair(record())
        self.assertEqual(out['final_status'], 'accepted_repaired_provisional')
        self.assertEqual(out['repair_attempts'], 1)
        self.assertEqual(out['format_retry_attempts'], 1)
        self.assertEqual(out['repair_model_requests'], 2)
        self.assertEqual(calls.call_count, 2)
        self.assertIn('must cite', out['format_errors'][0])
        self.assertEqual(out['candidate_citations'], ['C1'])

    def test_missing_inline_citation_can_only_abstain_or_retry_with_valid_marker(self):
        responses = [raw(answer='Invented feature.', citations=['C1']),
                     raw(abstain=True)]
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', side_effect=responses):
            out = er.assess_and_repair(record())
        self.assertEqual(out['final_status'], 'repaired_abstained')
        self.assertEqual(out['candidate_citations'], [])
        self.assertEqual(out['format_retry_attempts'], 1)

    def test_chunk_metadata_maps_only_to_known_c_ids_and_trims_unused(self):
        response = raw(answer='Kubernetes schedules Pods to Nodes [C1].',
                       citations=['a-sec-1', 'b-sec-2'])
        parsed = er._parse_repair(response, record())
        self.assertEqual(parsed['citations'], ['C1'])
        self.assertIn('[C1]', parsed['answer'])

    def test_rejects_unknown_chunk_metadata(self):
        response = raw(answer='Kubernetes schedules Pods [C1].',
                       citations=['a-sec-1', 'fabricated-chunk'])
        with self.assertRaisesRegex(er.GenerationError, 'does not match'):
            er._parse_repair(response, record())

    def test_rejects_citations_that_do_not_map_to_inline_marker(self):
        response = raw(answer='The scheduler checks Node resources [C2].', citations=['a-sec-1'])
        with self.assertRaisesRegex(er.GenerationError, 'does not match'):
            er._parse_repair(response, record())

    def test_never_inserts_missing_inline_marker_during_metadata_conversion(self):
        response = raw(answer='Kubernetes schedules Pods.', citations=['a-sec-1'])
        with self.assertRaisesRegex(er.GenerationError, 'must cite evidence'):
            er._parse_repair(response, record())

    def test_unknown_inline_marker_rejected(self):
        response = raw(answer='Kubernetes schedules Pods [C19].', citations=['a-sec-1'])
        with self.assertRaises(er.GenerationError):
            er._parse_repair(response, record())

    def test_invalid_format_after_retry_is_still_error(self):
        response = raw(answer='Made-up statement.', citations=['C1'])
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', return_value=response) as calls:
            out = er.assess_and_repair(record())
        self.assertEqual(out['final_status'], 'repair_generation_error')
        self.assertEqual(out['format_retry_attempts'], 1)
        self.assertEqual(calls.call_count, 2)
        self.assertIsNone(out['candidate_answer'])

    def test_ollama_timeout_is_recorded_not_treated_as_abstention(self):
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', side_effect=eg.GateError('timed out')):
            out = er.assess_and_repair(record())
        self.assertEqual(out['final_status'], 'repair_generation_error')
        self.assertIn('transport failure', out['error'])
        self.assertEqual(out['repair_model_requests'], 1)

    def test_timeout_on_format_retry_is_recorded_not_treated_as_abstention(self):
        first = raw(answer='Invalid no markers.', citations=['C1'])
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', side_effect=[first, eg.GateError('timed out')]):
            out = er.assess_and_repair(record())
        self.assertEqual(out['final_status'], 'repair_generation_error')
        self.assertEqual(out['format_retry_attempts'], 1)
        self.assertIn('transport failure', out['error'])

    def test_prompt_does_not_see_answerability_or_reference_answer(self):
        source = record()
        source['reference_answer'] = 'DO NOT LEAK'
        first = raw(answer='Incorrect answer.', citations=['C1'])
        second = raw(abstain=True)
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', side_effect=[first, second]) as calls:
            er.assess_and_repair(source)
        for call in calls.call_args_list:
            prompt = call.args[2]
            self.assertNotIn('DO NOT LEAK', prompt)
            self.assertNotIn('reference_answer', prompt)
            self.assertNotIn('answerable', prompt)

    def test_no_extra_request_for_legal_abstention(self):
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', return_value=raw(abstain=True)) as calls:
            out = er.assess_and_repair(record())
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(out['repair_model_requests'], 1)
        self.assertEqual(out['format_retry_attempts'], 0)
        self.assertEqual(out['final_status'], 'repaired_abstained')


if __name__ == '__main__':
    unittest.main()
