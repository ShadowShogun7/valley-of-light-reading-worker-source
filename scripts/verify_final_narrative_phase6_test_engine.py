#!/usr/bin/env python3
"""Verify meaning, personalization, and invariants in the final narrative layer."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_reading_phase7_calibration import CORPUS_VERSION  # noqa: E402
from build_reading_production_baseline import (  # noqa: E402
    ANALYSIS_DATE,
    DESIRED_OUTCOMES,
    build_runtime_case,
    deterministic_pairs,
    reading_for_pair,
)
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    load_articles,
    load_claims_by_article,
)
from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FinalNarrativeComposer,
    FinalNarrativeSemanticInput,
    SectionNarrativeSpecError,
)
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    SECTION_COMPOSITION_RULES,
    FinalNarrativeCompositionError,
    composition_contract_errors,
    validate_reading_composition,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    FINAL_NARRATIVE_FACT_POLICIES,
)
from readable_interpretation.final_narrative_page_grammar import (  # noqa: E402
    FinalNarrativePageGrammarError,
    validate_page_grammar,
)
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    semantic_policy_alignment_errors,
)
from readable_interpretation.final_narrative_test_engine import (  # noqa: E402
    CONTEXT_ROLES,
    FINAL_NARRATIVE_CANONICAL_RECORD_VERSION,
    FINAL_NARRATIVE_TEST_ENGINE_VERSION,
    analyze_output_collapses,
    build_canonical_record,
    changed_sections,
    compact_semantic_projection,
    stable_hash,
    validate_canonical_record,
)
from readable_interpretation.section_narrative_spec import SECTION_NARRATIVE_IDS  # noqa: E402
from structured_runtime import load_structured_kb  # noqa: E402
from verify_final_narrative_phase4_semantic_coverage import (  # noqa: E402
    exhaustive_value_domain_check,
    render_synthetic,
)


DEFAULT_CANONICAL_PATH = ROOT / "data" / "reading-test-engine" / "v1" / "canonical-record.json"
DEFAULT_CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"
DEFAULT_REGRESSION_PATH = ROOT / "data" / "reading-quality-cases" / "final-narrative-phase6-regressions.json"
DEFAULT_FEEDBACK_PATH = ROOT / "data" / "reading-human-feedback" / "phase5-review-v2-regressions.json"
DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "35-final-narrative-phase6-test-engine.md"

METAMORPHIC_POLICIES = {
    "question": {"changedSections": {"core-answer", "timing-reading", "action-direction"}},
    "status": {"changedSections": {"core-answer"}},
    "contact": {"changedSections": {"core-answer", "timing-reading", "action-direction"}},
    "unsafe-risk": {"changedSections": {"action-direction"}},
    "chart": {
        "changedSections": {"chart-positioning", "relationship-fit", "core-answer", "timing-reading"},
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def context(
    *,
    stage: str = "cold-war",
    question: str = "still-love-me",
    contact: str = "no-contact",
    emotional_risk: str = "calm",
) -> dict[str, Any]:
    return {
        "relationship_stage": stage,
        "main_question": question,
        "contact_status": contact,
        "desired_outcome": DESIRED_OUTCOMES[question],
        "emotional_risk": emotional_risk,
        "analysis_date": ANALYSIS_DATE,
        "timing_scan_days": 56,
        "timing_scan_step_days": 7,
    }


def build_runtime_records() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    pairs = deterministic_pairs(80)
    cases = {
        "base": (pairs[0], context()),
        "question": (pairs[0], context(question="what-did-i-do-wrong")),
        "status": (pairs[0], context(stage="broke-up-long")),
        "contact": (pairs[0], context(contact="blocked")),
        "unsafe-risk": (pairs[0], context(emotional_risk="desperate")),
        "chart": (pairs[37], context()),
    }
    records: dict[str, dict[str, Any]] = {}
    view_models: dict[str, dict[str, Any]] = {}
    for axis, (pair, case_context) in cases.items():
        reading = reading_for_pair(
            reading_id="phase6-canonical-base" if axis == "base" else f"phase6-metamorphic-{axis}",
            pair=pair,
            context=case_context,
            mix_unknown_times=False,
            record_index=0,
        )
        calculation_payload, view_model = build_runtime_case(
            reading,
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        )
        records[axis] = build_canonical_record(reading, calculation_payload, view_model)
        view_models[axis] = view_model
    return records, view_models


def fact_role_values(record: Mapping[str, Any], section_id: str) -> dict[str, list[str]]:
    section = ((((record.get("facts") or {}).get("sections") or {}).get(section_id)) or {})
    output: dict[str, list[str]] = {}
    for fact in section.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        role = str(fact.get("role") or "")
        value = str(fact.get("valueKey") or "")
        if role and value:
            output.setdefault(role, []).append(value)
    return {role: sorted(set(values)) for role, values in output.items()}


def fact_value(record: Mapping[str, Any], identity: str) -> str:
    section_id, role = identity.split(".", 1)
    return next(iter(fact_role_values(record, section_id).get(role) or []), "")


def assert_metamorphic_behavior(records: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    base = records["base"]
    results: list[dict[str, Any]] = []
    base_chart = str((base.get("fingerprints") or {}).get("chart") or "")
    for axis, policy in METAMORPHIC_POLICIES.items():
        variant = records[axis]
        expected = set(policy["changedSections"])
        fact_changes = changed_sections(base, variant, "facts")
        projection_changes = changed_sections(base, variant, "roleProjection")
        output_changes = changed_sections(base, variant, "output")
        require(fact_changes == expected, f"{axis}: fact impact mismatch: {sorted(fact_changes)}")
        require(projection_changes == expected, f"{axis}: meaning impact mismatch: {sorted(projection_changes)}")
        require(output_changes == expected, f"{axis}: output impact mismatch: {sorted(output_changes)}")
        require(fact_changes == output_changes, f"{axis}: fact changes collapsed or leaked into output")
        chart_changed = base_chart != str((variant.get("fingerprints") or {}).get("chart") or "")
        require(chart_changed is (axis == "chart"), f"{axis}: chart fingerprint changed unexpectedly")
        results.append(
            {
                "axis": axis,
                "changedSections": sorted(output_changes),
                "chartChanged": chart_changed,
            }
        )

    chart_variant = records["chart"]
    for section_id in SECTION_NARRATIVE_IDS:
        base_roles = fact_role_values(base, section_id)
        variant_roles = fact_role_values(chart_variant, section_id)
        for role in CONTEXT_ROLES & (set(base_roles) | set(variant_roles)):
            require(
                base_roles.get(role) == variant_roles.get(role),
                f"chart: changed context-owned role {section_id}:{role}",
            )
    return results


def assert_boundary_behavior(
    records: Mapping[str, dict[str, Any]],
    regression: Mapping[str, Any],
) -> dict[str, int]:
    blocked = records["contact"]
    blocked_contract = regression.get("blockedContact") or {}
    for identity, expected in (blocked_contract.get("requiredFactValues") or {}).items():
        require(fact_value(blocked, identity) == expected, f"blocked boundary fact mismatch: {identity}")
    blocked_sections = (blocked.get("outputs") or {}).get("sections") or {}
    blocked_text = "".join(
        str(value)
        for section_id in ("timing-reading", "action-direction")
        for value in (blocked_sections.get(section_id) or {}).values()
    )
    required_markers = [str(value) for value in blocked_contract.get("requiredVisibleMarkers") or []]
    require(any(marker in blocked_text for marker in required_markers), "blocked boundary is not reader-visible")
    forbidden_prompts = [
        marker
        for marker in blocked_contract.get("forbiddenVisiblePrompts") or []
        if str(marker) in blocked_text
    ]
    require(not forbidden_prompts, f"blocked result prompts contact: {forbidden_prompts}")

    unsafe = records["unsafe-risk"]
    for identity, expected in ((regression.get("unsafeEmotionalRisk") or {}).get("requiredFactValues") or {}).items():
        require(fact_value(unsafe, identity) == expected, f"unsafe-risk boundary fact mismatch: {identity}")
    return {
        "blockedFacts": len(blocked_contract.get("requiredFactValues") or {}),
        "blockedForbiddenPrompts": len(forbidden_prompts),
        "unsafeFacts": len((regression.get("unsafeEmotionalRisk") or {}).get("requiredFactValues") or {}),
    }


def semantic_input(view_model: Mapping[str, Any], bundle: dict[str, Any]) -> FinalNarrativeSemanticInput:
    context_value = view_model.get("context") if isinstance(view_model.get("context"), dict) else {}
    return FinalNarrativeSemanticInput(
        question_key=str(context_value.get("main_question") or ""),
        stage_key=str(context_value.get("relationship_stage") or ""),
        contact_key=str(context_value.get("contact_status") or ""),
        section_specs=bundle,
        fact_contract=bundle.get("finalNarrativeFacts"),
    )


def expect_rejected(identity: str, operation: Callable[[], Any]) -> None:
    try:
        operation()
    except (
        FinalNarrativeCompositionError,
        FinalNarrativePageGrammarError,
        FinalNarrativeSemanticCoverageError,
        SectionNarrativeSpecError,
    ):
        return
    raise AssertionError(f"deliberate invalid case was accepted: {identity}")


def assert_invalid_cases(
    base_record: Mapping[str, Any],
    base_view_model: Mapping[str, Any],
) -> int:
    invalid_count = 0

    stale_record = copy.deepcopy(base_record)
    stale_record["outputs"]["sections"]["core-answer"]["headline"] += " stale"
    require(validate_canonical_record(stale_record), "stale canonical fingerprint was accepted")
    invalid_count += 1

    def invalid_bundle(mutation: str) -> None:
        bundle = copy.deepcopy(base_view_model.get("sectionNarrativeSpecs") or {})
        contract = bundle["finalNarrativeFacts"]
        if mutation == "stale-source":
            bundle["sections"]["chart-positioning"]["semanticSlots"]["personAEmotionalNeed"] = "changed"
        elif mutation == "unowned-evidence":
            contract["sections"]["timing-reading"]["facts"][0]["evidenceIds"] = ["E-not-owned"]
        elif mutation == "unowned-role":
            contract["sections"]["core-answer"]["facts"][0]["role"] = "relationship-archetype"
        elif mutation == "missing-role":
            section = contract["sections"]["core-answer"]
            removed = section["facts"].pop(0)
            section["selectedFactIds"] = [
                value for value in section["selectedFactIds"] if value != removed["id"]
            ]
        elif mutation == "facts-optional":
            contract["factsRequired"] = False
        elif mutation == "specs-optional":
            bundle["rendererConsumesSpecs"] = False
        else:
            raise AssertionError(f"unknown invalid mutation: {mutation}")
        FinalNarrativeComposer.from_semantic_input(semantic_input(base_view_model, bundle))

    for mutation in (
        "stale-source",
        "unowned-evidence",
        "unowned-role",
        "missing-role",
        "facts-optional",
        "specs-optional",
    ):
        expect_rejected(mutation, lambda mutation=mutation: invalid_bundle(mutation))
        invalid_count += 1

    chart_roles = fact_role_values(base_record, "chart-positioning")
    unsupported = {role: list(values) for role, values in chart_roles.items()}
    unsupported["user-emotional-need"] = ["moon.unsupported"]
    expect_rejected(
        "unsupported-value",
        lambda: render_synthetic("chart-positioning", unsupported),
    )
    invalid_count += 1

    bundle = base_view_model.get("sectionNarrativeSpecs") or {}
    composer = FinalNarrativeComposer.from_semantic_input(
        semantic_input(base_view_model, copy.deepcopy(bundle))
    )
    incomplete_reader = SectionFactReader(contract=composer.facts, section_id="core-answer")
    incomplete_reader.first("question", required=True)
    expect_rejected("unconsumed-semantic-roles", incomplete_reader.assert_complete)
    invalid_count += 1

    weakened_dispositions = copy.deepcopy(FINAL_NARRATIVE_ROLE_DISPOSITIONS)
    weakened_dispositions["action-direction"].pop("blocked-action")
    require(
        composition_contract_errors(SECTION_COMPOSITION_RULES, weakened_dispositions),
        "Phase 3 role coverage could be weakened without detection",
    )
    invalid_count += 1

    weakened_rules = dict(SECTION_COMPOSITION_RULES)
    action_rule = weakened_rules["action-direction"]
    role_owners = dict(action_rule.role_owners)
    role_owners.pop("completion-boundary")
    weakened_rules["action-direction"] = replace(action_rule, role_owners=role_owners)
    require(
        composition_contract_errors(weakened_rules, FINAL_NARRATIVE_ROLE_DISPOSITIONS),
        "Phase 5 ownership could be weakened without detection",
    )
    invalid_count += 1

    weakened_policies = copy.deepcopy(FINAL_NARRATIVE_FACT_POLICIES)
    weakened_policies["relationship-fit"]["allowedRoles"] = tuple(
        role
        for role in weakened_policies["relationship-fit"]["allowedRoles"]
        if role != "growth-signal"
    )
    require(
        semantic_policy_alignment_errors(weakened_policies),
        "Phase 2 fact ownership could be weakened without detection",
    )
    invalid_count += 1

    invalid_page = copy.deepcopy((base_record.get("outputs") or {}).get("sections") or {})
    invalid_page["action-direction"]["headline"] = "高吸引高摩擦型：下一步"
    expect_rejected(
        "page-grammar-leak",
        lambda: validate_page_grammar("action-direction", invalid_page["action-direction"]),
    )
    invalid_count += 1

    invalid_reading = copy.deepcopy((base_record.get("outputs") or {}).get("sections") or {})
    invalid_reading["action-direction"]["caution"] = invalid_reading["core-answer"]["caution"]
    expect_rejected("cross-page-copy", lambda: validate_reading_composition(invalid_reading))
    invalid_count += 1
    return invalid_count


def assert_complaint_regressions(
    cases: list[Mapping[str, Any]],
    regression: Mapping[str, Any],
    feedback: Mapping[str, Any],
) -> dict[str, Any]:
    forbidden = [
        *[str(value) for value in feedback.get("forbiddenExactPhrases") or []],
        *[str(value) for value in regression.get("forbiddenPhrases") or []],
        *[str(value) for value in regression.get("readerMetaFragments") or []],
    ]
    failures: list[str] = []
    semantic_pages: dict[str, str] = {}
    for case in cases:
        case_id = str(case.get("id") or "")
        sections = case.get("sections") if isinstance(case.get("sections"), dict) else {}
        for section_id, section in sections.items():
            text = "".join(str(value) for value in (section or {}).values())
            for phrase in forbidden:
                if phrase and phrase in text:
                    failures.append(f"{case_id}:{section_id}: complaint phrase returned: {phrase}")
            semantic_identity = stable_hash(compact_semantic_projection(case, section_id))
            semantic_pages[f"{section_id}:{semantic_identity}"] = text

    family_results: list[dict[str, Any]] = []
    advice_families = [
        {
            "id": "phase5-overused-advice",
            "markers": feedback.get("overusedAdviceMarkers") or [],
            "maximumDistinctSemanticCoverage": feedback.get("maximumAdviceFamilyCoverage") or 0.45,
        },
        *[item for item in regression.get("adviceFamilies") or [] if isinstance(item, dict)],
    ]
    for family in advice_families:
        markers = [str(value) for value in family.get("markers") or []]
        matching = {
            identity
            for identity, text in semantic_pages.items()
            if any(marker and marker in text for marker in markers)
        }
        coverage = len(matching) / max(1, len(semantic_pages))
        maximum = float(family.get("maximumDistinctSemanticCoverage") or 0)
        if coverage > maximum:
            failures.append(
                f"advice family {family.get('id')} covers {coverage:.3f}; maximum {maximum:.3f}"
            )
        family_results.append(
            {
                "id": str(family.get("id") or ""),
                "coverage": round(coverage, 3),
                "maximum": maximum,
            }
        )
    require(not failures, "reader complaint regressions failed: " + "; ".join(failures[:12]))
    return {
        "forbiddenPhraseCount": len(set(forbidden)),
        "semanticPageCount": len(semantic_pages),
        "adviceFamilies": family_results,
    }


def evaluate(
    *,
    records: Mapping[str, dict[str, Any]],
    view_models: Mapping[str, dict[str, Any]],
    canonical: Mapping[str, Any],
    corpus: Mapping[str, Any],
    regression: Mapping[str, Any],
    feedback: Mapping[str, Any],
) -> dict[str, Any]:
    base = records["base"]
    require(not validate_canonical_record(base), f"current canonical record is invalid: {validate_canonical_record(base)}")
    require(not validate_canonical_record(canonical), f"stored canonical record is invalid: {validate_canonical_record(canonical)}")
    require(stable_hash(base) == stable_hash(canonical), "stored canonical record is stale; run with --update-canonical")
    require(corpus.get("version") == CORPUS_VERSION, "Phase 6 holdout corpus is stale")
    require(
        regression.get("version") == "final-narrative-phase6-regressions-v1",
        "Phase 6 regression contract is stale",
    )

    metamorphic = assert_metamorphic_behavior(records)
    boundary = assert_boundary_behavior(records, regression)
    invalid_count = assert_invalid_cases(base, view_models["base"])

    exhaustive = exhaustive_value_domain_check()
    registered_role_count = sum(len(roles) for roles in FINAL_NARRATIVE_ROLE_DISPOSITIONS.values())
    require(
        exhaustive.get("testedRoleCount") == registered_role_count,
        "not every registered semantic role has exhaustive value coverage",
    )
    require(exhaustive.get("knownFallbackCount") == 0, "known supported values use fallback copy")

    cases = [
        item
        for item in [*(corpus.get("matrixCases") or []), *(corpus.get("comparisonCases") or [])]
        if isinstance(item, dict)
    ]
    for case in cases:
        contracts = ((case.get("sectionContracts") or {}).get("sections") or {})
        for section_id in SECTION_NARRATIVE_IDS:
            section = contracts.get(section_id) or {}
            require(section.get("conceptKeys"), f"{case.get('id')}:{section_id}: concept keys missing")
            require(
                section.get("evidenceConceptKeys"),
                f"{case.get('id')}:{section_id}: evidence concept keys missing",
            )
    collapse = analyze_output_collapses(cases)
    require(not collapse["unexplainedCollapses"], f"unexplained section collapse: {collapse['unexplainedCollapses'][:3]}")
    require(
        not collapse["fullReadingUnexplainedCollapses"],
        f"unexplained full-reading collapse: {collapse['fullReadingUnexplainedCollapses'][:3]}",
    )
    complaints = assert_complaint_regressions(cases, regression, feedback)

    return {
        "passed": True,
        "testEngineVersion": FINAL_NARRATIVE_TEST_ENGINE_VERSION,
        "canonicalRecordVersion": FINAL_NARRATIVE_CANONICAL_RECORD_VERSION,
        "canonicalFingerprint": stable_hash(canonical),
        "metamorphicComparisons": metamorphic,
        "boundary": boundary,
        "deliberateInvalidCasesRejected": invalid_count,
        "registeredRoleCount": registered_role_count,
        "testedRoleCount": exhaustive["testedRoleCount"],
        "testedValueCount": exhaustive["testedValueCount"],
        "knownValueRenderCount": exhaustive["knownRenderCount"],
        "holdoutCaseCount": collapse["caseCount"],
        "uniqueRoleConceptSignatures": collapse["uniqueRoleConceptSignatures"],
        "explainedCollapseCount": len(collapse["explainedCollapses"]),
        "unexplainedCollapseCount": len(collapse["unexplainedCollapses"]),
        "fullReadingUnexplainedCollapseCount": len(collapse["fullReadingUnexplainedCollapses"]),
        "complaints": complaints,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |" for row in rows),
    ]


def render_report(result: Mapping[str, Any]) -> str:
    metamorphic_rows = [
        [item["axis"], ", ".join(item["changedSections"]), "yes" if item["chartChanged"] else "no"]
        for item in result.get("metamorphicComparisons") or []
    ]
    signature_rows = [
        [section_id, count]
        for section_id, count in (result.get("uniqueRoleConceptSignatures") or {}).items()
    ]
    advice_rows = [
        [item["id"], f"{float(item['coverage']):.3f}", f"{float(item['maximum']):.3f}"]
        for item in (result.get("complaints") or {}).get("adviceFamilies") or []
    ]
    lines = [
        "# Final Narrative Phase 6 Test Engine",
        "",
        "## Verdict",
        "",
        "- Phase 6 upgraded semantic test engine: **PASS**",
        f"- Engine: `{result.get('testEngineVersion')}`",
        f"- Canonical record: `{result.get('canonicalRecordVersion')}`",
        f"- Holdout cases: {result.get('holdoutCaseCount')}",
        f"- Deliberate invalid cases rejected: {result.get('deliberateInvalidCasesRejected')}",
        f"- Registered semantic roles tested: {result.get('testedRoleCount')} / {result.get('registeredRoleCount')}",
        f"- Supported role values tested: {result.get('testedValueCount')}",
        f"- Known-value renders without fallback: {result.get('knownValueRenderCount')}",
        f"- Unexplained section collapses: {result.get('unexplainedCollapseCount')}",
        f"- Unexplained full-reading collapses: {result.get('fullReadingUnexplainedCollapseCount')}",
        "",
        "## Canonical Record",
        "",
        "The canonical test record contains the complete user inputs, chart and section evidence, typed facts,",
        "role/concept fingerprints, and all five reader-facing outputs. Its fingerprints are recomputed on every",
        "run, so stale evidence, facts, contract registries, or visible output fail before quality scoring.",
        "",
        "## Metamorphic Tests",
        "",
        *markdown_table(["Changed input", "Pages whose meaning and output changed", "Chart changed"], metamorphic_rows),
        "",
        "Each comparison changes one user input axis. Every changed fact projection must produce a changed output,",
        "and every stable fact projection must keep its page stable. Chart changes also prove that question, status,",
        "and contact roles remain unchanged.",
        "",
        "## Semantic Collapse",
        "",
        *markdown_table(["Page", "Unique role + concept signatures"], signature_rows),
        "",
        f"- Explicitly explained raw-evidence equivalences: {result.get('explainedCollapseCount')}",
        "- An output collision is allowed only when raw evidence differences map to the same declared role-and-concept projection.",
        "- Different visible-role projections may not collapse into one page or one full reading.",
        "",
        "## Reader Complaints",
        "",
        f"- Permanent forbidden complaint phrases: {(result.get('complaints') or {}).get('forbiddenPhraseCount')}",
        f"- Distinct semantic pages checked: {(result.get('complaints') or {}).get('semanticPageCount')}",
        *markdown_table(["Advice family", "Coverage", "Maximum"], advice_rows),
        "",
        "Blocked contact must produce boundary-first timing and action facts and may not prompt a new message.",
        "Unsafe emotional risk must switch the action stopping condition to stability-first.",
        "",
        "## Exit Gate",
        "",
        "- All page-ownership invariants pass.",
        "- All deliberate invalid cases fail.",
        "- Every registered role and supported value has an executable test path.",
        "- No unexplained output collapse exists in the holdout corpus.",
        "- Phase 2-5 boundaries reject deliberate weakening mutations.",
        "",
        "Phase 7 corpus calibration is verified separately. Phase 8 human acceptance remains pending.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, default=DEFAULT_CANONICAL_PATH)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--regressions", type=Path, default=DEFAULT_REGRESSION_PATH)
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK_PATH)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--update-canonical", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        records, view_models = build_runtime_records()
        if args.update_canonical:
            write_json(args.canonical, records["base"])
        require(args.canonical.exists(), "canonical record is missing; run with --update-canonical")
        result = evaluate(
            records=records,
            view_models=view_models,
            canonical=read_json(args.canonical),
            corpus=read_json(args.corpus),
            regression=read_json(args.regressions),
            feedback=read_json(args.feedback),
        )
    except (
        AssertionError,
        FinalNarrativeCompositionError,
        FinalNarrativePageGrammarError,
        FinalNarrativeSemanticCoverageError,
        SectionNarrativeSpecError,
    ) as exc:
        if args.json:
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Final narrative Phase 6 test engine failed: {exc}")
        return 1

    report = render_report(result)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print("Final narrative Phase 6 test engine passed")
        print(f"- metamorphic comparisons: {len(result['metamorphicComparisons'])}")
        print(f"- deliberate invalid cases rejected: {result['deliberateInvalidCasesRejected']}")
        print(f"- semantic roles tested: {result['testedRoleCount']}/{result['registeredRoleCount']}")
        print(f"- supported values tested: {result['testedValueCount']}")
        print(f"- holdout cases: {result['holdoutCaseCount']}")
        print(f"- unexplained output collapses: {result['unexplainedCollapseCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
