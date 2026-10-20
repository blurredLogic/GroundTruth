# GroundTruth v0.7 — DEV generated-answer factuality audit

**Provenance: assistant first-pass review, not independent adjudication.**

- DEV questions: 60; answered: 56; generation errors: 3; abstentions: 1.
- Assistant-assessed generated answers: 56 / 56.
- Correct and complete: 26; factually correct but incomplete: 17; incorrect: 13.
- Unassessed generated answers: 0.
- Citation support judgments: {'fully_supported': 24, 'partially_supported': 23, 'unsupported': 9}.
- Negative question false answers in original output: 5; correct negative abstentions: 1.
- Independent human review: 0 / 60.

## Interpretation

Assistant-assessed fractions are **subset statistics**, not full 60-question answer accuracy or a deployed groundedness guarantee.
For defensible release claims, obtain a separate human review of the relevant answer claims and citations, resolve unassessed cases, and report full-DEV denominators.
Retain retrieval metrics as frozen and report generation failures and negative false answers alongside factuality.

## Generation errors

k8s-022, k8s-034, k8s-068

## Provenance

- Source SHA256: `5a04e6d3bed733e7a3e9ef2f82f3adbe82cf0b6296f02f5445862a79420a46f7`
- Review SHA256: `234421742e0c877ad48937dabfaea137f3198874fd12cae422af3ba987e69256`
