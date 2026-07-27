#!/usr/bin/env python3
"""Smoke-test the final user-facing interpretation layer for paid Western V1."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from visible_reading_depth import build_view_models, visible_phrases  # noqa: E402
from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FINAL_COPY_ABSTRACT_PHRASES,
    FINAL_NARRATIVE_SECTION_CONTRACTS,
)
from readable_interpretation.final_narrative_fact_renderer import (  # noqa: E402
    OBSERVABLE_FORMS,
)
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    BLOCKED_ACTION_INFINITIVES,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    ARCHETYPE_HEADLINES,
)
from readable_interpretation.final_narrative_story_arc import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
)
from readable_interpretation.zh_tw import (  # noqa: E402
    RELATIONSHIP_FIT_ATTRACTION_BANK,
    RELATIONSHIP_FIT_BOUNDARY_BY_CONTACT,
    RELATIONSHIP_FIT_FRICTION_BANK,
    RELATIONSHIP_FIT_GROWTH_BANK,
    RELATIONSHIP_FIT_OBSERVABLE_BY_CONTACT,
    RELATIONSHIP_FIT_REPAIR_BY_DYNAMIC,
    RELATIONSHIP_FIT_REPAIR_BY_PAIR,
    RELATIONSHIP_FIT_VIABILITY_BY_QUESTION,
    humanize_visible_copy,
)


SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)
READABLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
EXACT_DATE_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}|第\s*\d+\s*天")
MONTH_PERIOD_PATTERN = re.compile(r"20\d{2} 年\s*\d{1,2} 月(?:上旬|中旬|下旬)(?:到\s*\d{1,2} 月(?:上旬|中旬|下旬))?")
ASPECT_PAIR_PATTERN = re.compile(r"(?:太陽|月亮|水星|金星|火星|木星|土星|天王星|海王星|冥王星)[-－](?:太陽|月亮|水星|金星|火星|木星|土星|天王星|海王星|冥王星)")
SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？!?]\s*")
FORBIDDEN_VISIBLE_TERMS = (
    "birth_time",
    "noon fallback",
    "date_noon_fallback",
    "time-sensitive",
    "timing band",
    "timing climate",
    "reducer",
    "selector",
    "methodClaim",
    "sourceClaim",
    "low pressure",
    "free",
    "免費",
    "解鎖",
    "NT$",
    "八字",
    "日主",
    "四柱",
    "bazi",
    "精準日期",
    "精準日",
    "用熱度要求對方立刻定義關係",
    "先拆掉",
    "先退回防線",
    "表達容易變慢、變怕承諾",
    "自尊和責任感被碰到時冷掉",
    "防衛點",
    "防線",
    "這不是",
    "這裡不是",
    "不是替",
    "不替對方宣告",
    "不能替對方",
    "心理結論",
    "讀心",
    "relationshipThesis",
    "relationshipCaseModel",
    "evidencePacket",
    "candidateDynamics",
    "selectedCandidateId",
    "primaryDynamic",
    "secondaryDynamics",
    "dynamicInteractionPlan",
    "這組動力",
    "關係型態：",
    "判斷：",
    "判讀",
    "轉折氣候",
    "此刻建議",
    "土星訊號",
    "相位",
    "承接度",
    "方法邊界",
    "關係生存指南",
    "你們不是只有想像中的好感",
    "談責任、承諾或結果時，關係容易變重、變慢或有人先防衛",
    "關係有機會透過耐心、規則和實際行動慢慢穩住",
    "所以這頁的重點不是誰先低頭",
    "反而讓互動進入防衛",
    "通道未斷",
    "穩定投入",
    "副動力",
    "單一星盤線索",
    "把距離直接解讀成不在乎",
    "承諾和距離感會讓回應變得比較保守",
    "避免推進速度又把對方推進防衛",
    "偶爾回覆還不能直接當成穩定投入",
    "行動速度",
    "互動很快從想處理變成對抗或升溫",
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
    "直接等於關係答案",
    "關係答案",
    "防衛",
    "互動速度",
    "靠近速度",
    "對抗或升溫",
    "進入對抗",
    "可觀察條件",
    "可觀察",
    *FINAL_COPY_ABSTRACT_PHRASES,
)
MAX_VISIBLE_SENTENCE_CHARS = 180
MAX_VISIBLE_SEMICOLONS = 2
MAX_FINAL_BODY_CHARS = 520
OLD_RELATIONSHIP_FIT_SLOT_LABELS = (
    "吸引力在這裡：",
    "卡住的地方在這裡：",
    "能不能繼續，要看：",
    "接下來現實裡要看：",
    "比較有用的是：",
    "先守住這條界線：",
)
MAX_BODY_COLONS_BY_SECTION = {
    "chart-positioning": 4,
    "relationship-fit": 1,
    "core-answer": 3,
    "timing-reading": 1,
    "action-direction": 3,
}
NON_ACTION_BODY_TERMS = ("下一步", "訊息", "開口", "攤牌", "補第二段", "行動方向")
TIMING_ONLY_TERMS = ("指定日期", "時段", "這段時間")
FIT_ONLY_TERMS = ("關係類型", "相處方式")
DYNAMIC_VISIBLE_MARKERS = {
    "emotional_safety": ("安全感", "情緒", "不安", "安心", "接住"),
    "saturn_pressure": ("承諾", "責任", "界線", "壓力", "變重"),
    "communication_repair": ("訊息", "開口", "說法", "接話", "對話"),
    "attraction_pursuit": ("吸引", "火花", "靠近", "熱絡", "延續"),
    "action_conflict": ("氣氛", "變硬", "衝突", "爭", "急"),
    "identity_rhythm": ("尊重", "台階", "自尊", "面子", "被看見"),
    "outer_intensity": ("強烈", "現實", "界線", "感覺", "行動"),
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def bank_phrase_count(bank: dict[Any, tuple[str, ...]]) -> int:
    return sum(len([item for item in values if item]) for values in bank.values())


def assert_relationship_fit_bank_capacity() -> None:
    expectations = {
        "attraction": (RELATIONSHIP_FIT_ATTRACTION_BANK, 21),
        "friction": (RELATIONSHIP_FIT_FRICTION_BANK, 24),
        "growth": (RELATIONSHIP_FIT_GROWTH_BANK, 15),
        "pair_repair": (RELATIONSHIP_FIT_REPAIR_BY_PAIR, 22),
        "dynamic_repair": (RELATIONSHIP_FIT_REPAIR_BY_DYNAMIC, 21),
        "viability": (RELATIONSHIP_FIT_VIABILITY_BY_QUESTION, 15),
        "observable": (RELATIONSHIP_FIT_OBSERVABLE_BY_CONTACT, 15),
        "boundary": (RELATIONSHIP_FIT_BOUNDARY_BY_CONTACT, 10),
    }
    for label, (bank, minimum) in expectations.items():
        count = bank_phrase_count(bank)
        assert_true(count >= minimum, f"relationship-fit {label} bank too small: {count} < {minimum}")


def visible_section_text(section: dict[str, Any]) -> str:
    return "\n".join(str(section.get(field) or "") for field in READABLE_FIELDS if section.get(field))


def section_fingerprint(section: dict[str, Any]) -> str:
    return "|".join(visible_phrases(visible_section_text(section))[:5])


def meaningful_marker_variants(marker: str) -> list[str]:
    raw = str(marker or "").strip()
    if not raw:
        return []
    candidates = [raw, humanize_visible_copy(raw)]
    for value in list(candidates):
        if "：" in value:
            candidates.append(value.split("：", 1)[-1].strip())
        if ":" in value:
            candidates.append(value.split(":", 1)[-1].strip())
    output: list[str] = []
    for value in candidates:
        cleaned = re.sub(r"\s+", "", value.strip("。；;，, "))
        if len(cleaned) >= 8 and cleaned not in output:
            output.append(cleaned)
    return output


def acceptable_turning_titles(title: str, view_model: dict[str, Any]) -> list[str]:
    if title != "承諾與責任壓力期":
        return [title]
    action = str((view_model.get("timingGuidance") or {}).get("recommendedAction") or "")
    normalized = {
        "avoid_push": "界線和承擔變敏感的時段",
        "low_pressure_message": "低壓靠近條件",
        "observe_for_soft_window": "先觀察柔和訊號",
        "observe_only": "目前節奏觀察",
        "not_calculated": "資料不足，保守判斷",
    }.get(action, "界線和承擔變敏感的時段")
    return [title, normalized]


def assert_section(section: dict[str, Any], label: str, section_id: str) -> None:
    assert_true(section.get("version") == "readable-interpretation-v1", f"{label}: readable version mismatch")
    assert_true(str(section.get("module") or "").startswith("final_"), f"{label}: module should be final_*")
    assert_true(section.get("locale") == "zh-TW", f"{label}: locale mismatch")
    assert_true(len(str(section.get("headline") or "")) >= 4, f"{label}: headline too thin")
    assert_true(len(str(section.get("meaning") or "")) >= 18, f"{label}: meaning too thin")
    minimum_body_chars = {
        "chart-positioning": 18,
        "relationship-fit": 55,
        "core-answer": 18,
        "timing-reading": 20,
        "action-direction": 18,
    }[section_id]
    assert_true(
        len(str(section.get("body") or "")) >= minimum_body_chars,
        f"{label}: body too thin",
    )
    assert_true(
        len(str(section.get("body") or "")) <= MAX_FINAL_BODY_CHARS,
        f"{label}: body too long ({len(str(section.get('body') or ''))} > {MAX_FINAL_BODY_CHARS})",
    )
    assert_true(len(str(section.get("nextMove") or "")) >= 14, f"{label}: nextMove too thin")
    assert_true(len(str(section.get("caution") or "")) >= 18, f"{label}: caution too thin")
    assert_true(section.get("sourceClaimIds"), f"{label}: sourceClaimIds missing")
    assert_true(section.get("methodClaimIds"), f"{label}: methodClaimIds missing")
    assert_true(section.get("evidenceClusterKeys"), f"{label}: evidenceClusterKeys missing")

    text = visible_section_text(section)
    assert_true(not EXACT_DATE_PATTERN.search(text), f"{label}: exact-date/day language leaked")
    assert_true(not ASPECT_PAIR_PATTERN.search(text), f"{label}: visible astrology pair label leaked")
    for term in FORBIDDEN_VISIBLE_TERMS:
        assert_true(term not in text, f"{label}: forbidden visible term leaked: {term}")
    for sentence in SENTENCE_SPLIT_PATTERN.split(text):
        normalized = re.sub(r"\s+", "", sentence)
        if not normalized:
            continue
        assert_true(
            len(normalized) <= MAX_VISIBLE_SENTENCE_CHARS,
            f"{label}: visible sentence too long ({len(normalized)} > {MAX_VISIBLE_SENTENCE_CHARS}): {normalized[:80]}",
        )
        semicolon_count = normalized.count("；") + normalized.count(";")
        assert_true(
            semicolon_count <= MAX_VISIBLE_SEMICOLONS,
            f"{label}: visible sentence has too many clauses ({semicolon_count} > {MAX_VISIBLE_SEMICOLONS}): {normalized[:80]}",
        )


def assert_final_narrative_contract(sections: dict[str, Any], label: str) -> None:
    assert_true(
        set(FINAL_NARRATIVE_SECTION_CONTRACTS) == set(SECTION_IDS),
        f"{label}: final narrative composer contracts do not cover all sections",
    )
    section_texts = {section_id: visible_section_text(sections.get(section_id) or {}) for section_id in SECTION_IDS}
    fit_text = section_texts["relationship-fit"]
    for old_label in OLD_RELATIONSHIP_FIT_SLOT_LABELS:
        assert_true(old_label not in fit_text, f"{label}: old relationship-fit slot label still visible: {old_label}")

    for section_id, section in sections.items():
        body = str((section or {}).get("body") or "")
        colon_count = body.count("：") + body.count(":")
        assert_true(
            colon_count <= MAX_BODY_COLONS_BY_SECTION[section_id],
            f"{label}:{section_id}: body still reads like slot copy ({colon_count} colons)",
        )

    for section_id in ("chart-positioning", "relationship-fit", "timing-reading"):
        body = str((sections.get(section_id) or {}).get("body") or "")
        action_hits = [term for term in NON_ACTION_BODY_TERMS if term in body]
        assert_true(
            len(action_hits) <= 1,
            f"{label}:{section_id}: action language leaks into non-action body: {', '.join(action_hits)}",
        )
    core_body = str((sections.get("core-answer") or {}).get("body") or "")
    core_action_hits = [term for term in ("下一步", "攤牌", "補第二段", "行動方向") if term in core_body]
    assert_true(
        not core_action_hits,
        f"{label}:core-answer: action-plan language leaks into answer body: {', '.join(core_action_hits)}",
    )

    for section_id in ("chart-positioning", "relationship-fit", "core-answer", "action-direction"):
        body = str((sections.get(section_id) or {}).get("body") or "")
        timing_hits = [term for term in TIMING_ONLY_TERMS if term in body]
        assert_true(
            not timing_hits,
            f"{label}:{section_id}: timing language leaks into non-timing body: {', '.join(timing_hits)}",
        )

    action_body = str((sections.get("action-direction") or {}).get("body") or "")
    fit_hits = [term for term in FIT_ONLY_TERMS if term in action_body]
    assert_true(not fit_hits, f"{label}: action body re-analyzes relationship fit: {', '.join(fit_hits)}")

    sentences: list[str] = []
    for text in section_texts.values():
        sentences.extend(item.strip() for item in SENTENCE_SPLIT_PATTERN.split(text) if len(item.strip()) >= 14)
    repeated = [sentence for sentence in set(sentences) if sentences.count(sentence) > 1]
    assert_true(not repeated, f"{label}: duplicate final sentences across sections: {' / '.join(repeated[:2])}")


def assert_scenario(view_model: dict[str, Any]) -> None:
    label = str(view_model.get("id") or "unknown")
    final = view_model.get("finalInterpretation") or {}
    nested = ((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("finalInterpretation") or {}
    thesis = view_model.get("relationshipThesis") or ((view_model.get("westernRelationshipCaseFile") or {}).get("relationshipThesis") or {})
    assert_true(final.get("version") == "final-reading-interpretation-v1", f"{label}: final version missing")
    assert_true(final == nested, f"{label}: nested final interpretation mismatch")
    assert_true(thesis.get("version") == "relationship-thesis-v1", f"{label}: relationship thesis missing")
    assert_true((thesis.get("validation") or {}).get("passed") is True, f"{label}: relationship thesis did not pass validation")
    assert_true(final.get("locale") == "zh-TW", f"{label}: final locale mismatch")
    assert_true(final.get("methodClaimIds"), f"{label}: final methodClaimIds missing")
    assert_true(final.get("evidenceClusterKeys"), f"{label}: final evidenceClusterKeys missing")
    section_specs = view_model.get("sectionNarrativeSpecs") or final.get("sectionSpecs") or {}
    assert_true(section_specs.get("rendererConsumesSpecs") is True, f"{label}: final renderer is not consuming specs")
    assert_true((section_specs.get("validation") or {}).get("status") == "valid", f"{label}: section spec bundle invalid")

    sections = final.get("sections") or {}
    specs = section_specs.get("sections") or {}
    assert_true(set(sections) == set(SECTION_IDS), f"{label}: final section ids mismatch")
    assert_true(set(specs) == set(SECTION_IDS), f"{label}: section spec ids mismatch")
    for section_id in SECTION_IDS:
        assert_section(sections.get(section_id) or {}, f"{label}:{section_id}", section_id)
        keys = set((sections.get(section_id) or {}).get("evidenceClusterKeys") or [])
        expected_keys = set(((specs.get(section_id) or {}).get("trace") or {}).get("evidenceClusterKeys") or [])
        assert_true(keys == expected_keys, f"{label}:{section_id}: visible evidence does not match section-owned trace")
        if section_id in {"chart-positioning", "relationship-fit"}:
            assert_true(not ((specs.get(section_id) or {}).get("context") or {}), f"{label}:{section_id}: context leaked into chart-owned spec")
    assert_final_narrative_contract(sections, label)

    final_text = "\n".join(visible_section_text(sections.get(section_id) or {}) for section_id in SECTION_IDS)
    dynamic_key = str(thesis.get("centralDynamicKey") or "")
    dynamic_markers = DYNAMIC_VISIBLE_MARKERS.get(dynamic_key) or ()
    assert_true(
        any(marker in final_text for marker in dynamic_markers),
        f"{label}: primary dynamic not reflected in final readable copy: {dynamic_key}",
    )
    fact_sections = ((section_specs.get("finalNarrativeFacts") or {}).get("sections") or {})
    core_facts = (fact_sections.get("core-answer") or {}).get("facts") or []
    observable_keys = [
        str(item.get("valueKey") or "")
        for item in core_facts
        if isinstance(item, dict) and item.get("role") == "observable-sign"
    ]
    visible_signs = [
        value
        for key in observable_keys
        if key in OBSERVABLE_FORMS
        for value in (
            OBSERVABLE_FORMS[key].direct,
            OBSERVABLE_FORMS[key].situational,
            OBSERVABLE_FORMS[key].relational,
        )
    ]
    assert_true(
        any(sign in final_text for sign in visible_signs),
        f"{label}: observable thesis signs not reflected in final copy",
    )

    fit_facts = (fact_sections.get("relationship-fit") or {}).get("facts") or []
    archetype_fact = next(
        (
            item
            for item in fit_facts
            if isinstance(item, dict) and item.get("role") == "relationship-archetype"
        ),
        None,
    )
    assert_true(archetype_fact is not None, f"{label}: fit archetype fact missing")
    archetype_key = str((archetype_fact or {}).get("valueKey") or "unknown")
    expected_headline = ARCHETYPE_HEADLINES.get(archetype_key)
    assert_true(expected_headline is not None, f"{label}: unsupported fit archetype: {archetype_key}")
    assert_true(
        sections["relationship-fit"].get("headline") == expected_headline,
        f"{label}: fit headline does not match approved archetype realization",
    )
    partner_need_facts = [
        item
        for item in core_facts
        if isinstance(item, dict) and item.get("role") == "partner-relationship-need"
    ]
    core_domains = {
        str(item.get("domain") or "")
        for item in (specs.get("core-answer") or {}).get("evidence") or []
        if isinstance(item, dict)
    }
    assert_true(
        bool(partner_need_facts)
        and "partnerNatal" in core_domains
        and FINAL_NARRATIVE_ROLE_PRESENTATIONS["core-answer"][
            "partner-relationship-need"
        ]
        == "hidden-support",
        f"{label}: core partner-need support contract is incomplete",
    )
    turning_title = str((((view_model.get("relationshipTurningWindows") or {}).get("items") or [{}])[0]).get("title") or "")
    if turning_title:
        timing_facts = (fact_sections.get("timing-reading") or {}).get("facts") or []
        assert_true(
            any(isinstance(item, dict) and item.get("role") == "timing-window" for item in timing_facts),
            f"{label}: timing section does not use its timing-window fact",
        )
    period_label = str((((view_model.get("relationshipTurningWindows") or {}).get("items") or [{}])[0]).get("periodLabel") or "")
    if period_label:
        if MONTH_PERIOD_PATTERN.search(period_label):
            assert_true(period_label in visible_section_text(sections["timing-reading"]), f"{label}: timing section does not use period label")
        else:
            timing_slots = ((specs.get("timing-reading") or {}).get("semanticSlots") or {})
            assert_true(not timing_slots.get("preciseDatesAvailable"), f"{label}: invalid timing period label: {period_label}")
    landmine_title = str((((view_model.get("fightLandmines") or {}).get("items") or [{}])[0]).get("title") or "")
    if landmine_title:
        action_facts = (fact_sections.get("action-direction") or {}).get("facts") or []
        blocked_keys = [
            str(item.get("valueKey") or "")
            for item in action_facts
            if isinstance(item, dict) and item.get("role") == "blocked-action"
        ]
        action_text = visible_section_text(sections["action-direction"])
        assert_true(
            any(
                BLOCKED_ACTION_INFINITIVES.get(key, "") in action_text
                for key in blocked_keys
                if BLOCKED_ACTION_INFINITIVES.get(key)
            ),
            f"{label}: action section does not use blocked-action facts",
        )

    rendered = json.dumps(final, ensure_ascii=False)
    assert_true("八字" not in rendered and "bazi" not in rendered.lower(), f"{label}: BaZi leaked in final payload")


def main() -> int:
    view_models = build_view_models()
    failures: list[str] = []
    fingerprints: dict[str, set[str]] = {section_id: set() for section_id in SECTION_IDS}
    try:
        assert_relationship_fit_bank_capacity()
    except AssertionError as exc:
        failures.append(str(exc))
    for view_model in view_models:
        try:
            assert_scenario(view_model)
        except AssertionError as exc:
            failures.append(str(exc))
        final = view_model.get("finalInterpretation") or {}
        sections = final.get("sections") or {}
        for section_id in SECTION_IDS:
            if isinstance(sections.get(section_id), dict):
                fingerprints[section_id].add(section_fingerprint(sections[section_id]))

    for section_id, values in fingerprints.items():
        if len({value for value in values if value}) < 4:
            failures.append(f"{section_id}: scenario variation too low ({len(values)} < 4)")

    if failures:
        print("Western final interpretation layer smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Western final interpretation layer smoke passed")
    print(f"- validated scenarios: {len(view_models)}")
    print(f"- section variation: { {key: len(value) for key, value in fingerprints.items()} }")
    print("- final narrative composer contracts: enforced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
