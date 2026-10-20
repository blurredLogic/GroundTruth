# GroundTruth — publication checklist

Run through this before publishing the repository or enabling its badge.

## Source and dependencies

- [ ] Copy `README.md`, `requirements.txt` and `requirements-optional.txt` to the repository root.
- [ ] Check `groundtruth/ingestion/fetch_documents.py` for any additional third-party imports not in `requirements.txt` (its source wasn't among the files reviewed to build this documentation).
- [ ] Ensure the actual folder/module names match the documented `python -m` commands.
- [ ] Verify setup from a **fresh Python 3.10 virtual environment**, not just a machine that already has dependencies installed.
- [ ] Preserve the frozen `configs/frozen_retrieval_v1.json` and the golden set.
- [ ] Keep `manifest/kubernetes_v0.1.yaml` and `data/processed/sections.jsonl` in checkout (or provide a documented artifact restoration step for the manual CI action).
- [ ] Do not upload local API keys, `.env` files, model weights, personal filesystem paths in reports, or unnecessary GB-sized indexes.
- [ ] Add an explicit repository LICENSE after choosing one; do not claim a license beforehand.

## Reproduction and CI

- [ ] `python -m pip check` passes.
- [ ] `python -m compileall -q groundtruth` passes.
- [ ] `python -m groundtruth.ci.check_golden` passes.
- [ ] All dependency-light fast CI unit tests pass.
- [ ] `python -m groundtruth.ci.run_frozen_regression --preflight-only` passes.
- [ ] Full frozen retrieval regression passes (local and, if corpus artifacts are available, manually triggered GitHub Action).
- [ ] One locally generated cited answer works with Ollama and is inspected manually.
- [ ] Precomputed reports referenced in README are committed or downloadable from a stable release artifact.

## Research integrity

- [ ] Clearly label TEST retrieval scores as **historical frozen benchmark**, and specify the 36 answerable-case denominator.
- [ ] Clearly label first-pass factuality assessments as **assistant-reviewed**, not independently verified.
- [ ] Disclose five falsely answered negatives, three generation errors, and semantic-verifier false acceptance.
- [ ] Keep source-first, repair and verifier experiments **shadow-only**.
- [ ] Do not claim a completed held-out *generation* evaluation or production readiness.
- [ ] Record source/provenance hashes whenever updating corpus or reports.
- [ ] Do not silently modify frozen retrieval parameters or golden annotations.

## Optional presentation improvements

- [ ] Add an architecture image/screenshot if desired; Mermaid in README is already valid GitHub Markdown.
- [ ] Add a small example JSON trace using a genuinely run command (exclude secrets).
- [ ] Link relevant evaluation reports from a GitHub Release after confirming their paths.
- [ ] Replace the `git clone` URL placeholder with the actual repository URL.
