#!/usr/bin/env python3
"""
Smoke-test Western relationship-result behavior across real chart variation.

The context matrix proves reducer behavior over user state. This script proves
the runtime can handle different calculated Moon/Mercury/Venus/Mars/Saturn signs,
synastry mixes, and birth-data precision states without leaking legacy payloads
or inventing blocked angle/house claims.
"""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload  # noqa: E402
from structured_runtime import load_structured_kb  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
    western_aspect_function_combination_cluster,
    western_aspect_pair_contact_template,
)


ARTICLES = load_articles(DEFAULT_ARTICLES_PATH)
CLAIMS_BY_ARTICLE = load_claims_by_article(DEFAULT_CLAIMS_PATH)
LEGACY_TERMS = ("bazi", "八字", "配偶星", "日主", "四柱", "十神")
SATURN_BOUNDARY_SOURCE_CLAIMS = {
    "western-aspects-saturn-pressure-001",
    "western-aspects-saturn-pressure-003",
}
SATURN_BOUNDARY_METHOD_CLAIM = "greene-saturn-defense-not-permanent-rejection"
AWKWARD_PROFILE_COPY = (
    "這個功能的表達語氣",
    "功能的表達語氣",
    "這個功能",
    "Moon 的安全感",
    "Venus 的被重視",
    "Moon/Venus",
    "適合什麼",
    "不適合什麼",
)
FUNCTION_CLUSTERS = {
    "moonSignEmotionalSafety": "Moon",
    "mercurySignCommunicationRepair": "Mercury",
    "venusSignAffectionStyle": "Venus",
    "marsSignPursuitConflict": "Mars",
    "saturnSignDefenseDelay": "Saturn",
}
FUNCTION_TEMPLATE_CLAIMS = {
    "moonSignEmotionalSafety": "western-relationship-function-sign-templates-002",
    "mercurySignCommunicationRepair": "western-relationship-function-sign-templates-003",
    "venusSignAffectionStyle": "western-relationship-function-sign-templates-004",
    "marsSignPursuitConflict": "western-relationship-function-sign-templates-005",
    "saturnSignDefenseDelay": "western-relationship-function-sign-templates-006",
}
ELEMENT_CLAIMS = {
    "Fire": "western-function-element-templates-002",
    "Air": "western-function-element-templates-003",
    "Earth": "western-function-element-templates-004",
    "Water": "western-function-element-templates-005",
}
MODALITY_CLAIMS = {
    "Cardinal": "western-function-modality-templates-002",
    "Fixed": "western-function-modality-templates-003",
    "Mutable": "western-function-modality-templates-004",
}
REQUIRED_SIGNAL_IDS = {
    "western-aspects-mercury-contacts",
    "western-aspects-mercury-sun",
    "western-aspects-mars-mars",
    "western-aspects-moon-mars",
    "western-aspects-moon-moon",
    "western-aspects-moon-saturn",
    "western-aspects-moon-venus",
    "western-aspects-mars-saturn",
    "western-aspects-sun-mars",
    "western-aspects-sun-moon",
    "western-aspects-sun-saturn",
    "western-aspects-sun-venus",
    "western-aspects-venus-mars",
    "western-aspects-venus-saturn",
    "western-aspects-venus-venus",
}
REQUIRED_SYNASTRY_BUCKETS = {"attraction", "emotionalSafety", "pressure", "communication", "repair"}
REQUIRED_CONTACT_MODIFIERS = {"conjunction", "soft", "hard"}
REQUIRED_SAFETY_VALIDATION_RELATIONS = {"natural", "effort", "friction"}
PAIR_TEMPLATE_SOURCE_IDS = {
    "western-aspects-sun-venus",
    "western-aspects-moon-mars",
    "western-aspects-venus-venus",
    "western-aspects-mercury-jupiter",
    "western-aspects-moon-moon",
    "western-aspects-mars-mars",
    "western-aspects-mercury-sun",
    "western-aspects-mercury-contacts",
    "western-aspects-sun-mars",
    "western-aspects-venus-mars",
    "western-aspects-moon-venus",
    "western-aspects-sun-moon",
    "western-aspects-moon-saturn",
    "western-aspects-venus-saturn",
    "western-aspects-mars-saturn",
    "western-aspects-sun-saturn",
}
REQUIRED_PAIR_CONTACT_TEMPLATES = {
    "western-aspects-sun-venus:hard",
    "western-aspects-moon-mars:conjunction",
    "western-aspects-moon-mars:hard",
    "western-aspects-venus-venus:soft",
    "western-aspects-venus-venus:hard",
    "western-aspects-moon-moon:soft",
    "western-aspects-mars-mars:soft",
    "western-aspects-mercury-sun:hard",
}
REQUIRED_ASPECT_FUNCTION_PAIRS = {"Mercury-Sun", "Moon-Saturn", "Venus-Saturn", "Mars-Saturn"}
ASPECT_FUNCTION_SOURCE_CLAIMS = {
    "Sun-Mars": "western-aspects-sun-mars-001",
    "Venus-Mars": "western-aspects-venus-mars-001",
    "Moon-Venus": "western-aspects-moon-venus-001",
    "Sun-Moon": "western-aspects-sun-moon-001",
    "Sun-Venus": "western-aspects-sun-venus-001",
    "Moon-Mars": "western-aspects-moon-mars-001",
    "Venus-Venus": "western-aspects-venus-venus-001",
    "Moon-Moon": "western-aspects-moon-moon-001",
    "Mars-Mars": "western-aspects-mars-mars-001",
    "Mercury-Sun": "western-aspects-mercury-sun-001",
    "Mercury-Jupiter": "western-aspects-mercury-jupiter-001",
    "Mercury-Moon": "western-aspects-mercury-contacts-002",
    "Mercury-Venus": "western-aspects-mercury-contacts-005",
    "Mercury-Mars": "western-aspects-mercury-contacts-003",
    "Mercury-Saturn": "western-aspects-mercury-contacts-004",
    "Mercury-Mercury": "western-aspects-mercury-contacts-001",
    "Moon-Saturn": "western-aspect-function-combination-reducers-002",
    "Venus-Saturn": "western-aspect-function-combination-reducers-003",
    "Mars-Saturn": "western-aspect-function-combination-reducers-004",
    "Sun-Saturn": "western-aspects-sun-saturn-001",
    "Outer-planet intensity": "western-aspects-outer-planet-intensity-families-001",
}
PAIR_TEMPLATE_V2_CASES = {
    "Sun-Mars": ("Sun", "Mars", "western-aspects-sun-mars", "western-aspects-sun-mars-001"),
    "Venus-Mars": ("Venus", "Mars", "western-aspects-venus-mars", "western-aspects-venus-mars-001"),
    "Moon-Venus": ("Moon", "Venus", "western-aspects-moon-venus", "western-aspects-moon-venus-001"),
    "Sun-Moon": ("Sun", "Moon", "western-aspects-sun-moon", "western-aspects-sun-moon-001"),
    "Sun-Venus": ("Sun", "Venus", "western-aspects-sun-venus", "western-aspects-sun-venus-001"),
    "Moon-Mars": ("Moon", "Mars", "western-aspects-moon-mars", "western-aspects-moon-mars-001"),
    "Venus-Venus": ("Venus", "Venus", "western-aspects-venus-venus", "western-aspects-venus-venus-001"),
    "Moon-Moon": ("Moon", "Moon", "western-aspects-moon-moon", "western-aspects-moon-moon-001"),
    "Mars-Mars": ("Mars", "Mars", "western-aspects-mars-mars", "western-aspects-mars-mars-001"),
    "Mercury-Sun": ("Mercury", "Sun", "western-aspects-mercury-sun", "western-aspects-mercury-sun-001"),
    "Mercury-Jupiter": ("Mercury", "Jupiter", "western-aspects-mercury-jupiter", "western-aspects-mercury-jupiter-001"),
    "Mercury-Moon": ("Mercury", "Moon", "western-aspects-mercury-contacts", "western-aspects-mercury-contacts-002"),
    "Mercury-Venus": ("Mercury", "Venus", "western-aspects-mercury-contacts", "western-aspects-mercury-contacts-005"),
    "Mercury-Mars": ("Mercury", "Mars", "western-aspects-mercury-contacts", "western-aspects-mercury-contacts-003"),
    "Mercury-Saturn": ("Mercury", "Saturn", "western-aspects-mercury-contacts", "western-aspects-mercury-contacts-004"),
    "Mercury-Mercury": ("Mercury", "Mercury", "western-aspects-mercury-contacts", "western-aspects-mercury-contacts-001"),
    "Moon-Saturn": ("Moon", "Saturn", "western-aspects-moon-saturn", "western-aspects-moon-saturn-001"),
    "Venus-Saturn": ("Venus", "Saturn", "western-aspects-venus-saturn", "western-aspects-venus-saturn-001"),
    "Mars-Saturn": ("Mars", "Saturn", "western-aspects-mars-saturn", "western-aspects-mars-saturn-001"),
    "Sun-Saturn": ("Sun", "Saturn", "western-aspects-sun-saturn", "western-aspects-sun-saturn-001"),
}
PAIR_TEMPLATE_METHOD_CLAIMS = {
    "Venus-Mars": {"skymates-venus-mars-attraction-pursuit-polarity"},
    "Moon-Venus": {"burk-moon-venus-safety-validation-alignment", "skymates-moon-venus-nurture-trust-bond"},
    "Sun-Moon": {"skymates-sun-moon-core-rhythm-interaspect"},
    "Moon-Saturn": {"burk-saturn-to-moon-venus-need-blocks", "skymates-moon-saturn-practical-emotional-translation"},
    "Venus-Saturn": {"burk-saturn-to-moon-venus-need-blocks", "skymates-venus-saturn-commitment-and-blockage"},
    "Mars-Saturn": {"skymates-mars-saturn-action-boundary-pressure"},
}
CONTACT_TYPE_ASPECTS = {
    "conjunction": "Conjunction",
    "soft": "Trine",
    "hard": "Square",
}
SYNTHETIC_OBJECTS = {
    "sun": {"sign": "Leo", "sign_element": "Fire"},
    "moon": {"sign": "Cancer", "sign_element": "Water"},
    "mercury": {"sign": "Gemini", "sign_element": "Air"},
    "venus": {"sign": "Taurus", "sign_element": "Earth"},
    "mars": {"sign": "Aries", "sign_element": "Fire"},
    "jupiter": {"sign": "Sagittarius", "sign_element": "Fire"},
    "saturn": {"sign": "Capricorn", "sign_element": "Earth"},
}

