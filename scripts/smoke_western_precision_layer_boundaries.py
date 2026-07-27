#!/usr/bin/env python3
"""Smoke-test paid V1 precision-layer boundaries.

This keeps the remaining advanced layers honest: houses/overlays require
reliable birth data and a productized calculation, composite/Davison cannot
become interpretation without relationship-chart calculation support, and
deeper Saturn body claims stay blocked while the local source text is weak.
"""

from __future__ import annotations

import copy
import re
import sys
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


BASE_READING_PATH = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
READING_PATHS = (
    BASE_READING_PATH,
    ROOT / "examples" / "readings" / "broke-up-long-any-chance.json",
    ROOT / "examples" / "readings" / "cold-war-when-to-contact.json",
    ROOT / "examples" / "readings" / "broke-up-recent-what-did-i-do-wrong.json",
    ROOT / "examples" / "readings" / "crisis-stay-or-let-go.json",
    ROOT / "examples" / "readings" / "blocked-anxious-still-love-me.json",
    ROOT / "examples" / "readings" / "no-contact-desperate-when-to-contact.json",
)
SATURN_RAW_PATH = ROOT / "raw" / "western" / "488023677-Liz-Greene-Robert-Hand-Saturn-A-New-Look-at-an-Old-Devil-Weiser-Books-2011-pdf.txt"
REQUIREMENTS_CALCULATION = ROOT / "requirements-calculation.txt"
RUNTIME_PATH = ROOT / "scripts" / "complete_relationship_result_runtime.py"
KERYKEION_PROBE_PATH = ROOT / "scripts" / "compare_western_engines.py"

