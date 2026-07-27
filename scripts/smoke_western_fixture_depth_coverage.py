#!/usr/bin/env python3
"""Smoke-test V2 relationship fixture depth and visible-copy variety."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
MANIFEST_PATH = ROOT / "examples" / "calculations" / "relationship-depth-fixtures-v2.json"

MIN_DYNAMIC_COUNTS = {
    "emotional_safety": 5,
    "saturn_pressure": 5,
    "communication_repair": 5,
    "attraction_pursuit": 5,
    "action_conflict": 5,
    "identity_rhythm": 4,
    "outer_intensity": 3,
}

MIN_TIMING_COUNTS = {
    "low_pressure_message": 8,
    "observe_for_soft_window": 5,
    "observe_only": 5,
    "not_calculated": 4,
}

VISIBLE_PHRASE_LIMITS = {
    "不要一次談完整段關係": 0.2,
    "越要把問題拆小": 0.2,
    "一推進就升溫": 0.25,
    "變成爭辯": 0.25,
    "界線和承擔變敏感": 0.35,
}
FORBIDDEN_REPEATED_RELATIONSHIP_FIT_PHRASES = (
    "你們不是只有想像中的好感",
    "談責任、承諾或結果時，關係容易變重、變慢或有人先防衛",
    "關係有機會透過耐心、規則和實際行動慢慢穩住",
    "所以這頁的重點不是誰先低頭",
    "行動速度就容易變急，互動很快從想處理變成對抗或升溫",
    "你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案",
    "更像一個位置",
    "更像一個入口",
    "可以當位置",
    "可以當入口",
    "可以當方式",
    "訊息要比感覺更輕",
    "開口方式要小於你的情緒強度",
    "開口要比情緒小很多",
    "把行動縮小",
    "壓力測試",
    "低要求",
    "把火花落到",
    "零散回應",
    "小訊號",
    "聯絡受阻",
    "自我穩定",
    "校準",
    "小而可觀察",
    "修復方向",
    "被彼此反應",
)
OLD_RELATIONSHIP_FIT_SLOT_LABELS = (
    "吸引力在這裡：",
    "卡住的地方在這裡：",
    "能不能繼續，要看：",
    "接下來現實裡要看：",
    "比較有用的是：",
    "先守住這條界線：",
)
RELATIONSHIP_FIT_BODY_SLOT_INDEXES = {
    "attraction": 0,
    "friction": 1,
    "supporting": 2,
}
RELATIONSHIP_FIT_NARRATIVE_MINIMUMS = {
    "archetype": 4,
    "attraction": 4,
    "friction": 5,
    "supporting": 5,
    "repair": 6,
}
RELATIONSHIP_FIT_NARRATIVE_MAX_REPEATS = {
    "archetype": 18,
    "attraction": 20,
    "friction": 18,
    "supporting": 8,
    "repair": 8,
}
TURNING_WINDOW_TITLES = ("關係氣氛比較柔和", "容易擦槍走火的時段")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def rendered_turning_window_text(scenario: dict[str, Any]) -> str:
    turning_windows = ((scenario.get("relationshipTurningWindows") or {}).get("items") or [])
    return compact_json([item for item in turning_windows if str(item.get("title") or "") in TURNING_WINDOW_TITLES])


def turning_periods_overlap(first: dict[str, Any], second: dict[str, Any]) -> bool:
    if str(first.get("periodLabel") or "") == str(second.get("periodLabel") or ""):
        return True
    first_start = str(first.get("periodStartDate") or "")
    first_end = str(first.get("periodEndDate") or first_start)
    second_start = str(second.get("periodStartDate") or "")
    second_end = str(second.get("periodEndDate") or second_start)
    if not first_start or not first_end or not second_start or not second_end:
        return False
    return not (first_end < second_start or second_end < first_start)


def assert_turning_window_contract(scenarios: list[dict[str, Any]]) -> None:
    allowed_titles = set(TURNING_WINDOW_TITLES)
    for scenario in scenarios:
        scenario_id = str(scenario.get("id") or "unknown")
        items = ((scenario.get("relationshipTurningWindows") or {}).get("items") or [])
        titles = [str(item.get("title") or "") for item in items if isinstance(item, dict)]
        require(len(items) <= 2, f"{scenario_id}: relationshipTurningWindows has more than two cards: {titles}")
        unexpected = [title for title in titles if title not in allowed_titles and not title.endswith("互動時機資料不足")]
        require(not unexpected, f"{scenario_id}: unexpected turning-window titles: {unexpected}")
        for title in allowed_titles:
            require(titles.count(title) <= 1, f"{scenario_id}: duplicate turning-window title: {title}")
        soft_window = next((item for item in items if str(item.get("title") or "") == "關係氣氛比較柔和"), None)
        tension_window = next((item for item in items if str(item.get("title") or "") == "容易擦槍走火的時段"), None)
        if soft_window and tension_window:
            require(
                not turning_periods_overlap(soft_window, tension_window),
                f"{scenario_id}: soft and tension windows overlap: {soft_window.get('periodLabel')} / {tension_window.get('periodLabel')}",
            )


def visible_payload_text(scenario: dict[str, Any]) -> str:
    visible_payload = {
        "finalInterpretation": scenario.get("finalInterpretation"),
        "normalUserAnswer": scenario.get("normalUserAnswer"),
        "timingGuidance": scenario.get("timingGuidance"),
        "actionGuidance": scenario.get("actionGuidance"),
        "relationshipThesis": scenario.get("relationshipThesis"),
        "renderedTurningWindows": rendered_turning_window_text(scenario),
    }
    return compact_json(visible_payload)


def count_by(scenarios: list[dict[str, Any]], key_path: tuple[str, ...]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for scenario in scenarios:
        value: Any = scenario
        for key in key_path:
            value = value.get(key) if isinstance(value, dict) else None
        counts[str(value or "")] += 1
    return counts


def relationship_fit_semantic_signatures(scenario: dict[str, Any]) -> dict[str, str]:
    slots = (
        (((scenario.get("sectionNarrativeSpecs") or {}).get("sections") or {}).get("relationship-fit") or {})
        .get("semanticSlots")
        or {}
    )

    def first_key(slot: str) -> str:
        values = slots.get(slot) or []
        first = values[0] if values else {}
        return str(first.get("key") or "unknown") if isinstance(first, dict) else "unknown"

    secondary_values = slots.get("secondaryDynamicKeys") or []
    return {
        "archetype": str(slots.get("archetypeTitle") or "unknown"),
        "attraction": first_key("attractionSignals"),
        "friction": first_key("frictionSignals"),
        "supporting": str(secondary_values[0] if secondary_values else "unknown"),
        "repair": first_key("growthSignals"),
    }


def main() -> int:
    scenarios = read_json(SCENARIOS_PATH)
    manifest = read_json(MANIFEST_PATH)
    cases = manifest.get("cases") or []
    require(isinstance(scenarios, list), "Generated scenarios must be a list.")
    require(25 <= len(scenarios) <= 50, f"Expected 25-50 generated scenarios, got {len(scenarios)}.")
    require(25 <= len(cases) <= 40, f"Expected 25-40 V2 manifest cases, got {len(cases)}.")

    scenarios_by_id = {str(scenario.get("id") or ""): scenario for scenario in scenarios}
    require(len(scenarios_by_id) == len(scenarios), "Generated scenario IDs must be unique.")
    missing_v2 = [case.get("id") for case in cases if case.get("id") not in scenarios_by_id]
    require(not missing_v2, f"Missing generated V2 scenarios: {missing_v2[:5]}")

    for case in cases:
        scenario = scenarios_by_id[str(case["id"])]
        actual_dynamic = ((scenario.get("relationshipThesis") or {}).get("centralDynamicKey") or "")
        actual_action = ((scenario.get("timingGuidance") or {}).get("recommendedAction") or "")
        require(
            actual_dynamic == case["intended_dynamic"],
            f"{case['id']} selected {actual_dynamic}, expected {case['intended_dynamic']}.",
        )
        require(
            actual_action == case["timing_profile"],
            f"{case['id']} timing action {actual_action}, expected {case['timing_profile']}.",
        )

    required_stages = {"ambiguous", "broke-up-recent", "broke-up-long", "cold-war", "crisis"}
    for label, path, minimum in (
        ("questions", ("context", "main_question"), 5),
        ("stages", ("context", "relationship_stage"), 5),
        ("contact statuses", ("context", "contact_status"), 5),
    ):
        counts = count_by(scenarios, path)
        require(len(counts) >= minimum, f"Expected at least {minimum} {label}, got {dict(counts)}.")
        require(min(counts.values()) >= 6 if label == "stages" else min(counts.values()) >= 6, f"{label} under-covered: {dict(counts)}")
        if label == "stages":
            missing_stages = sorted(required_stages - set(counts))
            require(not missing_stages, f"Missing relationship stages: {missing_stages}")

    dynamic_counts = count_by(scenarios, ("relationshipThesis", "centralDynamicKey"))
    for dynamic, minimum in MIN_DYNAMIC_COUNTS.items():
        require(dynamic_counts[dynamic] >= minimum, f"{dynamic} count {dynamic_counts[dynamic]} < {minimum}.")

    timing_counts = count_by(scenarios, ("timingGuidance", "recommendedAction"))
    for action, minimum in MIN_TIMING_COUNTS.items():
        require(timing_counts[action] >= minimum, f"{action} count {timing_counts[action]} < {minimum}.")
    require(
        timing_counts["avoid_push"] <= int(len(scenarios) * 0.35),
        f"avoid_push appears too often: {timing_counts['avoid_push']} of {len(scenarios)}.",
    )

    central_theses = [str((scenario.get("relationshipThesis") or {}).get("centralThesis") or "") for scenario in scenarios]
    require(len(set(central_theses)) >= 30, f"Central thesis variety too low: {len(set(central_theses))}.")
    max_duplicate = Counter(central_theses).most_common(1)[0][1]
    require(max_duplicate <= 2, f"One central thesis repeats {max_duplicate} times.")
    assert_turning_window_contract(scenarios)

    visible_texts = {str(scenario.get("id") or ""): visible_payload_text(scenario) for scenario in scenarios}
    for phrase, ratio in VISIBLE_PHRASE_LIMITS.items():
        count = sum(1 for text in visible_texts.values() if phrase in text)
        limit = max(1, int(len(scenarios) * ratio))
        require(count <= limit, f"Visible phrase {phrase!r} appears {count} times; limit is {limit}.")
    for phrase in FORBIDDEN_REPEATED_RELATIONSHIP_FIT_PHRASES:
        count = sum(1 for text in visible_texts.values() if phrase in text)
        require(count == 0, f"Old generic relationship-fit phrase {phrase!r} still appears {count} times.")
    require(
        not any("承諾與責任壓力期" in text for text in visible_texts.values()),
        "Visible payload still contains the old repeated timing headline.",
    )

    relationship_fit_sections = [
        (((scenario.get("finalInterpretation") or {}).get("sections") or {}).get("relationship-fit") or {})
        for scenario in scenarios
    ]
    relationship_fit_bodies = [str(section.get("body") or "") for section in relationship_fit_sections]
    relationship_fit_texts = [
        "\n".join(str(section.get(field) or "") for field in ("headline", "meaning", "body", "nextMove", "caution"))
        for section in relationship_fit_sections
    ]
    require(
        len(set(relationship_fit_bodies)) >= 10,
        f"Relationship-fit body variety too low: {len(set(relationship_fit_bodies))} unique of {len(scenarios)}.",
    )
    for old_label in OLD_RELATIONSHIP_FIT_SLOT_LABELS:
        count = sum(1 for text in relationship_fit_texts if old_label in text)
        require(count == 0, f"Old relationship-fit slot label {old_label!r} still appears {count} times.")
    narrative_values: dict[str, set[str]] = {slot: set() for slot in RELATIONSHIP_FIT_NARRATIVE_MINIMUMS}
    narrative_counts: dict[str, Counter[str]] = {slot: Counter() for slot in RELATIONSHIP_FIT_NARRATIVE_MINIMUMS}
    semantic_outputs: dict[str, dict[str, set[str]]] = {
        slot: {} for slot in RELATIONSHIP_FIT_NARRATIVE_MINIMUMS
    }
    output_semantics: dict[str, dict[str, set[str]]] = {
        slot: {} for slot in RELATIONSHIP_FIT_NARRATIVE_MINIMUMS
    }
    semantic_counts: dict[str, Counter[str]] = {
        slot: Counter() for slot in RELATIONSHIP_FIT_NARRATIVE_MINIMUMS
    }
    for scenario, section in zip(scenarios, relationship_fit_sections, strict=True):
        signatures = relationship_fit_semantic_signatures(scenario)

        def record(slot: str, value: str) -> None:
            narrative_values[slot].add(value)
            narrative_counts[slot][value] += 1
            semantic_outputs[slot].setdefault(signatures[slot], set()).add(value)
            output_semantics[slot].setdefault(value, set()).add(signatures[slot])
            semantic_counts[slot][signatures[slot]] += 1

        archetype = str(section.get("headline") or "").split("：", 1)[0].strip()
        if archetype:
            record("archetype", archetype)
        repair = str(section.get("nextMove") or "").strip().rstrip("。！？!?")
        if repair:
            record("repair", repair)
        body_sentences = [
            item.strip()
            for item in re.split(r"[。！？!?]+", str(section.get("body") or ""))
            if item.strip()
        ]
        for slot, index in RELATIONSHIP_FIT_BODY_SLOT_INDEXES.items():
            if index < len(body_sentences):
                record(slot, body_sentences[index])
    for slot, minimum in RELATIONSHIP_FIT_NARRATIVE_MINIMUMS.items():
        value = len(narrative_values[slot])
        require(value >= minimum, f"Relationship-fit {slot} narrative variety too low: {value} < {minimum}.")
        unstable = {
            signature: sorted(outputs)
            for signature, outputs in semantic_outputs[slot].items()
            if len(outputs) != 1
        }
        collapsed = {
            output: sorted(signatures)
            for output, signatures in output_semantics[slot].items()
            if len(signatures) != 1
        }
        require(not unstable, f"Relationship-fit {slot} semantic values render inconsistently: {unstable}.")
        require(not collapsed, f"Relationship-fit {slot} semantic values collapse to one sentence: {collapsed}.")
    for slot, maximum in RELATIONSHIP_FIT_NARRATIVE_MAX_REPEATS.items():
        max_repeat = narrative_counts[slot].most_common(1)[0][1] if narrative_counts[slot] else 0
        repeated_semantic_input = semantic_counts[slot].most_common(1)[0][1] if semantic_counts[slot] else 0
        allowed_maximum = max(maximum, repeated_semantic_input)
        require(max_repeat <= allowed_maximum, f"Relationship-fit {slot} narrative repeats too often: {max_repeat} > {allowed_maximum}.")

    print("Fixture depth smoke passed.")
    print(f"Scenarios: {len(scenarios)}")
    print(f"Questions: {dict(count_by(scenarios, ('context', 'main_question')))}")
    print(f"Stages: {dict(count_by(scenarios, ('context', 'relationship_stage')))}")
    print(f"Contact statuses: {dict(count_by(scenarios, ('context', 'contact_status')))}")
    print(f"Dynamics: {dict(dynamic_counts)}")
    print(f"Timing actions: {dict(timing_counts)}")
    print(f"Unique central theses: {len(set(central_theses))}")
    print(f"Relationship-fit narrative variants: { {slot: len(values) for slot, values in narrative_values.items()} }")
    print(f"Relationship-fit max narrative repeats: { {slot: (counts.most_common(1)[0][1] if counts else 0) for slot, counts in narrative_counts.items()} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
