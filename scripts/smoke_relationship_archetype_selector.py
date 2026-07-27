#!/usr/bin/env python3
"""Guard the relationship archetype selector against catch-all collapse."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CALCULATION_DIR,
    DEFAULT_CLAIMS_PATH,
    SCENARIO_ORDER,
    build_view_model,
    load_articles,
    load_claims_by_article,
    read_json,
    relationship_archetype_block,
)


CALCULATION_METADATA_STEMS = {"relationship-depth-fixtures-v2"}
EXPECTED_REACHABLE_TITLES = {
    "前世因緣感型",
    "命中貴人型",
    "溝通修復型",
    "彼此牽動型",
    "靈魂伴侶型",
    "磨合成長型",
    "歡喜冤家型",
    "高吸引高摩擦型",
    "自然吸引型",
    "慢熱安全感型",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def ordered_calculation_paths() -> list[Path]:
    available_paths = {
        path.stem: path
        for path in DEFAULT_CALCULATION_DIR.glob("*.json")
        if path.stem not in CALCULATION_METADATA_STEMS
    }
    ordered_paths = [available_paths[name] for name in SCENARIO_ORDER if name in available_paths]
    extra_paths = sorted(path for stem, path in available_paths.items() if stem not in set(SCENARIO_ORDER))
    return [*ordered_paths, *extra_paths]


def synthetic_cluster(
    *,
    theme_key: str = "",
    selected_pairs: tuple[str, ...] = (),
    detected_pairs: tuple[str, ...] = (),
    contact_type: str = "soft",
) -> dict[str, dict[str, Any]]:
    pairs = selected_pairs or detected_pairs
    selected = [
        {
            "id": f"synthetic-{index + 1}",
            "pairKey": pair,
            "contactType": contact_type,
            "relationshipFunction": theme_key or "synthetic",
        }
        for index, pair in enumerate(selected_pairs)
    ]
    detected = [
        {
            "pairKey": pair,
            "contactType": contact_type,
            "relationshipFunction": theme_key or "synthetic",
            "selectedEvidenceId": f"synthetic-{index + 1}" if pair in selected_pairs else "",
        }
        for index, pair in enumerate(pairs)
    ]
    repeated_theme = {"themeKey": theme_key, "label": theme_key, "count": 3, "selectedCount": len(selected_pairs)}
    cluster = {
        "selectedPairs": list(selected_pairs),
        "detectedPairs": list(dict.fromkeys([*selected_pairs, *detected_pairs])),
        "selectedCombinations": selected,
        "detectedPairDetails": detected,
        "dominantRepeatedThemeKey": theme_key,
        "dominantRepeatedThemeLabel": theme_key,
        "repeatedThemes": [repeated_theme] if theme_key else [],
        "hasRepeatedOuterIntensity": theme_key == "outer_intensity",
        "hasRepeatedCommunicationRepair": theme_key == "communication_repair",
        "hasRepeatedIdentityRhythm": theme_key == "identity_rhythm",
        "hasRepeatedEmotionalSafety": theme_key == "emotional_safety",
        "hasRepeatedSaturnPressure": theme_key == "saturn_pressure",
        "hasRepeatedActionConflict": theme_key == "action_conflict",
        "hasRepeatedAttractionPursuit": theme_key == "attraction_pursuit",
    }
    return {"aspectFunctionCombination": cluster}


def assert_synthetic_reachability() -> None:
    cases = {
        "前世因緣感型": synthetic_cluster(theme_key="outer_intensity", selected_pairs=("Outer-planet intensity",)),
        "命中貴人型": synthetic_cluster(theme_key="", selected_pairs=("Mercury-Jupiter",), contact_type="soft"),
        "溝通修復型": synthetic_cluster(theme_key="communication_repair", selected_pairs=("Mercury-Moon", "Mercury-Venus")),
        "彼此牽動型": synthetic_cluster(theme_key="identity_rhythm", selected_pairs=("Sun-Moon", "Moon-Moon")),
        "靈魂伴侶型": synthetic_cluster(theme_key="emotional_safety", selected_pairs=("Moon-Venus", "Mercury-Moon")),
        "磨合成長型": synthetic_cluster(theme_key="saturn_pressure", selected_pairs=("Moon-Saturn", "Venus-Saturn"), contact_type="hard"),
        "歡喜冤家型": synthetic_cluster(theme_key="action_conflict", selected_pairs=("Mercury-Mars", "Mars-Mars"), contact_type="hard"),
        "高吸引高摩擦型": synthetic_cluster(theme_key="attraction_pursuit", selected_pairs=("Venus-Mars", "Venus-Saturn"), contact_type="hard"),
        "自然吸引型": synthetic_cluster(theme_key="attraction_pursuit", selected_pairs=("Sun-Venus", "Moon-Venus"), contact_type="soft"),
        "慢熱安全感型": synthetic_cluster(),
    }
    titles = set()
    for expected, evidence_clusters in cases.items():
        actual = str(relationship_archetype_block(evidence_clusters).get("title") or "")
        assert_true(actual == expected, f"synthetic selector expected {expected}, got {actual}")
        titles.add(actual)
    assert_true(titles == EXPECTED_REACHABLE_TITLES, f"synthetic selector coverage mismatch: {sorted(titles)}")


def assert_fixture_distribution() -> Counter[str]:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims_by_article = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    counts: Counter[str] = Counter()
    for path in ordered_calculation_paths():
        view_model = build_view_model(read_json(path), articles, claims_by_article)
        title = str((view_model.get("relationshipArchetype") or {}).get("title") or "")
        assert_true(title, f"{path.name}: archetype title missing")
        counts[title] += 1

    total = sum(counts.values())
    assert_true(total >= 40, f"fixture distribution needs broad coverage, got {total}")
    assert_true(len(counts) >= 7, f"fixture archetypes collapsed: {dict(counts)}")
    dominant_title, dominant_count = counts.most_common(1)[0]
    assert_true(
        dominant_count / total <= 0.35,
        f"fixture archetype {dominant_title} is too dominant: {dominant_count}/{total}",
    )
    friction_total = counts.get("歡喜冤家型", 0) + counts.get("高吸引高摩擦型", 0)
    assert_true(
        friction_total / total <= 0.4,
        f"friction archetypes are swallowing the set: {friction_total}/{total} {dict(counts)}",
    )
    for required in ("溝通修復型", "彼此牽動型", "自然吸引型"):
        assert_true(counts.get(required, 0) > 0, f"fixture distribution missing {required}: {dict(counts)}")
    return counts


def main() -> int:
    assert_synthetic_reachability()
    counts = assert_fixture_distribution()
    print("Relationship archetype selector smoke passed")
    print(f"- reachable archetypes: {len(EXPECTED_REACHABLE_TITLES)}")
    print(f"- fixture distribution: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
