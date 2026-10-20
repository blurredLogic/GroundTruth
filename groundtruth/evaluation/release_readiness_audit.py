"""GroundTruth v0.7.1 non-deployable research release readiness preflight.

Consumes saved audit artifacts; no inference or TEST access. Does not run CI itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from groundtruth.evaluation.multihop_closure_audit import EXPECTED_SOURCE_SHA256, AuditError


def build_readiness(factuality: dict, closure: dict) -> dict:
    if factuality.get("schema") != "groundtruth_answer_factuality_audit_v0.7":
        raise AuditError("Factuality report schema mismatch")
    if closure.get("schema") != "groundtruth_multihop_closure_v0.7.1":
        raise AuditError("Closure report schema mismatch")
    if any(item.get("source_sha256") != EXPECTED_SOURCE_SHA256 for item in (factuality, closure)):
        raise AuditError("Reports do not match original saved DEV results")
    statuses = factuality.get("generation_status_counts", {})
    assessment = factuality.get("assistant_reviewed_assessment_counts", {})
    if statuses.get("answered") != 56 or statuses.get("abstained") != 1 or statuses.get("generation_error") != 3:
        raise AuditError("DEV generation-status baseline changed")
    if sum(assessment.values()) != 56:
        raise AuditError("Assistant factuality audit incomplete")
    independent_count = factuality.get("independent_reviewed_question_count")
    false_negatives = factuality.get("negative_false_answer_count_from_operational_labels")
    if not isinstance(independent_count, int) or not isinstance(false_negatives, int):
        raise AuditError("Missing independent-review or negative-answer count")
    if len(closure.get("cases", [])) != 2:
        raise AuditError("Missing multi-part diagnostic cases")
    gates = [
        {"name": "Full DEV assistant first-pass answer audit", "status": "met_first_pass_only", "actual": "56/56 generated answers assistant-reviewed"},
        {"name": "Diagnostic multi-part source coverage", "status": "met_diagnostic_only" if closure.get("all_facets_present") else "missing", "actual": "10/10 manually specified anchors present" if closure.get("all_facets_present") else "Anchors missing"},
        {"name": "Independent claim/citation factuality adjudication", "status": "blocked" if independent_count < 56 else "review_count_met_verify_quality", "actual": f"{independent_count}/56 generated answers independently adjudicated"},
        {"name": "False answers on negative DEV questions", "status": "blocked" if false_negatives else "met_on_dev", "actual": f"{false_negatives} negative false answers"},
        {"name": "Generation runtime errors on DEV", "status": "blocked" if statuses["generation_error"] else "met_on_dev", "actual": f"{statuses['generation_error']} generation errors"},
        {"name": "First-pass incorrect generated answers", "status": "requires_review", "actual": f"{assessment.get('incorrect', 0)} assistant-judged incorrect of 56"},
        {"name": "Frozen retrieval CI regression", "status": "must_run_locally", "actual": "Previously frozen metrics; this preflight does not rerun CI"},
        {"name": "Held-out TEST generation evaluation", "status": "not_run_by_this_workflow", "actual": "Freeze final policy and protocol before first held-out evaluation"},
    ]
    return {"schema": "groundtruth_release_readiness_v0.7.1", "source_sha256": EXPECTED_SOURCE_SHA256,
            "research_preview_documentation_possible": True,
            "factuality_validated_v1_release_ready": False,
            "gates": gates,
            "interpretation": "Research prototype may be published with explicit limitations and independently reproducible frozen retrieval metrics; validated-accuracy or production readiness must not be claimed.",
            "next_actions": ["Run original frozen retrieval regression and full unit-test suite locally.",
                             "Obtain independent adjudication of generated claims and citations (ideally all 56; prioritize 6 negatives and known failures).",
                             "Choose and freeze a single generation/abstention policy before touching TEST.",
                             "Conduct held-out TEST evaluation once and transparently report unsupported negative answers, missing generations and citation support."]}


def run(factuality_path: Path, closure_path: Path, output: Path) -> dict:
    factuality = json.loads(factuality_path.read_text(encoding="utf-8"))
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    result = build_readiness(factuality, closure)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--factuality", default="reports/factuality/dev_v07_assistant_audit.json")
    parser.add_argument("--closure", default="reports/factuality/multihop_closure_v071_audit.json")
    parser.add_argument("--output", default="reports/factuality/release_readiness_v071.json")
    a = parser.parse_args()
    result = run(Path(a.factuality), Path(a.closure), Path(a.output))
    for gate in result["gates"]:
        print(f"{gate['status']:>24} | {gate['name']}: {gate['actual']}")
    print("Validated v1.0 release ready: NO. Research-preview documentation may proceed.")


if __name__ == "__main__":
    main()