HOUSE_PRECISION_CLAIMS = {
    "western-houses-angles-foundation-001",
    "western-houses-angles-foundation-002",
    "western-houses-angles-foundation-003",
    "western-houses-angles-foundation-004",
    "western-precision-birth-data-quality-001",
    "western-precision-birth-data-quality-002",
    "western-precision-birth-data-quality-003",
}
RELATIONSHIP_CHART_CLAIMS = {
    "western-relationship-chart-layer-001",
    "western-relationship-chart-layer-002",
    "western-relationship-chart-layer-003",
}
RELATIONSHIP_CHART_METHOD_CLAIMS = {
    "suskin-method-order-relationship-chart-later",
    "davison-reserve-do-not-pretend-calculated",
}
ADVANCED_VISIBLE_TERMS = (
    "Composite",
    "Davison",
    "relationship chart",
    "overlay",
    "house overlay",
    "關係盤",
    "宮位重疊",
)
VISIBLE_TEXT_KEYS = {
    "answer",
    "body",
    "caution",
    "headline",
    "label",
    "meaning",
    "nextMove",
    "precisionWarnings",
    "relationshipUse",
    "responseRule",
    "summary",
    "title",
    "value",
}
VISIBLE_CONTAINER_KEYS = {
    "actionGuidance",
    "answerGuidance",
    "chance",
    "donts",
    "includedReadingRows",
    "readableInterpretation",
    "readableQuestionAnswer",
    "relationshipProfiles",
    "sections",
    "timeline",
    "timingGuidance",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_vm(reading: dict[str, Any], articles: dict[str, Any], claims_by_article: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    payload = build_payload(reading, include_drafts=True, select=True)
    return build_view_model(payload, articles, claims_by_article)


def case_file(view_model: dict[str, Any]) -> dict[str, Any]:
    case = view_model.get("westernRelationshipCaseFile")
    assert_true(isinstance(case, dict), "westernRelationshipCaseFile missing")
    return case


def visible_text(view_model: dict[str, Any]) -> str:
    parts: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, str):
            if value.strip():
                parts.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                add(item)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key in VISIBLE_TEXT_KEYS or key in VISIBLE_CONTAINER_KEYS:
                    add(child)

    for key in (
        "relationshipProfiles",
        "answerGuidance",
        "timingGuidance",
        "actionGuidance",
        "readableQuestionAnswer",
        "chance",
        "timeline",
        "donts",
        "includedReadingRows",
    ):
        add(view_model.get(key))
    return "\n".join(parts)


def person_quality(case: dict[str, Any]) -> list[dict[str, Any]]:
    quality = case.get("inputQuality") or {}
    return [quality.get("personA") or {}, quality.get("personB") or {}]


def assert_house_overlay_boundary(case: dict[str, Any], *, expected_status: str, label: str) -> None:
    layer = case.get("houseOverlayLayer") or {}
    gate = layer.get("precisionGate") or {}
    claim_ids = set(layer.get("claimIds") or [])
    assert_true(layer.get("status") == expected_status, f"{label}: house overlay status mismatch: {layer}")
    assert_true(layer.get("source") == "western-precision-birth-data-quality", f"{label}: house overlay source missing")
    assert_true(HOUSE_PRECISION_CLAIMS.issubset(claim_ids), f"{label}: house precision claim ids incomplete")
    assert_true(gate.get("version") == "house-angle-precision-gate-v1", f"{label}: precision gate version missing")
    assert_true(gate.get("canCreateAstrologyConclusion") is False, f"{label}: precision gate can create astrology conclusion")
    if expected_status == "not_available":
        assert_true(gate.get("status") == "allowed_by_precision", f"{label}: high precision gate should be allowed")
        assert_true(gate.get("allowsHouseOverlaysByPrecision") is True, f"{label}: precision should allow overlays in principle")
        assert_true(gate.get("houseOverlayCalculationAvailable") is False, f"{label}: overlay calculation must stay unavailable")
        assert_true("calculation is not wired" in str(layer.get("reason") or ""), f"{label}: overlay calculation reason missing")
    elif expected_status == "blocked_by_birth_time":
        assert_true(gate.get("status") == "blocked_by_birth_time", f"{label}: birth-time gate mismatch")
        assert_true("house_overlays" in set(gate.get("blockedClaims") or []), f"{label}: house overlays not blocked")
    elif expected_status == "blocked_by_location":
        assert_true(gate.get("status") == "blocked_by_location", f"{label}: location gate mismatch")
        assert_true("house_overlays" in set(gate.get("blockedClaims") or []), f"{label}: house overlays not blocked")


def assert_composite_boundary(case: dict[str, Any], *, label: str) -> None:
    layer = case.get("compositeLayer") or {}
    claim_ids = set(layer.get("claimIds") or [])
    method_claim_ids = set(layer.get("methodClaimIds") or [])
    assert_true(layer.get("status") == "not_calculated", f"{label}: composite status mismatch")
    assert_true(layer.get("source") == "western-relationship-chart-layer", f"{label}: composite source missing")
    assert_true(RELATIONSHIP_CHART_CLAIMS.issubset(claim_ids), f"{label}: relationship-chart claim ids incomplete")
    assert_true(
        RELATIONSHIP_CHART_METHOD_CLAIMS.issubset(method_claim_ids),
        f"{label}: relationship-chart method claim ids incomplete",
    )
    assert_true(layer.get("canCreateAstrologyConclusion") is False, f"{label}: composite can create conclusion")
    assert_true(layer.get("requiresCalculatedRelationshipChart") is True, f"{label}: composite calculation requirement missing")
    for forbidden_key in ("compositeCore", "relationshipChart", "davisonChart", "interpretation"):
        assert_true(forbidden_key not in layer, f"{label}: composite layer leaked {forbidden_key}")

    cluster = ((case.get("evidenceClusters") or {}).get("relationshipChartLayer") or {})
    assert_true(cluster.get("dominantContactType") == "not_calculated", f"{label}: relationship chart cluster not blocked")
    assert_true(set(cluster.get("claimIds") or []) >= RELATIONSHIP_CHART_CLAIMS, f"{label}: relationship chart cluster claims missing")


def assert_visible_boundary(view_model: dict[str, Any], *, label: str) -> None:
    text = visible_text(view_model)
    leaked = [term for term in ADVANCED_VISIBLE_TERMS if term in text]
    assert_true(not leaked, f"{label}: advanced precision terms leaked into visible copy: {leaked}")


def assert_precision_variants(articles: dict[str, Any], claims_by_article: dict[str, list[dict[str, Any]]]) -> None:
    base = read_json(BASE_READING_PATH)
    scenarios = [
        ("high_precision_not_available", base, "not_available"),
        ("missing_birth_time_blocks_overlay", copy.deepcopy(base), "blocked_by_birth_time"),
        ("missing_city_blocks_overlay", copy.deepcopy(base), "blocked_by_location"),
    ]
    scenarios[1][1]["person_a"]["birth_time"] = None
    scenarios[1][1]["person_b"]["birth_time"] = None
    scenarios[2][1]["person_a"]["birth_place"] = ""
    scenarios[2][1]["person_b"]["birth_place"] = ""

    for label, reading, expected_status in scenarios:
        reading["reading_id"] = f"precision-boundary-{label}"
        view_model = build_vm(reading, articles, claims_by_article)
        case = case_file(view_model)
        assert_house_overlay_boundary(case, expected_status=expected_status, label=label)
        assert_composite_boundary(case, label=label)
        assert_visible_boundary(view_model, label=label)


def assert_paid_examples(articles: dict[str, Any], claims_by_article: dict[str, list[dict[str, Any]]]) -> None:
    for path in READING_PATHS:
        reading = read_json(path)
        view_model = build_vm(reading, articles, claims_by_article)
        label = str(view_model.get("id") or path.stem)
        case = case_file(view_model)
        assert_composite_boundary(case, label=label)
        assert_visible_boundary(view_model, label=label)
        qualities = person_quality(case)
        if all(item.get("timeKnown") and item.get("locationKnown") for item in qualities):
            assert_house_overlay_boundary(case, expected_status="not_available", label=label)


def assert_saturn_source_still_blocked() -> dict[str, int]:
    text = SATURN_RAW_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    layout_marker_lines = sum(1 for line in lines if "45173_TXT.indd" in line or "Saturn Layout Pages" in line)
    in_synastry_hits = [index + 1 for index, line in enumerate(lines) if "In Synastry" in line]
    chapter_body_markers = [
        index + 1
        for index, line in enumerate(lines)
        if re.search(r"^\s*6\s*[•.-]\s*In Synastry\s*$", line)
    ]
    assert_true("Contents" in text and "6   •   In Synastry" in text, "Saturn contents page missing")
    assert_true(layout_marker_lines >= 100, "Saturn raw file no longer looks like the weak local extraction; review blocker")
    assert_true(len(in_synastry_hits) <= 1, f"Saturn synastry body may now exist at lines {in_synastry_hits}; extract before keeping blocked")
    assert_true(not chapter_body_markers, f"Saturn chapter 6 body marker found at lines {chapter_body_markers}; extract before keeping blocked")
    return {
        "raw_lines": len(lines),
        "layout_marker_lines": layout_marker_lines,
        "in_synastry_hits": len(in_synastry_hits),
    }


def assert_optional_engine_boundary() -> None:
    requirements_lines = REQUIREMENTS_CALCULATION.read_text(encoding="utf-8").splitlines()
    active_kerykeion = [
        line
        for line in requirements_lines
        if "kerykeion" in line.lower() and line.strip() and not line.strip().startswith("#")
    ]
    assert_true(not active_kerykeion, f"Kerykeion must not be an active production dependency: {active_kerykeion}")
    runtime_text = RUNTIME_PATH.read_text(encoding="utf-8")
    assert_true("kerykeion" not in runtime_text.lower(), "production relationship runtime imports or mentions Kerykeion")
    probe_text = KERYKEION_PROBE_PATH.read_text(encoding="utf-8")
    assert_true("build-stage decision tool" in probe_text, "Kerykeion probe must remain marked as build-stage only")
    assert_true("AGPL/commercial-sensitive" in probe_text, "Kerykeion probe must preserve license boundary wording")


def main() -> int:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims_by_article = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    errors: list[str] = []

    saturn_stats: dict[str, int] = {}
    checks = (
        ("precision variants", lambda: assert_precision_variants(articles, claims_by_article)),
        ("paid examples", lambda: assert_paid_examples(articles, claims_by_article)),
        ("saturn source quality", lambda: saturn_stats.update(assert_saturn_source_still_blocked())),
        ("optional engine boundary", assert_optional_engine_boundary),
    )
    for label, check in checks:
        try:
            check()
        except AssertionError as exc:
            errors.append(f"{label}: {exc}")

    if errors:
        print("Western precision-layer boundary contract failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Western precision-layer boundary contract passed")
    print("- house overlays: precision-gated and not productized")
    print("- composite/Davison: source-traced and not calculated")
    print(
        "- Saturn source quality: "
        f"{saturn_stats.get('raw_lines', 0)} raw lines, "
        f"{saturn_stats.get('layout_marker_lines', 0)} layout marker lines, "
        f"{saturn_stats.get('in_synastry_hits', 0)} contents-only synastry hit(s)"
    )
    print("- optional Kerykeion probe: not production runtime dependency")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
