#!/usr/bin/env python3
"""Validate the committed Phase 0 production-reading baseline."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_reading_production_baseline import (  # noqa: E402
    BASELINE_VERSION,
    CONTACTS,
    DEFAULT_OUTPUT_DIR,
    QUESTIONS,
    SECTION_NARRATIVE_IDS,
    STAGE_ORDER,
    build_baseline,
    file_hash,
    stable_hash,
)
from readable_interpretation.section_narrative_spec import (  # noqa: E402
    SECTION_NARRATIVE_SPEC_VERSION,
    SUPPORTED_SECTION_NARRATIVE_SPEC_VERSIONS,
    validate_section_narrative_specs,
)


HISTORICAL_BASELINE_SPEC_VERSIONS = (
    *SUPPORTED_SECTION_NARRATIVE_SPEC_VERSIONS,
    "section-narrative-spec-v3",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_balanced(values: list[str], expected: tuple[str, ...], expected_each: int, label: str) -> None:
    counts = Counter(values)
    require(set(counts) == set(expected), f"{label}: values mismatch: {sorted(counts)}")
    require(set(counts.values()) == {expected_each}, f"{label}: unbalanced counts: {dict(counts)}")


def assert_section_bundle(
    bundle: dict[str, Any],
    case_id: str,
    *,
    renderer_consumes_specs: bool,
    expected_spec_version: str,
) -> None:
    require(bundle.get("version") == expected_spec_version, f"{case_id}: spec version mismatch")
    require(
        bundle.get("rendererConsumesSpecs") is renderer_consumes_specs,
        f"{case_id}: renderer consumption flag mismatch",
    )
    require((bundle.get("validation") or {}).get("status") == "valid", f"{case_id}: invalid spec bundle")
    specs = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    require(set(specs) == set(SECTION_NARRATIVE_IDS), f"{case_id}: section spec set mismatch")
    if expected_spec_version == SECTION_NARRATIVE_SPEC_VERSION:
        validation = validate_section_narrative_specs(specs)
        require(
            validation.get("status") == "valid",
            f"{case_id}: live contract validation failed: {validation}",
        )


def assert_artifacts(
    output_dir: Path,
    *,
    expected_version: str,
    renderer_consumes_specs: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    paths = {
        "manifest": output_dir / "manifest.json",
        "golden": output_dir / "golden-cases.json",
        "distribution": output_dir / "distribution-corpus.json",
        "metrics": output_dir / "metrics.json",
    }
    for label, path in paths.items():
        require(path.exists(), f"{label} artifact missing: {path}")

    manifest = read_json(paths["manifest"])
    golden = read_json(paths["golden"])
    distribution = read_json(paths["distribution"])
    metrics = read_json(paths["metrics"])
    require(manifest.get("version") == expected_version, "manifest version mismatch")
    require(golden.get("version") == expected_version, "golden version mismatch")
    require(distribution.get("version") == expected_version, "distribution version mismatch")
    require(metrics.get("version") == expected_version, "metrics version mismatch")
    require(manifest.get("syntheticDataOnly") is True, "baseline must contain synthetic data only")
    require(manifest.get("goldenCaseCount") == 50, "golden baseline must contain 50 cases")
    require(manifest.get("distributionCaseCount") == 500, "distribution baseline must contain 500 cases")
    require(tuple(manifest.get("supportedStages") or []) == tuple(STAGE_ORDER), "supported stage contract mismatch")
    require(tuple(manifest.get("supportedQuestions") or []) == tuple(QUESTIONS), "supported question contract mismatch")
    require(tuple(manifest.get("supportedContacts") or []) == tuple(CONTACTS), "supported contact contract mismatch")
    manifest_spec_version = str(manifest.get("sectionSpecVersion") or "")
    require(
        manifest_spec_version in HISTORICAL_BASELINE_SPEC_VERSIONS,
        f"unsupported section spec manifest: {manifest_spec_version}",
    )

    expected_hashes = manifest.get("files") or {}
    require(expected_hashes.get("golden-cases.json") == file_hash(paths["golden"]), "golden artifact hash mismatch")
    require(expected_hashes.get("distribution-corpus.json") == file_hash(paths["distribution"]), "distribution artifact hash mismatch")
    require(expected_hashes.get("metrics.json") == file_hash(paths["metrics"]), "metrics artifact hash mismatch")

    golden_records = golden.get("records") if isinstance(golden.get("records"), list) else []
    distribution_records = distribution.get("records") if isinstance(distribution.get("records"), list) else []
    require(len(golden_records) == 50, f"golden record count mismatch: {len(golden_records)}")
    require(len(distribution_records) == 500, f"distribution record count mismatch: {len(distribution_records)}")
    assert_balanced(
        [str((record.get("input") or {}).get("context", {}).get("relationship_stage") or "") for record in golden_records],
        tuple(STAGE_ORDER),
        10,
        "golden stages",
    )
    assert_balanced(
        [str((record.get("input") or {}).get("context", {}).get("main_question") or "") for record in golden_records],
        tuple(QUESTIONS),
        10,
        "golden questions",
    )
    assert_balanced(
        [str((record.get("input") or {}).get("context", {}).get("contact_status") or "") for record in golden_records],
        tuple(CONTACTS),
        10,
        "golden contacts",
    )

    for record in golden_records:
        case_id = str(record.get("id") or "unknown")
        assert_section_bundle(
            record.get("sectionSpecs") or {},
            case_id,
            renderer_consumes_specs=renderer_consumes_specs,
            expected_spec_version=manifest_spec_version,
        )
        sections = ((record.get("finalInterpretation") or {}).get("sections") or {})
        require(set(sections) == set(SECTION_NARRATIVE_IDS), f"{case_id}: visible section set mismatch")
        for section_id in SECTION_NARRATIVE_IDS:
            section = sections.get(section_id) or {}
            require(section.get("headline"), f"{case_id}:{section_id}: headline missing")
            require(section.get("body"), f"{case_id}:{section_id}: body missing")
        fingerprints = record.get("fingerprints") or {}
        require(fingerprints.get("chart"), f"{case_id}: chart fingerprint missing")
        require(fingerprints.get("hiddenModel"), f"{case_id}: hidden-model fingerprint missing")

    require(len({record.get("pairFingerprint") for record in distribution_records}) == 500, "distribution pair fingerprints are not unique")
    require(len({record.get("chartFingerprint") for record in distribution_records}) == 500, "distribution chart fingerprints are not unique")
    fixed_context = distribution.get("fixedContext") or {}
    require(fixed_context.get("timing_scan_days") == 0, "distribution timing must be disabled")
    require((metrics.get("golden") or {}).get("caseCount") == 50, "golden metric count mismatch")
    require((metrics.get("distribution") or {}).get("caseCount") == 500, "distribution metric count mismatch")
    require((metrics.get("golden") or {}).get("validSectionSpecBundles") == 50, "not all golden specs are valid")
    return manifest, golden, distribution, metrics


def assert_live_sample(manifest: dict[str, Any], golden: dict[str, Any], distribution: dict[str, Any], count: int) -> None:
    require(
        manifest.get("sectionSpecVersion") == SECTION_NARRATIVE_SPEC_VERSION,
        "live samples are only supported for the current section spec version",
    )
    rebuilt_manifest, rebuilt_golden, rebuilt_distribution, _metrics = build_baseline(
        golden_count=count,
        distribution_count=count,
        golden_timing_days=int(manifest.get("goldenTimingScanDays") or 90),
        golden_timing_step=int(manifest.get("goldenTimingScanStepDays") or 2),
        progress_every=0,
        baseline_version=str(manifest.get("version") or BASELINE_VERSION),
    )
    require(rebuilt_manifest.get("engineVersions") == manifest.get("engineVersions"), "live engine versions differ from baseline")
    expected_golden = (golden.get("records") or [])[:count]
    expected_distribution = (distribution.get("records") or [])[:count]
    require(stable_hash(rebuilt_golden.get("records") or []) == stable_hash(expected_golden), "live golden sample differs from baseline")
    require(
        stable_hash(rebuilt_distribution.get("records") or []) == stable_hash(expected_distribution),
        "live distribution sample differs from baseline",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Phase 0 production-reading baseline.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-version", default=BASELINE_VERSION)
    parser.add_argument("--renderer-consumes-specs", choices=("true", "false"), default="false")
    parser.add_argument("--live-sample", type=int, default=0, help="Recalculate the first N golden and distribution records.")
    args = parser.parse_args()
    renderer_consumes_specs = args.renderer_consumes_specs == "true"
    manifest, golden, distribution, metrics = assert_artifacts(
        args.output_dir,
        expected_version=str(args.expected_version),
        renderer_consumes_specs=renderer_consumes_specs,
    )
    if args.live_sample:
        assert_live_sample(manifest, golden, distribution, max(1, min(args.live_sample, 5)))
    print("Reading production baseline smoke passed.")
    print("- 50 complete golden readings with balanced status, question, and contact coverage")
    print("- 500 unique synthetic chart pairs for distribution calibration")
    print(f"- all golden SectionNarrativeSpec bundles are valid; rendererConsumesSpecs={renderer_consumes_specs}")
    if args.live_sample:
        print(f"- live deterministic sample: {max(1, min(args.live_sample, 5))}")
    print(f"- current distribution archetypes: {len((metrics.get('distribution') or {}).get('archetypeCounts') or {})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