BASE_CONTEXT = {
    "relationship_stage": "cold-war",
    "main_question": "still-love-me",
    "contact_status": "still-in-contact",
    "desired_outcome": "reconnect",
    "emotional_risk": "calm",
    "analysis_date": "2026-05-23",
    "timing_scan_days": 0,
}

CHART_SCENARIOS = [
    ("aries-libra", ("1992-04-05", "06:15", "Taipei, Taiwan"), ("1990-10-08", "18:40", "Taichung, Taiwan")),
    ("taurus-scorpio", ("1989-05-12", "21:20", "Kaohsiung, Taiwan"), ("1993-11-18", "04:55", "Tainan, Taiwan")),
    ("gemini-sagittarius", ("1995-06-02", "09:35", "New Taipei, Taiwan"), ("1991-12-11", "15:10", "Hsinchu, Taiwan")),
    ("cancer-capricorn", ("1994-07-14", "01:45", "Taipei, Taiwan"), ("1988-01-03", "12:25", "Taoyuan, Taiwan")),
    ("leo-aquarius", ("1996-08-19", "11:05", "Hong Kong"), ("1992-02-09", "23:30", "Singapore")),
    ("virgo-pisces", ("1990-09-07", "16:50", "Tokyo"), ("1997-03-12", "07:05", "Seoul")),
    ("libra-aries", ("1993-10-03", "05:25", "Taipei, Taiwan"), ("1995-04-16", "20:35", "Kaohsiung, Taiwan")),
    ("scorpio-taurus", ("1987-11-06", "14:05", "Taichung, Taiwan"), ("1994-05-01", "02:20", "Tainan, Taiwan")),
    ("sagittarius-gemini", ("1998-12-05", "19:45", "Hsinchu, Taiwan"), ("1990-06-19", "08:10", "Taipei, Taiwan")),
    ("capricorn-cancer", ("1991-01-16", "03:15", "Taoyuan, Taiwan"), ("1996-07-22", "13:50", "New Taipei, Taiwan")),
    ("safety-friction-water-fire", ("1988-01-31", "02:52", "Hsinchu, Taiwan"), ("1999-09-07", "03:14", "New Taipei, Taiwan")),
]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_saturn_process_boundary(cluster: dict[str, Any], label: str) -> None:
    boundary = cluster.get("saturnProcessBoundary") or {}
    assert_true(boundary.get("version") == "saturn-nonfatal-process-boundary-v1", f"{label} Saturn boundary missing")
    assert_true(boundary.get("role") == "pressure_process_not_fate", f"{label} Saturn boundary role mismatch")
    assert_true(boundary.get("canCreatePermanentOutcome") is False, f"{label} Saturn boundary must not create permanent outcomes")
    assert_true(boundary.get("canProveInnerState") is False, f"{label} Saturn boundary must not prove inner state")
    blocked = set(boundary.get("cannotClaim") or [])
    for key in ("permanent_rejection", "doomed_relationship", "fated_waiting", "secret_love_proof"):
        assert_true(key in blocked, f"{label} Saturn boundary missing blocked claim {key}")
    assert_true(
        SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(set(boundary.get("sourceClaimIds") or [])),
        f"{label} Saturn source claims missing",
    )
    assert_true(
        SATURN_BOUNDARY_METHOD_CLAIM in set(boundary.get("methodClaimIds") or []),
        f"{label} Saturn method claim missing",
    )


def person(birth_date: str, birth_time: str | None, birth_place: str, gender: str) -> dict[str, Any]:
    return {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_timezone": "Asia/Taipei",
        "birth_place": birth_place,
        "gender": gender,
    }


