#!/usr/bin/env python3
"""Smoke-test native Traditional Chinese copy on paid V1 visible result surfaces."""

from __future__ import annotations

import re
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
from readable_interpretation.copy_contract import reader_meta_narration_hits  # noqa: E402
from readable_interpretation.final_narrative_composer import FINAL_COPY_ABSTRACT_PHRASES  # noqa: E402


READING_PATHS = (
    ROOT / "examples" / "readings" / "cold-war-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-long-any-chance.json",
    ROOT / "examples" / "readings" / "cold-war-when-to-contact.json",
    ROOT / "examples" / "readings" / "broke-up-recent-what-did-i-do-wrong.json",
    ROOT / "examples" / "readings" / "crisis-stay-or-let-go.json",
    ROOT / "examples" / "readings" / "broke-up-recent-still-love-me.json",
    ROOT / "examples" / "readings" / "blocked-anxious-still-love-me.json",
    ROOT / "examples" / "readings" / "no-contact-desperate-when-to-contact.json",
    ROOT / "examples" / "readings" / "still-in-contact-self-blaming-what-did-i-do-wrong.json",
    ROOT / "examples" / "readings" / "ambiguous-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-long-release-stay-or-let-go.json",
)
FORBIDDEN_VISIBLE_TERMS = (
    "八字",
    "免費",
    "付費",
    "完整報告",
    "解鎖",
    "upsell",
    "reducer",
    "selector",
    "timing",
    "avoid_push",
    "low_pressure",
    "not_calculated",
    "boundary_only",
    "soft_tone",
    "low stimulation",
    "低壓",
    "低刺激",
    "低需求",
    "可不回",
    "需求語言",
    "橋接",
    "有橋",
    "控速",
    "降刺激",
    "推進速度與衝突反應",
    "責任與長期承接",
    "星盤只能支持",
    "精準日期",
    "精準日",
    "日期精度",
    "行動窗口",
    "聯絡窗口",
    "未來掃描",
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
    "Moon/Venus",
    "Moon 的",
    "Venus 的",
    "Saturn-in-sign",
    "Saturn timing",
    "Saturn pressure",
    "certainty",
    "fatal verdict",
    "Hard contact",
    "hard contact",
    "Soft contact",
    "soft contact",
    "overlay",
    "Asc/Desc",
)
FINAL_FORBIDDEN_TECHNICAL_TERMS = (
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
    "relationshipThesis",
    "relationshipCaseModel",
    "dynamicInteractionPlan",
    "primaryDynamic",
    "secondaryDynamics",
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
    "這頁",
    "這一頁",
    "時機頁",
    "先不把其他問題一次放進來",
    "吸引在",
    "卡住在",
    "這比一句回覆或一次冷熱更重要",
    "回覆不穩先保守",
    "互動地雷 1",
    "低強度線索",
    "回覆不穩時答案要保守",
    *FINAL_COPY_ABSTRACT_PHRASES,
)
FATALISTIC_VISIBLE_TERMS = (
    "這段關係一定會復合",
    "你們一定會復合",
    "一定會分手",
    "一定沒有機會",
    "一定沒機會",
    "注定分開",
    "注定復合",
    "命中註定",
    "保證會復合",
    "保證對方會回來",
    "永久結束",
    "他一定還愛你",
    "他一定不愛你",
    "對方一定還愛你",
    "對方一定不愛你",
    "他心裡一定",
    "對方心裡一定",
    "某天聯絡一定成功",
    "聯絡一定成功",
)
EXACT_DATE_PATTERNS = (
    re.compile(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}\b"),
    re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日"),
    re.compile(r"(哪一天|某一天|某天).{0,8}(一定|保證|必然|成功|回覆|復合)"),
)
REQUIRED_EVERYDAY_MARKERS = (
    "短、輕",
    "自然接住",
    "先停",
    "不要",
    "回應",
)
DISPLAY_TEXT_KEYS = {
    "answer",
    "badge",
    "body",
    "caution",
    "confidenceNote",
    "doesNotFit",
    "headline",
    "helper",
    "label",
    "meaning",
    "naturalResponse",
    "nextMove",
    "placement",
    "precisionWarnings",
    "preview",
    "question",
    "range",
    "relationshipUse",
    "responseRule",
    "safety",
    "stage",
    "stuckPattern",
    "style",
    "summary",
    "suitableFor",
    "tensionPattern",
    "title",
    "value",
    "relationshipStyleWanted",
    "emotionalSafetyCondition",
    "affectionLanguage",
    "communicationNeed",
    "conflictDefense",
    "commitmentPace",
    "whatOpensHimUp",
    "whatShutsHimDown",
    "commonMisread",
    "boundaryNote",
    "framing",
    "windowLabel",
    "periodLabel",
    "suggestion",
    "whatToAvoid",
}
DISPLAY_CONTAINER_KEYS = {
    "action",
    "actionGuidance",
    "cards",
    "chance",
    "donts",
    "effort",
    "evidenceHighlights",
    "finalInterpretation",
    "fitSummary",
    "friction",
    "includedReadingRows",
    "metrics",
    "natural",
    "items",
    "partnerNeeds",
    "personA",
    "personB",
    "profile",
    "readableInterpretation",
    "reasons",
    "reading",
    "relationshipProfiles",
    "relationshipTurningWindows",
    "sections",
    "selectedSignals",
    "thoughts",
    "timeline",
    "timing",
    "timingGuidance",
}
USER_REPORTED_VISIBLE_TERMS = (
    "反而讓互動進入防衛",
    "偶爾回覆只代表通道未斷，還不能當成穩定投入",
    "副動力要用來分辨值得等待和繼續消耗",
    "單一星盤線索",
    "把距離直接解讀成不在乎",
    "承諾和距離感會讓回應變得比較保守",
    "避免推進速度又把對方推進防衛",
    "偶爾回覆還不能直接當成穩定投入",
    "副動力",
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
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def visible_text_parts(view_model: dict[str, Any]) -> list[str]:
    parts: list[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if value.strip():
                parts.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                add(item)
        elif isinstance(value, dict):
            for key, child in value.items():
                if key in DISPLAY_TEXT_KEYS or key in DISPLAY_CONTAINER_KEYS:
                    add(child)

    for path in (
        ("reading",),
        ("metrics",),
        ("relationshipProfiles", "personA", "headline"),
        ("relationshipProfiles", "personA", "summary"),
        ("relationshipProfiles", "personA", "cards"),
        ("relationshipProfiles", "personA", "precisionWarnings"),
        ("relationshipProfiles", "personB", "headline"),
        ("relationshipProfiles", "personB", "summary"),
        ("relationshipProfiles", "personB", "cards"),
        ("relationshipProfiles", "personB", "precisionWarnings"),
        ("relationshipProfiles", "fitSummary"),
        ("partnerNeeds",),
        ("relationshipTurningWindows",),
        ("answerGuidance",),
        ("timingGuidance",),
        ("actionGuidance",),
        ("finalInterpretation",),
        ("readableQuestionAnswer", "sections"),
        ("reasons",),
        ("chance",),
        ("timeline",),
        ("donts",),
        ("includedReadingRows",),
    ):
        current: Any = view_model
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        add(current)
    return parts


def visible_text(view_model: dict[str, Any]) -> str:
    return "\n".join(visible_text_parts(view_model))


def final_interpretation_text(view_model: dict[str, Any]) -> str:
    final = view_model.get("finalInterpretation") or {}
    sections = final.get("sections") if isinstance(final, dict) else {}
    parts: list[str] = []
    for section in (sections or {}).values():
        if not isinstance(section, dict):
            continue
        for field in ("headline", "meaning", "body", "nextMove", "caution"):
            if section.get(field):
                parts.append(str(section.get(field) or ""))
    return "\n".join(parts)


def audit_view_model(view_model: dict[str, Any]) -> list[str]:
    text = visible_text(view_model)
    final_text = final_interpretation_text(view_model)
    errors: list[str] = []
    for term in FORBIDDEN_VISIBLE_TERMS:
        if term in text:
            errors.append(f"forbidden visible term {term!r}")
    for term in USER_REPORTED_VISIBLE_TERMS:
        if term in text:
            errors.append(f"user-reported technical phrase leaked: {term!r}")
    for term in FATALISTIC_VISIBLE_TERMS:
        if term in text:
            errors.append(f"fatalistic or mind-reading claim {term!r}")
    for term in FINAL_FORBIDDEN_TECHNICAL_TERMS:
        if term in final_text:
            errors.append(f"final interpretation leaked technical term {term!r}")
    meta_hits = reader_meta_narration_hits(final_text)
    if meta_hits:
        errors.append(f"final interpretation leaked page narration: {meta_hits[:4]}")
    final = view_model.get("finalInterpretation") if isinstance(view_model.get("finalInterpretation"), dict) else {}
    sections = final.get("sections") if isinstance(final.get("sections"), dict) else {}
    fit_section = sections.get("relationship-fit") if isinstance(sections.get("relationship-fit"), dict) else {}
    fit_body = str(fit_section.get("body") or "")
    if fit_body.count("先看") >= 2:
        errors.append(f"relationship-fit paragraph overuses `先看`: {fit_body[:96]}")
    for section_id, section in (sections or {}).items():
        if not isinstance(section, dict):
            continue
        headline = str(section.get("headline") or "")
        if headline.startswith(("先回答：", "下一步只處理：", "時機看")):
            errors.append(f"{section_id}.headline uses scaffold title wording: {headline}")
        if "，回覆不穩" in headline or "，沉默先" in headline or "，聯絡方式" in headline:
            errors.append(f"{section_id}.headline includes contact-state tail: {headline}")
        for field in ("meaning", "body", "nextMove", "caution"):
            value = str(section.get(field) or "")
            if not value:
                continue
            if value.count("先看") >= 2:
                errors.append(f"{section_id}.{field} overuses `先看`: {value[:96]}")
            if value.count("下一步") >= 2:
                errors.append(f"{section_id}.{field} overuses `下一步`: {value[:96]}")
            if value.count("；") >= 4:
                errors.append(f"{section_id}.{field} reads like slot fragments: {value[:96]}")
    for pattern in EXACT_DATE_PATTERNS:
        if pattern.search(text):
            errors.append(f"exact-date promise pattern {pattern.pattern!r}")
    if not any(marker in text for marker in REQUIRED_EVERYDAY_MARKERS):
        errors.append("missing everyday-language markers")
    return errors


def unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def main() -> int:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims_by_article = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    errors: list[str] = []
    answer_bodies: list[str] = []
    action_bodies: list[str] = []
    timing_bodies: list[str] = []
    theme_keys: list[str] = []

    for path in READING_PATHS:
        reading = read_json(path)
        payload = build_payload(reading, include_drafts=True, select=True)
        view_model = build_view_model(payload, articles, claims_by_article)
        example_id = str(view_model.get("id") or reading.get("reading_id") or path.stem)
        example_errors = audit_view_model(view_model)
        errors.extend(f"{example_id}: {error}" for error in example_errors)
        answer_readable = ((view_model.get("answerGuidance") or {}).get("readableInterpretation") or {})
        action_readable = ((view_model.get("actionGuidance") or {}).get("readableInterpretation") or {})
        timing_readable = ((view_model.get("timingGuidance") or {}).get("readableInterpretation") or {})
        answer_bodies.append(str(answer_readable.get("body") or ""))
        action_bodies.append(str(action_readable.get("body") or ""))
        timing_bodies.append(str(timing_readable.get("body") or ""))
        theme_keys.append(str(((view_model.get("answerGuidance") or {}).get("relationshipTheme") or {}).get("themeKey") or ""))

    if len(unique(answer_bodies)) < 5:
        errors.append("answer readable bodies are not varied enough")
    if len(unique(action_bodies)) < 5:
        errors.append("action readable bodies are not varied enough")
    if len(unique(timing_bodies)) < 3:
        errors.append("timing readable bodies are not varied enough")
    if len(unique(theme_keys)) < 4:
        errors.append("relationship themes are not varied enough")

    if errors:
        print("Western native copy contract failed")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Western native copy contract passed")
    print(f"- examples: {len(READING_PATHS)}")
    print(f"- answer variants: {len(unique(answer_bodies))}")
    print(f"- action variants: {len(unique(action_bodies))}")
    print(f"- timing variants: {len(unique(timing_bodies))}")
    print(f"- relationship themes: {', '.join(unique(theme_keys))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
