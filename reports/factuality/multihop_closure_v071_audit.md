# GroundTruth v0.7.1 — DEV multi-part evidence closure

**SHADOW DIAGNOSTIC ONLY — not new retrieval benchmark or model accuracy.**

Original DEV generation source SHA-256: `5a04e6d3bed733e7a3e9ef2f82f3adbe82cf0b6296f02f5445862a79420a46f7`

| DEV question | Manually decomposed queries | Evidence facets present | Result |
|---|---:|---:|---|
| k8s-034 | 3 | 5/5 | All specified facets present |
| k8s-068 | 3 | 5/5 | All specified facets present |

## Evidence anchors

### k8s-034
- **deployment_selector** (present): `work-009-sec-033-ch-001` — `.spec.selector` is a required field
- **replicaset_template_match** (present): `work-010-sec-008-ch-001` — `.spec.template.metadata.labels` must match `spec.selector`
- **daemonset_explicit_selector** (present): `work-012-sec-006-ch-001` — You must specify a pod selector that matches the labels
- **statefulset_matching_selector** (present): `work-011-sec-006-ch-001` — You must set the `.spec.selector` field of a StatefulSet
- **job_auto_selector** (present): `work-013-sec-040-ch-001` — The system defaulting logic adds this field when the Job is created

### k8s-068
- **external_plugin_architecture** (present): `stor-002-sec-046-ch-001` — without adding their plugin source code to the Kubernetes repository
- **migration_to_csi** (present): `stor-002-sec-052-ch-001` — The `CSIMigration` feature directs operations against existing in-tree
- **snapshots_require_csi** (present): `stor-008-sec-002-ch-001` — VolumeSnapshot support is only available for CSI drivers
- **snapshot_driver_support_varies** (present): `stor-008-sec-002-ch-002` — CSI drivers may or may not have implemented the volume snapshot functionality
- **volume_cloning_requires_csi** (present): `stor-003-sec-066-ch-001` — only available for CSI volume plugins

## Interpretation

The union of **manually designed targeted subqueries** recovers the specified parts of both DEV questions. This does **not** show that the original whole-question top-4 retriever captured every part; its scores remain frozen.

The original answers for both questions remain **generation errors** in the v0.7 baseline. This addendum does not backfill, regenerate, or score them as correct.

## Remaining release blockers

- 0 independently adjudicated generated answers in the v0.7 audit.
- 5 unsupported answers across 6 negative DEV cases in original generation.
- 3 original generation errors and 13 assistant-judged incorrect generated answers.
- Held-out TEST generation must remain untouched until a final policy and scoring protocol are frozen.

**Suggested release positioning:** evaluation-first local RAG *research prototype*. Not a production-verified factual question-answering system.
