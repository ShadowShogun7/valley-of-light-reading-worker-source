#!/usr/bin/env python3
"""Verify Phase 7 split integrity, semantic coverage, and calibration quality."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from build_reading_phase7_calibration import (
    COMPARISON_AXES,
    CORPUS_VERSION,
    DEFAULT_CONTRACT_PATH,
    DEFAULT_OUTPUT_DIR,
    EMOTIONAL_RISKS,
    PRECISION_PROFILES,
    REVIEW_VERSION,
    review_coverage,
    runtime_source_hashes,
)
from build_reading_production_baseline import CONTACTS, QUESTIONS, stable_hash
from kb_utils import ROOT
from readable_interpretation.final_narrative_fact_contract import (
    FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
    FINAL_NARRATIVE_FACT_RENDERER_MODE,
)
from readable_interpretation.final_narrative_composer import FINAL_NARRATIVE_COMPOSER_VERSION
from readable_interpretation.final_narrative_chinese_quality import (
    FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
    hard_quality_contract_fingerprint,
)
from readable_interpretation.final_narrative_composition import (
    FINAL_NARRATIVE_COMPOSITION_VERSION,
)
from readable_interpretation.final_narrative_paragraph_plan import (
    FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
)
from readable_interpretation.final_narrative_semantic_coverage import (
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
)
from readable_interpretation.final_narrative_test_engine import (
    analyze_output_collapses,
    compact_semantic_projection,
)
from readable_interpretation.section_narrative_spec import (
    SECTION_NARRATIVE_IDS,
    SECTION_NARRATIVE_SPEC_VERSION,
)
from relationship_status_answer_policy import STAGE_ORDER
from test_reading_phase5_calibration import (
    MINIMUM_SCORE_AVERAGES,
    intra_page_repetition,
    score_pages,
    sentence_slot_repetition,
)
from test_reading_quality_engine import load_quality_contract


DEFAULT_CORPUS_PATH = DEFAULT_OUTPUT_DIR / "holdout-corpus.json"
DEFAULT_REVIEW_PATH = DEFAULT_OUTPUT_DIR / "review-manifest.json"
DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "36-final-narrative-phase7-calibration.md"
DEFAULT_QUALITY_CONTRACT_DIR = ROOT / "data" / "reading-quality-cases"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def section_semantic_identity(case: Mapping[str, Any], section_id: str) -> str:
    return stable_hash(compact_semantic_projection(case, section_id))


def section_output_identity(case: Mapping[str, Any], section_id: str) -> str:
    return stable_hash(((case.get("sections") or {}).get(section_id) or {}))


def changed_sections(left: Mapping[str, Any], right: Mapping[str, Any], identity: str) -> set[str]:
    identity_function = section_semantic_identity if identity == "semantic" else section_output_identity
    return {
        section_id
        for section_id in SECTION_NARRATIVE_IDS
        if identity_function(left, section_id) != identity_function(right, section_id)
    }


def role_value(case: Mapping[str, Any], section_id: str, role: str) -> str:
    section = (((case.get("finalFactContract") or {}).get("sections") or {}).get(section_id) or {})
    values = (section.get("roleValues") or {}).get(role) or []
    return str(next(iter(values), ""))


def distribution(case: Mapping[str, Any], key: str) -> list[str]:
    context = case.get("context") or {}
    hidden = case.get("hiddenModel") or {}
    if key == "archetype":
        return [str(hidden.get("archetypeTitle") or "")]
    if key == "primary":
        return [str(hidden.get("primaryDynamicKey") or "")]
    if key == "secondary":
        return [
            str(item.get("key") or "")
            for item in hidden.get("secondaryDynamics") or []
            if isinstance(item, dict) and item.get("key")
        ]
    if key == "timing":
        return [role_value(case, "timing-reading", "recommended-action")]
    if key == "repair":
        return [role_value(case, "action-direction", "repair-lever")]
    if key == "risk":
        return [str(context.get("emotional_risk") or "")]
    raise ValueError(f"unknown Phase 7 distribution: {key}")


def distribution_counts(cases: Iterable[Mapping[str, Any]], key: str) -> Counter[str]:
    return Counter(
        value
        for case in cases
        for value in distribution(case, key)
        if value
    )


def comparison_input_errors(left: Mapping[str, Any], right: Mapping[str, Any], axis: str) -> list[str]:
    errors: list[str] = []
    left_context = dict(left.get("context") or {})
    right_context = dict(right.get("context") or {})
    context_changes = {
        key
        for key in set(left_context) | set(right_context)
        if left_context.get(key) != right_context.get(key)
    }
    expected_context_changes = {
        "question": {"main_question", "desired_outcome"},
        "status": {"relationship_stage"},
        "contact": {"contact_status"},
        "risk": {"emotional_risk"},
        "chart": set(),
    }[axis]
    if context_changes != expected_context_changes:
        errors.append(f"context changes {sorted(context_changes)} != {sorted(expected_context_changes)}")
    left_chart = str((left.get("fingerprints") or {}).get("chart") or "")
    right_chart = str((right.get("fingerprints") or {}).get("chart") or "")
    left_pair = str((left.get("fingerprints") or {}).get("pair") or "")
    right_pair = str((right.get("fingerprints") or {}).get("pair") or "")
    chart_changed = left_chart != right_chart
    pair_changed = left_pair != right_pair
    if chart_changed != (axis == "chart") or pair_changed != (axis == "chart"):
        errors.append(f"chart/pair change mismatch: chart={chart_changed} pair={pair_changed}")
    left_precision = str((left.get("calibrationAxes") or {}).get("inputPrecision") or "")
    right_precision = str((right.get("calibrationAxes") or {}).get("inputPrecision") or "")
    if left_precision != right_precision:
        errors.append("input precision changed")
    return errors


def validate_case_contract(case: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    case_id = str(case.get("id") or "unknown")
    section_contract = case.get("sectionContracts") or {}
    if section_contract.get("version") != SECTION_NARRATIVE_SPEC_VERSION:
        errors.append(f"{case_id}: section spec version is stale")
    if section_contract.get("validationStatus") != "valid":
        errors.append(f"{case_id}: section spec is invalid")
    fact_contract = case.get("finalFactContract") or {}
    if fact_contract.get("version") != FINAL_NARRATIVE_FACT_CONTRACT_VERSION:
        errors.append(f"{case_id}: fact contract version is stale")
    if fact_contract.get("rendererMode") != FINAL_NARRATIVE_FACT_RENDERER_MODE:
        errors.append(f"{case_id}: final renderer is not fact-only")
    if fact_contract.get("semanticCoverageVersion") != FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION:
        errors.append(f"{case_id}: semantic coverage version is stale")
    if fact_contract.get("validationStatus") != "valid":
        errors.append(f"{case_id}: final fact contract is invalid")
    fact_sections = fact_contract.get("sections") or {}
    visible_sections = case.get("sections") or {}
    for section_id in SECTION_NARRATIVE_IDS:
        visible = visible_sections.get(section_id) or {}
        if not all(str(visible.get(field) or "").strip() for field in ("headline", "meaning", "body", "nextMove", "caution")):
            errors.append(f"{case_id}:{section_id}: visible fields are incomplete")
        fact_section = fact_sections.get(section_id) or {}
        roles = set((fact_section.get("roleValues") or {}).keys())
        expected_roles = set(FINAL_NARRATIVE_ROLE_DISPOSITIONS[section_id])
        if roles != expected_roles:
            errors.append(
                f"{case_id}:{section_id}: role set mismatch missing={sorted(expected_roles - roles)} extra={sorted(roles - expected_roles)}"
            )
        if fact_section.get("compatibilityProseSlots"):
            errors.append(f"{case_id}:{section_id}: legacy prose entered calibration")
    return errors


def evaluate(
    corpus: dict[str, Any],
    review_manifest: dict[str, Any],
    contract: dict[str, Any],
    quality_contract: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    matrix_cases = [case for case in corpus.get("matrixCases") or [] if isinstance(case, dict)]
    comparison_cases = [case for case in corpus.get("comparisonCases") or [] if isinstance(case, dict)]
    all_cases = {str(case.get("id") or ""): case for case in [*matrix_cases, *comparison_cases]}
    matrix_contract = contract.get("matrix") or {}
    comparison_contract = contract.get("controlledComparisons") or {}
    coverage_contract = contract.get("coverage") or {}
    review_contract = contract.get("humanReview") or {}

    if corpus.get("version") != CORPUS_VERSION:
        failures.append("Phase 7 corpus version is stale")
    if corpus.get("contractVersion") != contract.get("version"):
        failures.append("Phase 7 calibration contract version is stale")
    if corpus.get("composerVersion") != FINAL_NARRATIVE_COMPOSER_VERSION:
        failures.append("Phase 7 composer version is stale")
    if corpus.get("compositionVersion") != FINAL_NARRATIVE_COMPOSITION_VERSION:
        failures.append("Phase 7 composition version is stale")
    if corpus.get("paragraphPlanVersion") != FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION:
        failures.append("Phase 7 paragraph-plan version is stale")
    if corpus.get("semanticCoverageVersion") != FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION:
        failures.append("Phase 7 semantic coverage version is stale")
    if corpus.get("hardQualityVersion") != FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION:
        failures.append("Phase 7 R6 hard-quality version is stale")
    if corpus.get("hardQualityContractFingerprint") != hard_quality_contract_fingerprint():
        failures.append("Phase 7 R6 hard-quality fingerprint is stale")
    if corpus.get("runtimeSourceHashes") != runtime_source_hashes():
        failures.append("Phase 7 runtime source hashes are stale; rebuild the corpus")
    expected_count = int(matrix_contract.get("expectedCaseCount") or 0)
    if len(matrix_cases) != expected_count:
        failures.append(f"matrix count {len(matrix_cases)} != {expected_count}")
    expected_comparison_count = len(COMPARISON_AXES) * int(comparison_contract.get("casesPerAxis") or 0)
    if len(comparison_cases) != expected_comparison_count:
        failures.append(f"comparison count {len(comparison_cases)} != {expected_comparison_count}")

    expected_cells = set(itertools.product(STAGE_ORDER, QUESTIONS, CONTACTS, EMOTIONAL_RISKS))
    actual_cell_counts = Counter(
        (
            str((case.get("context") or {}).get("relationship_stage") or ""),
            str((case.get("context") or {}).get("main_question") or ""),
            str((case.get("context") or {}).get("contact_status") or ""),
            str((case.get("context") or {}).get("emotional_risk") or ""),
        )
        for case in matrix_cases
    )
    if set(actual_cell_counts) != expected_cells or any(count != 1 for count in actual_cell_counts.values()):
        failures.append("four-axis context matrix is incomplete or duplicated")

    precision_counts = Counter(str((case.get("calibrationAxes") or {}).get("inputPrecision") or "") for case in matrix_cases)
    expected_precision_count = expected_count // len(PRECISION_PROFILES)
    if set(precision_counts) != set(PRECISION_PROFILES) or any(count != expected_precision_count for count in precision_counts.values()):
        failures.append(f"precision profiles are unbalanced: {dict(precision_counts)}")
    split_counts = Counter(str(case.get("split") or "") for case in matrix_cases)
    if dict(split_counts) != {str(key): int(value) for key, value in (matrix_contract.get("splitCounts") or {}).items()}:
        failures.append(f"split counts do not match contract: {dict(split_counts)}")

    pair_ids = [str((case.get("fingerprints") or {}).get("pair") or "") for case in matrix_cases]
    chart_ids = [str((case.get("fingerprints") or {}).get("chart") or "") for case in matrix_cases]
    if len(set(pair_ids)) != len(matrix_cases) or len(set(chart_ids)) != len(matrix_cases):
        failures.append("matrix pairs or charts are not unique")
    charts_by_split = {
        split: {str((case.get("fingerprints") or {}).get("chart") or "") for case in matrix_cases if case.get("split") == split}
        for split in split_counts
    }
    for left, right in itertools.combinations(charts_by_split, 2):
        if charts_by_split[left] & charts_by_split[right]:
            failures.append(f"chart leakage between {left} and {right}")

    for case in [*matrix_cases, *comparison_cases]:
        failures.extend(validate_case_contract(case))

    observed_roles: dict[str, set[str]] = defaultdict(set)
    for case in matrix_cases:
        for section_id in SECTION_NARRATIVE_IDS:
            fact_section = (((case.get("finalFactContract") or {}).get("sections") or {}).get(section_id) or {})
            observed_roles[section_id].update((fact_section.get("roleValues") or {}).keys())
    for section_id in SECTION_NARRATIVE_IDS:
        if observed_roles[section_id] != set(FINAL_NARRATIVE_ROLE_DISPOSITIONS[section_id]):
            failures.append(f"{section_id}: not every registered role appears in the corpus")

    distribution_specs = (
        ("archetype", "minimumDistinctArchetypes", "minimumCasesPerArchetype", "maximumArchetypeCoverage"),
        ("primary", "minimumDistinctPrimaryDynamics", "minimumCasesPerPrimaryDynamic", "maximumPrimaryDynamicCoverage"),
        ("secondary", "minimumDistinctSecondaryDynamics", "minimumCasesPerSecondaryDynamic", None),
        ("timing", "minimumDistinctTimingActions", "minimumCasesPerTimingAction", "maximumTimingActionCoverage"),
        ("repair", "minimumDistinctRepairLevers", "minimumCasesPerRepairLever", "maximumRepairLeverCoverage"),
    )
    distributions: dict[str, dict[str, int]] = {}
    for key, distinct_key, minimum_key, maximum_key in distribution_specs:
        counts = distribution_counts(matrix_cases, key)
        distributions[key] = dict(sorted(counts.items()))
        if len(counts) < int(coverage_contract.get(distinct_key) or 0):
            failures.append(f"{key} distinct coverage is too thin: {len(counts)}")
        too_rare = {value: count for value, count in counts.items() if count < int(coverage_contract.get(minimum_key) or 0)}
        if too_rare:
            failures.append(f"{key} values below minimum coverage: {too_rare}")
        if maximum_key and counts:
            coverage = counts.most_common(1)[0][1] / max(1, len(matrix_cases))
            if coverage > float(coverage_contract.get(maximum_key) or 0):
                failures.append(f"{key} concentration {coverage:.3f} exceeds {coverage_contract.get(maximum_key)}")

    semantic_signature_counts = {
        section_id: len({section_semantic_identity(case, section_id) for case in matrix_cases})
        for section_id in SECTION_NARRATIVE_IDS
    }
    for section_id, minimum in (coverage_contract.get("minimumSemanticSignatures") or {}).items():
        if semantic_signature_counts.get(section_id, 0) < int(minimum):
            failures.append(
                f"{section_id} semantic signatures {semantic_signature_counts.get(section_id, 0)} below {minimum}"
            )

    comparison_results: list[dict[str, Any]] = []
    for comparison in corpus.get("controlledComparisons") or []:
        axis = str(comparison.get("type") or "")
        left = all_cases.get(str(comparison.get("leftId") or "")) or {}
        right = all_cases.get(str(comparison.get("rightId") or "")) or {}
        errors = [] if left and right and axis in COMPARISON_AXES else ["comparison endpoint or axis missing"]
        if not errors:
            errors.extend(comparison_input_errors(left, right, axis))
            semantic_changes = changed_sections(left, right, "semantic")
            output_changes = changed_sections(left, right, "output")
            required = set(comparison.get("requiredChangedSections") or [])
            allowed = set(comparison.get("allowedChangedSections") or [])
            if not required <= semantic_changes or not semantic_changes <= allowed:
                errors.append(f"semantic impact {sorted(semantic_changes)} outside required={sorted(required)} allowed={sorted(allowed)}")
            if not required <= output_changes or not output_changes <= allowed:
                errors.append(f"output impact {sorted(output_changes)} outside required={sorted(required)} allowed={sorted(allowed)}")
            if semantic_changes != output_changes:
                errors.append(
                    f"semantic/output impact mismatch semantic={sorted(semantic_changes)} output={sorted(output_changes)}"
                )
        if errors:
            failures.append(f"{comparison.get('id')}: {'; '.join(errors)}")
        comparison_results.append({"id": comparison.get("id"), "type": axis, "passed": not errors, "errors": errors})

    collapse = analyze_output_collapses([*matrix_cases, *comparison_cases])
    if collapse.get("unexplainedCollapses"):
        failures.append(f"unexplained section collapses: {len(collapse['unexplainedCollapses'])}")
    if collapse.get("fullReadingUnexplainedCollapses"):
        failures.append(f"unexplained full-reading collapses: {len(collapse['fullReadingUnexplainedCollapses'])}")

    split_scores: dict[str, Any] = {}
    for split in ("development", "automated-holdout"):
        cases = [case for case in matrix_cases if case.get("split") == split]
        scores, averages = score_pages(cases, quality_contract)
        split_scores[split] = averages
        for section_id, dimensions in averages.items():
            for dimension, minimum in MINIMUM_SCORE_AVERAGES.items():
                if float(dimensions.get(dimension) or 0) < minimum:
                    failures.append(f"{split}:{section_id}:{dimension} below {minimum}")
        if any(item.get("technicalHits") or item.get("readerMetaHits") or item.get("unsafeHits") or item.get("topicHits") for item in scores):
            failures.append(f"{split}: automated copy violations detected")
        if sentence_slot_repetition(cases, quality_contract):
            failures.append(f"{split}: sentence-slot repetition exceeds threshold")
        if intra_page_repetition(cases):
            failures.append(f"{split}: intra-page repetition detected")

    review_cases = [case for case in review_manifest.get("cases") or [] if isinstance(case, dict)]
    review_ids = [str(case.get("id") or "") for case in review_cases]
    matrix_by_id = {str(case.get("id") or ""): case for case in matrix_cases}
    if review_manifest.get("version") != REVIEW_VERSION:
        failures.append("Phase 7 review version is stale")
    if review_manifest.get("corpusFingerprint") != corpus.get("corpusFingerprint"):
        failures.append("Phase 7 review manifest is stale")
    if review_manifest.get("compositionVersion") != FINAL_NARRATIVE_COMPOSITION_VERSION:
        failures.append("Phase 7 review composition version is stale")
    if review_manifest.get("paragraphPlanVersion") != FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION:
        failures.append("Phase 7 review paragraph-plan version is stale")
    if review_manifest.get("hardQualityVersion") != FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION:
        failures.append("Phase 7 review R6 hard-quality version is stale")
    if review_manifest.get("hardQualityContractFingerprint") != hard_quality_contract_fingerprint():
        failures.append("Phase 7 review R6 hard-quality fingerprint is stale")
    if len(review_cases) != int(review_contract.get("selectedCaseCount") or 0) or len(set(review_ids)) != len(review_ids):
        failures.append("Phase 7 review selection count or uniqueness is invalid")
    selected_records = [matrix_by_id[case_id] for case_id in review_ids if case_id in matrix_by_id]
    if len(selected_records) != len(review_cases) or any(case.get("split") == "automated-holdout" for case in selected_records):
        failures.append("review queue contains unknown or automated-holdout cases")
    if review_manifest.get("dimensions") != review_contract.get("dimensions"):
        failures.append("review dimensions do not match the Phase 7 contract")
    matrix_coverage = review_coverage(matrix_cases)
    selected_coverage = review_coverage(selected_records)
    for group, values in matrix_coverage.items():
        missing = set(values) - set(selected_coverage.get(group) or [])
        if missing:
            failures.append(f"review queue misses {group}: {sorted(missing)}")
    if review_manifest.get("coverage") != selected_coverage:
        failures.append("review manifest coverage summary is stale")

    return {
        "passed": not failures,
        "failures": failures,
        "matrixCaseCount": len(matrix_cases),
        "comparisonCaseCount": len(comparison_cases),
        "splitCounts": dict(sorted(split_counts.items())),
        "precisionCounts": dict(sorted(precision_counts.items())),
        "contextCellCount": len(actual_cell_counts),
        "distributionCounts": distributions,
        "semanticSignatureCounts": semantic_signature_counts,
        "comparisonCounts": dict(Counter(item["type"] for item in comparison_results if item["passed"])),
        "comparisonFailureCount": sum(1 for item in comparison_results if not item["passed"]),
        "unexplainedCollapseCount": len(collapse.get("unexplainedCollapses") or []),
        "fullReadingCollapseCount": len(collapse.get("fullReadingUnexplainedCollapses") or []),
        "explicitUnknownFactCount": sum(
            len(
                (((case.get("finalFactContract") or {}).get("sections") or {}).get(section_id) or {}).get("unknownFactIds")
                or []
            )
            for case in matrix_cases
            for section_id in SECTION_NARRATIVE_IDS
        ),
        "splitScoreAverages": split_scores,
        "reviewCaseCount": len(review_cases),
        "reviewRequiredAcceptedCount": int(review_manifest.get("requiredAcceptedCount") or 0),
        "reviewCoverage": selected_coverage,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |" for row in rows),
    ]


def render_report(result: Mapping[str, Any], corpus: Mapping[str, Any]) -> str:
    score_rows: list[list[Any]] = []
    for split, sections in (result.get("splitScoreAverages") or {}).items():
        for section_id, dimensions in sections.items():
            score_rows.append(
                [
                    split,
                    section_id,
                    *[f"{float(dimensions.get(key) or 0):.2f}" for key in ("readability", "specificity", "relevance", "emotionalSafety", "topicOwnership", "differentiation")],
                ]
            )
    distribution_rows = [
        [group, value, count]
        for group, counts in (result.get("distributionCounts") or {}).items()
        for value, count in counts.items()
    ]
    lines = [
        "# Final Narrative Phase 7 Calibration Corpus",
        "",
        "## Verdict",
        "",
        f"- Phase 7 rebuilt calibration corpus: **{'PASS' if result.get('passed') else 'FAIL'}**",
        f"- Corpus: `{corpus.get('version')}`",
        f"- Four-axis matrix cases: {result.get('matrixCaseCount')}",
        f"- Controlled one-input variants: {result.get('comparisonCaseCount')}",
        f"- Complete status/question/contact/risk cells: {result.get('contextCellCount')}",
        f"- Unexplained section collapses: {result.get('unexplainedCollapseCount')}",
        f"- Unexplained full-reading collapses: {result.get('fullReadingCollapseCount')}",
        f"- Explicit data-limit facts retained: {result.get('explicitUnknownFactCount')}",
        "",
        "## Isolated Splits",
        "",
        *markdown_table(["Split", "Cases"], [[key, value] for key, value in (result.get("splitCounts") or {}).items()]),
        "",
        "Every matrix case uses a unique synthetic pair and chart. Development, automated holdout, and human-review",
        "candidate charts are disjoint, so copy tuning cannot silently reuse the automated holdout inputs.",
        "",
        "## Input Coverage",
        "",
        *markdown_table(["Birth-time precision", "Cases"], [[key, value] for key, value in (result.get("precisionCounts") or {}).items()]),
        "",
        "The matrix contains every supported status, question, contact, and emotional-risk combination exactly once.",
        "Birth-time precision is balanced independently across four known/unknown-time profiles.",
        "",
        "## Semantic Distribution",
        "",
        *markdown_table(["Family", "Value", "Cases"], distribution_rows),
        "",
        *markdown_table(
            ["Page", "Distinct role + concept signatures"],
            [[key, value] for key, value in (result.get("semanticSignatureCounts") or {}).items()],
        ),
        "",
        "## Controlled Comparisons",
        "",
        *markdown_table(["Input changed", "Passing pairs"], [[key, value] for key, value in (result.get("comparisonCounts") or {}).items()]),
        "",
        f"- Comparison failures: {result.get('comparisonFailureCount')}",
        "- Each pair changes one logical input axis and enforces required and allowed page impacts.",
        "- Semantic and visible-output page impacts must match.",
        "",
        "## Automated Split Scores",
        "",
        *markdown_table(
            ["Split", "Page", "Readability", "Specificity", "Relevance", "Safety", "Ownership", "Differentiation"],
            score_rows,
        ),
        "",
        "## Human Review Queue",
        "",
        f"- Coverage-driven cases: {result.get('reviewCaseCount')}",
        f"- Required accepted in Phase 8: {result.get('reviewRequiredAcceptedCount')}",
        "- Dimensions: 易讀程度、星盤具體度、頁面主題聚焦",
        "- Automated-holdout cases in review queue: 0",
        "- The queue covers every semantic family observed in the eligible development/review pool.",
        "",
        "## Failures",
        "",
        *([f"- {failure}" for failure in result.get("failures") or []] or ["- None."]),
        "",
        "Phase 8 human acceptance remains pending. Automated calibration does not create human scores.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_PATH)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--quality-contract-dir", type=Path, default=DEFAULT_QUALITY_CONTRACT_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = evaluate(
        load_json(args.corpus),
        load_json(args.review_manifest),
        load_json(args.contract),
        load_quality_contract(args.quality_contract_dir),
    )
    if not args.no_write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_report(result, load_json(args.corpus)), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Phase 7 calibration: {'PASS' if result['passed'] else 'FAIL'}")
        print(f"- matrix cases: {result['matrixCaseCount']}")
        print(f"- controlled comparisons: {result['comparisonCaseCount']}")
        print(f"- review cases: {result['reviewCaseCount']}")
        print(f"- unexplained collapses: {result['unexplainedCollapseCount']}")
        for failure in result.get("failures") or []:
            print(f"- {failure}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