def reading_for(scenario_id: str, person_a: tuple[str, str | None, str], person_b: tuple[str, str | None, str]) -> dict[str, Any]:
    return {
        "reading_id": f"chart-matrix-{scenario_id}",
        "person_a": person(*person_a, gender="female"),
        "person_b": person(*person_b, gender="male"),
        "context": dict(BASE_CONTEXT),
    }


def build_vm(reading: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = build_payload(reading, include_drafts=True, select=True)
    view_model = build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)
    rendered = json.dumps(view_model, ensure_ascii=False).lower()
    for term in LEGACY_TERMS:
        assert_true(term.lower() not in rendered, f"legacy term leaked into chart matrix view model: {term}")
    return payload, view_model


def case_file(view_model: dict[str, Any]) -> dict[str, Any]:
    case = view_model.get("westernRelationshipCaseFile")
    assert_true(isinstance(case, dict), "westernRelationshipCaseFile missing")
    assert_true(case.get("version") == "western-relationship-case-file-v1", "case file version mismatch")
    blueprint = view_model.get("readingBlueprint") or {}
    chapters = blueprint.get("chapters") or []
    assert_true(len(chapters) == 3, "blueprint chapter count mismatch")
    assert_true(len(blueprint.get("chapters") or []) == 3, "readingBlueprint.chapters missing")
    assert_true((case.get("timingLayer") or {}).get("windowScan", {}).get("status") == "not_calculated", "chart variation matrix should disable 60-day timing scan")
    return case


def assert_relationship_profile_copy(view_model: dict[str, Any]) -> None:
    profiles = view_model.get("relationshipProfiles") or {}
    assert_true(profiles.get("version") == "relationship-profiles-v1", "relationshipProfiles version mismatch")
    for person_key in ("personA", "personB"):
        person = profiles.get(person_key) or {}
        for card in person.get("cards") or []:
            readable = card.get("readableInterpretation") or {}
            visible_copy = " ".join(
                str(value or "")
                for value in (
                    readable.get("meaning"),
                    readable.get("body"),
                    readable.get("stuckPattern"),
                    card.get("naturalResponse"),
                    card.get("tensionPattern"),
                )
            )
            for bad in AWKWARD_PROFILE_COPY:
                assert_true(bad not in visible_copy, f"{person_key} profile card still has awkward copy: {bad}")
            assert_true("這張卡看的是" in str(readable.get("meaning") or ""), f"{person_key} profile meaning should explain card purpose")
            assert_true("落在" in str(readable.get("meaning") or ""), f"{person_key} profile meaning should explain sign placement")
            if person_key == "personB":
                assert_true("對方" not in str(readable.get("body") or ""), f"{person_key} body should use native pronoun copy")
                assert_true("對方" not in str(readable.get("stuckPattern") or ""), f"{person_key} stuck pattern should use native pronoun copy")
    fit = profiles.get("fitSummary") or {}
    summary_text = " ".join(
        str(value or "")
        for value in (
            profiles.get("principle"),
            fit.get("headline"),
            fit.get("summary"),
            (fit.get("readableInterpretation") or {}).get("headline"),
            (fit.get("readableInterpretation") or {}).get("body"),
        )
    )
    for bad in ("需要翻譯", "需要更多翻譯", "壓力反應容易誤會"):
        assert_true(bad not in summary_text, f"fit summary copy still uses awkward wording: {bad}")

    for bucket in ("natural", "effort", "friction"):
        for item in fit.get(bucket) or []:
            item_readable = item.get("readableInterpretation") or {}
            body = str(item_readable.get("body") or item.get("body") or "")
            next_move = str(item.get("nextMove") or item_readable.get("nextMove") or "")
            title_text = " ".join(
                str(value or "")
                for value in (
                    item.get("title"),
                    item.get("relationLabel"),
                    item_readable.get("headline"),
                )
            )
            for bad in (
                "你比較用",
                "處理界線與壓力",
                "這一項比較容易互相懂",
                "對話和空間處理",
                "土星這一塊",
                "壓力反應容易誤會",
            ):
                assert_true(bad not in body, f"{bucket} fit item still uses awkward body copy: {bad}")
            assert_true("需要翻譯" not in title_text, f"{bucket} fit item still uses internal relation label")
            assert_true("翻譯清楚" not in next_move, f"{bucket} fit item next move still uses awkward translation copy")

    pivotal = fit.get("pivotalAspect")
    if pivotal:
        pivotal_readable = pivotal.get("readableInterpretation") or {}
        pair_template = pivotal.get("pairContactTemplate") or {}
        source_claim_ids = {str(claim_id) for claim_id in pivotal_readable.get("sourceClaimIds") or []}
        visible_copy = " ".join(
            str(value or "")
            for value in (
                pivotal.get("title"),
                pivotal.get("body"),
                pivotal.get("nextMove"),
                pivotal.get("pairContactTemplateMeaning"),
                pivotal.get("pairContactTemplateGuardrail"),
                pivotal_readable.get("meaning"),
                pivotal_readable.get("body"),
                pivotal_readable.get("nextMove"),
            )
        )
        assert_true(pivotal.get("point") == "PivotalAspect", "pivotal aspect fit item point mismatch")
        assert_true(pivotal.get("relation") in {"natural", "effort", "friction"}, "pivotal aspect relation invalid")
        assert_true("western-aspect-function-combination-reducers-005" in source_claim_ids, "pivotal aspect source claim missing")
        assert_true("關鍵合盤相位" in visible_copy, "pivotal aspect copy should explain the card purpose")
        assert_true("完整相位清單" in visible_copy, "pivotal aspect copy should reject aspect dump behavior")
        assert_true(pair_template.get("atomId"), "pivotal aspect should expose pair-contact template atom")
        assert_true(pair_template.get("claimIds"), "pivotal aspect should expose pair-contact template claims")
        assert_true(pivotal.get("pairContactTemplateMeaning"), "pivotal aspect should expose pair-family meaning")
        assert_true(pivotal.get("pairContactTemplateGuardrail"), "pivotal aspect should expose pair-family guardrail")
        assert_true("行星互動" in visible_copy, "pivotal aspect copy should name the pair-family interpretation layer")
        assert_true(
            any(term in str(pivotal.get("pairContactTemplateGuardrail") or "") for term in ("不證明", "不保證", "不等於", "不能")),
            "pivotal aspect guardrail should block single-aspect verdicts",
        )
        for bad in ("pivotal interaspect", "aspect dump", "technical dump"):
            assert_true(bad not in visible_copy, f"pivotal aspect copy leaked method jargon: {bad}")


