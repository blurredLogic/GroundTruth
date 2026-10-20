import csv
import json
import tempfile
import unittest
from pathlib import Path
from groundtruth.evaluation.answer_factuality_audit import (AuditError,make_rows,score,write_review,load_dev,sha256,render_markdown)

class FactualityAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tests ship with no private files; tiny constructed 60-question DEV fixture.
        cls.raw={'split':'dev','per_question':[]}
        for i in range(60):
            is_negative=i>=54
            cls.raw['per_question'].append({'question_id':f'q{i:02d}', 'split':'dev',
               'question':f'Question {i}', 'answerable':not is_negative,
               'status':'abstained' if is_negative else 'answered',
               'answer':'No answer' if is_negative else 'Documented answer [C1]',
               'citations':[] if is_negative else ['C1'],
               'sources':[] if is_negative else [{'id':'C1','chunk_id':'chunk','source_url':'https://example.org','text':'Evidence text'}]})

    def setup_files(self,d):
        source=Path(d)/'report.json';source.write_text(json.dumps(self.raw),encoding='utf-8')
        review=Path(d)/'review.csv';write_review(review,make_rows(self.raw,{'q00':('correct_complete','fully_supported','Direct quote supports assertion',2)}))
        return source,review

    def test_requires_exact_dev(self):
        wrong={**self.raw,'split':'test'}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.json';p.write_text(json.dumps(wrong))
            with self.assertRaises(AuditError):load_dev(p)
    def test_valid_scores_and_unreviewed(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d); r=score(src,rev)
            self.assertEqual(r['generated_answer_count'],54)
            self.assertEqual(r['assistant_assessed_answer_count'],1)
            self.assertEqual(r['assistant_unreviewed_answer_count'],53)
            self.assertEqual(r['independent_reviewed_question_count'],0)
            self.assertFalse(r['groundedness_claim_level_independently_verified'])
            self.assertIn('not independent',render_markdown(r))
    def test_detect_source_hash_change(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with self.assertRaises(AuditError):score(src,rev,expected_source_sha256='0'*64)
    def test_detect_tampering_answer(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[0]['generated_answer']='doctored'
            write_review(rev,rows)
            with self.assertRaises(AuditError):score(src,rev)
    def test_detect_false_independent_review(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[0]['independent_review_status']='REVIEWED'
            write_review(rev,rows)
            with self.assertRaises(AuditError):score(src,rev)
    def test_cannot_grade_abstention(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[-1]['assistant_factuality']='correct_complete'
            write_review(rev,rows)
            with self.assertRaises(AuditError):score(src,rev)
    def test_no_unknown_review_label(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[0]['assistant_citation_support']='grounded'
            write_review(rev,rows)
            with self.assertRaises(AuditError):score(src,rev)
    def test_incomplete_review_never_fabricates_score(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[0]['assistant_factuality']='needs_review'
            write_review(rev,rows)
            result=score(src,rev)
            self.assertEqual(result['assistant_assessed_answer_count'],0)
            self.assertIsNone(result['assistant_assessed_accuracy_complete_only'])
    def test_review_count_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[1]['question_id']='q00'
            write_review(rev,rows)
            with self.assertRaises(AuditError):score(src,rev)
    def test_review_note_required(self):
        with tempfile.TemporaryDirectory() as d:
            src,rev=self.setup_files(d)
            with rev.open(newline="", encoding="utf-8") as f:
                rows=list(csv.DictReader(f))
            rows[0]['assistant_review_note']=''
            write_review(rev,rows)
            with self.assertRaises(AuditError):score(src,rev)
if __name__=='__main__':unittest.main()
