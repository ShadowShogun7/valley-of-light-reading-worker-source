#!/usr/bin/env python3
"""Smoke-test Moon/Venus safety-validation language reducer branches."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json  # noqa: E402
from structured_runtime import load_structured_kb  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    SIGN_ELEMENTS,
    SIGN_LABELS,
    build_view_model,
    load_articles,
    load_claims_by_article,
)


ARTICLES = load_articles(DEFAULT_ARTICLES_PATH)
CLAIMS_BY_ARTICLE = load_claims_by_article(DEFAULT_CLAIMS_PATH)
STRUCTURED_KB = load_structured_kb()
SCENARIOS_PATH = ROOT / "examples" / "relationship_fit" / "safety-validation-language-scenarios.json"
LEGACY_TERMS = ("bazi", "八字", "配偶星", "日主", "四柱", "十神")
AWKWARD_COPY = (
    "需要翻譯",
    "翻譯清楚",
    "你比較用",
    "處理界線與壓力",
    "這一項比較容易互相懂",
    "對話和空間處理",
    "這組語言",
    "Moon 的安全感",
    "Venus 的被重視",
    "比較 Moon",
    "Moon/Venus 語言",
    "比較容易接上",
    "容易聽岔",
)
VISIBLE_TEXT_FIELDS = ("title", "relationLabel", "body", "nextMove")
POINTS = ("Moon", "Venus")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_scenarios() -> dict[str, Any]:
    fixture = read_json(SCENARIOS_PATH)
    assert_true(fixture.get("version") == "safety-validation-language-scenarios-v1", "fixture version mismatch")
    scenarios = fixture.get("scenarios")
    assert_true(isinstance(scenarios, list) and scenarios, "safety-validation scenarios missing")
    return fixture


def scenario_reading(base_path: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    reading = copy.deepcopy(read_json(base_path))
    scenario_id = str(scenario.get("id") or "unnamed")
    reading["reading_id"] = f"safety-validation-language-{scenario_id}"
    context = reading.setdefault("context", {})
    context["relationship_stage"] = "cold-war"
    context["main_question"] = "still-love-me"
    context["contact_status"] = "no-contact"
    context["desired_outcome"] = "reconnect"
    context["emotional_risk"] = "calm"
    context["analysis_date"] = "2026-05-23"
    context["timing_scan_days"] = 0

    for role, scenario_key in (("person_a", "personA"), ("person_b", "personB")):
        person_config = scenario.get(scenario_key) or {}
        person = reading.setdefault(role, {})
        if person_config.get("birthTimeKnown") is False:
            person["birth_time"] = None
        elif not person.get("birth_time"):
            person["birth_time"] = "12:00"
    return reading


def inject_point_signs(payload: dict[str, Any], scenario: dict[str, Any]) -> None:
    for role, scenario_key in (("person_a", "personA"), ("person_b", "personB")):
        chart = (((payload.get("western") or {}).get("people") or {}).get(role) or {})
        objects = chart.get("objects") or {}
        person_config = scenario.get(scenario_key) or {}
        for point in POINTS:
            sign = str(person_config.get(point) or "")
            assert_true(sign in SIGN_ELEMENTS, f"{scenario.get('id')} {scenario_key}.{point} unknown sign: {sign}")
            obj = objects.get(point.lower())
            assert_true(isinstance(obj, dict), f"{scenario.get('id')} missing {role} {point} object")
            obj["sign"] = sign
            obj["sign_label"] = SIGN_LABELS.get(sign, sign)
            obj["sign_element"] = SIGN_ELEMENTS[sign]


def build_scenario_view_model(
    base_path: Path,
    scenario: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    reading = scenario_reading(base_path, scenario)
    payload = build_payload(reading, include_drafts=True, select=True)
    inject_point_signs(payload, scenario)
    view_model = build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE, STRUCTURED_KB)
    rendered = json.dumps(view_model, ensure_ascii=False).lower()
    for term in LEGACY_TERMS:
        assert_true(term.lower() not in rendered, f"{scenario.get('id')} leaked legacy term: {term}")
    return payload, view_model


def western_case_file(view_model: dict[str, Any]) -> dict[str, Any]:
    case = view_model.get("westernRelationshipCaseFile")
    assert_true(isinstance(case, dict), "westernRelationshipCaseFile missing")
    assert_true(case.get("version") == "western-relationship-case-file-v1", "western case file version mismatch")
    return case


def safety_cluster(view_model: dict[str, Any]) -> dict[str, Any]:
    cluster = ((western_case_file(view_model).get("evidenceClusters") or {}).get("safetyValidationLanguage") or {})
    assert_true(cluster.get("category") == "safetyValidationLanguage", "safety cluster category mismatch")
    assert_true(cluster.get("atomId") == "western-atom-safety-validation-language", "safety cluster atom mismatch")
    assert_true(cluster.get("source") == "western-safety-validation-language", "safety cluster source mismatch")
    assert_true(cluster.get("itemCount") == 4, "safety cluster should expose four Moon/Venus pairs")
    claim_ids = set(str(claim_id) for claim_id in cluster.get("claimIds") or [])
    for claim_id in (
        "western-safety-validation-language-001",
        "western-safety-validation-language-002",
        "western-safety-validation-language-003",
        "western-safety-validation-language-004",
    ):
        assert_true(claim_id in claim_ids, f"safety cluster missing source claim: {claim_id}")
    assert_true(cluster.get("claimSupport"), "safety cluster claim support missing")
    assert_true(len(cluster.get("pairs") or []) == 4, "safety cluster pair list mismatch")
    return cluster


def moon_venus_fit_item(view_model: dict[str, Any], expected_bucket: str) -> dict[str, Any]:
    profiles = view_model.get("relationshipProfiles") or {}
    fit = profiles.get("fitSummary") or {}
    mirrored_cluster = fit.get("safetyValidationLanguage") or {}
    assert_true(mirrored_cluster.get("source") == "western-safety-validation-language", "fit summary safety cluster missing")
    found: list[tuple[str, dict[str, Any]]] = []
    for bucket in ("natural", "effort", "friction"):
        for item in fit.get(bucket) or []:
            if item.get("point") == "MoonVenus":
                found.append((bucket, item))
    assert_true(len(found) == 1, f"MoonVenus fit item should appear once, got {len(found)}")
    bucket, item = found[0]
    assert_true(bucket == expected_bucket, f"MoonVenus fit bucket mismatch: expected {expected_bucket}, got {bucket}")
    readable = item.get("readableInterpretation") or {}
    assert_true(readable.get("module") == "fit_summary_item", "MoonVenus readable module mismatch")
    assert_true(item.get("source") == "western-safety-validation-language", "MoonVenus item source mismatch")
    assert_true(readable.get("sourceClaimIds"), "MoonVenus readable source claim ids missing")
    visible_text = " ".join(
        str(value or "")
        for value in (
            *[item.get(field) for field in VISIBLE_TEXT_FIELDS],
            readable.get("headline"),
            readable.get("meaning"),
            readable.get("body"),
            readable.get("nextMove"),
            readable.get("confidenceNote"),
        )
    )
    for phrase in AWKWARD_COPY:
        assert_true(phrase not in visible_text, f"MoonVenus fit item uses awkward copy: {phrase}")
    assert_true("月亮" in str(readable.get("meaning") or ""), "MoonVenus meaning should explain Moon as 月亮")
    assert_true("金星" in str(readable.get("meaning") or ""), "MoonVenus meaning should explain Venus as 金星")
    assert_true("愛不愛" in str(readable.get("meaning") or ""), "MoonVenus meaning should keep non-verdict framing")
    assert_true("月亮與金星互動" in str(item.get("body") or ""), "MoonVenus body should include interaction count framing")
    assert_true("最值得先看的是" in str(item.get("body") or ""), "MoonVenus body should identify the selected pair")
    relation = str(item.get("relation") or "")
    relation_label = str(item.get("relationLabel") or "")
    assert_true(
        relation_label in {"容易被接住", "需要講明白", "容易誤會成壓力"},
        f"MoonVenus relation label should be native Chinese, got {relation_label}",
    )
    if relation == "natural":
        assert_true("容易被接住" in visible_text, "natural MoonVenus copy should name the received-safety branch")
    elif relation == "effort":
        assert_true("講明白" in visible_text, "effort MoonVenus copy should name the explicit-need branch")
    elif relation == "friction":
        assert_true("壓力" in visible_text, "friction MoonVenus copy should name the pressure-misread branch")
    return item


def assert_scenario(scenario: dict[str, Any], cluster: dict[str, Any], view_model: dict[str, Any]) -> None:
    expected = scenario.get("expected") or {}
    scenario_id = str(scenario.get("id") or "unnamed")
    for key in (
        "dominantContactType",
        "naturalLanguageCount",
        "effortLanguageCount",
        "frictionLanguageCount",
        "hasNaturalNeedBridge",
        "hasSafetyValidationObstacle",
        "lowConfidenceCount",
        "confidence",
    ):
        assert_true(cluster.get(key) == expected.get(key), f"{scenario_id} {key} mismatch: {cluster.get(key)} != {expected.get(key)}")

    pair_relations = {str(pair.get("id")): str(pair.get("relation")) for pair in cluster.get("pairs") or []}
    assert_true(pair_relations == expected.get("pairs"), f"{scenario_id} pair relation mismatch: {pair_relations}")
    low_pairs = {str(pair.get("id")) for pair in cluster.get("pairs") or [] if pair.get("confidence") == "low"}
    assert_true(low_pairs == set(expected.get("lowConfidencePairs") or []), f"{scenario_id} low-confidence pair mismatch: {sorted(low_pairs)}")

    fit_item = moon_venus_fit_item(view_model, str(expected.get("fitBucket") or ""))
    assert_true(fit_item.get("relation") == expected.get("dominantContactType"), f"{scenario_id} fit relation mismatch")
    if expected.get("confidence") == "low":
        assert_true(
            (fit_item.get("readableInterpretation") or {}).get("confidenceNote"),
            f"{scenario_id} low-confidence fit item should expose confidence note",
        )
    else:
        assert_true(
            not (fit_item.get("readableInterpretation") or {}).get("confidenceNote"),
            f"{scenario_id} medium-confidence fit item should not expose confidence note",
        )


def main() -> None:
    fixture = read_scenarios()
    base_path = ROOT / str(fixture.get("baseReading") or "")
    assert_true(base_path.exists(), f"base reading missing: {base_path}")
    scenario_ids: list[str] = []
    bucket_counts = {"natural": 0, "effort": 0, "friction": 0}

    for scenario in fixture.get("scenarios") or []:
        scenario_id = str(scenario.get("id") or "unnamed")
        _, view_model = build_scenario_view_model(base_path, scenario)
        cluster = safety_cluster(view_model)
        assert_scenario(scenario, cluster, view_model)
        scenario_ids.append(scenario_id)
        bucket = str((scenario.get("expected") or {}).get("fitBucket") or "")
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    print("Western safety-validation language matrix passed")
    print(f"- scenarios: {len(scenario_ids)} -> {', '.join(scenario_ids)}")
    print(f"- visible MoonVenus bucket coverage: {dict(sorted(bucket_counts.items()))}")


if __name__ == "__main__":
    main()