def assert_function_clusters(
    case: dict[str, Any],
    sign_coverage: dict[str, set[str]],
    element_coverage: dict[str, set[str]],
    modality_coverage: dict[str, set[str]],
    low_confidence_counter: Counter[str],
) -> None:
    clusters = case.get("evidenceClusters") or {}
    for cluster_key, point in FUNCTION_CLUSTERS.items():
        cluster = clusters.get(cluster_key) or {}
        assert_true(cluster.get("point") == point, f"{cluster_key} point mismatch")
        assert_true(cluster.get("atomId"), f"{cluster_key} atom missing")
        assert_true(len(cluster.get("personStyles") or []) == 2, f"{cluster_key} should have two person styles")
        assert_true(cluster.get("claimSupport"), f"{cluster_key} claim support missing")
        claim_ids = set(str(claim_id) for claim_id in cluster.get("claimIds") or [])
        assert_true(FUNCTION_TEMPLATE_CLAIMS[cluster_key] in claim_ids, f"{cluster_key} missing function template claim")
        if cluster_key == "saturnSignDefenseDelay":
            assert_true(SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(claim_ids), "saturnSignDefenseDelay Greene source claims missing")
            assert_saturn_process_boundary(cluster, cluster_key)
        assert_true(
            any(claim_id.startswith("western-individual-sign-meanings-hand-") for claim_id in claim_ids),
            f"{cluster_key} missing selected sign claim",
        )
        assert_true(any(claim_id.startswith("western-function-element-templates-") for claim_id in claim_ids), f"{cluster_key} missing function element claim")
        assert_true(any(claim_id.startswith("western-function-modality-templates-") for claim_id in claim_ids), f"{cluster_key} missing function modality claim")
        for style in cluster.get("personStyles") or []:
            assert_true(style.get("element") in ELEMENT_CLAIMS, f"{cluster_key} person style missing element")
            assert_true(style.get("elementLabel"), f"{cluster_key} person style missing element label")
            assert_true(style.get("elementStyle"), f"{cluster_key} person style missing element style")
            assert_true(style.get("modality") in MODALITY_CLAIMS, f"{cluster_key} person style missing modality")
            assert_true(style.get("modalityLabel"), f"{cluster_key} person style missing modality label")
            assert_true(style.get("modalityStyle"), f"{cluster_key} person style missing modality style")
        sign_coverage[point].update(str(sign) for sign in cluster.get("selectedSigns") or [])
        element_coverage[point].update(str(element) for element in cluster.get("selectedElements") or [])
        modality_coverage[point].update(str(modality) for modality in cluster.get("selectedModalities") or [])
        if cluster.get("lowConfidenceCount"):
            low_confidence_counter[point] += int(cluster.get("lowConfidenceCount") or 0)

    element_matrix = clusters.get("functionElementMatrix") or {}
    assert_true(element_matrix.get("atomId") == "western-atom-function-element-matrix", "function element matrix atom mismatch")
    assert_true(element_matrix.get("source") == "western-function-element-templates", "function element matrix source mismatch")
    assert_true(element_matrix.get("itemCount") == 10, "function element matrix should cover 10 function placements")
    assert_true(element_matrix.get("claimSupport"), "function element matrix claim support missing")
    assert_true(set(element_matrix.get("selectedElements") or []).issubset(ELEMENT_CLAIMS), "function element matrix selected unknown element")
    assert_true("單獨證明" in str(element_matrix.get("doesNotProve") or ""), "function element matrix missing non-verdict guardrail")
    assert_true(sum(int(element_matrix.get(key) or 0) for key in ("fireCount", "earthCount", "airCount", "waterCount")) == 10, "function element counts should sum to 10")

    modality_matrix = clusters.get("functionModalityMatrix") or {}
    assert_true(modality_matrix.get("atomId") == "western-atom-function-modality-matrix", "function modality matrix atom mismatch")
    assert_true(modality_matrix.get("source") == "western-function-modality-templates", "function modality matrix source mismatch")
    assert_true(modality_matrix.get("itemCount") == 10, "function modality matrix should cover 10 function placements")
    assert_true(modality_matrix.get("claimSupport"), "function modality matrix claim support missing")
    assert_true(set(modality_matrix.get("selectedModalities") or []).issubset(MODALITY_CLAIMS), "function modality matrix selected unknown modality")
    assert_true("單獨證明" in str(modality_matrix.get("doesNotProve") or ""), "function modality matrix missing non-verdict guardrail")
    assert_true(sum(int(modality_matrix.get(key) or 0) for key in ("cardinalCount", "fixedCount", "mutableCount")) == 10, "function modality counts should sum to 10")


def assert_aspect_function_combination_cluster(case: dict[str, Any]) -> set[str]:
    cluster = (case.get("evidenceClusters") or {}).get("aspectFunctionCombination") or {}
    assert_true(cluster.get("atomId") == "western-atom-aspect-function-combination", "aspect function combination atom mismatch")
    assert_true(cluster.get("source") == "western-aspect-function-combination-reducers", "aspect function combination source mismatch")
    assert_true(cluster.get("claimSupport"), "aspect function combination claim support missing")
    selected = cluster.get("selectedCombinations") or []
    assert_true(selected, "aspect function combination selected list missing")
    repeated_reducer = cluster.get("repeatedThemeReducer") or {}
    assert_true(repeated_reducer.get("version") == "repeated-theme-reducer-v1", "aspect repeated-theme reducer missing")
    assert_true(
        "burk-repeated-themes-outweigh-single-contacts" in set(repeated_reducer.get("methodClaimIds") or []),
        "aspect repeated-theme method claim missing",
    )
    covered_pairs: set[str] = set()
    for item in selected:
        pair_key = str(item.get("pairKey") or "")
        covered_pairs.add(pair_key)
        assert_true(pair_key in ASPECT_FUNCTION_SOURCE_CLAIMS, f"unknown aspect function pair: {pair_key}")
        assert_true(item.get("sourceClaimId") == ASPECT_FUNCTION_SOURCE_CLAIMS[pair_key], f"{pair_key} source claim mismatch")
        expected_method_claims = PAIR_TEMPLATE_METHOD_CLAIMS.get(pair_key) or set()
        if expected_method_claims:
            assert_true(
                expected_method_claims.issubset(set(item.get("methodClaimIds") or [])),
                f"{pair_key} method claims missing on selected combination",
            )
        assert_true(item.get("aspectSource", "").startswith("western-aspects-"), f"{pair_key} aspect source missing")
        assert_true(item.get("functionSynthesis"), f"{pair_key} function synthesis missing")
        assert_true(item.get("reducerInstruction"), f"{pair_key} reducer instruction missing")
        assert_true(item.get("themeKeys"), f"{pair_key} repeated-theme keys missing")
        assert_true(len(item.get("pointStyles") or []) == 2, f"{pair_key} point styles missing")
        assert_true((item.get("contactModifier") or {}).get("source") == "western-aspect-contact-type-modifiers", f"{pair_key} contact modifier missing")
        assert_true((item.get("precision") or {}).get("display") in {"allowed", "allowed_with_uncertainty"}, f"{pair_key} precision gate invalid")
    if cluster.get("hasSaturnFunctionPressure"):
        assert_true(SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(set(cluster.get("claimIds") or [])), "aspect Saturn Greene source claims missing")
        assert_saturn_process_boundary(cluster, "aspectFunctionCombination")
    covered_pairs.update(str(pair_key) for pair_key in cluster.get("detectedPairs") or [] if pair_key)
    return covered_pairs


