"""No Ollama, GPU, torch, downloads or paid APIs required."""
import json
import tempfile
import unittest
from pathlib import Path

from groundtruth.generation.grounded_qa import GenerationError, GroundedQA


class RetrieverStub:
    def search(self, question, *, top_k=4):
        return [
            {
                "chunk_id": "stor-003-sec-002-ch-001",
                "document_id": "stor-003",
                "section_id": "stor-003-sec-002",
                "rank": 1,
                "heading_path": ["Persistent Volumes"],
                "source_url": "https://kubernetes.io/docs/concepts/storage/persistent-volumes/",
                "text": "A PersistentVolume is a cluster resource representing storage.",
            }
        ]


class SequencedBackend:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system, user):
        self.calls.append({"system": system, "user": user})
        return json.dumps(self.responses[len(self.calls) - 1])


class RetryTests(unittest.TestCase):
    def test_repairs_missing_inline_citation(self):
        backend = SequencedBackend([
            {"abstain": False, "answer": "A PV represents storage.", "citations": ["C1"]},
            {"abstain": False, "answer": "A PV represents storage [C1].", "citations": ["C1"]},
        ])
        qa = GroundedQA(RetrieverStub(), backend, top_k=4, validation_retries=1)
        result = qa.ask("What is a PersistentVolume?")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"], ["C1"])
        self.assertEqual(result["generation"]["validation_attempts"], 2)
        self.assertTrue(result["generation"]["format_repair_used"])
        self.assertEqual(len(backend.calls), 2)
        self.assertIn("validation_error", backend.calls[1]["user"])
        self.assertIn("[C1]", backend.calls[1]["user"])

    def test_failed_retries_never_invent_citation_and_save_raw(self):
        backend = SequencedBackend([
            {"abstain": False, "answer": "No cited answer", "citations": []},
            {"abstain": False, "answer": "Still no citation", "citations": []},
        ])
        with tempfile.TemporaryDirectory() as td:
            debug_path = Path(td) / "error_trace.json"
            qa = GroundedQA(RetrieverStub(), backend, validation_retries=1, debug_output=debug_path)
            with self.assertRaisesRegex(GenerationError, "after 2 attempt"):
                qa.ask("What is a PersistentVolume?")
            self.assertEqual(len(backend.calls), 2)
            self.assertTrue(debug_path.exists())
            trace = json.loads(debug_path.read_text(encoding="utf-8"))
            self.assertEqual(trace["allowed_evidence_ids"], ["C1"])
            self.assertEqual(len(trace["attempts"]), 2)

    def test_zero_retries_rejects_invalid(self):
        backend = SequencedBackend([
            {"abstain": False, "answer": "An uncited answer", "citations": []},
        ])
        qa = GroundedQA(RetrieverStub(), backend, validation_retries=0)
        with self.assertRaises(GenerationError):
            qa.ask("Question")
        self.assertEqual(len(backend.calls), 1)

    def test_success_does_not_add_retry(self):
        backend = SequencedBackend([
            {"abstain": False, "answer": "Storage [C1].", "citations": ["C1"]},
        ])
        qa = GroundedQA(RetrieverStub(), backend)
        result = qa.ask("What is a PersistentVolume?")
        self.assertEqual(result["generation"]["validation_attempts"], 1)
        self.assertFalse(result["generation"]["format_repair_used"])
        self.assertEqual(len(backend.calls), 1)

    def test_rejects_unknown_citations_even_after_retry(self):
        backend = SequencedBackend([
            {"abstain": False, "answer": "False [C99].", "citations": ["C99"]},
            {"abstain": False, "answer": "Still false [C99].", "citations": ["C99"]},
        ])
        qa = GroundedQA(RetrieverStub(), backend)
        with self.assertRaisesRegex(GenerationError, "not present in retrieved evidence"):
            qa.ask("Question")


if __name__ == "__main__":
    unittest.main()
