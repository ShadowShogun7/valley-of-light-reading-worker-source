#!/usr/bin/env python3
"""Smoke-test the Western 90-day timing selector contract."""

from __future__ import annotations

import copy
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


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
CONTACT_REDUCER_FIXTURES_PATH = ROOT / "examples" / "timing" / "contact-reducer-action-scenarios.json"
LEGACY_TERMS = ("bazi", "八字", "配偶星", "日主", "四柱", "十神")
SATURN_BOUNDARY_SOURCE_CLAIMS = {
    "western-aspects-saturn-pressure-001",
    "western-aspects-saturn-pressure-003",
}
SATURN_BOUNDARY_METHOD_CLAIM = "greene-saturn-defense-not-permanent-rejection"
CONTACT_ACTIONS = {"avoid_push", "low_pressure_message", "observe_for_soft_window", "observe_only", "not_calculated"}
REQUIRED_CONTACT_REDUCER_SCENARIOS = {
    "missing-timing-scan",
    "mercury-low-pressure-message",
    "venus-softening-message",
    "mixed-neutral-observe",
    "mars-activation-caution",
    "saturn-boundary-pressure",
    "background-observe-only",
}
TIMING_CLUSTERS = [
    "timingWindowBand",
    "timingMercuryCommunication",
    "timingVenusSoftening",
    "timingMarsActivation",
    "timingSaturnPressure",
    "timingMoonWeather",
    "timingContactReducer",
]
TIMING_ACTION_HEADLINE_NEEDLES = {
    "missing-timing-scan": "先用當下狀態判斷",
    "mercury-low-pressure-message": "短句把話說清楚",
    "venus-softening-message": "柔和釋放善意",
    "mixed-neutral-observe": "有柔和訊號",
    "mars-activation-caution": "先避開衝動傳訊",
    "saturn-boundary-pressure": "先避開逼近邊界",
    "background-observe-only": "目前先看",
}
FORBIDDEN_READABLE_TIMING = (
    "timing",
    "avoid_push",
    "low_pressure",
    "not_calculated",
    "reducer",
    "selector",
    "精準成功日期",
    "窗口",
    "低壓",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def blueprint_chapters(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    chapters = blueprint.get("chapters") or []
    return [chapter for chapter in chapters if isinstance(chapter, dict)]


def assert_exact_timing_policy(value: dict[str, Any], label: str) -> None:
    policy = value.get("exactTimingPolicy") or {}
    assert_true(value.get("preciseDatesAvailable") is False, f"{label} should expose preciseDatesAvailable=false")
    assert_true(policy.get("preciseDatesAvailable") is False, f"{label} exactTimingPolicy should block precise dates")


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


def timing_reading() -> dict[str, Any]:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "timing-window-90-day-scan"
    context = reading.setdefault("context", {})
    context["main_question"] = "when-to-contact"
    context["contact_status"] = "no-contact"
    context["desired_outcome"] = "reconnect"
    context["emotional_risk"] = "calm"
    context["analysis_date"] = "2026-05-23"
    context["timing_scan_days"] = 90
    context["timing_scan_step_days"] = 2
    return reading


def timing_reading_without_scan() -> dict[str, Any]:
    reading = timing_reading()
    reading["reading_id"] = "timing-contact-reducer-fixture-base"
    context = reading.setdefault("context", {})
    context["timing_scan_days"] = 0
    return reading


def read_fixture_scenarios() -> list[dict[str, Any]]:
    payload = read_json(CONTACT_REDUCER_FIXTURES_PATH)
    scenarios = payload.get("scenarios") or []
    assert_true(isinstance(scenarios, list) and scenarios, "contact reducer fixture scenarios missing")
    fixture_scenarios = [scenario for scenario in scenarios if isinstance(scenario, dict)]
    scenario_ids = {str(scenario.get("id") or "") for scenario in fixture_scenarios}
    missing_ids = REQUIRED_CONTACT_REDUCER_SCENARIOS - scenario_ids
    assert_true(not missing_ids, f"contact reducer fixture scenarios missing required ids: {sorted(missing_ids)}")
    return fixture_scenarios


def synthetic_windows(day_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for summary in day_summaries:
        band = str(summary.get("band") or "neutral")
        if current is None or current.get("band") != band:
            if current:
                windows.append(current)
            current = {
                "band": band,
                "start_date": summary.get("date"),
                "end_date": summary.get("date"),
                "sample_count": 1,
                "max_score": float(summary.get("score") or 0),
                "dominant_categories": [summary.get("strongest_category") or "background"],
            }
            continue
        current["end_date"] = summary.get("date")
        current["sample_count"] = int(current.get("sample_count") or 0) + 1
        current["max_score"] = max(float(current.get("max_score") or 0), float(summary.get("score") or 0))
        current.setdefault("dominant_categories", []).append(summary.get("strongest_category") or "background")
    if current:
        windows.append(current)
    return windows


def synthetic_timing_scan(scenario: dict[str, Any]) -> dict[str, Any]:
    sample_groups = scenario.get("samples") or []
    if not sample_groups:
        return {
            "method": "western-transit-window-scan-v1",
            "status": "not_calculated",
            "scan_days": 0,
            "granularity_days": 2,
            "sample_count": 0,
            "top_band": "neutral",
            "better_count": 0,
            "neutral_count": 0,
            "avoid_count": 0,
            "category_counts": {},
            "better_window_count": 0,
            "avoid_window_count": 0,
            "windows": [],
            "day_summaries": [],
            "timing_summary": "本次未執行未來三個月 timing scan。",
        }

    day_summaries: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    start_date = date(2026, 5, 27)
    index = 0
    for group in sample_groups:
        if not isinstance(group, dict):
            continue
        count = int(group.get("count") or 0)
        category = str(group.get("category") or "background")
        band = str(group.get("band") or "neutral")
        score = float(group.get("score") or 0)
        for _ in range(count):
            sample_date = start_date + timedelta(days=index * 2)
            day_summaries.append(
                {
                    "date": sample_date.isoformat(),
                    "band": band,
                    "score": score,
                    "score_components": {
                        "better": max(score, 0.0),
                        "avoid": abs(min(score, 0.0)),
                    },
                    "strongest_category": category,
                    "profile": {
                        "confidence": "medium" if category != "background" else "low",
                        "window_label": str(group.get("label") or category),
                        "relationship_meaning": str(group.get("meaning") or "synthetic timing reducer fixture"),
                        "strongest_category": category,
                        "strongest_label": str(group.get("label") or category),
                        "strongest_transit_point": str(group.get("transitPoint") or ""),
                        "strongest_natal_point": str(group.get("natalPoint") or ""),
                        "strongest_aspect": str(group.get("aspect") or ""),
                    },
                }
            )
            category_counts[category] = category_counts.get(category, 0) + 1
            index += 1

    band_counts = {
        "better": sum(1 for item in day_summaries if item.get("band") == "better"),
        "neutral": sum(1 for item in day_summaries if item.get("band") == "neutral"),
        "avoid": sum(1 for item in day_summaries if item.get("band") == "avoid"),
    }
    top_band = max(band_counts, key=lambda band: band_counts[band]) if day_summaries else "neutral"
    windows = synthetic_windows(day_summaries)
    return {
        "method": "western-transit-window-scan-v1",
        "status": "calculated",
        "scan_days": max(index * 2, 1),
        "granularity_days": 2,
        "sample_count": len(day_summaries),
        "top_band": top_band,
        "better_count": band_counts["better"],
        "neutral_count": band_counts["neutral"],
        "avoid_count": band_counts["avoid"],
        "category_counts": dict(sorted(category_counts.items())),
        "better_window_count": sum(1 for window in windows if window.get("band") == "better"),
        "avoid_window_count": sum(1 for window in windows if window.get("band") == "avoid"),
        "windows": windows,
        "day_summaries": day_summaries,
        "timing_summary": f"synthetic fixture {scenario.get('id')}: {top_band}",
    }


def assert_current_transits_include_mercury(payload: dict[str, Any]) -> None:
    transits = (payload.get("western") or {}).get("transits") or {}
    for person in ("person_a", "person_b"):
        chart = transits.get(person) or {}
        objects = chart.get("objects") or {}
        assert_true("mercury" in objects, f"{person} current transit Mercury object missing")


def assert_raw_scan(payload: dict[str, Any]) -> dict[str, Any]:
    scan = ((payload.get("western") or {}).get("analysis") or {}).get("timing_window_scan") or {}
    assert_true(scan.get("method") == "western-transit-window-scan-v1", "timing scan method mismatch")
    assert_true(scan.get("scan_days") == 90, "timing scan should cover exactly the next 90 days")
    assert_true(scan.get("sample_count", 0) > 0, "timing scan produced no samples")
    assert_true(scan.get("day_summaries"), "raw timing scan should keep day_summaries in calculation analysis")
    assert_true(scan.get("windows"), "raw timing scan should keep compressed windows in calculation analysis")
    return scan


def assert_public_scan(case: dict[str, Any], raw_scan: dict[str, Any]) -> None:
    window_scan = ((case.get("timingLayer") or {}).get("windowScan") or {})
    assert_true(window_scan.get("method") == "western-transit-window-scan-v1", "public windowScan method mismatch")
    assert_true(window_scan.get("sampleCount") == raw_scan.get("sample_count"), "public scan sample count mismatch")
    assert_exact_timing_policy(window_scan, "public windowScan")
    forbidden_keys = {"windows", "day_summaries", "daySummaries", "start_date", "end_date", "date"}
    assert_true(not forbidden_keys.intersection(window_scan), "public windowScan leaked exact date fields")
    rendered = json.dumps(window_scan, ensure_ascii=False)
    assert_true("start_date" not in rendered and "end_date" not in rendered, "public windowScan leaked date ranges")


def assert_timing_clusters(case: dict[str, Any]) -> None:
    clusters = case.get("evidenceClusters") or {}
    for cluster_key in TIMING_CLUSTERS:
        cluster = clusters.get(cluster_key) or {}
        assert_true(cluster.get("atomId"), f"{cluster_key} atom missing")
        assert_true(cluster.get("claimIds"), f"{cluster_key} claim ids missing")
        expected_source = "western-contact-timing-action-reducers" if cluster_key == "timingContactReducer" else "western-transits-timing-selector-windows"
        assert_true(cluster.get("source") == expected_source, f"{cluster_key} source mismatch")
        assert_exact_timing_policy(cluster, cluster_key)
        if cluster_key == "timingSaturnPressure":
            assert_true(SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(set(cluster.get("claimIds") or [])), "timingSaturnPressure Greene source claims missing")
            assert_saturn_process_boundary(cluster, cluster_key)

    band = clusters.get("timingWindowBand") or {}
    assert_true(band.get("sampleCount", 0) > 0, "timingWindowBand sample count missing")
    assert_true(band.get("topBand") in {"better", "neutral", "avoid"}, "timingWindowBand top band invalid")
    assert_true(band.get("betterCount", 0) + band.get("neutralCount", 0) + band.get("avoidCount", 0) == band.get("sampleCount"), "timingWindowBand counts do not match samples")

    mercury = clusters.get("timingMercuryCommunication") or {}
    assert_true(mercury.get("sampleCount", 0) > 0, "Mercury timing cluster should see scan samples")
    assert_true(mercury.get("confidence") in {"low", "medium"}, "Mercury timing confidence should stay bounded")

    moon = clusters.get("timingMoonWeather") or {}
    assert_true(moon.get("confidence") in {"low", "medium"}, "Moon timing confidence should stay bounded")
    assert_true("保證" in str(moon.get("doesNotProve") or ""), "Moon timing should explicitly avoid guarantee claims")

    contact = clusters.get("timingContactReducer") or {}
    assert_true(contact.get("atomId") == "western-atom-timing-contact-reducer", "timingContactReducer atom mismatch")
    contact_claim_ids = {str(claim_id) for claim_id in contact.get("claimIds") or []}
    assert_true("western-contact-timing-action-reducers-006" in contact_claim_ids, "timingContactReducer missing contact-status bid claim")
    assert_true("western-contact-timing-action-reducers-007" in contact_claim_ids, "timingContactReducer missing repair-tone claim")
    assert_true(contact.get("recommendedAction") in {"avoid_push", "low_pressure_message", "observe_for_soft_window", "observe_only", "not_calculated"}, "timingContactReducer action invalid")
    assert_true(contact.get("contactMode"), "timingContactReducer contact mode missing")
    assert_true(contact.get("contactInstruction"), "timingContactReducer contact instruction missing")
    assert_true(contact.get("selectedTimingReducers"), "timingContactReducer selected reducers missing")
    forbidden_date_keys = {"date", "start_date", "end_date", "startDate", "endDate", "daySummaries", "day_summaries", "windows"}
    assert_true(all(not forbidden_date_keys.intersection(set(item.keys())) for item in contact.get("selectedTimingReducers") or []), "timingContactReducer leaked exact date fields")
    assert_true(contact.get("recommendedAction") == "avoid_push", "timing scan fixture should recommend avoiding high-pressure push")


def assert_contact_reducer_fixture(case: dict[str, Any], scenario: dict[str, Any]) -> None:
    clusters = case.get("evidenceClusters") or {}
    contact = clusters.get("timingContactReducer") or {}
    expected = scenario.get("expected") or {}
    scenario_id = str(scenario.get("id") or "unnamed")
    selected_categories = {str(item.get("category") or "") for item in contact.get("selectedTimingReducers") or []}
    expected_categories = set(str(item) for item in expected.get("selectedCategories") or [])
    forbidden_date_keys = {"date", "start_date", "end_date", "startDate", "endDate", "daySummaries", "day_summaries", "windows"}

    assert_true(contact.get("atomId") == "western-atom-timing-contact-reducer", f"{scenario_id}: timingContactReducer atom mismatch")
    assert_true(contact.get("source") == "western-contact-timing-action-reducers", f"{scenario_id}: timingContactReducer source mismatch")
    contact_claim_ids = {str(claim_id) for claim_id in contact.get("claimIds") or []}
    assert_true("western-contact-timing-action-reducers-006" in contact_claim_ids, f"{scenario_id}: timingContactReducer missing contact-status bid claim")
    assert_true("western-contact-timing-action-reducers-007" in contact_claim_ids, f"{scenario_id}: timingContactReducer missing repair-tone claim")
    assert_true(contact.get("claimSupport"), f"{scenario_id}: timingContactReducer claim support missing")
    assert_true(contact.get("recommendedAction") in CONTACT_ACTIONS, f"{scenario_id}: invalid contact action")
    assert_true(contact.get("recommendedAction") == expected.get("recommendedAction"), f"{scenario_id}: action mismatch")
    assert_true(contact.get("contactMode") == expected.get("contactMode"), f"{scenario_id}: contact mode mismatch")
    assert_true(contact.get("topBand") == expected.get("topBand"), f"{scenario_id}: top band mismatch")
    assert_true(selected_categories == expected_categories, f"{scenario_id}: selected reducer categories mismatch")
    assert_true(contact.get("supportSignalCount") == expected.get("supportSignalCount"), f"{scenario_id}: support count mismatch")
    assert_true(contact.get("cautionSignalCount") == expected.get("cautionSignalCount"), f"{scenario_id}: caution count mismatch")
    for flag in (
        "hasLowPressureContactWindow",
        "hasAvoidPressureWindow",
        "hasMercuryCommunicationWindow",
        "hasVenusSofteningWindow",
        "hasMarsActivationRisk",
        "hasSaturnBoundaryRisk",
    ):
        assert_true(contact.get(flag) == expected.get(flag), f"{scenario_id}: {flag} mismatch")
    assert_true(str(expected.get("instructionContains") or "") in str(contact.get("contactInstruction") or ""), f"{scenario_id}: instruction mismatch")
    assert_exact_timing_policy(contact, f"{scenario_id}: timingContactReducer")
    assert_true(all(not forbidden_date_keys.intersection(set(item.keys())) for item in contact.get("selectedTimingReducers") or []), f"{scenario_id}: selected reducers leaked exact date fields")

    band = clusters.get("timingWindowBand") or {}
    assert_true(band.get("topBand") == expected.get("topBand"), f"{scenario_id}: timingWindowBand top band mismatch")
    assert_exact_timing_policy(band, f"{scenario_id}: timingWindowBand")
    window_scan = ((case.get("timingLayer") or {}).get("windowScan") or {})
    forbidden_public_keys = {"windows", "day_summaries", "daySummaries", "start_date", "end_date", "date"}
    assert_true(not forbidden_public_keys.intersection(window_scan), f"{scenario_id}: public scan leaked exact date fields")
    assert_exact_timing_policy(window_scan, f"{scenario_id}: public scan")


def assert_timing_guidance(view_model: dict[str, Any], scenario: dict[str, Any] | None = None) -> None:
    scenario_id = str((scenario or {}).get("id") or "calculated-scan")
    timing_guidance = view_model.get("timingGuidance") or {}
    readable = timing_guidance.get("readableInterpretation") or {}
    sections = (view_model.get("readableQuestionAnswer") or {}).get("sections") or {}
    sections_timing = sections.get("timing") or {}
    assert_true(timing_guidance.get("version") == "timing-guidance-v1", f"{scenario_id}: timing guidance version missing")
    assert_true(sections_timing.get("version") == "timing-guidance-v1", f"{scenario_id}: readable sections timing missing")
    assert_true(readable.get("module") == "question_timing", f"{scenario_id}: timing readable module mismatch")
    assert_true(readable.get("headline"), f"{scenario_id}: timing readable headline missing")
    assert_true(readable.get("body"), f"{scenario_id}: timing readable body missing")
    assert_true(readable.get("nextMove"), f"{scenario_id}: timing readable nextMove missing")
    assert_true(timing_guidance.get("preciseDatesAvailable") is False, f"{scenario_id}: timing guidance should block precise dates")
    rendered = "\n".join(str(readable.get(key) or "") for key in ("headline", "meaning", "body", "nextMove", "caution")).lower()
    for term in FORBIDDEN_READABLE_TIMING:
        assert_true(term.lower() not in rendered, f"{scenario_id}: timing readable leaked internal/awkward term: {term}")
    expected = (scenario or {}).get("expected") or {}
    if expected:
        assert_true(timing_guidance.get("recommendedAction") == expected.get("recommendedAction"), f"{scenario_id}: timing guidance action mismatch")
        assert_true(timing_guidance.get("topBand") == expected.get("topBand"), f"{scenario_id}: timing guidance band mismatch")
    needle = TIMING_ACTION_HEADLINE_NEEDLES.get(scenario_id)
    if needle:
        assert_true(needle in str(readable.get("headline") or ""), f"{scenario_id}: timing headline does not match branch")
    donts = sections.get("donts") or []
    dont_claim_ids = {
        str(claim_id)
        for item in donts
        for claim_id in ((item.get("readableInterpretation") or {}).get("sourceClaimIds") or [])
    }
    dont_copy = " ".join(str(item.get("body") or "") for item in donts)
    assert_true("western-contact-timing-action-reducers-007" in dont_claim_ids, f"{scenario_id}: donts missing repair-tone source claim")
    assert_true(any(needle in dont_copy for needle in ("長訊息", "補訊息", "連續傳訊息", "長文")), f"{scenario_id}: donts should include repair-tone pressure boundary")


def assert_blueprint_uses_timing(view_model: dict[str, Any]) -> None:
    blueprint = view_model.get("readingBlueprint") or {}
    chapters = blueprint_chapters(blueprint)
    chance = next((chapter for chapter in chapters if chapter.get("id") == "chance"), {})
    sources = {str(item.get("source") or "") for item in chance.get("evidence") or []}
    assert_true("western-transits-timing-selector-windows" in sources, "chance chapter missing timing selector evidence")
    assert_true("western-contact-timing-action-reducers" in sources, "chance chapter missing contact timing reducer evidence")
    assert_true(len(chapters) == 3, "chapter count changed")
    assert_true(len(blueprint.get("chapters") or []) == 3, "readingBlueprint.chapters alias missing")
    for chapter in chapters:
        assert_true(bool(chapter.get("methodBoundary")), f"{chapter.get('id')}: methodBoundary missing")


def assert_contact_reducer_fixture_matrix() -> list[str]:
    base_payload = build_payload(timing_reading_without_scan(), include_drafts=True, select=True)
    passed: list[str] = []
    for scenario in read_fixture_scenarios():
        scenario_id = str(scenario.get("id") or "unnamed")
        payload = copy.deepcopy(base_payload)
        payload["reading_id"] = f"timing-contact-reducer-{scenario_id}"
        analysis = (payload.get("western") or {}).setdefault("analysis", {})
        analysis["timing_window_scan"] = synthetic_timing_scan(scenario)
        debug = payload.setdefault("debug", {})
        debug["western_analysis"] = analysis
        view_model = build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)
        rendered = json.dumps(view_model, ensure_ascii=False).lower()
        for term in LEGACY_TERMS:
            assert_true(term.lower() not in rendered, f"{scenario_id}: legacy BaZi term leaked into timing view model: {term}")
        case = view_model.get("westernRelationshipCaseFile") or {}
        assert_true(case.get("version") == "western-relationship-case-file-v1", f"{scenario_id}: case file version mismatch")
        assert_contact_reducer_fixture(case, scenario)
        assert_timing_guidance(view_model, scenario)
        assert_blueprint_uses_timing(view_model)
        passed.append(scenario_id)
    return passed


def main() -> int:
    payload = build_payload(timing_reading(), include_drafts=True, select=True)
    assert_current_transits_include_mercury(payload)
    raw_scan = assert_raw_scan(payload)
    view_model = build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)
    rendered = json.dumps(view_model, ensure_ascii=False).lower()
    for term in LEGACY_TERMS:
        assert_true(term.lower() not in rendered, f"legacy BaZi term leaked into timing view model: {term}")
    case = view_model.get("westernRelationshipCaseFile") or {}
    assert_true(case.get("version") == "western-relationship-case-file-v1", "case file version mismatch")
    assert_public_scan(case, raw_scan)
    assert_timing_clusters(case)
    assert_timing_guidance(view_model)
    assert_blueprint_uses_timing(view_model)
    contact_fixture_ids = assert_contact_reducer_fixture_matrix()

    window_scan = (case.get("timingLayer") or {}).get("windowScan") or {}
    print("Western timing window smoke passed")
    print(f"- samples: {window_scan.get('sampleCount')}")
    print(f"- top band: {window_scan.get('topBand')} ({window_scan.get('topBandLabel')})")
    print(f"- timing summary: {window_scan.get('timingSummary')}")
    print(f"- contact reducer fixtures: {', '.join(contact_fixture_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