def assert_sun_moon_asc_profile_cluster(
    case: dict[str, Any],
    *,
    expected_item_count: int | None = None,
    expected_blocked_count: int | None = None,
    expected_reliable_ascendant: bool | None = None,
    min_low_moon_confidence: int = 0,
) -> None:
    cluster = (case.get("evidenceClusters") or {}).get("sunMoonAscProfile") or {}
    assert_true(cluster.get("atomId") == "western-atom-sun-moon-asc-profile", "sun Moon Asc profile atom mismatch")
    assert_true(cluster.get("source") == "western-sun-moon-asc-profile-george-bloch", "sun Moon Asc profile source mismatch")
    assert_true(cluster.get("claimSupport"), "sun Moon Asc profile claim support missing")
    assert_true(cluster.get("hasSunMoonProfile") is True, "sun Moon Asc profile should keep both Sun/Moon profiles")
    assert_true(cluster.get("hasBothPeopleProfile") is True, "sun Moon Asc profile should include both people")
    if expected_item_count is not None:
        assert_true(cluster.get("itemCount") == expected_item_count, f"sun Moon Asc item count mismatch: {cluster}")
    if expected_blocked_count is not None:
        assert_true(cluster.get("blockedCount") == expected_blocked_count, f"sun Moon Asc blocked count mismatch: {cluster}")
    if expected_reliable_ascendant is not None:
        assert_true(
            cluster.get("hasReliableAscendant") is expected_reliable_ascendant,
            f"sun Moon Asc reliable Ascendant mismatch: {cluster}",
        )
    assert_true(
        int(cluster.get("lowMoonConfidenceCount") or 0) >= min_low_moon_confidence,
        f"sun Moon Asc low Moon confidence too low: {cluster}",
    )


def assert_full_chart(case: dict[str, Any], payload: dict[str, Any]) -> tuple[set[str], dict[str, int], set[str], set[str]]:
    quality = case.get("inputQuality") or {}
    assert_true(quality.get("overall") == "high", "full chart should keep high input quality")
    clusters = case.get("evidenceClusters") or {}
    assert_sun_moon_asc_profile_cluster(
        case,
        expected_item_count=6,
        expected_blocked_count=0,
        expected_reliable_ascendant=True,
    )
    assert_true(clusters.get("ascendantImpression", {}).get("itemCount") == 2, "full chart should allow Asc impressions")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("itemCount", 0) > 0, "full chart should allow house factors")

    synastry_counts = {key: len((case.get("synastryLayer") or {}).get(key) or []) for key in REQUIRED_SYNASTRY_BUCKETS}
    for key, count in synastry_counts.items():
        assert_true(count > 0, f"full chart missing synastry bucket: {key}")
    contact_modifiers: set[str] = set()
    for key in REQUIRED_SYNASTRY_BUCKETS:
        for item in (case.get("synastryLayer") or {}).get(key) or []:
            modifier = item.get("contactModifier") or {}
            assert_true(modifier.get("source") == "western-aspect-contact-type-modifiers", f"{key} contact modifier source missing")
            assert_true(modifier.get("claimIds"), f"{key} contact modifier claim ids missing")
            assert_true(modifier.get("claimSupport"), f"{key} contact modifier claim support missing")
            contact_modifiers.add(str(modifier.get("type") or ""))
    pair_contact_templates: set[str] = set()
    for key in REQUIRED_SYNASTRY_BUCKETS:
        for item in (case.get("synastryLayer") or {}).get(key) or []:
            source = str(item.get("source") or "")
            if source not in PAIR_TEMPLATE_SOURCE_IDS:
                continue
            template = item.get("pairContactTemplate") or {}
            assert_true(
                template.get("source") in {"western-aspect-pair-contact-phrase-templates", *PAIR_TEMPLATE_SOURCE_IDS},
                f"{key} pair-contact template source missing",
            )
            assert_true(template.get("claimIds"), f"{key} pair-contact template claim ids missing")
            assert_true(template.get("claimSupport"), f"{key} pair-contact template claim support missing")
            pair_contact_templates.add(f"{template.get('source') or source}:{template.get('contactType')}")

    signals = {str(signal.get("id")) for signal in (payload.get("candidate_signals") or {}).get("western_signals") or []}
    assert_true(bool(signals), "full chart should produce Western candidate signals")
    aspect_function = clusters.get("aspectFunctionCombination") or {}
    if "western-aspects-mercury-jupiter" in signals:
        assert_true(
            "western-aspects-mercury-jupiter" in set(aspect_function.get("detectedSources") or []),
            "Mercury-Jupiter signal should be detected by aspect function cluster",
        )
        assert_true(
            aspect_function.get("hasMercuryJupiterSupport") is True
            or aspect_function.get("hasMercuryJupiterHard") is True,
            "Mercury-Jupiter signal should expose support/hard reducer flags",
        )
    if "western-aspects-outer-planet-intensity-families" in signals:
        assert_true(
            aspect_function.get("hasOuterPlanetIntensity") is True,
            "outer-planet signal should expose outer intensity reducer flag",
        )
    return signals, synastry_counts, contact_modifiers, pair_contact_templates


def assert_missing_city_precision(case: dict[str, Any]) -> None:
    quality = case.get("inputQuality") or {}
    assert_true(quality.get("personA", {}).get("precision") == "location_fallback", "personA should use location_fallback")
    assert_true(quality.get("personB", {}).get("precision") == "location_fallback", "personB should use location_fallback")
    clusters = case.get("evidenceClusters") or {}
    assert_true(clusters.get("ascendantImpression", {}).get("blockedCount") == 1, "missing city should block Asc claims")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("blockedCount") == 1, "missing city should block house claims")
    assert_sun_moon_asc_profile_cluster(
        case,
        expected_item_count=4,
        expected_blocked_count=2,
        expected_reliable_ascendant=False,
    )


def assert_no_birth_time_precision(case: dict[str, Any]) -> None:
    quality = case.get("inputQuality") or {}
    assert_true(quality.get("personA", {}).get("precision") == "date_only", "personA should be date_only")
    assert_true(quality.get("personB", {}).get("precision") == "date_only", "personB should be date_only")
    clusters = case.get("evidenceClusters") or {}
    assert_true(clusters.get("moonSignEmotionalSafety", {}).get("lowConfidenceCount", 0) >= 2, "date-only Moon styles should be low confidence")
    assert_true(clusters.get("ascendantImpression", {}).get("blockedCount") == 1, "missing time should block Asc claims")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("blockedCount") == 1, "missing time should block house claims")
    assert_sun_moon_asc_profile_cluster(
        case,
        expected_item_count=4,
        expected_blocked_count=2,
        expected_reliable_ascendant=False,
        min_low_moon_confidence=2,
    )


def assert_unknown_city_precision(case: dict[str, Any], payload: dict[str, Any]) -> None:
    warnings = payload.get("debug", {}).get("calculation_warnings") or []
    assert_true(any("Unknown birth_place" in str(warning) for warning in warnings), "unknown city warning missing")
    quality = case.get("inputQuality") or {}
    assert_true(quality.get("personA", {}).get("precision") == "unavailable", "unknown city should mark personA unavailable")
    assert_true(quality.get("overall") == "low", "unknown city should downgrade overall precision")
    assert_true(not any((case.get("synastryLayer") or {}).values()), "unknown city should not invent synastry evidence")


