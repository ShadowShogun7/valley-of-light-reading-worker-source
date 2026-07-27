#!/usr/bin/env python3
"""Smoke-test the richer paid V1 relationship insight data layer."""

from __future__ import annotations

import json
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


READING_PATHS = (
    ROOT / "examples" / "readings" / "cold-war-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-long-any-chance.json",
    ROOT / "examples" / "readings" / "cold-war-when-to-contact.json",
    ROOT / "examples" / "readings" / "broke-up-recent-what-did-i-do-wrong.json",
    ROOT / "examples" / "readings" / "crisis-stay-or-let-go.json",
)

ARTICLES = load_articles(DEFAULT_ARTICLES_PATH)
CLAIMS_BY_ARTICLE = load_claims_by_article(DEFAULT_CLAIMS_PATH)
EXACT_DATE_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}|第\s*\d+\s*天")
MONTH_PERIOD_PATTERN = re.compile(r"20\d{2} 年\s*\d{1,2} 月(?:上旬|中旬|下旬)(?:到\s*\d{1,2} 月(?:上旬|中旬|下旬))?")
AWKWARD_VISIBLE_PHRASES = (
    "用熱度要求對方立刻定義關係",
    "先拆掉",
    "先退回防線",
    "表達容易變慢、變怕承諾",
    "自尊和責任感被碰到時冷掉",
    "防衛點",
    "防線",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_vm(path: Path) -> dict[str, Any]:
    reading = read_json(path)
    payload = build_payload(reading, include_drafts=True, select=True)
    return build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)


def assert_block_common(block: dict[str, Any], label: str) -> None:
    assert_true(block, f"{label}: block missing")
    assert_true(block.get("version"), f"{label}: version missing")
    assert_true(block.get("methodClaimIds"), f"{label}: methodClaimIds missing")
    assert_true(block.get("evidenceClusterKeys"), f"{label}: evidenceClusterKeys missing")


