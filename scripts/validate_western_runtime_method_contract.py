#!/usr/bin/env python3
"""Validate that Western runtime sections are backed by book-digest method claims."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from book_coverage import flattened_coverages, load_book_coverage_files
from book_digests import flattened_digests, load_book_digest_files
from kb_utils import ROOT
from complete_relationship_result_runtime import DEFAULT_OUTPUT_PATH, WESTERN_METHOD_TRACE_SECTIONS


ACCEPTED_COVERAGE_STATUSES = {"reviewed", "implemented"}
ACCEPTED_IMPLEMENTATION_STATUSES = {"partial", "implemented"}
ACCEPTED_EVIDENCE_LEVELS = {"source_backed", "source_guided", "product_hypothesis"}
PRODUCT_INSIGHT_RUNTIME_TARGETS = {
    "relationshipArchetype",
    "attractionDynamics",
    "conflictDynamics",
    "growthDynamics",
    "partnerNeeds",
    "fightLandmines",
    "survivalGuide",
    "relationshipTurningWindows",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def method_claim_map() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for digest in flattened_digests(load_book_digest_files()):
        for claim in digest.method_claims:
            output[claim.id] = {
                "sourceId": digest.source_id,
                "implementationStatus": claim.implementation_status,
                "evidenceLevel": claim.evidence_level,
                "runtimeTargets": list(claim.runtime_targets),
            }
    return output


def coverage_index() -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    claim_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    target_index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for coverage in flattened_coverages(load_book_coverage_files()):
        for section in coverage.sections:
            section_payload = {
                "sourceId": coverage.source_id,
                "sectionId": section.section_id,
                "status": section.status,
            }
            for claim_id in section.digest_claim_ids:
                claim_index[claim_id].append(section_payload)
            if section.status in ACCEPTED_COVERAGE_STATUSES and section.digest_claim_ids:
                for target in section.runtime_targets:
                    target_index[target].append(section_payload)
    return claim_index, target_index


def expected_section_ids() -> list[str]:
    return [str(section.get("sectionId")) for section in WESTERN_METHOD_TRACE_SECTIONS]


def expected_runtime_targets() -> set[str]:
    return {
        str(target)
        for section in WESTERN_METHOD_TRACE_SECTIONS
        for target in section.get("requiredRuntimeTargets", [])
    }


def validate_method_trace(
    view_model: dict[str, Any],
    *,
    claim_map: dict[str, dict[str, Any]],
    coverage_claims: dict[str, list[dict[str, str]]],
    coverage_targets: dict[str, list[dict[str, str]]],
) -> list[str]:
    label = str(view_model.get("label") or view_model.get("id") or "scenario")
    errors: list[str] = []
    case_file = view_model.get("westernRelationshipCaseFile") or {}
    if case_file.get("version") != "western-relationship-case-file-v1":
        return [f"{label}: westernRelationshipCaseFile missing or wrong version"]
    evidence_clusters = case_file.get("evidenceClusters") or {}
    method_trace = case_file.get("methodTrace") or {}
    if method_trace.get("version") != "western-method-trace-v1":
        return [f"{label}: methodTrace missing or wrong version"]

    sections = method_trace.get("sections") or []
    section_ids = [str(section.get("sectionId")) for section in sections]
    if section_ids != expected_section_ids():
        errors.append(f"{label}: methodTrace section order mismatch: {section_ids}")
    summary = method_trace.get("summary") or {}
    if summary.get("sectionCount") != len(expected_section_ids()):
        errors.append(f"{label}: methodTrace summary sectionCount mismatch")
    if summary.get("coveredSectionCount") != len(expected_section_ids()):
        errors.append(f"{label}: not all methodTrace sections are covered")

    for section in sections:
        section_id = str(section.get("sectionId") or "")
        prefix = f"{label}:{section_id}"
        if section.get("status") != "covered":
            errors.append(f"{prefix}: status is not covered")
        if section.get("missingRequirements"):
            errors.append(f"{prefix}: missing requirements {section.get('missingRequirements')}")
        if not section.get("liveEvidenceCount"):
            errors.append(f"{prefix}: liveEvidenceCount is empty")
        if not section.get("runtimeClaimIds"):
            errors.append(f"{prefix}: runtimeClaimIds is empty")
        if not section.get("usedAtomIds"):
            errors.append(f"{prefix}: usedAtomIds is empty")

        required_sources = set(section.get("requiredSourceIds") or [])
        if not required_sources:
            errors.append(f"{prefix}: requiredSourceIds is empty")
        for target in section.get("requiredRuntimeTargets") or []:
            if target in PRODUCT_INSIGHT_RUNTIME_TARGETS:
                cluster = evidence_clusters.get(target) or {}
                if not cluster:
                    errors.append(f"{prefix}: composed insight target has no evidence cluster: {target}")
                    continue
                if not cluster.get("methodClaimIds"):
                    errors.append(f"{prefix}: composed insight target has no method claims: {target}")
                if not cluster.get("source"):
                    errors.append(f"{prefix}: composed insight target has no source marker: {target}")
            elif target not in coverage_targets:
                errors.append(f"{prefix}: runtime target has no reviewed/implemented coverage: {target}")
        for claim_id in section.get("methodClaimIds") or []:
            claim = claim_map.get(str(claim_id))
            if not claim:
                errors.append(f"{prefix}: unknown method claim {claim_id}")
                continue
            if claim["sourceId"] not in required_sources:
                errors.append(f"{prefix}: claim {claim_id} belongs to {claim['sourceId']} outside required sources")
            if claim["implementationStatus"] not in ACCEPTED_IMPLEMENTATION_STATUSES:
                errors.append(f"{prefix}: claim {claim_id} implementation is {claim['implementationStatus']}")
            if claim["evidenceLevel"] not in ACCEPTED_EVIDENCE_LEVELS:
                errors.append(f"{prefix}: claim {claim_id} evidence level is {claim['evidenceLevel']}")
            coverage_rows = [
                row
                for row in coverage_claims.get(str(claim_id), [])
                if row["status"] in ACCEPTED_COVERAGE_STATUSES
            ]
            if not coverage_rows:
                errors.append(f"{prefix}: claim {claim_id} has no reviewed/implemented book coverage")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Western runtime method trace contract.")
    parser.add_argument("--fixtures", default=str(DEFAULT_OUTPUT_PATH), help="Generated complete relationship result scenarios JSON.")
    args = parser.parse_args()

    fixtures_path = Path(args.fixtures)
    if not fixtures_path.is_absolute():
        fixtures_path = ROOT / fixtures_path
    if not fixtures_path.exists():
        print(f"- generated fixtures do not exist: {fixtures_path.relative_to(ROOT)}")
        return 1

    scenarios = load_json(fixtures_path)
    if not isinstance(scenarios, list) or not scenarios:
        print("- generated fixtures must be a non-empty list")
        return 1

    claim_map = method_claim_map()
    coverage_claims, coverage_targets = coverage_index()
    errors: list[str] = []
    for target in sorted(expected_runtime_targets()):
        if target in PRODUCT_INSIGHT_RUNTIME_TARGETS:
            continue
        if target not in coverage_targets:
            errors.append(f"coverage: runtime target has no reviewed/implemented section: {target}")
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("scenario payload must be an object")
            continue
        errors.extend(
            validate_method_trace(
                scenario,
                claim_map=claim_map,
                coverage_claims=coverage_claims,
                coverage_targets=coverage_targets,
            )
        )

    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Validated Western runtime method trace: "
        f"{len(scenarios)} scenario(s), "
        f"{len(expected_section_ids())} section(s), "
        f"{len(expected_runtime_targets())} required runtime target(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
