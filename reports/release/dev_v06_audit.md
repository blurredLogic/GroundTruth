# GroundTruth v0.6 — DEV release evidence audit

**Status: EVALUATION SNAPSHOT, NOT RELEASE-READY.** No TEST questions are used.

## Grounded counts

- Original DEV generation: 56 answered, 1 abstained, 3 errors.
- Unsupported answers on the six DEV negatives: 5/6; correct abstentions 1/6.
- Saved evidence: 57/60, missing 3: k8s-022, k8s-034, k8s-068.
- Assistant review selected-excerpt relations: contradicted=3, insufficient=5, partial=15, supported=34, unreviewed=3.
- For 54 answerable questions: insufficient=2, partial=15, supported=34, unreviewed=3.
- For six negative questions: contradicted=3, insufficient=3.

## Critical distinctions

- `supported` means selected retrieved excerpts can answer the QUESTION. It is **not** model-answer accuracy.
- `partial` often means the excerpt selector dropped one part of a multi-part question; see review notes for full-source follow-up.
- `insufficient` means these selected excerpts do not establish the answer, not that the entire Kubernetes documentation cannot answer it.
- Three missing cases are **unreviewed**, not negative questions and not insufficient evidence.
- Six negative DEV questions were previously inspected for tuning/triage: results are diagnostic, not unbiased hold-out performance.

## Release decision

**Do not release as a factuality-validated v1.0.** The frozen retrieval regression is green, but generator factual correctness/abstention and independent adjudication remain incomplete. Leave experimental semantic gates in shadow mode.

Next: (1) re-retrieve evidence for 022/034/068, (2) expand selected excerpts where partial, (3) perform an independent answer-versus-evidence factual review, (4) freeze criteria before a final untouched TEST evaluation.
