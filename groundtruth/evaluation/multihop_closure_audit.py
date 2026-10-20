"""Deterministic DEV-only evidence coverage addendum for GroundTruth v0.7.1.

This does not evaluate answer accuracy, generate answers, or change retrieval.
It checks manually specified evidence facets against the saved diagnostic chunks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_SHA256 = "5a04e6d3bed733e7a3e9ef2f82f3adbe82cf0b6296f02f5445862a79420a46f7"
EXPECTED_PARAMS = {"fusion": "reciprocal_rank_fusion", "rrf_k": 20.0, "candidate_k": 20,
                   "dense_weight": 1.0, "bm25_weight": 0.1, "chunk_count": 1223}
# These are independently documented facets of two specific DEV questions.
# Text matching certifies that cited material is PRESENT, not that it proves every nuance.
FACETS = {
    "k8s-034": [
        ("deployment_selector", "work-009-sec-033-ch-001", "`.spec.selector` is a required field"),
        ("replicaset_template_match", "work-010-sec-008-ch-001", "`.spec.template.metadata.labels` must match `spec.selector`"),
        ("daemonset_explicit_selector", "work-012-sec-006-ch-001", "You must specify a pod selector that matches the labels"),
        ("statefulset_matching_selector", "work-011-sec-006-ch-001", "You must set the `.spec.selector` field of a StatefulSet"),
        ("job_auto_selector", "work-013-sec-040-ch-001", "The system defaulting logic adds this field when the Job is created"),
    ],
    "k8s-068": [
        ("external_plugin_architecture", "stor-002-sec-046-ch-001", "without adding their plugin source code to the Kubernetes repository"),
        ("migration_to_csi", "stor-002-sec-052-ch-001", "The `CSIMigration` feature directs operations against existing in-tree"),
        ("snapshots_require_csi", "stor-008-sec-002-ch-001", "VolumeSnapshot support is only available for CSI drivers"),
        ("snapshot_driver_support_varies", "stor-008-sec-002-ch-002", "CSI drivers may or may not have implemented the volume snapshot functionality"),
        ("volume_cloning_requires_csi", "stor-003-sec-066-ch-001", "only available for CSI volume plugins"),
    ],
}

class AuditError(ValueError):
    pass


def squish(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def validate_and_assess(document: dict[str, Any], raw_sha256: str) -> dict[str, Any]:
    if document.get("schema") != "groundtruth_multihop_diagnostic_v0.7":
        raise AuditError("Unexpected diagnostic schema")
    if document.get("split") != "dev" or document.get("shadow_only") is not True:
        raise AuditError("Only DEV shadow diagnostics can be audited")
    if document.get("source_sha256") != EXPECTED_SOURCE_SHA256:
        raise AuditError("Source report fingerprint mismatch")
    params = document.get("retriever_description", {})
    for key, value in EXPECTED_PARAMS.items():
        if params.get(key) != value:
            raise AuditError(f"Frozen retrieval setting changed: {key}")
    records = document.get("records", [])
    if len(records) != 2 or {r.get("question_id") for r in records} != set(FACETS):
        raise AuditError("Expected exactly the two DEV multihop diagnostic questions")
    cases = []
    for r in records:
        qid = r["question_id"]
        queries = r.get("retrievals", [])
        if len(queries) != 3 or any(len(x.get("sources", [])) != 4 for x in queries):
            raise AuditError(f"Unexpected subquery/source count in {qid}")
        for item in queries:
            if not isinstance(item.get("subquery"), str) or not item["subquery"].strip():
                raise AuditError("Missing manual subquery text")
        all_sources = [s for item in queries for s in item["sources"]]
        chunk_texts: dict[str, str] = {}
        urls: dict[str, str] = {}
        for src in all_sources:
            cid = src.get("chunk_id", "")
            url = src.get("source_url", "")
            txt = src.get("text", "")
            if not cid or not url.startswith("https://kubernetes.io/") or not txt:
                raise AuditError(f"Untraceable source {qid}: {cid}")
            if cid in chunk_texts and squish(chunk_texts[cid]) != squish(txt):
                raise AuditError(f"Conflicting text for repeated chunk {cid}")
            chunk_texts[cid] = txt
            urls[cid] = url
        facets = []
        for facet, cid, quote in FACETS[qid]:
            src = chunk_texts.get(cid)
            matches = src is not None and squish(quote) in squish(src)
            facets.append({"facet": facet, "chunk_id": cid, "source_url": urls.get(cid),
                           "anchor": quote, "evidence_present": matches})
        cases.append({"question_id": qid, "manual_subqueries": len(queries),
                      "retrieved_hits_including_duplicates": len(all_sources),
                      "unique_chunks": len(chunk_texts),
                      "facet_count": len(facets),
                      "facets_present": sum(x["evidence_present"] for x in facets),
                      "diagnostic_facets_all_present": all(x["evidence_present"] for x in facets),
                      "facets": facets,
                      "interpretation": "Targeted, manually decomposed subqueries surface all pre-specified source facets. Not a single-query retrieval or answer-correctness result."})
    return {"schema": "groundtruth_multihop_closure_v0.7.1",
            "scope": "DEV diagnostic only; frozen original retrieval and 3 original generation errors unchanged",
            "source_sha256": EXPECTED_SOURCE_SHA256, "diagnostic_sha256": raw_sha256,
            "retriever_params": EXPECTED_PARAMS,
            "all_facets_present": all(c["diagnostic_facets_all_present"] for c in cases),
            "cases": sorted(cases, key=lambda x: x["question_id"]),
            "release_implication": "Improved coverage is possible through manual question decomposition; no change to baseline MRR/Recall or original generation outcome",
            "limitations": ["Manually crafted subqueries are diagnostic, not a measured general-purpose multi-hop strategy.",
                            "String anchors confirm that evidence is present, not that claims are fully entailed.",
                            "Generation errors for k8s-034 and k8s-068 remain in the DEV baseline.",
                            "No TEST queries, new answer generations, or gold/reference answers used."]}


def markdown_report(report: dict[str, Any]) -> str:
    lines = ["# GroundTruth v0.7.1 — DEV multi-part evidence closure", "",
             "**SHADOW DIAGNOSTIC ONLY — not new retrieval benchmark or model accuracy.**", "",
             f"Original DEV generation source SHA-256: `{report['source_sha256']}`", "",
             "| DEV question | Manually decomposed queries | Evidence facets present | Result |", "|---|---:|---:|---|" ]
    for c in report["cases"]:
        status = "All specified facets present" if c["diagnostic_facets_all_present"] else "Incomplete"
        lines.append(f"| {c['question_id']} | {c['manual_subqueries']} | {c['facets_present']}/{c['facet_count']} | {status} |")
    lines.extend(["", "## Evidence anchors", ""])
    for c in report["cases"]:
        lines.append(f"### {c['question_id']}")
        for f in c["facets"]:
            icon = "present" if f["evidence_present"] else "MISSING"
            lines.append(f"- **{f['facet']}** ({icon}): `{f['chunk_id']}` — {f['anchor']}")
        lines.append("")
    lines.extend(["## Interpretation", "",
                  "The union of **manually designed targeted subqueries** recovers the specified parts of both DEV questions. This does **not** show that the original whole-question top-4 retriever captured every part; its scores remain frozen.",
                  "", "The original answers for both questions remain **generation errors** in the v0.7 baseline. This addendum does not backfill, regenerate, or score them as correct.",
                  "", "## Remaining release blockers", "",
                  "- 0 independently adjudicated generated answers in the v0.7 audit.",
                  "- 5 unsupported answers across 6 negative DEV cases in original generation.",
                  "- 3 original generation errors and 13 assistant-judged incorrect generated answers.",
                  "- Held-out TEST generation must remain untouched until a final policy and scoring protocol are frozen.",
                  "", "**Suggested release positioning:** evaluation-first local RAG *research prototype*. Not a production-verified factual question-answering system.", ""])
    return "\n".join(lines)


def run(input_path: Path, output_prefix: Path) -> dict[str, Any]:
    raw = input_path.read_bytes()
    document = json.loads(raw.decode("utf-8"))
    report = validate_and_assess(document, hashlib.sha256(raw).hexdigest())
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    output_prefix.with_name(output_prefix.name + "_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    output_prefix.with_name(output_prefix.name + "_audit.md").write_text(markdown_report(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="reports/factuality/multihop_diagnostic_v07.json")
    parser.add_argument("--output-prefix", default="reports/factuality/multihop_closure_v071")
    args = parser.parse_args()
    result = run(Path(args.input), Path(args.output_prefix))
    for case in result["cases"]:
        print(f"{case['question_id']}: {case['facets_present']}/{case['facet_count']} manually specified evidence facets found")
    print("Status: DEV evidence diagnostic only — original generation errors unchanged")


if __name__ == "__main__":
    main()
