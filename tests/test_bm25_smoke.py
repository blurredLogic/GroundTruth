"""Fast native BM25 smoke test: build/index/search/check hash validation."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from groundtruth.indexing.build_bm25_index import run_build
from groundtruth.retrieval.bm25_retriever import BM25Retriever, BM25RetrieverError


class BM25SmokeTests(unittest.TestCase):
    def test_end_to_end_bm25_and_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corpus = root / 'indexable.jsonl'
            output = root / 'bm25'
            rows = []
            for i, (domain, passage) in enumerate([
                ('storage', 'PersistentVolume PersistentVolume is cluster storage.'),
                ('services_networking', 'LoadBalancer exposes Kubernetes Service outside cluster.'),
            ], start=1):
                doc = f'doc-{i:03d}'
                sid = f'{doc}-sec-001'
                rows.append({
                    'chunk_id': f'{sid}-ch-001',
                    'document_id': doc, 'section_id': sid, 'chunk_index': 1,
                    'domain': domain, 'heading_path': ['Kubernetes', domain],
                    'source_url': f'https://example.test/{domain}',
                    'text': passage, 'retrieval_text': passage,
                    'content_sha256': 'sha256:test', 'retrieval_text_sha256': 'sha256:test',
                })
            corpus.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
            self.assertEqual(run_build(input_path=corpus, output_dir=output, k1=1.5, b=0.75), 0)
            retriever = BM25Retriever(index_dir=output, verify_hashes=True)
            self.assertEqual(retriever.search('What is a PersistentVolume?', top_k=2)[0]['chunk_id'], rows[0]['chunk_id'])
            self.assertEqual(retriever.search('Kubernetes LoadBalancer service', top_k=2)[0]['chunk_id'], rows[1]['chunk_id'])
            metadata_path = output / 'metadata.jsonl'
            metadata_path.write_text(metadata_path.read_text(encoding='utf-8') + ' ', encoding='utf-8')
            with self.assertRaises(BM25RetrieverError):
                BM25Retriever(index_dir=output, verify_hashes=True)


if __name__ == '__main__':
    unittest.main()
