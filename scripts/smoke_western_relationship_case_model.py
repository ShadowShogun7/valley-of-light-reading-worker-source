#!/usr/bin/env python3
"""Smoke-test the hidden RelationshipCaseModel interpretation layer."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from visible_reading_depth import build_view_models  # noqa: E402
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    relationship_fit_sentence_trace,
)
from readable_interpretation.final_narrative_story_arc import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
)
from readable_interpretation.section_narrative_spec import canonical_value_key  # noqa: E402


SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"

SECTION_IDS = {
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
}

PRIMARY_DYNAMICS = {
    "emotional_safety",
    "saturn_pressure",
    "communication_repair",
    "attraction_pursuit",
    "action_conflict",
    "identity_rhythm",
    "outer_intensity",
}

SECONDARY_ROLES = {"amplifier", "blocker", "repairLever", "softener", "timingActivator"}

REQUIRED_GRAMMAR_PAIRS = {
    ("saturn_pressure", "attraction_pursuit"),
    ("action_conflict", "attraction_pursuit"),
    ("emotional_safety", "attraction_pursuit"),
    ("attraction_pursuit", "action_conflict"),
    ("identity_rhythm", "emotional_safety"),
    ("communication_repair", "saturn_pressure"),
    ("communication_repair", "action_conflict"),
    ("emotional_safety", "saturn_pressure"),
    ("action_conflict", "communication_repair"),
    ("outer_intensity", "saturn_pressure"),
}

DYNAMIC_INTERACTION_PLAN_FIELDS = {
    "dynamicInteraction",
    "whatThisMeans",
    "whatItDoesNotMean",
    "repairImplication",
    "actionBoundary",
    "timingModifier",
    "contactModifier",
}

FIT_NARRATIVE_MARKERS = (
    "相處",
    "吸引",
    "火花",
    "好感",
    "靠近",
    "摩擦",
    "磨合",
    "衝突",
    "調整",
)

CASE_TRACE_FIELDS = {
    "version",
    "caseModelVersion",
    "sectionId",
    "primaryDynamicKey",
    "secondaryDynamicKey",
    "secondaryRole",
    "grammarId",
    "grammarMode",
    "caseEvidenceIds",
}

CASE_TRACE_SECTION_IDS = {"core-answer", "timing-reading", "action-direction"}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def final_text(view_model: dict[str, Any]) -> str:
    final = view_model.get("finalInterpretation") or {}
    pieces: list[str] = []
    for section in (final.get("sections") or {}).values():
        if not isinstance(section, dict):
            continue
        for field in ("headline", "meaning", "body", "nextMove", "caution"):
            if section.get(field):
                pieces.append(str(section.get(field) or ""))
    return "\n".join(pieces)


def facts_for(view_model: dict[str, Any], section_id: str, role: str) -> list[dict[str, Any]]:
    bundle = view_model.get("sectionNarrativeSpecs") or {}
    fact_contract = bundle.get("finalNarrativeFacts") if isinstance(bundle.get("finalNarrativeFacts"), dict) else {}
    sections = fact_contract.get("sections") if isinstance(fact_contract.get("sections"), dict) else {}
    section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else {}
    return [
        item
        for item in section.get("facts") or []
        if isinstance(item, dict) and item.get("role") == role
    ]


def model_from_view_model(view_model: dict[str, Any]) -> dict[str, Any]:
    label = str(view_model.get("id") or "unknown")
    model = view_model.get("relationshipCaseModel") or {}
    case_file_model = ((view_model.get("westernRelationshipCaseFile") or {}).get("relationshipCaseModel") or {})
    assert_true(model.get("version") == "relationship-case-model-v1", f"{label}: relationshipCaseModel missing")
    assert_true(model == case_file_model, f"{label}: top-level and case-file relationshipCaseModel mismatch")
    return model


def assert_model_schema(view_model: dict[str, Any]) -> None:
    label = str(view_model.get("id") or "unknown")
    thesis = view_model.get("relationshipThesis") or ((view_model.get("westernRelationshipCaseFile") or {}).get("relationshipThesis") or {})
    model = model_from_view_model(view_model)
    validation = model.get("validation") or {}
    assert_true(validation.get("passed") is True, f"{label}: relationshipCaseModel validation failed: {validation.get('failures')}")

    primary = model.get("primaryDynamic") or {}
    assert_true(primary.get("key") == thesis.get("centralDynamicKey"), f"{label}: primary dynamic does not match thesis")
    assert_true(primary.get("centralThesis"), f"{label}: primary central thesis missing")
    assert_true(primary.get("readerMeaning"), f"{label}: primary reader meaning missing")
    assert_true(primary.get("evidenceIds"), f"{label}: primary evidence ids missing")

    secondaries = model.get("secondaryDynamics") or []
    assert_true(secondaries, f"{label}: secondary dynamics missing")
    for item in secondaries:
        assert_true(item.get("key") != primary.get("key"), f"{label}: secondary repeats primary: {item.get('key')}")
        assert_true(item.get("role") in SECONDARY_ROLES, f"{label}: invalid secondary role: {item.get('role')}")
        assert_true(item.get("evidenceIds"), f"{label}: secondary evidence ids missing: {item.get('key')}")
        assert_true(item.get("interactionEffect"), f"{label}: secondary interaction effect missing: {item.get('key')}")
        assert_true(item.get("whyItMatters"), f"{label}: secondary whyItMatters missing: {item.get('key')}")

    for field in ("centralLoop", "emotionalBlocker", "repairLever", "contactPosture", "timingPosture", "riskPosture", "answerStrategy", "dynamicInteractionPlan"):
        assert_true(isinstance(model.get(field), dict) and model.get(field), f"{label}: case model field missing: {field}")

    interaction_plan = model.get("dynamicInteractionPlan") or {}
    assert_true(
        interaction_plan.get("version") == "dynamic-interaction-plan-v1",
        f"{label}: dynamicInteractionPlan version mismatch",
    )
    assert_true(interaction_plan.get("primaryKey") == primary.get("key"), f"{label}: dynamicInteractionPlan primary mismatch")
    assert_true(
        interaction_plan.get("secondaryKey") == secondaries[0].get("key"),
        f"{label}: dynamicInteractionPlan secondary mismatch",
    )
    assert_true(isinstance(interaction_plan.get("matchedGrammar"), bool), f"{label}: matchedGrammar must be boolean")
    assert_true(interaction_plan.get("matchedGrammar") is True, f"{label}: dynamicInteractionPlan is unmatched")
    assert_true(interaction_plan.get("grammarMode") in {"explicit", "composed"}, f"{label}: grammarMode is invalid")
    assert_true(interaction_plan.get("grammarId"), f"{label}: dynamicInteractionPlan grammarId missing")
    assert_true("fallback" not in str(interaction_plan.get("grammarId") or ""), f"{label}: fallback grammar remains")
    assert_true(interaction_plan.get("evidenceIds"), f"{label}: dynamicInteractionPlan evidence ids missing")
    for field in DYNAMIC_INTERACTION_PLAN_FIELDS:
        assert_true(interaction_plan.get(field), f"{label}: dynamicInteractionPlan missing {field}")
    for phrase in interaction_plan.get("phrasesToAvoid") or []:
        assert_true(phrase not in final_text(view_model), f"{label}: avoided pair phrase leaked into final copy: {phrase}")

    section_plans = model.get("sectionPlans") or {}
    assert_true(set(section_plans) == SECTION_IDS, f"{label}: sectionPlans mismatch: {set(section_plans)}")
    for section_id in SECTION_IDS:
        plan = section_plans.get(section_id) or {}
        assert_true(plan.get("interpretiveJob"), f"{label}:{section_id}: interpretive job missing")
        assert_true(plan.get("caseBridge"), f"{label}:{section_id}: case bridge missing")
        assert_true("relationshipCaseModel" in (plan.get("evidenceClusterKeys") or []), f"{label}:{section_id}: case evidence missing from plan")

    canonical_primary = canonical_value_key(primary.get("key"))
    primary_facts = facts_for(view_model, "core-answer", "central-dynamic")
    assert_true(
        len(primary_facts) == 1 and primary_facts[0].get("valueKey") == canonical_primary,
        f"{label}: core fact does not preserve primary dynamic: {primary.get('key')}",
    )
    assert_true(
        FINAL_NARRATIVE_ROLE_PRESENTATIONS["core-answer"]["central-dynamic"]
        == "hidden-support",
        f"{label}: primary dynamic is no longer protected as hidden support",
    )
    fit_primary_facts = facts_for(view_model, "relationship-fit", "primary-dynamic")
    assert_true(
        len(fit_primary_facts) == 1
        and fit_primary_facts[0].get("valueKey") == canonical_primary,
        f"{label}: relationship-fit lost the primary dynamic: {primary.get('key')}",
    )
    relationship_fit_section = (
        ((view_model.get("finalInterpretation") or {}).get("sections") or {}).get(
            "relationship-fit"
        )
        or {}
    )
    primary_trace = relationship_fit_sentence_trace(
        str(relationship_fit_section.get("meaning") or "")
    )
    assert_true(
        primary_trace
        and primary_trace.get("role") == "primary-dynamic"
        and primary_trace.get("valueKey") == canonical_primary,
        f"{label}: relationship-fit has no approved primary sentence trace: {primary.get('key')}",
    )
    contact_facts = facts_for(view_model, "core-answer", "contact-status")
    blocked_contact = any(item.get("valueKey") == "blocked" for item in contact_facts)
    relationship_fit_text = "\n".join(
        str(((((view_model.get("finalInterpretation") or {}).get("sections") or {}).get("relationship-fit") or {}).get(field)) or "")
        for field in ("headline", "meaning", "body", "nextMove", "caution")
    )
    assert_true(
        sum(1 for marker in FIT_NARRATIVE_MARKERS if marker in relationship_fit_text) >= 2,
        f"{label}: relationship-fit final copy does not expose readable fit markers",
    )
    final = view_model.get("finalInterpretation") or {}
    bundle = view_model.get("sectionNarrativeSpecs") or final.get("sectionSpecs") or {}
    assert_true(bundle.get("rendererConsumesSpecs") is True, f"{label}: final renderer does not consume specs")
    assert_true((bundle.get("validation") or {}).get("status") == "valid", f"{label}: section specs invalid")
    specs = bundle.get("sections") or {}
    assert_true(not ((specs.get("chart-positioning") or {}).get("context") or {}), f"{label}: chart spec is not context-free")
    assert_true(not ((specs.get("relationship-fit") or {}).get("context") or {}), f"{label}: fit spec is not context-free")
    core_slots = (specs.get("core-answer") or {}).get("semanticSlots") or {}
    timing_slots = (specs.get("timing-reading") or {}).get("semanticSlots") or {}
    action_slots = (specs.get("action-direction") or {}).get("semanticSlots") or {}
    expected_timing_posture = (
        "avoid-push"
        if blocked_contact
        else canonical_value_key((model.get("timingPosture") or {}).get("key"))
    )
    assert_true(core_slots.get("centralDynamicKey") == primary.get("key"), f"{label}: core spec lost selected primary dynamic")
    assert_true(
        timing_slots.get("timingPostureKey") == expected_timing_posture,
        f"{label}: timing spec lost timing posture",
    )
    assert_true(
        action_slots.get("repairLeverKey") == (model.get("repairLever") or {}).get("key"),
        f"{label}: action spec lost repair lever",
    )
    assert_true("relationshipCaseModel" not in (final.get("evidenceClusterKeys") or []), f"{label}: global case model still owns final evidence")
    for section_id, section in (final.get("sections") or {}).items():
        expected = set(((specs.get(section_id) or {}).get("trace") or {}).get("evidenceClusterKeys") or [])
        actual = set(section.get("evidenceClusterKeys") or [])
        assert_true(actual == expected, f"{label}:{section_id}: final evidence does not match section spec trace")
        spec_case_trace = (specs.get(section_id) or {}).get("caseModelTrace") or {}
        final_case_trace = section.get("caseModelTrace") or {}
        if section_id not in CASE_TRACE_SECTION_IDS:
            assert_true(not spec_case_trace, f"{label}:{section_id}: case trace leaked into context-free spec")
            assert_true(not final_case_trace, f"{label}:{section_id}: case trace leaked into context-free copy")
            continue
        assert_true(set(spec_case_trace) == CASE_TRACE_FIELDS, f"{label}:{section_id}: case trace fields mismatch")
        assert_true(spec_case_trace == final_case_trace, f"{label}:{section_id}: final case trace differs from spec")
        assert_true(spec_case_trace.get("version") == "relationship-case-model-trace-v1", f"{label}:{section_id}: trace version mismatch")
        assert_true(spec_case_trace.get("caseModelVersion") == model.get("version"), f"{label}:{section_id}: model version mismatch")
        assert_true(spec_case_trace.get("sectionId") == section_id, f"{label}:{section_id}: trace section mismatch")
        assert_true(spec_case_trace.get("primaryDynamicKey") == primary.get("key"), f"{label}:{section_id}: trace primary mismatch")
        assert_true(spec_case_trace.get("secondaryDynamicKey") == secondaries[0].get("key"), f"{label}:{section_id}: trace secondary mismatch")
        assert_true(spec_case_trace.get("secondaryRole") == secondaries[0].get("role"), f"{label}:{section_id}: trace role mismatch")
        assert_true(spec_case_trace.get("grammarId") == interaction_plan.get("grammarId"), f"{label}:{section_id}: trace grammar mismatch")
        assert_true(spec_case_trace.get("grammarMode") == interaction_plan.get("grammarMode"), f"{label}:{section_id}: trace grammar mode mismatch")
        assert_true(spec_case_trace.get("caseEvidenceIds") == interaction_plan.get("evidenceIds"), f"{label}:{section_id}: trace evidence mismatch")

    final_case_trace = final.get("caseModelTrace") or {}
    expected_final_trace = dict((specs.get("core-answer") or {}).get("caseModelTrace") or {})
    expected_final_trace["sectionId"] = "final-reading"
    assert_true(final_case_trace == expected_final_trace, f"{label}: top-level final case trace mismatch")


def assert_v2_secondary_depth(scenarios: list[dict[str, Any]]) -> None:
    primary_counts: Counter[str] = Counter()
    secondary_by_primary: dict[str, set[str]] = defaultdict(set)
    roles_by_primary: dict[str, set[str]] = defaultdict(set)
    pair_counts: Counter[tuple[str, str, str]] = Counter()

    for scenario in scenarios:
        model = model_from_view_model(scenario)
        primary = str((model.get("primaryDynamic") or {}).get("key") or "")
        primary_counts[primary] += 1
        for secondary in model.get("secondaryDynamics") or []:
            secondary_key = str(secondary.get("key") or "")
            role = str(secondary.get("role") or "")
            if secondary_key:
                secondary_by_primary[primary].add(secondary_key)
            if role:
                roles_by_primary[primary].add(role)
            pair_counts[(primary, secondary_key, role)] += 1

    missing = sorted(PRIMARY_DYNAMICS - set(primary_counts))
    assert_true(not missing, f"V2 missing primary dynamics: {missing}")
    for primary in PRIMARY_DYNAMICS:
        assert_true(
            len(secondary_by_primary[primary]) >= 2,
            f"{primary}: expected at least 2 secondary dynamics, got {sorted(secondary_by_primary[primary])}",
        )
        assert_true(
            len(roles_by_primary[primary]) >= 2,
            f"{primary}: expected at least 2 secondary roles, got {sorted(roles_by_primary[primary])}",
        )
    assert_true(len(pair_counts) >= 18, f"primary/secondary/role combinations too thin: {len(pair_counts)}")


def interaction_plan(view_model: dict[str, Any]) -> dict[str, Any]:
    return (model_from_view_model(view_model).get("dynamicInteractionPlan") or {})


def assert_required_pair_grammar_coverage(scenarios: list[dict[str, Any]]) -> None:
    observed: Counter[tuple[str, str]] = Counter()
    unmatched_required: list[str] = []

    for scenario in scenarios:
        plan = interaction_plan(scenario)
        pair = (str(plan.get("primaryKey") or ""), str(plan.get("secondaryKey") or ""))
        if not all(pair):
            continue
        observed[pair] += 1
        if pair in REQUIRED_GRAMMAR_PAIRS and plan.get("matchedGrammar") is not True:
            unmatched_required.append(f"{scenario.get('id')}: {pair[0]} + {pair[1]}")

    missing = sorted(REQUIRED_GRAMMAR_PAIRS - set(observed))
    assert_true(not missing, f"V4 missing required pair grammar fixture coverage: {missing}")
    assert_true(not unmatched_required, f"V4 required pair grammar fell back: {unmatched_required}")


def assert_compositional_grammar_coverage(scenarios: list[dict[str, Any]]) -> None:
    modes: Counter[str] = Counter()
    fallback_scenarios: list[str] = []
    for scenario in scenarios:
        plan = interaction_plan(scenario)
        modes[str(plan.get("grammarMode") or "missing")] += 1
        if plan.get("matchedGrammar") is not True or "fallback" in str(plan.get("grammarId") or ""):
            fallback_scenarios.append(str(scenario.get("id") or "unknown"))
    assert_true(not fallback_scenarios, f"V4 fallback grammars remain: {fallback_scenarios}")
    assert_true(modes["explicit"] > 0, "V4 explicit grammar coverage is empty")
    assert_true(modes["composed"] > 0, "V4 compositional grammar coverage is empty")


def find_plan_by_pair(scenarios: list[dict[str, Any]], primary: str, secondary: str) -> dict[str, Any]:
    for scenario in scenarios:
        plan = interaction_plan(scenario)
        if plan.get("primaryKey") == primary and plan.get("secondaryKey") == secondary:
            return plan
    raise AssertionError(f"missing scenario for pair: {primary} + {secondary}")


def plan_text(plan: dict[str, Any]) -> str:
    return "\n".join(str(plan.get(field) or "") for field in DYNAMIC_INTERACTION_PLAN_FIELDS)


def assert_v4_pair_contrast(scenarios: list[dict[str, Any]]) -> None:
    safety_attraction = find_plan_by_pair(scenarios, "emotional_safety", "attraction_pursuit")
    safety_saturn = find_plan_by_pair(scenarios, "emotional_safety", "saturn_pressure")
    assert_true(
        safety_attraction.get("whatThisMeans") != safety_saturn.get("whatThisMeans"),
        "emotional_safety pair grammar collapsed across attraction_pursuit and saturn_pressure",
    )
    assert_true("吸引" in plan_text(safety_attraction), "emotional_safety + attraction_pursuit does not mention attraction")
    assert_true(
        any(term in plan_text(safety_saturn) for term in ("壓力", "承擔", "責任")),
        "emotional_safety + saturn_pressure does not mention pressure/responsibility",
    )

    repair_saturn = find_plan_by_pair(scenarios, "communication_repair", "saturn_pressure")
    repair_conflict = find_plan_by_pair(scenarios, "communication_repair", "action_conflict")
    assert_true(
        repair_saturn.get("whatThisMeans") != repair_conflict.get("whatThisMeans"),
        "communication_repair pair grammar collapsed across saturn_pressure and action_conflict",
    )
    assert_true(
        any(term in plan_text(repair_saturn) for term in ("承擔", "責任", "關係審判")),
        "communication_repair + saturn_pressure does not mention burden/responsibility",
    )
    assert_true(
        any(term in plan_text(repair_conflict) for term in ("節奏", "急迫", "推對方回答")),
        "communication_repair + action_conflict does not mention speed/urgency",
    )


def main() -> int:
    failures: list[str] = []
    built_view_models = build_view_models()
    generated_scenarios = read_json(SCENARIOS_PATH)
    for view_model in [*built_view_models, *generated_scenarios]:
        try:
            assert_model_schema(view_model)
        except AssertionError as exc:
            failures.append(str(exc))
    try:
        assert_v2_secondary_depth(generated_scenarios)
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_required_pair_grammar_coverage(generated_scenarios)
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_v4_pair_contrast(generated_scenarios)
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_compositional_grammar_coverage(generated_scenarios)
    except AssertionError as exc:
        failures.append(str(exc))

    if failures:
        print("Western RelationshipCaseModel smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Western RelationshipCaseModel smoke passed")
    print(f"- built scenarios: {len(built_view_models)}")
    print(f"- generated scenarios: {len(generated_scenarios)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