def run_full_chart_matrix() -> None:
    sign_coverage: dict[str, set[str]] = defaultdict(set)
    element_coverage: dict[str, set[str]] = defaultdict(set)
    modality_coverage: dict[str, set[str]] = defaultdict(set)
    low_confidence_counter: Counter[str] = Counter()
    signal_coverage: set[str] = set()
    synastry_bucket_totals: Counter[str] = Counter()
    contact_modifier_coverage: set[str] = set()
    pair_template_coverage: set[str] = set()
    aspect_function_pair_coverage: set[str] = set()
    safety_validation_relation_coverage: set[str] = set()

    for scenario_id, person_a, person_b in CHART_SCENARIOS:
        payload, view_model = build_vm(reading_for(scenario_id, person_a, person_b))
        case = case_file(view_model)
        assert_relationship_profile_copy(view_model)
        assert_function_clusters(case, sign_coverage, element_coverage, modality_coverage, low_confidence_counter)
        safety_validation_relation_coverage.add(
            str(
                ((case.get("evidenceClusters") or {}).get("safetyValidationLanguage") or {}).get("dominantContactType")
                or ""
            )
        )
        aspect_function_pair_coverage.update(assert_aspect_function_combination_cluster(case))
        signals, bucket_counts, contact_modifiers, pair_contact_templates = assert_full_chart(case, payload)
        signal_coverage.update(signals)
        synastry_bucket_totals.update(bucket_counts)
        contact_modifier_coverage.update(contact_modifiers)
        pair_template_coverage.update(pair_contact_templates)

    all_function_signs = set().union(*sign_coverage.values())
    assert_true(len(all_function_signs) == 12, f"function-sign layer should cover all 12 signs, got {sorted(all_function_signs)}")
    assert_true(len(sign_coverage["Moon"]) >= 8, f"Moon sign coverage too thin: {sorted(sign_coverage['Moon'])}")
    assert_true(len(sign_coverage["Mercury"]) >= 8, f"Mercury sign coverage too thin: {sorted(sign_coverage['Mercury'])}")
    assert_true(len(sign_coverage["Venus"]) >= 8, f"Venus sign coverage too thin: {sorted(sign_coverage['Venus'])}")
    assert_true(len(sign_coverage["Mars"]) >= 8, f"Mars sign coverage too thin: {sorted(sign_coverage['Mars'])}")
    assert_true(len(sign_coverage["Saturn"]) >= 4, f"Saturn sign coverage too thin: {sorted(sign_coverage['Saturn'])}")
    all_function_elements = set().union(*element_coverage.values())
    all_function_modalities = set().union(*modality_coverage.values())
    assert_true(all_function_elements == set(ELEMENT_CLAIMS), f"function-element layer should cover all elements, got {sorted(all_function_elements)}")
    assert_true(all_function_modalities == set(MODALITY_CLAIMS), f"function-modality layer should cover all modalities, got {sorted(all_function_modalities)}")
    for point in ("Moon", "Mercury", "Venus", "Mars", "Saturn"):
        assert_true(len(element_coverage[point]) >= 3, f"{point} element coverage too thin: {sorted(element_coverage[point])}")
        assert_true(len(modality_coverage[point]) >= 2, f"{point} modality coverage too thin: {sorted(modality_coverage[point])}")
    missing_signals = REQUIRED_SIGNAL_IDS - signal_coverage
    assert_true(not missing_signals, f"signal coverage missing: {sorted(missing_signals)}")
    assert_true(REQUIRED_SYNASTRY_BUCKETS.issubset(synastry_bucket_totals), "synastry bucket coverage missing")
    missing_modifiers = REQUIRED_CONTACT_MODIFIERS - contact_modifier_coverage
    assert_true(not missing_modifiers, f"contact modifier coverage missing: {sorted(missing_modifiers)}")
    missing_safety_validation_relations = REQUIRED_SAFETY_VALIDATION_RELATIONS - safety_validation_relation_coverage
    assert_true(
        not missing_safety_validation_relations,
        f"safety-validation relation coverage missing: {sorted(missing_safety_validation_relations)}",
    )
    missing_pair_templates = REQUIRED_PAIR_CONTACT_TEMPLATES - pair_template_coverage
    assert_true(not missing_pair_templates, f"pair-contact template coverage missing: {sorted(missing_pair_templates)}")
    missing_aspect_function_pairs = REQUIRED_ASPECT_FUNCTION_PAIRS - aspect_function_pair_coverage
    assert_true(not missing_aspect_function_pairs, f"aspect function pair coverage missing: {sorted(missing_aspect_function_pairs)}")

    print("Western chart variation matrix passed")
    print(f"- full chart scenarios: {len(CHART_SCENARIOS)}")
    print(f"- function signs covered: {len(all_function_signs)}/12")
    for point in ("Moon", "Mercury", "Venus", "Mars", "Saturn"):
        print(f"- {point} signs: {len(sign_coverage[point])} -> {', '.join(sorted(sign_coverage[point]))}")
        print(f"  elements: {', '.join(sorted(element_coverage[point]))}; modalities: {', '.join(sorted(modality_coverage[point]))}")
    print(f"- candidate signal ids: {len(signal_coverage)}")
    print(f"- synastry bucket totals: {dict(sorted(synastry_bucket_totals.items()))}")
    print(f"- contact modifiers: {', '.join(sorted(contact_modifier_coverage))}")
    print(f"- safety-validation relations: {', '.join(sorted(safety_validation_relation_coverage))}")
    print(f"- pair-contact templates: {len(pair_template_coverage)}")
    print(f"- aspect-function pairs: {', '.join(sorted(aspect_function_pair_coverage))}")
    print(f"- low-confidence function styles: {dict(low_confidence_counter)}")


def run_precision_variants() -> None:
    _, person_a, person_b = CHART_SCENARIOS[0]

    missing_city = reading_for("precision-missing-city", person_a, person_b)
    missing_city["person_a"]["birth_place"] = ""
    missing_city["person_b"]["birth_place"] = ""
    payload, view_model = build_vm(missing_city)
    assert_missing_city_precision(case_file(view_model))
    assert_relationship_profile_copy(view_model)

    no_birth_time = reading_for("precision-no-birth-time", person_a, person_b)
    no_birth_time["person_a"]["birth_time"] = None
    no_birth_time["person_b"]["birth_time"] = None
    payload, view_model = build_vm(no_birth_time)
    assert_no_birth_time_precision(case_file(view_model))
    assert_relationship_profile_copy(view_model)

    unknown_city = reading_for("precision-unknown-city", person_a, person_b)
    unknown_city["person_a"]["birth_place"] = "Atlantis"
    payload, view_model = build_vm(unknown_city)
    assert_unknown_city_precision(case_file(view_model), payload)
    assert_relationship_profile_copy(view_model)

    print("- precision variants: missing_city, no_birth_time, unknown_city")


