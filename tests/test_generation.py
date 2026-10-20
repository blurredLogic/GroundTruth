"""No model downloads, GPU, API key, or inference service required."""
import json
import unittest

from groundtruth.generation.grounded_qa import (
    GenerationError,
    GroundedQA,
    parse_generation,
    select_evidence,
)
from groundtruth.evaluation.evaluate_generation import summarize


class FakeRetriever:
    def search(self, query, *, top_k=8):
        return [{
            "chunk_id": "stor-003-sec-002-ch-001",
            "document_id": "stor-003",
            "section_id": "stor-003-sec-002",
            "rank": 1,
            "heading_path": ["Persistent Volumes", "Introduction"],
            "source_url": "https://kubernetes.io/docs/concepts/storage/persistent-volumes/",
            "text": "A PersistentVolume is a cluster resource representing storage.",
        }]


class FakeBackend:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        assert "evidence" in user
        assert "JSON" in system
        return json.dumps(self.result)


class GroundedQATests(unittest.TestCase):
    def setUp(self):
        self.evidence = select_evidence(FakeRetriever().search("what"))

    def test_accepts_cited_answer(self):
        parsed = parse_generation(json.dumps({
            "abstain": False,
            "answer": "A PV represents storage [C1].",
            "citations": ["C1"],
        }), self.evidence)
        self.assertEqual(parsed["citations"], ["C1"])

    def test_rejects_fabricated_citation(self):
        with self.assertRaises(GenerationError):
            parse_generation(json.dumps({
                "abstain": False,
                "answer": "False [C9].",
                "citations": ["C9"],
            }), self.evidence)

    def test_rejects_uncited_answer(self):
        with self.assertRaises(GenerationError):
            parse_generation(json.dumps({
                "abstain": False,
                "answer": "An unsupported answer.",
                "citations": [],
            }), self.evidence)

    def test_rejects_mismatched_citations(self):
        with self.assertRaises(GenerationError):
            parse_generation(json.dumps({
                "abstain": False,
                "answer": "Hello [C1].",
                "citations": [],
            }), self.evidence)

    def test_allows_abstention(self):
        parsed = parse_generation(json.dumps({
            "abstain": True, "answer": "", "citations": []
        }), self.evidence)
        self.assertTrue(parsed["abstained"])

    def test_end_to_end_stub(self):
        backend = FakeBackend({
            "abstain": False,
            "answer": "A PV represents storage [C1].",
            "citations": ["C1"],
        })
        qa = GroundedQA(FakeRetriever(), backend, model_label="test", backend_label="fake")
        trace = qa.ask("What is a PersistentVolume?")
        self.assertEqual(trace["status"], "answered")
        self.assertTrue(trace["sources"][0]["cited"])
        self.assertEqual(backend.calls, 1)

    def test_negative_rates_do_not_inflate_groundedness(self):
        summary = summarize([
            {"answerable": True, "abstained": False, "citations": ["C1"],
             "retrieved_gold_hit": True, "cited_gold_hit": True},
            {"answerable": False, "abstained": True, "citations": [],
             "retrieved_gold_hit": False, "cited_gold_hit": False},
        ])
        self.assertEqual(summary["negative_abstention_rate"], 1.0)
        self.assertEqual(summary["manual_correctness_and_groundedness"],
                         "NOT_SCORED_REQUIRES_HUMAN_REVIEW")


if __name__ == "__main__":
    unittest.main()
