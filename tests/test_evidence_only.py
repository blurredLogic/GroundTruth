"""Offline, no-model tests for v0.5 evidence-only audit."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from groundtruth.evaluation import evidence_only as ev


def fake(qid='k8s-001', answerable=True, question='Which field configures storage?'):
    return {
        'question_id': qid, 'question': question, 'answerable': answerable,
        'status': 'answered', 'split': 'dev',
        'reference_answer': 'HIDDEN GOLD', 'answer': 'HIDDEN MODEL',
        'sources': [
            {'id': 'C1', 'rank': 1, 'chunk_id': 'stor-1', 'section_id': 's1',
             'heading_path': ['Storage', 'Volume'], 'source_url': 'https://kubernetes.io/docs/a',
             'text': '## Storage\n\nThe `volumeMode` field selects a volume mode.\nIt does not automatically convert an existing disk.'},
            {'id': 'C2', 'rank': 2, 'chunk_id': 'stor-2', 'section_id': 's2',
             'heading_path': ['Storage'], 'source_url': 'https://kubernetes.io/docs/b',
             'text': 'Storage is allocated to workloads as needed. You should verify the storage class.'},
        ],
    }


class ExtractTests(unittest.TestCase):
    def test_offsets_and_no_added_words(self):
        r = fake()
        for q in ev.rank_evidence(r):
            src = next(s['text'] for s in r['sources'] if s['chunk_id'] == q['chunk_id'])
            self.assertEqual(src[q['source_start']:q['source_end']], q['quote'])
            self.assertIn(q['source_id'], ('C1', 'C2'))

    def test_is_deterministic(self):
        self.assertEqual(ev.rank_evidence(fake()), ev.rank_evidence(fake()))

    def test_max_snippets_per_source_and_budget(self):
        xs = ev.rank_evidence(fake(), max_snippets=2, per_source=1, max_chars=80)
        self.assertLessEqual(len(xs), 2)
        self.assertEqual(len(set(x['chunk_id'] for x in xs)), len(xs))
        self.assertTrue(all(len(x['quote']) <= 80 for x in xs))

    def test_no_reference_or_generated_answer_affects_selection(self):
        x, y = fake(), fake()
        y['reference_answer'] = 'FAKE DIFFERENT GOLD'
        y['answer'] = 'COMPLETELY DIFFERENT GENERATED TEXT'
        y['answerable'] = False
        self.assertEqual(ev.rank_evidence(x), ev.rank_evidence(y))

    def test_missing_source_returns_empty(self):
        x = fake()
        x['sources'] = []
        x['status'] = 'generation_error'
        self.assertEqual(ev.rank_evidence(x), [])

    def test_source_truncation_labeled(self):
        x = fake()
        x['sources'][0]['text'] = 'Short sentence about storage.\n\nThis text is truncated. [TRUNCATED EXCERPT]'
        self.assertTrue(any(e['excerpt_truncated'] for e in ev.rank_evidence(x)))

    def test_split_fails_closed(self):
        x = {'split': 'test', 'per_question': [fake()]}
        with self.assertRaises(ev.EvidenceError): ev._validate_input(x, None)
        x['split'] = 'dev'; x['per_question'][0]['split'] = 'test'
        with self.assertRaises(ev.EvidenceError): ev._validate_input(x, None)

    def test_duplicate_fails_closed(self):
        x = {'split': 'dev', 'per_question': [fake(), fake()]}
        with self.assertRaises(ev.EvidenceError): ev._validate_input(x, None)

    def test_unknown_ids_fails_closed(self):
        x = {'split': 'dev', 'per_question': [fake()]}
        with self.assertRaises(ev.EvidenceError): ev._validate_input(x, {'not-here'})

    def test_quote_cannot_be_synthesized(self):
        x = fake()
        x['sources'][0]['text'] = 'The volume is a filesystem. It has no automatic conversion.'
        selected = ev.rank_evidence(x)
        self.assertTrue(all('HIDDEN MODEL' not in e['quote'] for e in selected))

    def test_quote_sanitizes_csv_formula_only(self):
        self.assertEqual(ev._csv_safe('=1+1'), "'=1+1")
        self.assertEqual(ev._csv_safe('Normal answer'), 'Normal answer')


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root/'input.json'
        data = {'split': 'dev', 'per_question': [fake(), fake(qid='k8s-002', answerable=False, question='Does it auto convert a disk?')]}
        self.input.write_text(json.dumps(data), encoding='utf-8')
        self.prefix = self.root/'out'/'dev'

    def _build(self):
        return ev.build(self.input, self.prefix)

    def _edit_review(self, edits):
        path = ev._paths(self.prefix)['review']
        with path.open(encoding='utf-8-sig', newline='') as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            if row['question_id'] in edits:
                row.update(edits[row['question_id']])
        ev._write_csv(path, ev.REVIEW_COLUMNS, rows)

    def test_build_blind_review_and_missing_source(self):
        doc = self._build()
        self.assertEqual(doc['summary']['questions'], 2)
        review_path = ev._paths(self.prefix)['review']
        with review_path.open(encoding='utf-8-sig', newline='') as fh:
            r = fh.read()
        self.assertNotIn('HIDDEN GOLD', r)
        self.assertNotIn('HIDDEN MODEL', r)
        self.assertNotIn('answerable', r.lower())
        self.assertIn('review_relation', r)
        self.assertIsNone(doc['summary']['automatically_supported_answers'])

    def test_dont_overwrite_human_work(self):
        self._build()
        self._edit_review({'k8s-001': {'review_relation':'supported', 'review_confidence_0_2':'2'}})
        with self.assertRaises(ev.EvidenceError): self._build()
        p = ev._paths(self.prefix)['review']
        self.assertIn('supported', p.read_text(encoding='utf-8-sig'))

    def test_score_blank_review_is_not_auto_truth(self):
        self._build()
        audit = ev.score_review(self.input, self.prefix)
        self.assertEqual(audit['summary']['reviewed'], 0)
        self.assertFalse(audit['summary']['all_reviewed'])
        self.assertIsNone(audit['summary']['automatic_groundedness_score'])

    def test_score_join_gold_only_after_review(self):
        self._build()
        self._edit_review({'k8s-001': {'review_relation':'supported','review_confidence_0_2':'2'},
                           'k8s-002': {'review_relation':'insufficient','review_confidence_0_2':'2'}})
        audit = ev.score_review(self.input, self.prefix)
        self.assertEqual(audit['summary']['positive_supported'], 1)
        self.assertEqual(audit['summary']['negative_insufficient'], 1)
        self.assertTrue(audit['summary']['all_reviewed'])

    def test_invalid_review_relation_fails(self):
        self._build()
        self._edit_review({'k8s-001': {'review_relation':'definitely_correct', 'review_confidence_0_2':'2'}})
        with self.assertRaises(ev.EvidenceError): ev.score_review(self.input, self.prefix)

    def test_no_review_confidence_fails(self):
        self._build()
        self._edit_review({'k8s-001': {'review_relation':'supported'}})
        with self.assertRaises(ev.EvidenceError): ev.score_review(self.input, self.prefix)

    def test_modified_input_fails(self):
        self._build()
        data = json.loads(self.input.read_text(encoding='utf-8'))
        data['per_question'][0]['question'] = 'MODIFIED'
        self.input.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ev.EvidenceError): ev.score_review(self.input, self.prefix)

    def test_question_ids_filter(self):
        result = ev.build(self.input, self.prefix, ids={'k8s-002'})
        self.assertEqual(result['summary']['questions'], 1)
        self.assertEqual(result['per_question'][0]['question_id'], 'k8s-002')

    def test_preserve_missing_as_missing(self):
        data = json.loads(self.input.read_text(encoding='utf-8'))
        data['per_question'][1]['sources'] = []
        data['per_question'][1]['status'] = 'generation_error'
        self.input.write_text(json.dumps(data), encoding='utf-8')
        report = self._build()
        self.assertEqual(report['summary']['missing_saved_retrieval_evidence'], 1)
        self.assertEqual(report['per_question'][1]['evidence_status'], 'missing_saved_retrieval')

    def test_input_limit_first(self):
        with self.assertRaises(ev.EvidenceError): ev.rank_evidence(fake(), max_chars=45)


if __name__ == '__main__':
    unittest.main()

class MarkdownSafetyTests(unittest.TestCase):
    def test_verbatim_fenced_code_is_preserved(self):
        quote = 'This includes a literal ``` sequence in the source.'
        packet = ev._packet_md([{'question_id':'k8s-010', 'question':'What is this?', 'selected': [{
            'evidence_id':'E1','chunk_id':'a','retrieval_rank':1,'source_url':'https://kubernetes.io/docs/a',
            'heading_path':['A'], 'source_start':0, 'source_end':len(quote), 'excerpt_truncated':False,
            'quote':quote}]}])
        self.assertIn(quote, packet)
        self.assertIn('````text', packet)