def run_function_matrix_rule_variant() -> None:
    scenario_id, person_a, person_b = CHART_SCENARIOS[2]
    reading = reading_for(f"function-matrix-rule-{scenario_id}", person_a, person_b)
    reading["context"]["main_question"] = "what-did-i-do-wrong"
    reading["context"]["desired_outcome"] = "understand"
    reading["context"]["contact_status"] = "no-contact"
    reading["context"]["emotional_risk"] = "calm"
    _, view_model = build_vm(reading)
    case = case_file(view_model)
    assert_relationship_profile_copy(view_model)
    answer = case.get("answerLayer") or {}
    clusters = case.get("evidenceClusters") or {}
    assert_true(answer.get("ruleId") == "western-rule-what-wrong-function-water-pressure", "function-element water pressure rule should be selectable")
    assert_true(clusters.get("functionElementMatrix", {}).get("hasWaterMoonOrVenus") is True, "water Moon/Venus selector should be true")
    assert_true(
        any("行星功能元素" in str(item) for item in answer.get("because") or []),
        "function matrix rule should surface functionElementMatrix in answer evidence",
    )
    print("- function matrix rule variant: water Moon/Venus pressure")


def run_aspect_function_flag_variant() -> None:
    fixture = {
        "western": {
            "people": {
                "person_a": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": {
                        "mercury": {"sign": "Gemini", "sign_element": "Air"},
                        "venus": {"sign": "Scorpio", "sign_element": "Water"},
                    },
                },
                "person_b": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": {
                        "jupiter": {"sign": "Libra", "sign_element": "Air"},
                        "uranus": {"sign": "Aquarius", "sign_element": "Air"},
                    },
                },
            },
            "synastry": {
                "inter_aspects": [
                    {
                        "person_a_point": "Mercury",
                        "person_b_point": "Jupiter",
                        "aspect": "Trine",
                        "orb": 0.8,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Venus",
                        "person_b_point": "Uranus",
                        "aspect": "Square",
                        "orb": 0.7,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                ]
            },
        }
    }
    cluster = western_aspect_function_combination_cluster(fixture, load_structured_kb())
    assert_true(cluster.get("hasMercuryJupiterSupport") is True, "Mercury-Jupiter support flag missing")
    assert_true(cluster.get("hasOuterPlanetIntensity") is True, "outer intensity flag missing")
    assert_true(cluster.get("hasOuterPlanetHardIntensity") is True, "outer hard intensity flag missing")
    assert_true("western-aspects-mercury-jupiter" in set(cluster.get("detectedSources") or []), "Mercury-Jupiter detected source missing")
    assert_true(
        "western-aspects-outer-planet-intensity-families" in set(cluster.get("detectedSources") or []),
        "outer intensity detected source missing",
    )
    print("- aspect function flag variant: Mercury-Jupiter + outer intensity")


def run_pivotal_interaspect_selection_variant() -> None:
    fixture = {
        "western": {
            "people": {
                "person_a": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": dict(SYNTHETIC_OBJECTS),
                },
                "person_b": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": dict(SYNTHETIC_OBJECTS),
                },
            },
            "synastry": {
                "inter_aspects": [
                    {
                        "person_a_point": "Moon",
                        "person_b_point": "Saturn",
                        "aspect": "Square",
                        "orb": 0.1,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Mercury",
                        "person_b_point": "Sun",
                        "aspect": "Square",
                        "orb": 0.3,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Venus",
                        "person_b_point": "Mars",
                        "aspect": "Trine",
                        "orb": 0.6,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Sun",
                        "person_b_point": "Venus",
                        "aspect": "Conjunction",
                        "orb": 1.0,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Mars",
                        "person_b_point": "Mars",
                        "aspect": "Trine",
                        "orb": 4.8,
                        "max_orb": 6,
                        "applying": False,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Moon",
                        "person_b_point": "Mars",
                        "aspect": "Conjunction",
                        "orb": 0.0,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": False,
                    },
                    {
                        "person_a_point": "Sun",
                        "person_b_point": "Moon",
                        "aspect": "Semisextile",
                        "orb": 0.2,
                        "max_orb": 2,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                ]
            },
        }
    }
    cluster = western_aspect_function_combination_cluster(fixture, load_structured_kb())
    selected = cluster.get("selectedCombinations") or []
    selected_pairs = [str(item.get("pairKey") or "") for item in selected]
    selected_contact_types = [str(item.get("contactType") or "") for item in selected]
    assert_true(len(selected) == 4, f"pivotal interaspect reducer should keep 4 selected rows, got {len(selected)}")
    assert_true(
        selected_pairs == ["Moon-Saturn", "Mercury-Sun", "Venus-Mars", "Sun-Venus"],
        f"pivotal interaspect ordering drifted: {selected_pairs}",
    )
    assert_true(
        selected_contact_types == ["hard", "hard", "soft", "conjunction"],
        f"pivotal interaspect contact types drifted: {selected_contact_types}",
    )
    assert_true("Mars-Mars" not in selected_pairs, "weak fifth aspect should not enter pivotal selections")
    assert_true("Moon-Mars" not in selected_pairs, "ineligible exact aspect should not enter pivotal selections")
    assert_true("Sun-Moon" not in selected_pairs, "minor contact should not enter pivotal function selections")
    assert_true(cluster.get("dominantPairKey") == "Moon-Saturn", "strongest pivotal pair should be Moon-Saturn")
    assert_true(cluster.get("dominantContactType") == "hard", "strongest pivotal contact type should be hard")
    assert_true(cluster.get("hasHardFunctionCombination") is True, "hard pivotal contact flag missing")
    assert_true(cluster.get("hasMoonSaturnPressure") is True, "Moon-Saturn pressure flag missing")
    assert_true(cluster.get("hasMercurySunHard") is True, "Mercury-Sun hard flag missing")
    repeated_reducer = cluster.get("repeatedThemeReducer") or {}
    repeated_themes = repeated_reducer.get("repeatedThemes") or []
    attraction_theme = next((item for item in repeated_themes if item.get("themeKey") == "attraction_pursuit"), None)
    assert_true(repeated_reducer.get("version") == "repeated-theme-reducer-v1", "repeated theme reducer version missing")
    assert_true(
        "burk-repeated-themes-outweigh-single-contacts" in set(repeated_reducer.get("methodClaimIds") or []),
        "repeated theme reducer should cite Burk repeated-theme method claim",
    )
    assert_true(cluster.get("hasRepeatedThemeEvidence") is True, "repeated theme evidence flag missing")
    assert_true(cluster.get("hasRepeatedAttractionPursuit") is True, "repeated attraction/pursuit theme flag missing")
    assert_true(attraction_theme is not None, "repeated attraction/pursuit theme missing")
    assert_true(
        {"Venus-Mars", "Sun-Venus"}.issubset(set((attraction_theme or {}).get("pairKeys") or [])),
        f"repeated attraction/pursuit should include Venus-Mars and Sun-Venus: {attraction_theme}",
    )
    for item in selected:
        assert_true(item.get("sourceClaimId") == ASPECT_FUNCTION_SOURCE_CLAIMS[item.get("pairKey")], "pivotal source claim mismatch")
        assert_true(item.get("pairContactTemplate"), "pivotal item should attach pair contact template")
        assert_true(item.get("functionSynthesis"), "pivotal item missing function synthesis")
        assert_true(item.get("themeKeys"), "pivotal item missing repeated-theme keys")
        assert_true(len(item.get("pointStyles") or []) == 2, "pivotal item missing function point styles")
        assert_true((item.get("precision") or {}).get("display") == "allowed", "pivotal item precision should be allowed")
    print("- pivotal interaspect selection fixture: top 4 eligible major contacts")


