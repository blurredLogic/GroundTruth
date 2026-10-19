# GroundTruth CI v1 — frozen retrieval core

This package is **additive**. It does not replace any current retriever, experiment, or evaluation module. It freezes the selected architecture: 512/64 chunks; 1,223 indexable passages; BGE-small-en-v1.5 cosine, query prefix **OFF**; BM25 `k1=1.5, b=0.75`; weighted RRF dense=1.0/BM25=0.1, `k=20`, candidate depth 20. It leaves user-requested enhancements for the next project phase.

## Install

Unzip the contents at the GroundTruth repository root, preserving `.github/workflows/`, `groundtruth/ci/`, `configs/`, and `tests/`. Keep your existing `.gitignore`, appending the lines in `CI_GITIGNORE_SNIPPET.txt`.

You **must** keep the existing `data/evaluation/golden_questions.jsonl` in the repo; the fast CI checks its semantic fingerprint, using the original `golden_questions_100.jsonl` previously generated for the benchmark. The baseline fingerprint is pinned in `configs/frozen_retrieval_v1.json`. Do not auto-update this fingerprint as part of feature changes.

## Fast local checks (no model imports required)

Run from the repository root:

```powershell
python -m compileall -q groundtruth
python -m groundtruth.ci.check_golden
python -m unittest discover -s tests -p "test_ci_gates.py" -v
python -m unittest discover -s tests -p "test_bm25_smoke.py" -v
```

The GitHub Actions **GroundTruth fast CI** workflow runs these checks on every push and pull request. It validates the 100-question (60-dev/40-test) frozen golden set, 90 answerable/10 negative balance, unchanged golden judgments, Python compilation, BM25 build/retrieve/integrity, and regression-gate logic. **It does not run model retrieval**, so a green fast CI badge is **not** proof that production retrieval metrics still pass.

## Quick check of existing held-out report (smoke test only)

```powershell
python -m groundtruth.ci.check_retrieval_regression --report reports/evaluation/hybrid_rrf_v0_2_test.json
```

This checks the historical report's shape/config/metrics, not new retrieval behavior; it does **not** substitute for the full regression run.

## Full local regression (evaluates fresh artifacts)

Requires all previous GroundTruth pipeline modules and already-working SentenceTransformers/PyTorch/CUDA environment. Your Windows install previously reported `torch 2.11.0+cu128` with CUDA available.

```powershell
python -m groundtruth.ci.run_frozen_regression --preflight-only
python -m groundtruth.ci.run_frozen_regression --device cuda
```

The runner discovers your existing project modules under `groundtruth/**/`, then:
1. Verifies frozen golden questions.
2. Builds canonical 512/64 chunks from `data/processed/sections.jsonl` and `manifest/kubernetes_v0.1.yaml`, twice, checking byte-for-byte determinism.
3. Prepares indexable enriched chunks in `data/ci/frozen_retrieval/`.
4. Builds fresh dense and BM25 indexes in the isolated workspace.
5. Evaluates frozen Hybrid v0.2 on the **held-out test set** (40 questions, 36 answerable).
6. Validates the fresh result against configuration, corpus count, and metric floors.

The runner accepts only a workspace under `data/ci/` for safe cleanup. Nothing under the regular `data/index/dense`, `data/index/bm25`, or `reports/evaluation/` directories is overwritten. Artifacts from a successful run remain in `data/ci/frozen_retrieval/` for debugging and are ignored by Git.

The benchmark is frozen. Treat quality-gate failures as regressions to investigate, **not** an invitation to tune model parameters on test. The numerical floors are engineering tolerances, not formal statistical confidence bounds.

## Full GitHub Actions quality gate

Open the repository **Actions** tab and select **GroundTruth frozen retrieval regression** > **Run workflow**. This is **manual only**, because a CPU hosted runner needs substantial model downloads and compute. The workflow uses CPU PyTorch and uploads report artifacts even after an error.

**Important prerequisite:** `manifest/kubernetes_v0.1.yaml`, `data/processed/sections.jsonl`, and `data/evaluation/golden_questions.jsonl` must be available after checkout. If source sections are excluded by `.gitignore`, you will need to explicitly track them or add a trusted artifact restoration step before enabling the hosted full run. You do **not** need to commit pretrained model binaries, the dense embeddings, or BM25 index artifacts.

## Frozen held-out test baseline

| Metric | Frozen result | Maximum tolerated absolute drop |
| --- | ---: | ---: |
| Recall@5 | 0.664352 | 0.020 |
| Recall@10 | 0.773148 | 0.010 |
| MRR | 0.846561 | 0.015 |
| nDCG@5 | 0.755878 | 0.020 |
| nDCG@10 | 0.785889 | 0.010 |
| Top-1 hit | 0.777778 | 0.028 |

If a report has a wrong split, fewer questions, changed query prefix, model, RRF parameters, or index counts, the gate fails even when its scores look good. The quality metrics exclude the four test negatives; negative-question performance is evaluated separately and isn't covered by this gate.

## Subsequent feature work

After this foundation is passing, add advanced features in separate branches. Suggested order: grounded answer generation and citation quality evaluation; more robust abstention calibration with additional negative examples; provenance/trace viewer; latency/cost dashboard; reproducible release artifacts. Features should extend this locked retrieval baseline, not silently modify its test data.
