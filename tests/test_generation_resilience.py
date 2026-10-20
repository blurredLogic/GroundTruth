"""CPU-only tests. No Ollama, model downloads, Hugging Face, GPU or API calls."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from groundtruth.generation.grounded_qa import (
    GenerationError,
    GroundedQA,
    canonicalize_unused_citation_metadata,
    parse_generation,
)
from groundtruth.evaluation.evaluate_generation import (
    evaluate_with_checkpoint,
    summarize,
)


class FakeRetriever:
    def search(self, question, *, top_k):
        return [
            {
                "chunk_id": f"stor-003-sec-00{i}-ch-001",
                "document_id": "stor-003",
                "section_id": f"stor-003-sec-00{i}",
                "rank": i,
                "heading_path": ["Persistent Volumes"],
                "source_url": "https://kubernetes.io/docs/concepts/storage/persistent-volumes/",
                "text": f"Documentation passage {i}. Storage details.",
            }
            for i in range(1, 5)
        ]


class FakeBackend:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete(self, system, user):
        result = self.replies[self.calls]
        self.calls += 1
        return json.dumps(result)


class CitationTests(unittest.TestCase):
    def setUp(self):
        self.retriever = FakeRetriever()

    def test_c1_marker_extra_known_metadata_is_normalized(self):
        backend = FakeBackend([{
            "abstain": False,
            "answer": "A PV is storage [C1].",
            "citations": ["C1", "C2", "C3", "C4"],
        }])
        qa = GroundedQA(self.retriever, backend, top_k=4)
        result = qa.ask("What is a PersistentVolume?")
        self.assertEqual(result["citations"], ["C1"])
        self.assertEqual(result["answer"], "A PV is storage [C1].")
        self.assertTrue(result["generation"]["citation_metadata_normalized"])
        self.assertEqual(result["generation"]["validation_attempts"], 1)
        self.assertEqual(backend.calls, 1)
        self.assertEqual([s["id"] for s in result["sources"] if s["cited"]], ["C1"])

    def test_unknown_metadata_id_is_not_discarded(self):
        from groundtruth.generation.grounded_qa import select_evidence
        evidence = select_evidence(self.retriever.search("x", top_k=4))
        raw = json.dumps({"abstain": False, "answer": "Some fact [C1].", "citations": ["C1", "C99"]})
        self.assertIsNone(canonicalize_unused_citation_metadata(raw, evidence))
        with self.assertRaises(GenerationError):
            parse_generation(raw, evidence)

    def test_unknown_inline_marker_is_never_changed(self):
        from groundtruth.generation.grounded_qa import select_evidence
        evidence = select_evidence(self.retriever.search("x", top_k=4))
        raw = json.dumps({"abstain": False, "answer": "False [C99].", "citations": ["C99"]})
        self.assertIsNone(canonicalize_unused_citation_metadata(raw, evidence))
        with self.assertRaises(GenerationError):
            parse_generation(raw, evidence)

    def test_missing_inline_marker_is_still_invalid(self):
        from groundtruth.generation.grounded_qa import select_evidence
        evidence = select_evidence(self.retriever.search("x", top_k=4))
        raw = json.dumps({"abstain": False, "answer": "Missing a marker.", "citations": ["C1"]})
        self.assertIsNone(canonicalize_unused_citation_metadata(raw, evidence))
        with self.assertRaises(GenerationError):
            parse_generation(raw, evidence)

    def test_missing_array_entry_still_invalid(self):
        from groundtruth.generation.grounded_qa import select_evidence
        evidence = select_evidence(self.retriever.search("x", top_k=4))
        raw = json.dumps({"abstain": False, "answer": "Fact [C1].", "citations": []})
        self.assertIsNone(canonicalize_unused_citation_metadata(raw, evidence))
        with self.assertRaises(GenerationError):
            parse_generation(raw, evidence)


class ResumableEvalTests(unittest.TestCase):
    def test_failed_question_does_not_stop_run_or_inflate_abstentions(self):
        questions = [
            {"question_id": "q1", "question": "First", "split": "dev", "answerable": True, "relevance_judgments": []},
            {"question_id": "q2", "question": "Second", "split": "dev", "answerable": False, "relevance_judgments": []},
            {"question_id": "q3", "question": "Third", "split": "dev", "answerable": True, "relevance_judgments": []},
        ]
        result = {
            "status": "answered", "abstained": False, "answer": "An answer [C1].",
            "citations": ["C1"], "sources": [{"chunk_id": "chunk1", "source_url": "https://example.com", "cited": True}],
            "generation": {"model": "stub"},
        }
        class QA:
            debug_output = None
            def __init__(self): self.calls = []
            def ask(self, question):
                self.calls.append(question)
                if question == "Second":
                    raise GenerationError("Invalid model response")
                return result
        with tempfile.TemporaryDirectory() as td:
            qa = QA()
            checkpoint = Path(td)/"checkpoint.json"
            rows = evaluate_with_checkpoint(
                questions, qa, checkpoint, "fingerprint", False, Path(td)/"debug"
            )
            self.assertEqual(len(qa.calls), 3)
            self.assertEqual([r["status"] for r in rows], ["answered", "generation_error", "answered"])
            self.assertIsNone(rows[1]["abstained"])
            totals = summarize(rows)
            self.assertEqual(totals["negative_abstention_rate"], 0)
            self.assertEqual(totals["negative_generation_failure_rate"], 1)
            self.assertEqual(totals["generation_failure_count"], 1)
            self.assertTrue(checkpoint.exists())
            qa2 = QA()
            rows2 = evaluate_with_checkpoint(
                questions, qa2, checkpoint, "fingerprint", True, Path(td)/"debug"
            )
            self.assertEqual(qa2.calls, ["Second"])
            self.assertEqual(len(rows2), 3)

    def test_mismatched_checkpoint_rejected(self):
        questions = [{"question_id": "q1", "question": "x"}]
        class QA: pass
        with tempfile.TemporaryDirectory() as td:
            checkpoint = Path(td)/"checkpoint.json"
            checkpoint.write_text(json.dumps({"fingerprint": "old", "per_question": []}))
            with self.assertRaisesRegex(GenerationError, "Checkpoint doesn't match"):
                evaluate_with_checkpoint(questions, QA(), checkpoint, "new", True, Path(td))


if __name__ == "__main__":
    unittest.main()
