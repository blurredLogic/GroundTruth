"""CPU-only unit tests. No Ollama, API key, GPU, network or model downloads."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from groundtruth.evaluation import evidence_gate as eg
from groundtruth.evaluation import evidence_repair as er


def sample(status='answered', answer='Incorrect claim [C1].', answerable=True):
    return {
        'question_id': 'test-1', 'question': 'How does this feature work?',
        'status': status, 'answerable': answerable,
        'reference_answer': 'SECRET GOLD ANSWER: should never reach a model',
        'answer': answer if status == 'answered' else '', 'citations': ['C1'],
        'sources': [
            {'id': 'C1', 'chunk_id': 'a', 'cited': True, 'text': 'A node is created automatically.',
             'source_url': 'https://kubernetes.io/docs/'},
            {'id': 'C2', 'chunk_id': 'b', 'cited': False, 'text': 'A Pod is a Kubernetes API object.',
             'source_url': 'https://kubernetes.io/docs/'},
        ],
    }


def verdict(which, reason='', quotes=None):
    return {'verdict': which, 'would_block': which in ('unsupported', 'contradicted'),
            'verifier_reason': reason, 'verified_quotes': quotes or [],
            'hard_flags': [], 'unsupported_claims': ['incorrect premise'] if which == 'unsupported' else [],
            'error': 'invalid verifier JSON' if which == 'verifier_error' else None}


class RepairTests(unittest.TestCase):
    def test_supported_original_is_kept_without_repair(self):
        r = sample(answer='A node is created automatically [C1].')
        with patch.object(er, '_verify_once', return_value=(verdict('supported'), 1)), \
             patch.object(eg, '_safe_post_ollama', side_effect=AssertionError('No repair expected')):
            out = er.assess_and_repair(r)
        self.assertEqual(out['final_status'], 'accepted_original_provisional')
        self.assertEqual(out['repair_attempts'], 0)

    def test_wrong_answer_is_repaired_and_reverified(self):
        r = sample()
        initial = verdict('unsupported', 'Incorrect assertion')
        final = verdict('supported', quotes=[{'id': 'C2', 'quote': 'A Pod is a Kubernetes API object.'}])
        raw = json.dumps({'abstain': False, 'answer': 'A Pod is a Kubernetes API object [C2].', 'citations': ['C2']})
        with patch.object(er, '_verify_once', side_effect=[(initial, 1), (final, 1)]) as verifier, \
             patch.object(eg, '_safe_post_ollama', return_value=raw) as repair:
            out = er.assess_and_repair(r)
        self.assertEqual(out['final_status'], 'accepted_repaired_provisional')
        self.assertEqual(out['candidate_citations'], ['C2'])
        self.assertEqual(out['verifier_attempts'], 2)
        self.assertEqual(out['repair_attempts'], 1)
        payload = json.loads(repair.call_args.args[2])
        self.assertNotIn('answerable', payload)
        self.assertNotIn('reference_answer', payload)
        self.assertNotIn('relevance_judgments', payload)
        self.assertNotIn('SECRET GOLD ANSWER', json.dumps(payload))
        self.assertEqual(len(payload['evidence']), 2)
        self.assertEqual(verifier.call_count, 2)

    def test_unsupported_negative_repairs_to_abstention(self):
        r = sample(answerable=False)
        raw = json.dumps({'abstain': True, 'answer': '', 'citations': []})
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', return_value=raw):
            out = er.assess_and_repair(r)
        self.assertEqual(out['final_status'], 'repaired_abstained')
        self.assertIsNone(out['repaired_verdict'])

    def test_unsupported_repair_gets_blocked(self):
        r = sample()
        raw = json.dumps({'abstain': False, 'answer': 'Invented feature [C1].', 'citations': ['C1']})
        with patch.object(er, '_verify_once', side_effect=[(verdict('unsupported'), 1), (verdict('contradicted'), 1)]), \
             patch.object(eg, '_safe_post_ollama', return_value=raw):
            out = er.assess_and_repair(r)
        self.assertEqual(out['final_status'], 'blocked_after_repair')

    def test_placeholder_repair_remains_invalid(self):
        r = sample(answer='The documented claim goes here [C1].', answerable=False)
        raw = json.dumps({'abstain': False, 'answer': 'The documented claim goes here [C1].', 'citations': ['C1']})
        with patch.object(er, '_verify_once', return_value=(verdict('structural_failure'), 1)), \
             patch.object(eg, '_safe_post_ollama', return_value=raw):
            out = er.assess_and_repair(r)
        self.assertEqual(out['final_status'], 'repair_generation_error')
        self.assertIn('structural', out['error'])

    def test_unknown_citation_is_not_accepted(self):
        r = sample()
        raw = json.dumps({'abstain': False, 'answer': 'Made up [C8].', 'citations': ['C8']})
        with patch.object(er, '_verify_once', return_value=(verdict('unsupported'), 1)), \
             patch.object(eg, '_safe_post_ollama', return_value=raw):
            out = er.assess_and_repair(r)
        self.assertEqual(out['final_status'], 'repair_generation_error')
        self.assertIn('not present', out['error'])

    def test_verifier_error_is_not_fail_open(self):
        r = sample(answerable=False)
        with patch.object(eg, 'assess', return_value=verdict('verifier_error')) as mock:
            out = er.assess_and_repair(r)
        self.assertEqual(mock.call_count, 2)
        self.assertEqual(out['final_status'], 'unverified_original')
        self.assertEqual(out['repair_attempts'], 0)

    def test_inconsistent_supported_verdict_is_downgraded(self):
        inconsistent = {**verdict('supported'), 'unsupported_claims': ['made up field']}
        with patch.object(eg, 'assess', return_value=inconsistent):
            outcome, num = er._verify_once(sample(), model='x', url='http://127.0.0.1:11434', timeout=1)
        self.assertEqual(num, 1)
        self.assertEqual(outcome['verdict'], 'uncertain')

    def test_uncertain_does_not_return_answer(self):
        with patch.object(er, '_verify_once', return_value=(verdict('uncertain'), 1)):
            out = er.assess_and_repair(sample())
        self.assertEqual(out['final_status'], 'unverified_original')
        self.assertIsNone(out['candidate_answer'])

    def test_existing_abstention_and_generation_error_not_repaired(self):
        for status, expected in [('abstained', 'original_abstained'), ('generation_error', 'original_generation_error')]:
            with patch.object(er, '_verify_once', side_effect=AssertionError('Should not verify')):
                out = er.assess_and_repair(sample(status=status))
            self.assertEqual(out['final_status'], expected)

    def test_input_unchanged(self):
        r = sample()
        before = copy.deepcopy(r)
        with patch.object(er, '_verify_once', return_value=(verdict('supported'), 1)):
            er.assess_and_repair(r)
        self.assertEqual(r, before)

    def test_counts_do_not_misclassify_blocked_as_abstention(self):
        originals = [dict(sample(answerable=True), question_id='p'),
                     dict(sample(answerable=False), question_id='n')]
        results = [{'question_id': 'p', 'final_status': 'blocked_after_repair'},
                   {'question_id': 'n', 'final_status': 'repaired_abstained'}]
        totals = er._counts(originals, results)
        self.assertEqual(totals['final_answerable_answers_provisional'], 0)
        self.assertEqual(totals['negative_abstentions_including_original'], 1)
        self.assertEqual(totals['answerable_blocked_or_unverified_NOT_abstentions'], 1)

    def test_remote_endpoint_rejected(self):
        with self.assertRaises(eg.GateError):
            eg._safe_post_ollama('https://example.org', 'model', '{}', 1.)

    def test_checkpoint_fingerprint_changes_with_input_or_prompt(self):
        x = er._fingerprint(b'original', model='x', url='http://127.0.0.1:11434', timeout=180, selected_ids=None, limit=None)
        y = er._fingerprint(b'changed', model='x', url='http://127.0.0.1:11434', timeout=180, selected_ids=None, limit=None)
        self.assertNotEqual(x, y)

    def test_report_input_must_be_complete_dev(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'report.json'
            path.write_text(json.dumps({'split': 'test', 'per_question': []}))
            self.assertEqual(er.main(['--input-report', str(path), '--output-prefix', str(Path(td)/'probe')]), 1)


if __name__ == '__main__':
    unittest.main()
