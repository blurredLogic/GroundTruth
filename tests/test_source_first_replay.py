"""Isolated CPU-only tests: no Ollama, network, GPU or API credits."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from groundtruth.evaluation import evidence_gate as eg
from groundtruth.evaluation import source_first_replay as sf


def example(status='answered', answerable=True):
    return {
        'question_id': 'k8s-test', 'question': 'What is a Pod?',
        'answerable': answerable, 'status': status,
        'answer': 'Old wrong answer [C1].',
        'reference_answer': 'TOP SECRET GOLD NEVER SEND',
        'citations': ['C1'],
        'sources': [
            {'id': 'C1', 'chunk_id': 'chunk1', 'text': 'A Pod is a group of containers.', 'cited': True,
             'source_url': 'https://kubernetes.io/docs/'},
            {'id': 'C2', 'chunk_id': 'chunk2', 'text': 'A Service provides network access to Pods.', 'cited': False,
             'source_url': 'https://kubernetes.io/docs/'}
        ],
    }


def answer(value='A Pod is a group of containers [C1].', **extra):
    return json.dumps({'abstain': False, 'answer': value, **extra})


def abstention():
    return json.dumps({'abstain': True, 'answer': ''})


def decision(verdict='supported'):
    return {'verdict': verdict, 'verifier_reason': 'checked', 'verified_quotes': [],
            'unsupported_claims': [], 'hard_flags': [], 'rejected_quote_problems': [], 'error': None}


class ParserTests(unittest.TestCase):
    def test_deduce_metadata_only_from_inline_citations(self):
        r = sf._parse(answer('A Pod exists [C1]. Services exist [C2]. [C1]'), example())
        self.assertEqual(r['citations'], ['C1', 'C2'])

    def test_invalid_model_metadata_does_not_become_citation(self):
        r = sf._parse(answer('A Pod exists [C1].', citations=['bad-chunk-id']), example())
        self.assertEqual(r['citations'], ['C1'])
        self.assertNotIn('bad-chunk-id', r['answer'])

    def test_no_inline_marker_never_added(self):
        with self.assertRaisesRegex(sf.GenerationError, 'must cite evidence'):
            sf._parse(answer('A Pod exists.'), example())

    def test_fabricated_inline_citation_rejected(self):
        with self.assertRaisesRegex(sf.GenerationError, 'not present'):
            sf._parse(answer('Unknown source [C8].'), example())

    def test_placeholder_rejected(self):
        with self.assertRaisesRegex(sf.GenerationError, 'structural'):
            sf._parse(answer('The documented claim goes here [C1].'), example())

    def test_abstention_requires_empty_answer(self):
        with self.assertRaisesRegex(sf.GenerationError, 'Abstentions'):
            sf._parse(json.dumps({'abstain': True, 'answer': 'Something'}), example())
        self.assertTrue(sf._parse(abstention(), example())['abstained'])

    def test_requires_boolean_and_string(self):
        with self.assertRaisesRegex(sf.GenerationError, 'Expected JSON'):
            sf._parse('{}', example())


class RunTests(unittest.TestCase):
    def test_prompt_never_shows_previous_answer_or_gold(self):
        p = sf._payload(example())
        for term in ('Old wrong answer', 'TOP SECRET', 'reference_answer', 'answerable'):
            self.assertNotIn(term, p)
        self.assertIn('A Pod is a group of containers.', p)

    def test_supported_regeneration_is_provisional(self):
        x = example()
        saved = copy.deepcopy(x)
        with patch.object(eg, '_safe_post_ollama', return_value=answer()) as model, \
             patch.object(sf.er, '_verify_once', return_value=(decision(), 1)) as verify:
            out = sf.run_one(x, model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'accepted_regenerated_provisional')
        self.assertEqual(out['model_requests'], 1)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(verify.call_count, 1)
        self.assertEqual(x, saved)

    def test_format_retry_recovers_without_inserting_marker(self):
        with patch.object(eg, '_safe_post_ollama', side_effect=[answer('No cite here'), answer()]) as model, \
             patch.object(sf.er, '_verify_once', return_value=(decision(), 1)):
            out = sf.run_one(example(), model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'accepted_regenerated_provisional')
        self.assertEqual(out['format_retry_attempts'], 1)
        self.assertEqual(out['model_requests'], 2)
        for call in model.call_args_list:
            self.assertNotIn('Old wrong answer', call.args[2])

    def test_unfixable_missing_inline_fails_closed(self):
        with patch.object(eg, '_safe_post_ollama', return_value=answer('No cite here')):
            out = sf.run_one(example(), model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'regeneration_error')
        self.assertEqual(out['model_requests'], 2)

    def test_no_evidence_no_model_call(self):
        x = example()
        x['sources'] = []
        with patch.object(eg, '_safe_post_ollama', side_effect=AssertionError('unexpected')):
            out = sf.run_one(x, model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'unverified_missing_evidence')

    def test_abstention_is_not_supported_answer(self):
        with patch.object(eg, '_safe_post_ollama', return_value=abstention()), \
             patch.object(sf.er, '_verify_once', side_effect=AssertionError('no verification for abstention')):
            out = sf.run_one(example(answerable=False), model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'regenerated_abstained')

    def test_blocked_remains_distinct_from_abstained(self):
        with patch.object(eg, '_safe_post_ollama', return_value=answer()), \
             patch.object(sf.er, '_verify_once', return_value=(decision('unsupported'), 1)):
            out = sf.run_one(example(answerable=False), model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'blocked_after_regeneration')
        c = sf._counts([example(answerable=False)], [out])
        self.assertEqual(c['negative_false_answers_provisional'], 0)
        self.assertEqual(c['negative_correct_abstentions'], 0)

    def test_verifier_error_not_success(self):
        with patch.object(eg, '_safe_post_ollama', return_value=answer()), \
             patch.object(sf.er, '_verify_once', return_value=(decision('verifier_error'), 2)):
            out = sf.run_one(example(), model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'unverified_regenerated')

    def test_timeout_not_abstention(self):
        with patch.object(eg, '_safe_post_ollama', side_effect=eg.GateError('timed out')):
            out = sf.run_one(example(answerable=False), model='m', url='http://127.0.0.1:11434', timeout=2)
        self.assertEqual(out['final_status'], 'regeneration_error')
        self.assertNotEqual(out['final_status'], 'regenerated_abstained')

    def test_refuses_test_split_without_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'src.json'
            path.write_text(json.dumps({'split': 'test', 'per_question': [example()] * 60}), encoding='utf-8')
            with patch.object(eg, '_safe_post_ollama', side_effect=AssertionError('unexpected')):
                ret = sf.main(['--input-report', str(path), '--output-prefix', str(Path(tmp)/'out')])
            self.assertEqual(ret, 1)

    def test_checkpoint_fingerprint_changed_by_prompt(self):
        a = sf._fingerprint(b'x', model='m', url='http://127.0.0.1:11434',
                            timeout=5, max_chars=4800, ids=None, limit=1)
        b = sf._fingerprint(b'x', model='m', url='http://127.0.0.1:11434',
                            timeout=5, max_chars=1000, ids=None, limit=1)
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main()