def normalize_field(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip("。；，, ")


def assert_distinct_text_fields(block: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    values = [normalize_field(block.get(key)) for key in keys]
    assert_true(all(values), f"{label}: one of {keys} is empty")
    assert_true(len(set(values)) == len(values), f"{label}: fields should not repeat the same answer: {keys}")


def assert_dynamics(block: dict[str, Any], label: str, *, require_item: bool = True) -> None:
    assert_block_common(block, label)
    assert_true(block.get("summary"), f"{label}: summary missing")
    items = [item for item in block.get("items") or [] if isinstance(item, dict)]
    if require_item:
        assert_true(items, f"{label}: items missing")
    for item in items:
        assert_true(item.get("pairKey"), f"{label}: pairKey missing")
        assert_true(item.get("technical"), f"{label}: technical missing")
        assert_true(item.get("meaning"), f"{label}: meaning missing")
        assert_true(item.get("everydaySignal"), f"{label}: everyday signal missing")
        assert_true(item.get("advice"), f"{label}: advice missing")
        assert_true(item.get("sourceClaimIds"), f"{label}: source claim ids missing")


def assert_relationship_insights(view_model: dict[str, Any], label: str) -> None:
    case = view_model.get("westernRelationshipCaseFile") or {}
    layer = case.get("relationshipInsightLayer") or {}
    assert_true(layer.get("version") == "relationship-insight-layer-v1", f"{label}: insight layer version missing")

    archetype = view_model.get("relationshipArchetype") or {}
    assert_block_common(archetype, f"{label}: archetype")
    assert_true(archetype.get("title"), f"{label}: archetype title missing")
    assert_true(archetype.get("whySelected"), f"{label}: archetype evidence rationale missing")
    assert_true(archetype.get("strengths"), f"{label}: archetype strengths missing")
    assert_true(archetype.get("risks"), f"{label}: archetype risks missing")

    assert_dynamics(view_model.get("attractionDynamics") or {}, f"{label}: attraction")
    assert_dynamics(view_model.get("conflictDynamics") or {}, f"{label}: conflict")
    assert_dynamics(view_model.get("growthDynamics") or {}, f"{label}: growth", require_item=False)

    growth_gaps = view_model.get("growthDynamics", {}).get("gaps") or []
    gap_labels = {str(gap.get("label") or "") for gap in growth_gaps}
    assert_true("Chiron 療癒相位" in gap_labels, f"{label}: Chiron gap should stay explicit")
    assert_true("North Node 業力方向" in gap_labels, f"{label}: North Node gap should stay explicit")

    partner_needs = view_model.get("partnerNeeds") or {}
    assert_block_common(partner_needs, f"{label}: partnerNeeds")
    assert_true("想被怎麼愛" in str(partner_needs.get("framing") or ""), f"{label}: partner needs framing missing relationship-depth purpose")
    profile = partner_needs.get("profile") or {}
    for key in (
        "relationshipStyleWanted",
        "emotionalSafetyCondition",
        "affectionLanguage",
        "conflictDefense",
        "commitmentPace",
        "whatOpensHimUp",
        "whatShutsHimDown",
        "commonMisread",
    ):
        assert_true(profile.get(key), f"{label}: partner needs profile {key} missing")
    assert_distinct_text_fields(
        profile,
        ("whatOpensHimUp", "whatShutsHimDown", "commonMisread"),
        f"{label}: partner needs profile top-layer fields",
    )
    assert_true(len(partner_needs.get("items") or []) >= 3, f"{label}: partner needs too thin")
    for item in partner_needs.get("items") or []:
        for key in (
            "relationshipStyleWanted",
            "emotionalSafetyCondition",
            "affectionLanguage",
            "conflictDefense",
            "commitmentPace",
            "whatOpensHimUp",
            "whatShutsHimDown",
            "commonMisread",
            "finalActionSuggestion",
        ):
            assert_true(item.get(key), f"{label}: partner need item {key} missing")
        assert_distinct_text_fields(
            item,
            ("whatOpensHimUp", "whatShutsHimDown", "commonMisread"),
            f"{label}: partner need item {item.get('point')}",
        )

    landmines = view_model.get("fightLandmines") or {}
    assert_block_common(landmines, f"{label}: fightLandmines")
    assert_true(len(landmines.get("items") or []) >= 3, f"{label}: fight landmines should expose three concrete risks")
    for item in landmines.get("items") or []:
        assert_true(item.get("trigger"), f"{label}: landmine trigger missing")
        assert_true(item.get("whatToDoInstead"), f"{label}: landmine repair missing")

    guide = view_model.get("survivalGuide") or {}
    assert_block_common(guide, f"{label}: survivalGuide")
    assert_true(len(guide.get("items") or []) == 5, f"{label}: survival guide should contain five suggestions")
    guide_titles = {str(item.get("title") or "") for item in guide.get("items") or []}
    assert_true(len(guide_titles) == 5, f"{label}: survival guide repeats titles")
    rendered_guide = json.dumps(guide, ensure_ascii=False)
    for phrase in AWKWARD_VISIBLE_PHRASES:
        assert_true(phrase not in rendered_guide, f"{label}: awkward survival guide phrase leaked: {phrase}")

    windows = view_model.get("relationshipTurningWindows") or {}
    assert_block_common(windows, f"{label}: turningWindows")
    assert_true(windows.get("preciseDatesAvailable") is False, f"{label}: turning windows must block precise dates")
    assert_true(windows.get("precision") == "climate_window_not_exact_date", f"{label}: turning window precision mismatch")
    rendered_windows = json.dumps(windows, ensure_ascii=False)
    assert_true(not EXACT_DATE_PATTERN.search(rendered_windows), f"{label}: turning windows leaked exact date/day")
    for phrase in AWKWARD_VISIBLE_PHRASES:
        assert_true(phrase not in rendered_windows, f"{label}: awkward timing phrase leaked: {phrase}")
    for item in windows.get("items") or []:
        period_label = str(item.get("periodLabel") or item.get("windowLabel") or "")
        assert_true(MONTH_PERIOD_PATTERN.search(period_label), f"{label}: turning window missing useful month-period label: {period_label}")

    clusters = case.get("evidenceClusters") or {}
    for key in (
        "relationshipArchetype",
        "attractionDynamics",
        "conflictDynamics",
        "growthDynamics",
        "partnerNeeds",
        "fightLandmines",
        "survivalGuide",
        "relationshipTurningWindows",
    ):
        cluster = clusters.get(key) or {}
        assert_true(cluster.get("category") == key, f"{label}: cluster {key} missing")
        assert_true(cluster.get("methodClaimIds"), f"{label}: cluster {key} method claims missing")


def assert_variation(view_models: list[dict[str, Any]]) -> None:
    titles = {str((vm.get("relationshipArchetype") or {}).get("title") or "") for vm in view_models}
    assert_true(len(titles) >= 3, f"archetypes should vary across scenarios, got {sorted(titles)}")

    attraction_pairs = {
        tuple(str(item.get("pairKey") or "") for item in (vm.get("attractionDynamics") or {}).get("items") or [])
        for vm in view_models
    }
    assert_true(len(attraction_pairs) >= 2, "attraction dynamics should vary across scenarios")

    conflict_pairs = {
        tuple(str(item.get("pairKey") or "") for item in (vm.get("conflictDynamics") or {}).get("items") or [])
        for vm in view_models
    }
    assert_true(len(conflict_pairs) >= 2, "conflict dynamics should vary across scenarios")

    guide_bodies = [
        " ".join(
            f"{item.get('title') or ''} {item.get('body') or ''}"
            for item in (vm.get("survivalGuide") or {}).get("items") or []
        )
        for vm in view_models
    ]
    assert_true(
        any(any(marker in text for marker in ("自然延續", "留在日常", "熱絡", "一時靠近")) for text in guide_bodies),
        "survival guide missing attraction-specific continuation advice",
    )
    assert_true(any("吵架地雷" in text for text in guide_bodies), "survival guide missing conflict-specific landmine advice")
    assert_true(any("不要猜心" in text for text in guide_bodies), "survival guide missing partner-needs advice")


def main() -> int:
    view_models = []
    for path in READING_PATHS:
        vm = build_vm(path)
        label = str(vm.get("id") or path.name)
        assert_relationship_insights(vm, label)
        view_models.append(vm)
    assert_variation(view_models)
    print("Western relationship insight blocks smoke passed")
    print(f"- validated readings: {len(view_models)}")
    print("- relationship archetypes, dynamics, needs, landmines, guide, and turning windows: covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
