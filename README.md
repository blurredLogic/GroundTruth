# GroundTruth
Kubernetes RAG Evaluation Benchmark

CORPUS
~75 official Kubernetes documentation pages

DOMAINS
1. Architecture
2. Workloads
3. Networking
4. Storage
5. Configuration
6. Security & Policies
7. Scheduling & Resources

TARGET SIZE
~1,500–2,500 chunks

CHUNK EXPERIMENTS
256 / 512 / 1024 tokens

GOLDEN SET
100 human-validated questions

QUESTION TYPES
20 direct
15 comparison
20 scenario
20 multi-hop
15 troubleshooting
10 negative/near-miss

DIFFICULTY
25 easy
45 medium
30 hard

RELEVANCE
0 irrelevant
1 related
2 supporting
3 directly relevant

EVALUATION
Recall@5
Recall@10
MRR
nDCG

GENERATION
Faithfulness
Answer relevance

EXPERIMENTS
Dense retrieval
Hybrid retrieval
Reranking
Chunk-size comparison

CI
Fail if Recall@10 decreases >1 percentage point

HELD-OUT TEST
40 stratified questions