def run_repeated_theme_reducer_variant() -> None:
    fixture = {
        "western": {
            "people": {
                "person_a": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": dict(SYNTHETIC_OBJECTS),
                },
                "person_b": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": dict(SYNTHETIC_OBJECTS),
                },
            },
            "synastry": {
                "inter_aspects": [
                    {
                        "person_a_point": "Moon",
                        "person_b_point": "Saturn",
                        "aspect": "Square",
                        "orb": 0.1,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Venus",
                        "person_b_point": "Saturn",
                        "aspect": "Square",
                        "orb": 0.2,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Mars",
                        "person_b_point": "Saturn",
                        "aspect": "Opposition",
                        "orb": 0.3,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Mercury",
                        "person_b_point": "Sun",
                        "aspect": "Trine",
                        "orb": 1.0,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                    {
                        "person_a_point": "Venus",
                        "person_b_point": "Mars",
                        "aspect": "Trine",
                        "orb": 1.2,
                        "max_orb": 6,
                        "applying": True,
                        "eligible_for_signal": True,
                    },
                ]
            },
        }
    }
    cluster = western_aspect_function_combination_cluster(fixture, load_structured_kb())
    selected = cluster.get("selectedCombinations") or []
    selected_pairs = [str(item.get("pairKey") or "") for item in selected]
    repeated_reducer = cluster.get("repeatedThemeReducer") or {}
    repeated_themes = repeated_reducer.get("repeatedThemes") or []
    saturn_theme = next((item for item in repeated_themes if item.get("themeKey") == "saturn_pressure"), None)
    assert_true(len(selected) == 4, f"Saturn repeated-theme fixture should keep 4 selected rows, got {len(selected)}")
    assert_true(
        selected_pairs[:3] == ["Moon-Saturn", "Venus-Saturn", "Mars-Saturn"],
        f"Saturn repeated-theme ordering drifted: {selected_pairs}",
    )
    assert_true(cluster.get("hasRepeatedThemeEvidence") is True, "Saturn fixture repeated evidence flag missing")
    assert_true(cluster.get("hasRepeatedSaturnPressure") is True, "Saturn repeated pressure flag missing")
    assert_true(cluster.get("dominantRepeatedThemeKey") == "saturn_pressure", "Saturn pressure should be dominant repeated theme")
    assert_true(saturn_theme is not None, "Saturn repeated theme missing")
    assert_true(int((saturn_theme or {}).get("count") or 0) >= 3, f"Saturn repeated theme count too low: {saturn_theme}")
    assert_true(
        {"Moon-Saturn", "Venus-Saturn", "Mars-Saturn"}.issubset(set((saturn_theme or {}).get("pairKeys") or [])),
        f"Saturn repeated theme should include Moon/Venus/Mars Saturn pairs: {saturn_theme}",
    )
    for item in selected[:3]:
        assert_true("saturn_pressure" in set(item.get("reinforcedThemeKeys") or []), "selected Saturn item missing reinforced theme")
    print("- repeated-theme reducer fixture: Saturn pressure branch")


def pair_template_fixture(aspect: dict[str, Any]) -> dict[str, Any]:
    return {
        "western": {
            "people": {
                "person_a": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": dict(SYNTHETIC_OBJECTS),
                },
                "person_b": {
                    "birth_precision": "date_time",
                    "location_precision": "known",
                    "objects": dict(SYNTHETIC_OBJECTS),
                },
            },
            "synastry": {
                "inter_aspects": [aspect],
            },
        }
    }


def run_pair_template_v2_variant() -> None:
    structured_kb = load_structured_kb()
    covered: set[str] = set()
    for pair_key, (point_a, point_b, source, source_claim_id) in PAIR_TEMPLATE_V2_CASES.items():
        for contact_type, aspect_name in CONTACT_TYPE_ASPECTS.items():
            aspect = {
                "person_a_point": point_a,
                "person_b_point": point_b,
                "aspect": aspect_name,
                "orb": 0.8,
                "max_orb": 6,
                "applying": True,
                "eligible_for_signal": True,
            }
            template = western_aspect_pair_contact_template(aspect, structured_kb)
            assert_true(template is not None, f"{pair_key} {contact_type} pair template missing")
            assert_true(template.get("source") == source, f"{pair_key} {contact_type} template source mismatch")
            assert_true(source_claim_id in set(template.get("claimIds") or []), f"{pair_key} {contact_type} source claim missing")
            expected_method_claims = PAIR_TEMPLATE_METHOD_CLAIMS.get(pair_key) or set()
            if expected_method_claims:
                assert_true(
                    expected_method_claims.issubset(set(template.get("methodClaimIds") or [])),
                    f"{pair_key} {contact_type} template method claims missing",
                )
            assert_true(template.get("contactType") == contact_type, f"{pair_key} {contact_type} contact type mismatch")
            assert_true(template.get("interpretation"), f"{pair_key} {contact_type} interpretation missing")
            assert_true(template.get("doesNotProve"), f"{pair_key} {contact_type} guardrail missing")

            cluster = western_aspect_function_combination_cluster(pair_template_fixture(aspect), structured_kb)
            selected = (cluster.get("selectedCombinations") or [{}])[0]
            assert_true(selected.get("pairKey") == pair_key, f"{pair_key} {contact_type} function pair not selected")
            assert_true(selected.get("aspectSource") == source, f"{pair_key} {contact_type} function source mismatch")
            assert_true(selected.get("sourceClaimId") == ASPECT_FUNCTION_SOURCE_CLAIMS[pair_key], f"{pair_key} source claim mismatch")
            if expected_method_claims:
                assert_true(
                    expected_method_claims.issubset(set(selected.get("methodClaimIds") or [])),
                    f"{pair_key} {contact_type} selected method claims missing",
                )
                assert_true(
                    expected_method_claims.issubset(set(cluster.get("methodClaimIds") or [])),
                    f"{pair_key} {contact_type} cluster method claims missing",
                )
            assert_true(selected.get("contactType") == contact_type, f"{pair_key} selected contact mismatch")
            assert_true((selected.get("pairContactTemplate") or {}).get("atomId") == template.get("atomId"), f"{pair_key} pair template not attached")
            assert_true(len(selected.get("pointStyles") or []) == 2, f"{pair_key} point styles missing")
            covered.add(f"{pair_key}:{contact_type}")

    expected = {
        f"{pair_key}:{contact_type}"
        for pair_key in PAIR_TEMPLATE_V2_CASES
        for contact_type in CONTACT_TYPE_ASPECTS
    }
    missing = expected - covered
    assert_true(not missing, f"pair-template v2 coverage missing: {sorted(missing)}")
    print(f"- pair-template v2 synthetic coverage: {len(covered)} templates")


def main() -> int:
    run_full_chart_matrix()
    run_precision_variants()
    run_function_matrix_rule_variant()
    run_aspect_function_flag_variant()
    run_pivotal_interaspect_selection_variant()
    run_repeated_theme_reducer_variant()
    run_pair_template_v2_variant()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
