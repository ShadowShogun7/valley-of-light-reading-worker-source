#!/usr/bin/env python3
"""Validate the paid V1 five-section Western result contract."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
)


ARTICLES = load_articles(DEFAULT_ARTICLES_PATH)
CLAIMS_BY_ARTICLE = load_claims_by_article(DEFAULT_CLAIMS_PATH)

READING_PATHS = [
    ROOT / "examples/readings/cold-war-still-love-me.json",
    ROOT / "examples/readings/broke-up-long-any-chance.json",
    ROOT / "examples/readings/cold-war-when-to-contact.json",
    ROOT / "examples/readings/broke-up-recent-what-did-i-do-wrong.json",
    ROOT / "examples/readings/crisis-stay-or-let-go.json",
    ROOT / "examples/readings/broke-up-recent-still-love-me.json",
    ROOT / "examples/readings/blocked-anxious-still-love-me.json",
    ROOT / "examples/readings/no-contact-desperate-when-to-contact.json",
    ROOT / "examples/readings/still-in-contact-self-blaming-what-did-i-do-wrong.json",
    ROOT / "examples/readings/ambiguous-still-love-me.json",
    ROOT / "examples/readings/broke-up-long-release-stay-or-let-go.json",
]

LEGACY_KEYS = {
    "relationshipCaseFile",
    "baziCompatibilityDiagnosis",
    "bazi",
    "freeChapters",
    "freeSummary",
    "lockedQuestions",
    "lockedRows",
    "paidBoundary",
    "paidDetailLocked",
    "paidExpansionPlan",
    "paidUnlock",
    "preciseDatesAvailableInFree",
}
LEGACY_TERMS = ("bazi", "八字", "配偶星", "日主", "四柱", "十神")
FORBIDDEN_TIMING_KEYS = {
    "date",
    "start_date",
    "end_date",
    "startDate",
    "endDate",
    "daySummaries",
    "day_summaries",
    "windows",
}

EXPECTED_TRACE_SECTIONS = {
    "profile": {
        "title": "星盤定位",
        "targets": {
            "personProfile",
            "relationshipProfiles",
            "identityNeeds",
            "planetSignStyle",
            "moonSignEmotionalSafety",
            "mercurySignCommunicationRepair",
            "venusSignAffectionStyle",
            "marsSignPursuitConflict",
            "saturnSignDefenseDelay",
            "precisionWarnings",
        },
    },
    "fit": {
        "title": "兩個人的關係契合度分析",
        "targets": {
            "relationshipFit",
            "fitSummary",
            "relationshipArchetype",
            "attractionDynamics",
            "conflictDynamics",
            "growthDynamics",
            "safetyValidationLanguage",
            "attraction",
            "emotionalSafety",
            "communication",
            "pressure",
            "repair",
            "aspectPriority",
            "aspectFunctionCombination",
        },
    },
    "question": {
        "title": "核心問題解讀",
        "targets": {
            "answerEvidenceContract",
            "contextModifier",
            "nonfatalSynastrySafety",
            "consultationSafety",
            "contactSituationPolicy",
            "partnerNeeds",
        },
    },
    "timing": {
        "title": "時機判讀",
        "targets": {
            "currentTransits",
            "timingWindowBand",
            "timingContactReducer",
            "timingMercuryCommunication",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
            "contactSituationPolicy",
            "relationshipTurningWindows",
        },
    },
    "action": {
        "title": "行動方向",
        "targets": {
            "actionBoundary",
            "actionDirection",
            "donts",
            "contactStatus",
            "contactSituationPolicy",
            "nonfatalSynastrySafety",
            "timingContactReducer",
            "fightLandmines",
            "survivalGuide",
        },
    },
}

SECTION_CLUSTERS = {
    "profile": {
        "birthDataQuality",
        "identityNeeds",
        "planetaryFunctions",
        "planetSignStyle",
        "moonSignEmotionalSafety",
        "mercurySignCommunicationRepair",
        "venusSignAffectionStyle",
        "marsSignPursuitConflict",
        "saturnSignDefenseDelay",
        "functionElementMatrix",
        "functionModalityMatrix",
    },
    "fit": {
        "relationshipPotential",
        "elementComparison",
        "luminaryComparison",
        "safetyValidationLanguage",
        "nonfatalSynastrySafety",
        "attraction",
        "emotionalSafety",
        "communication",
        "pressure",
        "repair",
        "aspectPriority",
        "aspectContactModifier",
        "aspectPairContactTemplate",
        "aspectFunctionCombination",
        "relationshipArchetype",
        "attractionDynamics",
        "conflictDynamics",
        "growthDynamics",
        "aspectSynthesisCrossCheck",
    },
    "question": {
        "consultationSafety",
        "contactStatus",
        "contactSituationPolicy",
        "desiredOutcome",
        "emotionalRisk",
        "relationshipStage",
        "safetyValidationLanguage",
        "partnerNeeds",
    },
    "timing": {
        "currentTransits",
        "timingWindowBand",
        "timingMercuryCommunication",
        "timingVenusSoftening",
        "timingMarsActivation",
        "timingSaturnPressure",
        "timingMoonWeather",
        "timingContactReducer",
        "contactSituationPolicy",
        "relationshipTurningWindows",
    },
    "action": {
        "consultationSafety",
        "contactStatus",
        "contactSituationPolicy",
        "relationshipStage",
        "emotionalRisk",
        "desiredOutcome",
        "nonfatalSynastrySafety",
        "timingContactReducer",
        "fightLandmines",
        "survivalGuide",
    },
}

REQUIRED_PERSON_POINTS = {"Moon", "Mercury", "Venus", "Mars", "Saturn"}
SUPPORTED_QUESTIONS = {
    "still-love-me",
    "any-chance",
    "when-to-contact",
    "what-did-i-do-wrong",
    "stay-or-let-go",
}
REQUIRED_CONTEXT_COMBINATIONS = {
    ("blocked", "anxious"),
    ("no-contact", "desperate"),
    ("still-in-contact", "self-blaming"),
    ("living-or-working-together", "desperate"),
}
REQUIRED_STAGE_QUESTION_COMBINATIONS = {
    ("ambiguous", "still-love-me"),
    ("broke-up-long", "stay-or-let-go"),
    ("cold-war", "when-to-contact"),
    ("broke-up-recent", "what-did-i-do-wrong"),
}
REQUIRED_PAID_FIXTURE_TIMING_ACTIONS = {
    "avoid_push",
    "low_pressure_message",
    "observe_only",
}
PRODUCT_INSIGHT_CLUSTERS = {
    "relationshipArchetype",
    "attractionDynamics",
    "conflictDynamics",
    "growthDynamics",
    "partnerNeeds",
    "fightLandmines",
    "survivalGuide",
    "relationshipTurningWindows",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def build_vm(reading: dict[str, Any]) -> dict[str, Any]:
    payload = build_payload(reading, include_drafts=True, select=True)
    return build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)


def case_file(view_model: dict[str, Any]) -> dict[str, Any]:
    case = view_model.get("westernRelationshipCaseFile") or {}
    assert_true(case.get("version") == "western-relationship-case-file-v1", "case-file version mismatch")
    return case


def assert_no_legacy_runtime_output(view_model: dict[str, Any], label: str) -> None:
    for item in walk(view_model):
        if isinstance(item, str):
            assert_true(item not in LEGACY_KEYS, f"{label}: legacy key leaked as value: {item}")
        if isinstance(item, dict):
            leaked = sorted(key for key in item if key in LEGACY_KEYS)
            assert_true(not leaked, f"{label}: legacy keys leaked: {', '.join(leaked)}")
    rendered = json.dumps(view_model, ensure_ascii=False).lower()
    for term in LEGACY_TERMS:
        assert_true(term.lower() not in rendered, f"{label}: legacy BaZi term leaked: {term}")


def assert_cluster_supported(clusters: dict[str, dict[str, Any]], cluster_key: str, label: str) -> None:
    cluster = clusters.get(cluster_key) or {}
    assert_true(cluster, f"{label}: missing evidence cluster {cluster_key}")
    assert_true(cluster.get("category") == cluster_key, f"{label}: {cluster_key} category mismatch")
    if cluster_key in PRODUCT_INSIGHT_CLUSTERS:
        assert_true(cluster.get("methodClaimIds"), f"{label}: {cluster_key} methodClaimIds missing")
    else:
        assert_true(cluster.get("atomId"), f"{label}: {cluster_key} atomId missing")
        assert_true(cluster.get("claimIds"), f"{label}: {cluster_key} claimIds missing")
    assert_true(cluster.get("source"), f"{label}: {cluster_key} source missing")


def assert_method_trace(case: dict[str, Any], label: str) -> None:
    trace = case.get("methodTrace") or {}
    assert_true(trace.get("version") == "western-method-trace-v1", f"{label}: methodTrace version mismatch")
    sections = {
        str(section.get("sectionId")): section
        for section in trace.get("sections") or []
        if isinstance(section, dict)
    }
    assert_true(set(sections) == set(EXPECTED_TRACE_SECTIONS), f"{label}: methodTrace section set mismatch")
    for section_id, expected in EXPECTED_TRACE_SECTIONS.items():
        section = sections[section_id]
        assert_true(section.get("title") == expected["title"], f"{label}: {section_id} title mismatch")
        assert_true(section.get("status") == "covered", f"{label}: {section_id} not covered")
        assert_true(section.get("liveEvidenceCount", 0) > 0, f"{label}: {section_id} live evidence missing")
        assert_true(section.get("methodClaimIds"), f"{label}: {section_id} method claims missing")
        assert_true(section.get("runtimeClaimIds"), f"{label}: {section_id} runtime claims missing")
        assert_true(section.get("requiredSourceIds"), f"{label}: {section_id} source ids missing")
        assert_true(section.get("evidenceClusterKeys"), f"{label}: {section_id} cluster keys missing")
        targets = set(str(item) for item in section.get("requiredRuntimeTargets") or [])
        missing = sorted(expected["targets"] - targets)
        assert_true(not missing, f"{label}: {section_id} missing runtime targets: {', '.join(missing)}")
        assert_true(not section.get("missingRequirements"), f"{label}: {section_id} has missing requirements")

    summary = trace.get("summary") or {}
    assert_true(summary.get("sectionCount") == 5, f"{label}: methodTrace should expose five sections")
    assert_true(summary.get("coveredSectionCount") == 5, f"{label}: all methodTrace sections should be covered")


def assert_relationship_profiles(view_model: dict[str, Any], label: str) -> None:
    profiles = view_model.get("relationshipProfiles") or {}
    assert_true(profiles.get("version") == "relationship-profiles-v1", f"{label}: relationshipProfiles version mismatch")
    for person_key in ("personA", "personB"):
        person = profiles.get(person_key) or {}
        assert_true(person.get("headline"), f"{label}: {person_key} headline missing")
        assert_true(person.get("summary"), f"{label}: {person_key} summary missing")
        cards = [card for card in person.get("cards") or [] if isinstance(card, dict)]
        points = {str(card.get("point") or "") for card in cards}
        assert_true(REQUIRED_PERSON_POINTS.issubset(points), f"{label}: {person_key} missing profile cards")
        for card in cards:
            assert_true(card.get("placement"), f"{label}: {person_key} card placement missing")
            assert_true(card.get("signLabel"), f"{label}: {person_key} card sign label missing")
            readable = card.get("readableInterpretation") or {}
            assert_true(readable.get("version") == "readable-interpretation-v1", f"{label}: {person_key} card readable version missing")
            assert_true(readable.get("module") == "person_function_sign", f"{label}: {person_key} card readable module mismatch")
            assert_true(readable.get("meaning"), f"{label}: {person_key} card meaning missing")
            assert_true(readable.get("body"), f"{label}: {person_key} card body missing")
            assert_true(readable.get("stuckPattern"), f"{label}: {person_key} card stuck pattern missing")

    fit = profiles.get("fitSummary") or {}
    assert_true(fit.get("headline"), f"{label}: fit headline missing")
    assert_true(fit.get("summary"), f"{label}: fit summary missing")
    assert_true(fit.get("readableInterpretation"), f"{label}: fit readable interpretation missing")
    assert_true(fit.get("safetyValidationLanguage"), f"{label}: safety validation cluster missing from fit")
    assert_true(fit.get("pivotalAspect"), f"{label}: pivotal aspect item missing from fit")
    for bucket in ("natural", "effort", "friction"):
        assert_true(isinstance(fit.get(bucket), list), f"{label}: fit bucket {bucket} missing")
    fit_item_count = sum(len(fit.get(bucket) or []) for bucket in ("natural", "effort", "friction"))
    assert_true(fit_item_count >= 3, f"{label}: fit summary needs at least three items")
    assert_true(profiles.get("answerBridge"), f"{label}: relationship profile answer bridge missing")


def assert_answer_contract(case: dict[str, Any], view_model: dict[str, Any], label: str) -> None:
    answer = case.get("answerLayer") or {}
    assert_true(answer.get("rulesetId") == "western-relationship-result-v1", f"{label}: answer ruleset mismatch")
    assert_true(answer.get("questionBlueprintId") == "western-relationship-result-v1", f"{label}: question blueprint mismatch")
    assert_true(answer.get("ruleId"), f"{label}: selected answer rule missing")
    assert_true(answer.get("shortAnswer"), f"{label}: short answer missing")
    evidence_contract = answer.get("evidenceContract") or {}
    assert_true(evidence_contract.get("calculationEvidence"), f"{label}: calculation evidence missing")
    context_modifier = evidence_contract.get("contextModifier") or {}
    boundary = context_modifier.get("contextEvidenceBoundary") or {}
    assert_true(boundary.get("version") == "context-evidence-boundary-v1", f"{label}: context boundary missing")
    assert_true(boundary.get("canCreateAstrologyConclusion") is False, f"{label}: context must not create conclusions")
    assert_true(boundary.get("requiresCalculationEvidenceForConclusion") is True, f"{label}: context should require calculation support")
    assert_true(boundary.get("requiresTransitEvidenceForTimingAction") is True, f"{label}: timing action should require transit support")

    readable = view_model.get("readableQuestionAnswer") or {}
    assert_true(readable.get("version") == "readable-question-answer-v1", f"{label}: readable question answer version mismatch")
    sections = readable.get("sections") or {}
    answer_section = sections.get("answer") or {}
    assert_true(answer_section.get("version") == "answer-guidance-v1", f"{label}: answer section missing")
    assert_true(view_model.get("answerGuidance", {}).get("version") == "answer-guidance-v1", f"{label}: top-level answer guidance missing")


def assert_timing_contract(case: dict[str, Any], view_model: dict[str, Any], label: str) -> None:
    timing_layer = case.get("timingLayer") or {}
    assert_true(timing_layer.get("currentTransits"), f"{label}: current transits missing")
    window_scan = timing_layer.get("windowScan") or {}
    assert_true(window_scan.get("method") == "western-transit-window-scan-v1", f"{label}: window scan method mismatch")
    assert_true(window_scan.get("preciseDatesAvailable") is False, f"{label}: public window scan must block precise dates")
    exact_policy = window_scan.get("exactTimingPolicy") or {}
    assert_true(exact_policy.get("preciseDatesAvailable") is False, f"{label}: exact timing policy should block dates")
    leaked_window_keys = FORBIDDEN_TIMING_KEYS.intersection(set(window_scan))
    assert_true(not leaked_window_keys, f"{label}: public window scan leaked date keys: {', '.join(sorted(leaked_window_keys))}")

    clusters = case.get("evidenceClusters") or {}
    contact_reducer = clusters.get("timingContactReducer") or {}
    assert_true(contact_reducer.get("recommendedAction"), f"{label}: contact reducer action missing")
    assert_true(contact_reducer.get("preciseDatesAvailable") is False, f"{label}: contact reducer should block precise dates")
    for reducer in contact_reducer.get("selectedTimingReducers") or []:
        leaked = FORBIDDEN_TIMING_KEYS.intersection(set(reducer))
        assert_true(not leaked, f"{label}: selected timing reducer leaked date keys: {', '.join(sorted(leaked))}")

    timing_guidance = view_model.get("timingGuidance") or {}
    assert_true(timing_guidance.get("version") == "timing-guidance-v1", f"{label}: timing guidance version mismatch")
    assert_true(timing_guidance.get("preciseDatesAvailable") is False, f"{label}: timing guidance should block dates")
    timing_section = ((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("timing") or {}
    assert_true(timing_section.get("version") == "timing-guidance-v1", f"{label}: readable timing section missing")


def assert_action_contract(case: dict[str, Any], view_model: dict[str, Any], label: str) -> None:
    clusters = case.get("evidenceClusters") or {}
    contact_policy = clusters.get("contactSituationPolicy") or {}
    boundary = contact_policy.get("contactActionBoundary") or {}
    assert_true(boundary.get("version") == "contact-action-boundary-v1", f"{label}: contact action boundary missing")
    assert_true(boundary.get("requiresCalculationSupport") is True, f"{label}: contact boundary should require calculation support")
    assert_true(boundary.get("timingCanOverrideBoundary") is False, f"{label}: timing cannot override contact boundary")
    assert_true(boundary.get("canCreateAstrologyConclusion") is False, f"{label}: contact boundary must not create chart conclusion")
    assert_true(boundary.get("canOverrideRealWorldBoundary") is False, f"{label}: contact boundary cannot override real-world boundary")

    action_guidance = view_model.get("actionGuidance") or {}
    assert_true(action_guidance, f"{label}: action guidance missing")
    assert_true(action_guidance.get("actionMode") == boundary.get("actionMode"), f"{label}: action mode does not match boundary")
    action_section = ((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("action") or {}
    assert_true(action_section, f"{label}: readable action section missing")
    donts = ((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("donts") or []
    assert_true(donts, f"{label}: action donts missing")


def assert_blueprint_and_rows(view_model: dict[str, Any], label: str) -> None:
    blueprint = view_model.get("readingBlueprint") or {}
    assert_true(blueprint.get("version") == "reading-blueprint-v1", f"{label}: reading blueprint version mismatch")
    chapters = [chapter for chapter in blueprint.get("chapters") or [] if isinstance(chapter, dict)]
    assert_true(len(chapters) == 3, f"{label}: reading blueprint should expose three chapters")
    for chapter in chapters:
        assert_true(chapter.get("evidence"), f"{label}: blueprint chapter evidence missing")
        assert_true(chapter.get("methodBoundary"), f"{label}: blueprint chapter method boundary missing")
    rows = [row for row in view_model.get("includedReadingRows") or [] if isinstance(row, dict)]
    assert_true(len(rows) >= 5, f"{label}: included reading rows missing")
    for row in rows:
        assert_true(row.get("title"), f"{label}: included row title missing")
        assert_true(row.get("preview"), f"{label}: included row preview missing")


def assert_section_clusters(case: dict[str, Any], label: str) -> None:
    clusters = case.get("evidenceClusters") or {}
    for section_id, cluster_keys in SECTION_CLUSTERS.items():
        for cluster_key in cluster_keys:
            assert_cluster_supported(clusters, cluster_key, f"{label}/{section_id}")

    assert_true((clusters.get("saturnSignDefenseDelay") or {}).get("saturnProcessBoundary"), f"{label}: Saturn sign boundary missing")
    assert_true((clusters.get("timingSaturnPressure") or {}).get("saturnProcessBoundary"), f"{label}: timing Saturn boundary missing")
    assert_true((case.get("compositeLayer") or {}).get("status") == "not_calculated", f"{label}: composite layer should be blocked")


def assert_paid_v1_contract(reading: dict[str, Any], label: str) -> dict[str, Any]:
    question_key = str((reading.get("context") or {}).get("main_question") or "")
    assert_true(question_key in SUPPORTED_QUESTIONS, f"{label}: unsupported question fixture {question_key}")
    view_model = build_vm(reading)
    assert_true(view_model.get("contractVersion") == "complete-relationship-result-v1", f"{label}: contract version mismatch")
    assert_no_legacy_runtime_output(view_model, label)
    case = case_file(view_model)
    assert_method_trace(case, label)
    assert_section_clusters(case, label)
    assert_relationship_profiles(view_model, label)
    assert_answer_contract(case, view_model, label)
    assert_timing_contract(case, view_model, label)
    assert_action_contract(case, view_model, label)
    assert_blueprint_and_rows(view_model, label)
    return view_model


def blocked_contact_variant() -> dict[str, Any]:
    reading = copy.deepcopy(read_json(ROOT / "examples/readings/cold-war-when-to-contact.json"))
    reading["reading_id"] = "paid-v1-contract-blocked-contact"
    context = reading.setdefault("context", {})
    context["contact_status"] = "blocked"
    context["emotional_risk"] = "unsafe-or-overwhelmed"
    return reading


def assert_blocked_contact_boundary() -> None:
    view_model = build_vm(blocked_contact_variant())
    case = case_file(view_model)
    clusters = case.get("evidenceClusters") or {}
    boundary = ((clusters.get("contactSituationPolicy") or {}).get("contactActionBoundary") or {})
    assert_true(boundary.get("statusKey") == "blocked", "blocked variant: status key mismatch")
    assert_true(boundary.get("isHardBoundary") is True, "blocked variant: hard boundary missing")
    assert_true(boundary.get("canSuggestDirectContact") is False, "blocked variant: direct contact should be blocked")
    assert_true(boundary.get("timingCanOverrideBoundary") is False, "blocked variant: timing cannot override block")
    assert_true("alternate_account_contact" in set(boundary.get("blockedActions") or []), "blocked variant: bypass action not blocked")
    action_guidance = view_model.get("actionGuidance") or {}
    assert_true(action_guidance.get("actionMode") == "boundary_only", "blocked variant: action mode should be boundary-only")


def assert_fixture_variation_coverage(readings: list[dict[str, Any]]) -> None:
    context_combinations = {
        (
            str((reading.get("context") or {}).get("contact_status") or ""),
            str((reading.get("context") or {}).get("emotional_risk") or ""),
        )
        for reading in readings
    }
    missing_contexts = sorted(REQUIRED_CONTEXT_COMBINATIONS - context_combinations)
    assert_true(
        not missing_contexts,
        "missing required contact/emotional-risk fixtures: "
        + ", ".join(f"{contact}/{risk}" for contact, risk in missing_contexts),
    )

    stage_questions = {
        (
            str((reading.get("context") or {}).get("relationship_stage") or ""),
            str((reading.get("context") or {}).get("main_question") or ""),
        )
        for reading in readings
    }
    missing_stage_questions = sorted(REQUIRED_STAGE_QUESTION_COMBINATIONS - stage_questions)
    assert_true(
        not missing_stage_questions,
        "missing required stage/question fixtures: "
        + ", ".join(f"{stage}/{question}" for stage, question in missing_stage_questions),
    )


def assert_paid_fixture_timing_action_coverage(view_models: list[dict[str, Any]]) -> None:
    actions = {
        str(
            (
                ((view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {}).get(
                    "timingContactReducer"
                )
                or {}
            ).get("recommendedAction")
            or ""
        )
        for view_model in view_models
    }
    missing = sorted(REQUIRED_PAID_FIXTURE_TIMING_ACTIONS - actions)
    assert_true(
        not missing,
        "paid fixture timing actions missing coverage: " + ", ".join(missing),
    )


def main() -> int:
    passed: list[str] = []
    readings: list[dict[str, Any]] = []
    view_models: list[dict[str, Any]] = []
    for path in READING_PATHS:
        reading = read_json(path)
        readings.append(reading)
        label = str(reading.get("reading_id") or path.name)
        view_models.append(assert_paid_v1_contract(reading, label))
        passed.append(label)
    assert_fixture_variation_coverage(readings)
    assert_paid_fixture_timing_action_coverage(view_models)
    assert_blocked_contact_boundary()
    print("Paid V1 result section contract passed")
    print(f"- validated readings: {len(passed)}")
    print(f"- sections: {', '.join(EXPECTED_TRACE_SECTIONS)}")
    print("- fixture variation coverage: passed")
    print("- paid fixture timing action coverage: passed")
    print("- blocked-contact boundary: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
