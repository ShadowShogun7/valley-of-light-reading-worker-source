#!/usr/bin/env python3
"""Lock-and-evolve checks for the FinalNarrativeComposer layer."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FINAL_COPY_ABSTRACT_PHRASES,
    FINAL_NARRATIVE_COMPOSER_VERSION,
    FINAL_NARRATIVE_SECTION_CONTRACTS,
    FinalNarrativeSemanticInput,
)
from visible_reading_depth import READING_PATHS, build_view_models  # noqa: E402


GOLDEN_PATH = ROOT / "data" / "reading-quality-cases" / "final-narrative-golden-v1.json"
SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
ZH_TW_PATH = ROOT / "scripts" / "readable_interpretation" / "zh_tw.py"
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
SECTION_IDS = ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction")

FORBIDDEN_VISIBLE_TERMS = (
    "判讀",
    "副動力",
    "承接度",
    "承接量",
    "可觀察",
    "通道未斷",
    "通道受阻",
    "壓力測試",
    "關係答案",
    "行動速度",
    "方法邊界",
    "reducer",
    "selector",
    "relationshipThesis",
    "relationshipCaseModel",
    "dynamicInteractionPlan",
    *FINAL_COPY_ABSTRACT_PHRASES,
)

OLD_SLOT_LABELS = (
    "吸引力在這裡：",
    "卡住的地方在這裡：",
    "能不能繼續，要看：",
    "接下來現實裡要看：",
    "比較有用的是：",
    "先守住這條界線：",
)

FORBIDDEN_DIRECT_SOURCE_KEYS = {
    "technical",
    "reducerInstruction",
    "dynamicInteraction",
    "whatThisMeans",
    "whatItDoesNotMean",
    "repairImplication",
    "actionBoundary",
    "timingModifier",
    "contactModifier",
    "interpretiveJob",
    "caseBridge",
    "readingRole",
    "psychologicalFocus",
    "answerContract",
    "interpretation",
    "emotionalMeaning",
}

DYNAMIC_MARKERS = {
    "emotional_safety": ("安全感", "不安", "安心", "情緒"),
    "saturn_pressure": ("承諾", "責任", "界線", "壓力"),
    "communication_repair": ("訊息", "開口", "說法", "接話"),
    "attraction_pursuit": ("吸引", "火花", "靠近", "熱絡"),
    "action_conflict": ("氣氛", "變硬", "爭", "急"),
    "identity_rhythm": ("尊重", "台階", "面子", "被看見"),
    "outer_intensity": ("強烈", "現實", "界線", "猜測"),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def final_visible_sections(view_model: dict[str, Any]) -> dict[str, dict[str, str]]:
    sections = (view_model.get("finalInterpretation") or {}).get("sections") or {}
    return {
        section_id: {
            field: str((sections.get(section_id) or {}).get(field) or "")
            for field in VISIBLE_FIELDS
        }
        for section_id in SECTION_IDS
    }


def final_visible_text(view_model: dict[str, Any]) -> str:
    sections = final_visible_sections(view_model)
    return "\n".join(
        value
        for section in sections.values()
        for value in section.values()
        if value
    )


def build_snapshot_payload(view_models: list[dict[str, Any]]) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for view_model in view_models:
        scenario_id = str(view_model.get("id") or "")
        records[scenario_id] = {
            "questionKey": str((view_model.get("context") or {}).get("main_question") or ""),
            "stageKey": str((view_model.get("context") or {}).get("relationship_stage") or ""),
            "contactKey": str((view_model.get("context") or {}).get("contact_status") or ""),
            "sections": final_visible_sections(view_model),
        }
    return {
        "version": "final-narrative-golden-v9",
        "composerVersion": FINAL_NARRATIVE_COMPOSER_VERSION,
        "scenarioIds": [str(view_model.get("id") or "") for view_model in view_models],
        "records": records,
    }


def assert_snapshot(current: dict[str, Any], expected: dict[str, Any]) -> None:
    require(expected.get("version") == "final-narrative-golden-v9", "golden snapshot version mismatch")
    require(expected.get("composerVersion") == FINAL_NARRATIVE_COMPOSER_VERSION, "golden snapshot composer version mismatch")
    require(current.get("scenarioIds") == expected.get("scenarioIds"), "golden snapshot scenario ids changed")
    failures: list[str] = []
    for scenario_id, current_record in (current.get("records") or {}).items():
        expected_record = (expected.get("records") or {}).get(scenario_id) or {}
        for section_id in SECTION_IDS:
            for field in VISIBLE_FIELDS:
                actual = (((current_record.get("sections") or {}).get(section_id) or {}).get(field) or "")
                wanted = (((expected_record.get("sections") or {}).get(section_id) or {}).get(field) or "")
                if actual != wanted:
                    failures.append(
                        f"{scenario_id}:{section_id}.{field}: snapshot changed "
                        f"expected={wanted[:60]!r} actual={actual[:60]!r}"
                    )
    require(not failures, "golden snapshot mismatch:\n- " + "\n- ".join(failures[:12]))


def assert_composer_ownership() -> None:
    source = ZH_TW_PATH.read_text(encoding="utf-8")
    require("FinalNarrativeSemanticInput(" in source, "final renderer does not build FinalNarrativeSemanticInput")
    require(
        "FinalNarrativeComposer.from_semantic_input(final_semantic_input)" in source,
        "final renderer does not construct composer from semantic input",
    )
    require(set(FINAL_NARRATIVE_SECTION_CONTRACTS) == set(SECTION_IDS), "composer section contracts are incomplete")
    require(
        set(FinalNarrativeSemanticInput.__dataclass_fields__) >= {
            "question_key",
            "stage_key",
            "contact_key",
            "section_specs",
            "fact_contract",
        },
        "FinalNarrativeSemanticInput is missing required semantic fields",
    )
    require("section_specs=section_specs" in source, "final renderer does not pass section specs to the composer")
    require(
        'fact_contract=section_specs.get("finalNarrativeFacts")' in source,
        "final renderer does not pass typed facts to the composer",
    )
    require("combined_directives" not in source, "global paragraph directives still reach final rendering")
    require("section_directives=" not in source, "section paragraph overrides still reach final rendering")


def assert_quality_lock(view_models: Iterable[dict[str, Any]]) -> None:
    failures: list[str] = []
    for view_model in view_models:
        scenario_id = str(view_model.get("id") or "unknown")
        sections = final_visible_sections(view_model)
        text = "\n".join(value for section in sections.values() for value in section.values())
        for term in FORBIDDEN_VISIBLE_TERMS:
            if term in text:
                failures.append(f"{scenario_id}: forbidden final visible term leaked: {term}")
        for label in OLD_SLOT_LABELS:
            if label in text:
                failures.append(f"{scenario_id}: old relationship-fit slot label leaked: {label}")
        for section_id, fields in sections.items():
            body = fields.get("body") or ""
            colon_count = body.count("：") + body.count(":")
            if section_id == "relationship-fit" and colon_count > 1:
                failures.append(f"{scenario_id}:{section_id}: body still reads like slot copy")
            if len(body) > 320:
                failures.append(f"{scenario_id}:{section_id}: body too long for final narrative lock: {len(body)}")
    require(not failures, "quality lock failed:\n- " + "\n- ".join(failures[:20]))


def iter_forbidden_direct_values(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[str, str]]:
    if path[:1] == ("finalInterpretation",):
        return
    if path[:3] == ("readableQuestionAnswer", "sections", "finalInterpretation"):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, str(key))
            if key in FORBIDDEN_DIRECT_SOURCE_KEYS and isinstance(child, str):
                normalized = normalize_text(child)
                if len(normalized) >= 18:
                    yield (".".join(child_path), normalized)
            yield from iter_forbidden_direct_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_forbidden_direct_values(child, (*path, str(index)))


def assert_no_direct_source_leaks(view_models: Iterable[dict[str, Any]]) -> None:
    failures: list[str] = []
    for view_model in view_models:
        scenario_id = str(view_model.get("id") or "unknown")
        final_text = normalize_text(final_visible_text(view_model))
        for path, source_text in iter_forbidden_direct_values(view_model):
            if source_text and source_text in final_text:
                failures.append(f"{scenario_id}: raw internal source leaked into final copy: {path}")
    require(not failures, "visible-source guard failed:\n- " + "\n- ".join(failures[:20]))


def assert_evolution(generated_scenarios: list[dict[str, Any]]) -> None:
    failures: list[str] = []
    dynamic_text: dict[str, str] = defaultdict(str)
    contact_fingerprints: dict[str, set[str]] = defaultdict(set)
    for scenario in generated_scenarios:
        model = scenario.get("relationshipCaseModel") or {}
        primary = str(((model.get("primaryDynamic") or {}).get("key")) or "")
        contact = str((scenario.get("context") or {}).get("contact_status") or "")
        text = final_visible_text(scenario)
        action_text = "\n".join((final_visible_sections(scenario).get("action-direction") or {}).values())
        if primary:
            dynamic_text[primary] += "\n" + text
        if contact:
            contact_fingerprints[contact].add(normalize_text(action_text)[:180])

    for dynamic, markers in DYNAMIC_MARKERS.items():
        text = dynamic_text.get(dynamic, "")
        if not any(marker in text for marker in markers):
            failures.append(f"{dynamic}: final copy does not reflect dynamic markers")
    for contact, fingerprints in contact_fingerprints.items():
        if len(fingerprints) < 2:
            failures.append(f"{contact}: contact state does not produce final action variation")
    require(not failures, "evolution guard failed:\n- " + "\n- ".join(failures[:20]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify FinalNarrativeComposer lock-and-evolve contract.")
    parser.add_argument("--update", action="store_true", help="Regenerate the golden snapshot file.")
    args = parser.parse_args()

    built_view_models = build_view_models(READING_PATHS)
    generated_scenarios = read_json(SCENARIOS_PATH)
    current_snapshot = build_snapshot_payload(built_view_models)

    if args.update:
        write_json(GOLDEN_PATH, current_snapshot)
        print(f"Wrote final narrative golden snapshots -> {GOLDEN_PATH.relative_to(ROOT)}")
        return 0

    failures: list[str] = []
    try:
        assert_composer_ownership()
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_snapshot(current_snapshot, read_json(GOLDEN_PATH))
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_quality_lock([*built_view_models, *generated_scenarios])
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_no_direct_source_leaks([*built_view_models, *generated_scenarios])
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_evolution(generated_scenarios)
    except AssertionError as exc:
        failures.append(str(exc))

    if failures:
        print("Final narrative lock smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Final narrative lock smoke passed")
    print(f"- golden scenarios: {len(built_view_models)}")
    print(f"- generated scenarios checked: {len(generated_scenarios)}")
    print("- composer ownership, source guard, quality lock, and evolution guard verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
