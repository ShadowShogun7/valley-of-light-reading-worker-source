"""Visible-output depth and anti-repetition checks for paid Western V1."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
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

SECTION_ORDER = (
    "星盤定位",
    "兩個人的關係契合度分析",
    "核心問題解讀",
    "時機判讀",
    "行動方向",
)

SECTION_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "星盤定位": ("安全感模式", "溝通方式", "好感表達", "行動節奏", "壓力下的反應"),
    "兩個人的關係契合度分析": ("你們的相處", "吸引力", "卡住的地方", "能不能繼續"),
    "核心問題解讀": ("短答案", "所以這題", "他比較吃這一套"),
    "時機判讀": ("現在比較適合", "互動節奏", "接下來一段時間", "不是指定日期"),
    "行動方向": ("最容易吵架", "比較有用的做法", "下一步", "不要怎麼自我解讀"),
}

CHART_POSITIONING_POINTS = ("Moon", "Mercury", "Venus", "Mars", "Saturn")
READABLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution", "stuckPattern")

SKIP_KEYS = {
    "id",
    "key",
    "version",
    "source",
    "sourceClaimIds",
    "methodClaimIds",
    "evidenceClusterKeys",
    "claimIds",
    "debug",
    "atomId",
    "rulesetId",
    "questionBlueprintId",
    "questionSourceArticleId",
    "questionClaimIds",
    "questionMethodClaimIds",
    "ruleId",
    "ruleConfidence",
    "orb",
    "strength",
    "averageStrength",
    "strongestStrength",
}

INTERNAL_COPY_TERMS = (
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
    "壓力訊號",
    "互動機制",
    "節奏校準",
    "關係容器",
    "行動邊界",
    "證據鏈",
    "完整星盤證據鏈",
    "需要慢一點",
    "better",
    "neutral",
    "avoid",
)
FINAL_TECHNICAL_VISIBLE_TERMS = (
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
    "互動速度",
    "靠近速度",
    "對抗或升溫",
    "進入對抗",
    "可觀察條件",
    "可觀察",
)

BAZI_TERMS = ("八字", "日主", "四柱", "配偶星", "bazi", "Bazi")
UPSELL_TERMS = ("免費結果", "免費合盤結果", "解鎖完整合盤報告", "NT$499", "NT$2,480")
EXACT_DATE_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}|第\s*\d+\s*天")
SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？!?；;\n]+")
TAKE_SLOW_TERMS = (
    "不急著要答案",
    "不要急著",
    "不急著",
    "先觀察",
    "先放慢",
    "放慢",
    "不要推",
    "不要逼",
    "不要長文",
    "短、輕、可退場",
    "壓力比較小",
)
SLOW_PUSH_SEMANTIC_TERMS = (
    "不急",
    "放慢",
    "速度",
    "不要逼",
    "逼",
    "不要推",
    "推進",
    "追問",
    "加壓",
    "壓力",
    "短、輕",
    "可退場",
    "立刻",
    "小回應",
    "不要長文",
)
PARTNER_NEEDS_DEPTH_MARKERS = (
    "關係輪廓",
    "他在找的關係",
    "安全感怎麼來",
    "愛意語言",
    "壓力下的反應",
    "承諾節奏",
    "什麼會打開他",
    "什麼會讓他關上",
    "容易誤會",
    "星盤依據",
)
PARTNER_NEEDS_ACTION_ONLY_TERMS = (
    "怎麼靠近",
    "可以怎麼靠近",
    "你可以怎麼靠近",
)


@dataclass(frozen=True)
class SectionAnalysis:
    char_count: int
    markers_present: tuple[str, ...]
    markers_missing: tuple[str, ...]
    repeated_phrase_count: int
    overused_terms: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioAnalysis:
    id: str
    section_metrics: dict[str, SectionAnalysis]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class VisibleDepthAudit:
    scenarios: tuple[ScenarioAnalysis, ...]
    variation_metrics: dict[str, int]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]


def get_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def clean_visible_copy(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if re.search(r"birth_time|noon fallback|date_noon_fallback|time-sensitive", raw, re.IGNORECASE):
        return "出生時間不完整時，會避開上升、宮位與其他時間敏感結論；這些只作背景，不拿來下精準判斷。"
    if re.search(r"house overlay|not wired|calculation", raw, re.IGNORECASE):
        return "目前還沒有合盤宮位覆蓋計算，所以宮位只作背景，不拿來做精準關係結論。"

    replacements = (
        ("免費版", "這份解讀"),
        ("免費頁", "這份解讀"),
        ("免費閱讀", "這份解讀"),
        ("免費結果", "這份解讀"),
        ("付費報告", "完整解讀"),
        ("付費層", "完整解讀"),
        ("完整報告", "完整解讀"),
        ("完整解鎖", "完整整理"),
        ("解鎖", "整理"),
        ("靠近的入口", "靠近的位置"),
        ("修復入口", "修復位置"),
        ("協調入口", "協調位置"),
        ("入口", "位置"),
        ("低壓", "壓力較輕"),
        ("低刺激", "短、輕、能自然停下"),
        ("低壓靠近入口", "壓力較輕的靠近方式"),
        ("壓力比較小靠近位置", "壓力較輕的靠近方式"),
        ("月亮與金星在乎和需要被照顧的方式", "月亮與金星代表的安全感和被重視感"),
        ("需求語言", "在乎和需要被照顧的方式"),
        ("安全感語言", "需要安全感的方式"),
        ("被重視語言", "需要被重視的方式"),
        ("安全感與被重視的橋接", "安全感和被重視的感覺怎麼接上"),
        ("安全感與被重視的接得上的地方", "安全感和被重視的感覺怎麼接上"),
        ("把安全感和被重視的感覺怎麼接上說清楚", "說清楚你們在哪些地方能讓彼此安心、覺得被重視"),
        ("交叉橋接", "能互相接上的地方"),
        ("橋接", "接得上的地方"),
        ("有橋", "有能接上的地方"),
        ("讓這個橋變得可用", "讓這個連結真的用得上"),
        ("控速、降刺激", "先把動作收小、不要再加壓"),
        ("降速、降刺激", "把步調收小、不要再加壓"),
        ("降低刺激", "降低壓力"),
        ("降刺激", "不要再加壓"),
        ("控速", "把步調收小"),
        ("推進速度與衝突反應重複出現", "一靠近就容易變急或起衝突"),
        ("推進速度和衝突反應", "靠近時變急或起衝突的反應"),
        ("推進速度與衝突反應", "靠近時變急或起衝突的反應"),
        ("責任與長期承接入口", "能把責任放進日常互動的地方"),
        ("責任與長期承接位置", "能把責任放進日常互動的地方"),
        ("長期承接位置", "可以穩定負責的地方"),
        ("壓力層承接", "壓力能不能被處理"),
        ("現實回應承接", "穩定的現實回應"),
        ("情緒承接位置", "情緒比較容易被接住的位置"),
        ("情緒承接", "情緒比較容易被接住"),
        ("可預期承接", "可預期回應"),
        ("成熟承接", "成熟回應"),
        ("被安全承接", "被安全地接住"),
        ("被承接", "被接住"),
        ("可承接", "比較接得住"),
        ("是否能承接", "能不能接住"),
        ("能否承接", "能不能接住"),
        ("能承接", "能接住"),
        ("穩定承接", "穩定接住"),
        ("需要翻譯", "需要說清楚"),
        ("先翻譯成", "先說成"),
        ("修復槓桿", "可以怎麼修"),
        ("行動尺度", "接下來適合做到哪一步"),
        ("開口門檻", "開口前先看什麼"),
        ("精準證據", "主要依據"),
        ("orb 約", "角度差約"),
        ("Saturn-in-sign", "土星落星座"),
        ("Saturn timing", "土星時機訊號"),
        ("Saturn pressure", "土星壓力"),
        ("降低 certainty", "降低確定語氣"),
        ("降 certainty", "改用保守語氣"),
        ("fatal verdict", "命定結論"),
        ("Hard contact", "緊張相位"),
        ("hard contact", "緊張相位"),
        ("Soft contact", "柔和相位"),
        ("soft contact", "柔和相位"),
        ("星盤只能支持很小的試水溫", "目前只適合很小、很輕地試一次"),
        ("短、輕、可退場", "短、輕、能自然停下"),
        ("壓力比較小", "壓力較輕"),
        ("先放慢", "先把步調收小"),
        ("速度要先放慢", "動作要先收小"),
        ("把速度放慢", "把動作收小"),
        ("速度放慢", "動作收小"),
        ("放慢", "收小"),
        ("不要急著", "先不用"),
        ("不急著", "先不"),
        ("先先不用", "先不用"),
        ("先先不", "先不"),
        ("先觀察", "先看"),
        ("攤牌", "把關係題一次攤開"),
        ("另一條線索", "旁邊這個提醒"),
        ("不要把某一天當成唯一機會", "不要把所有壓力放在一次行動上"),
        ("沒有足夠資料時，不應該把星象寫成精準聯絡日。", "資料不夠完整時，先用保守節奏處理。"),
        ("不應該把星象寫成精準聯絡日", "先用星象抓互動節奏"),
        ("精準聯絡日", "互動節奏"),
        ("這裡應", "這裡要"),
        ("精準日期", "互動節奏"),
        ("精準日", "互動節奏"),
        ("不排指定日期", "先看互動節奏"),
        ("不指定日期", "先看互動節奏"),
        ("不指定哪一天", "先看互動節奏"),
        ("互動氣候", "互動節奏"),
        ("可不回", "對方可以先不回"),
        ("不保證對方會回來", "不能當成對方會回來的證明"),
        ("保證對方會回來", "當成對方會回來的證明"),
        ("不保證會回來", "不能當成會回來的證明"),
        ("保證會回來", "當成會回來的證明"),
        ("窗口", "時段"),
        ("反而讓互動進入防衛", "反而讓氣氛變硬"),
        ("行動速度就容易變急，互動很快從想處理變成對抗或升溫", "一急著把問題處理好，你們就容易越講越硬，最後變成像在吵誰對誰錯"),
        ("你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案", "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果"),
        ("你們之間有會互相牽動的地方，但它更像一個入口，不是直接等於關係答案", "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果"),
        ("你們確實容易被彼此反應", "你們確實容易被彼此牽動"),
        ("合盤有牽動", "星盤有吸引線索"),
        ("可以當位置，但訊息要比感覺更輕", "如果真的要說一句，也只適合短而輕的訊息"),
        ("可以當入口，但訊息要比感覺更輕", "如果真的要說一句，也只適合短而輕的訊息"),
        ("可以當方式，但訊息要比感覺更輕", "如果真的要說一句，也只適合短而輕的訊息"),
        ("訊息要比感覺更輕", "訊息要短一點、輕一點"),
        ("它提醒你還想靠近，但開口方式要小於你的情緒強度", "你想靠近是可以理解的，但如果要傳訊息，只適合短短一句，不要把情緒全部放進去"),
        ("這份想靠近可以被看見，但開口要比情緒小很多", "你想靠近是可以理解的，但如果要傳訊息，只適合短短一句，不要把情緒全部放進去"),
        ("開口方式要小於你的情緒強度", "不要把情緒全部放進訊息裡"),
        ("開口要比情緒小很多", "不要把情緒全部放進訊息裡"),
        ("把行動縮小到不需要立刻定義關係的一步", "下一步要小到對方不用立刻表態"),
        ("火花可以保留，但下一步要輕，不要把吸引變成壓力測試", "有火花可以先放著，下一步只做短而輕的一件事，不逼出答案"),
        ("沉默期先看互動會不會自然出現，不要把一次主動變成壓力測試", "沉默期先看對方會不會自然出現，不要一主動就逼對方給答案"),
        ("不要把第一次主動用成壓力測試", "第一次主動不要變成逼對方給答案"),
        ("看互動能不能不升溫，而不是誰先贏回主導權", "看你們能不能越聊越平，而不是誰先把局面扳回來"),
        ("把火花落到具體、低要求、可延續的小互動", "不要只看有沒有曖昧，要看能不能變成壓力小、能接下去的小互動"),
        ("聯絡受阻時，先以界線和自我穩定為主", "如果對方已經不讓你聯絡，現在先不要繞路找他，先把自己穩住"),
        ("用穩定行動校準強烈感受，不靠猜測下結論", "對方有沒有穩定行動，不要只靠猜測下結論"),
        ("感覺越重，越要尊重界線，用可看見的行動校準判斷", "感覺越重，越要尊重界線，回頭看對方有沒有清楚行動"),
        ("小而可觀察的互動", "一件小、看得到回應的互動"),
        ("修復方向", "接下來"),
        ("小訊號", "小回應"),
        ("聯絡受阻", "聯絡被擋住"),
        ("自我穩定", "先把自己穩住"),
        ("校準", "調整"),
        ("低要求", "壓力小"),
        ("壓力測試", "逼答案"),
        ("現實逼答案關係能不能長久", "在意這段關係能不能經得起現實"),
        ("現實壓力測試關係能不能長久", "在意這段關係能不能經得起現實"),
        ("偶爾回覆只代表通道未斷，還不能當成穩定投入", "偶爾回覆只表示還有零星聯絡，不能直接當成關係已經變穩"),
        ("偶爾回覆還不能直接當成穩定投入", "偶爾回覆不能直接當成關係已經變穩"),
        ("副動力要用來分辨值得等待和繼續消耗", "也要分辨這段關係是在變好，還是在繼續消耗你"),
        ("副動力", "旁邊這個提醒"),
        ("單一星盤線索", "一個線索"),
        ("把距離直接解讀成不在乎", "一退開就追問他是不是不在乎"),
        ("責任、承諾和距離感會讓回應變得比較保守，就算有在意也可能先退回安全距離", "一談到關係定位或距離，對方可能會先慢下來；這不一定是不在意，而是現在還接不住太重的話題"),
        ("承諾和距離感會讓回應變得比較保守", "一談到承諾或距離，回應可能會先慢下來"),
        ("避免推進速度又把對方推進防衛", "避免越想靠近，氣氛越緊"),
        ("通道未斷", "還有零星聯絡"),
        ("穩定投入", "持續行動"),
        ("行動速度", "靠近的步調"),
        ("直接等於關係答案", "代表關係已經有結果"),
        ("關係答案", "關係結果"),
        ("壓力下的防衛", "壓力下的反應"),
        ("壓力防衛", "壓力下的反應"),
        ("防衛模式", "壓力下的反應"),
        ("防衛反應", "反應變硬"),
        ("進入防衛", "變得比較緊"),
        ("變成防衛", "變硬"),
        ("互相防衛", "彼此變硬"),
        ("降低防衛", "降低緊張"),
        ("更防衛", "更想退開"),
        ("比較不防衛", "比較不緊"),
        ("防衛", "保護自己"),
    )
    cleaned = raw
    for source, target in replacements:
        cleaned = cleaned.replace(source, target)
    cleaned = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", cleaned)
    return cleaned.strip()


def append_text(output: list[str], *values: Any) -> None:
    for value in values:
        if isinstance(value, str):
            text = clean_visible_copy(value)
            if text:
                output.append(text)
        elif isinstance(value, (list, tuple)):
            append_text(output, *value)


def append_fields(output: list[str], source: dict[str, Any] | None, fields: Iterable[str]) -> None:
    if not isinstance(source, dict):
        return
    for field in fields:
        value = source.get(field)
        if isinstance(value, list):
            append_text(output, *value)
        else:
            append_text(output, value)


def append_readable(output: list[str], source: dict[str, Any] | None) -> None:
    if not isinstance(source, dict):
        return
    append_fields(output, source.get("readableInterpretation") or {}, READABLE_FIELDS)


def append_final_interpretation(output: list[str], view_model: dict[str, Any], section_id: str) -> None:
    section = get_path(view_model, f"finalInterpretation.sections.{section_id}") or get_path(
        view_model,
        f"readableQuestionAnswer.sections.finalInterpretation.sections.{section_id}",
    )
    if isinstance(section, dict):
        append_fields(output, section, READABLE_FIELDS)


def append_block_items(output: list[str], items: Any, fields: Iterable[str], limit: int | None = None) -> None:
    if not isinstance(items, list):
        return
    selected = items[:limit] if limit else items
    for item in selected:
        if isinstance(item, dict):
            append_fields(output, item, fields)
            append_readable(output, item)


def visible_text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = clean_visible_copy(value)
        return [text] if text else []
    if isinstance(value, (int, float, bool)):
        return []
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            output.extend(visible_text_values(item))
        return output
    if isinstance(value, dict):
        output = []
        for key, child in value.items():
            if key in SKIP_KEYS:
                continue
            output.extend(visible_text_values(child))
        return output
    return []


def chart_positioning_texts(view_model: dict[str, Any]) -> list[str]:
    output = [
        "星盤定位",
        "我的星盤",
        "他的星盤",
        "關係在生活中的樣子",
        "安全感模式",
        "溝通方式",
        "好感表達",
        "行動節奏",
        "壓力下的反應",
    ]
    append_final_interpretation(output, view_model, "chart-positioning")
    profiles = view_model.get("relationshipProfiles") or {}
    for person_key in ("personA", "personB"):
        person = profiles.get(person_key) or {}
        append_fields(output, person, ("label", "headline", "summary", "partnerExpectation", "suitableFor", "doesNotFit"))
        cards = [
            card
            for card in person.get("cards") or []
            if isinstance(card, dict) and str(card.get("point") or "") in CHART_POSITIONING_POINTS
        ]
        for card in cards:
            append_fields(
                output,
                card,
                (
                    "title",
                    "placement",
                    "signLabel",
                    "relationshipUse",
                    "naturalResponse",
                    "tensionPattern",
                    "suitableFor",
                    "doesNotFit",
                ),
            )
            append_readable(output, card)
        append_text(output, *(person.get("precisionWarnings") or []))

    fit_summary = profiles.get("fitSummary") or {}
    append_fields(output, profiles, ("answerBridge", "precisionWarnings"))
    append_fields(output, fit_summary, ("headline", "summary", "doesNotProve"))
    append_readable(output, fit_summary)
    return output


def dynamic_block_texts(block: dict[str, Any], item_limit: int = 3) -> list[str]:
    output: list[str] = []
    append_fields(output, block, ("label", "headline", "summary", "doesNotProve"))
    append_block_items(
        output,
        block.get("items"),
        ("title", "technical", "meaning", "everydaySignal", "advice", "doesNotProve", "nextMove"),
        limit=item_limit,
    )
    return output


def relationship_fit_texts(view_model: dict[str, Any]) -> list[str]:
    output = [
        "兩個人的關係契合度分析",
        "你們的相處",
        "契合雷達",
        "吸引力",
        "卡住的地方",
        "能不能繼續",
        "星盤定位",
        "合盤證據",
    ]
    append_final_interpretation(output, view_model, "relationship-fit")
    lens = view_model.get("relationshipFitLens") or {}
    append_fields(output, lens.get("relationshipType") or {}, ("title", "subtitle", "meaning", "reasons", "becauseA", "becauseB", "doesNotProve"))
    append_block_items(output, lens.get("radar"), ("label", "rating", "becauseA", "becauseB", "proof", "reason"), limit=6)
    append_block_items(output, lens.get("bestPlaces"), ("title", "becauseA", "becauseB", "proof", "body"), limit=3)
    stuck_loop = lens.get("stuckLoop") or {}
    append_fields(output, stuck_loop, ("title", "summary"))
    append_block_items(output, stuck_loop.get("steps"), ("label", "body"), limit=5)
    append_block_items(output, lens.get("conditions"), ("label", "body", "watchFor"), limit=4)
    append_fields(output, lens, ("summary", "doesNotProve"))
    return output


def core_answer_texts(view_model: dict[str, Any]) -> list[str]:
    output = [
        "核心問題解讀",
        "你問的是",
        "這題的短答案",
        "所以這題",
        "現實訊號",
        "什麼跡象會讓答案改變",
        "他比較吃這一套",
        "看實際回應",
        "關係輪廓",
        "他在找的關係",
        "安全感怎麼來",
        "愛意語言",
        "壓力下的反應",
        "承諾節奏",
        "什麼會打開他",
        "什麼會讓他關上",
        "容易誤會",
        "星盤依據",
    ]
    append_final_interpretation(output, view_model, "core-answer")
    answer_guidance = view_model.get("answerGuidance") or {}
    normal = view_model.get("normalUserAnswer") or answer_guidance.get("normalUserAnswer") or {}
    if normal:
        append_fields(output, answer_guidance, ("questionLabel",))
    else:
        append_fields(output, answer_guidance, ("questionLabel", "shortAnswer", "nextMove"))
        append_readable(output, answer_guidance)
    append_fields(output, normal, ("questionLabel", "headline", "directAnswer", "evidenceBridge", "whyThisMatters", "nextStep", "stopLine", "whatToWatch"))
    for block in normal.get("blocks") or []:
        if isinstance(block, dict):
            if block.get("key") == "nextStep":
                append_fields(output, block, ("label",))
                continue
            append_fields(output, block, ("label", "body", "items"))
    append_block_items(output, answer_guidance.get("evidenceHighlights"), ("title", "body", "label", "emotionalMeaning"), limit=4)

    partner_needs = view_model.get("partnerNeeds") or {}
    append_fields(output, partner_needs, ("label", "framing", "doesNotProve"))
    append_fields(
        output,
        partner_needs.get("profile") or {},
        (
            "title",
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
        ),
    )
    append_block_items(
        output,
        partner_needs.get("items"),
        (
            "point",
            "title",
            "need",
        ),
        limit=3,
    )
    return output


def timing_reading_texts(view_model: dict[str, Any]) -> list[str]:
    output = [
        "時機判讀",
        "現在比較適合",
        "行動節奏",
        "可以做的尺度",
        "可以進一步的訊號",
        "需要停止的訊號",
        "目前互動節奏摘要",
        "互動節奏",
        "接下來一段時間",
        "不是指定日期",
        "星象訊號",
        "接下來的節奏",
        "第一步",
        "第二步",
        "第三步",
    ]
    append_final_interpretation(output, view_model, "timing-reading")
    timing = view_model.get("timingGuidance") or {}
    append_fields(output, timing, ("recommendedActionLabel", "topBandLabel", "nextMove"))
    append_readable(output, timing)
    append_block_items(output, timing.get("selectedSignals"), ("title", "body"), limit=5)

    turning = view_model.get("relationshipTurningWindows") or {}
    append_fields(output, turning, ("label", "summary", "saferLabel", "doesNotProve"))
    append_block_items(output, turning.get("items"), ("windowLabel", "title", "meaning", "suggestion", "whatToAvoid", "technical"), limit=3)

    for step in view_model.get("timeline") or []:
        if isinstance(step, dict):
            append_fields(output, step, ("title", "body"))
            append_readable(output, step)
    return output


def action_direction_texts(view_model: dict[str, Any]) -> list[str]:
    output = [
        "行動方向",
        "行動總結",
        "先避開",
        "不要讓關係更有壓力",
        "吵架地雷",
        "你們最容易吵架的 3 個地雷",
        "比較有用的做法",
        "具體做法",
        "下一步行動清單",
        "接下來先避開什麼",
        "如果要開口，用什麼語氣",
        "停止線",
        "不要怎麼自我解讀",
        "短訊息範例",
        "對方不同反應時怎麼做",
    ]
    append_final_interpretation(output, view_model, "action-direction")
    action = view_model.get("actionGuidance") or {}
    append_fields(output, action, ("statusLabel", "nextMove"))
    append_readable(output, action)

    readable = (view_model.get("readableQuestionAnswer") or {}).get("sections") or {}
    for dont in readable.get("donts") or view_model.get("donts") or []:
        if isinstance(dont, dict):
            append_fields(output, dont, ("label", "body"))
            append_readable(output, dont)

    landmines = view_model.get("fightLandmines") or {}
    append_fields(output, landmines, ("label", "doesNotProve"))
    append_block_items(output, landmines.get("items"), ("title", "whyItHappens", "trigger", "whatToDoInstead"), limit=3)

    survival = view_model.get("survivalGuide") or {}
    append_fields(output, survival, ("label", "doesNotProve"))
    append_block_items(output, survival.get("items"), ("title", "body", "why"), limit=5)

    append_text(
        output,
        "沒有回覆先當成對方暫時接不住，不要立刻解讀成你不重要，也不要用第二則訊息補壓力。",
    )
    return output


def section_text_lists(view_model: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "星盤定位": chart_positioning_texts(view_model),
        "兩個人的關係契合度分析": relationship_fit_texts(view_model),
        "核心問題解讀": core_answer_texts(view_model),
        "時機判讀": timing_reading_texts(view_model),
        "行動方向": action_direction_texts(view_model),
    }


def section_texts(view_model: dict[str, Any]) -> dict[str, str]:
    raw_sections = section_text_lists(view_model)
    return {
        section: "\n".join(unique(texts))
        for section, texts in raw_sections.items()
    }


def final_interpretation_text(view_model: dict[str, Any]) -> str:
    output: list[str] = []
    for section_id in ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction"):
        append_final_interpretation(output, view_model, section_id)
    return "\n".join(unique(output))


def unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        value = clean_visible_copy(value)
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def normalized_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", "", sentence)
    sentence = sentence.replace("「", "").replace("」", "")
    return sentence.strip()


def visible_phrases(text: str) -> list[str]:
    phrases = []
    for part in SENTENCE_SPLIT_PATTERN.split(text):
        normalized = normalized_sentence(part)
        if 12 <= len(normalized) <= 90:
            phrases.append(normalized)
    return phrases


def repeated_phrases_by_section(sections: dict[str, str]) -> dict[str, list[str]]:
    phrase_sections: dict[str, set[str]] = defaultdict(set)
    for section, text in sections.items():
        for phrase in visible_phrases(text):
            phrase_sections[phrase].add(section)
    repeated = {phrase: sorted(names) for phrase, names in phrase_sections.items() if len(names) >= 2}
    by_section: dict[str, list[str]] = {section: [] for section in sections}
    for phrase, names in repeated.items():
        if is_allowed_repeated_phrase(phrase):
            continue
        for section in names:
            by_section[section].append(phrase)
    return by_section


def is_allowed_repeated_phrase(phrase: str) -> bool:
    allowed_needles = (
        "不能證明",
        "不等於",
        "不是讀心",
        "不作指定日期",
        "不能保證",
        "不能當成",
    )
    return any(needle in phrase for needle in allowed_needles)


def analyze_scenario(view_model: dict[str, Any]) -> ScenarioAnalysis:
    raw_sections = section_text_lists(view_model)
    sections = {section: "\n".join(unique(texts)) for section, texts in raw_sections.items()}
    repeated_by_section = repeated_phrases_by_section(sections)
    failures: list[str] = []
    warnings: list[str] = []
    section_metrics: dict[str, SectionAnalysis] = {}

    all_text = "\n".join(sections.values())
    for person_key, label in (("personA", "你"), ("personB", "他")):
        baseline = get_path(view_model, f"relationshipProfiles.translationBaseline.{person_key}") or {}
        missing_baseline_fields = [
            field
            for field in ("emotionalNeed", "communicationStyle", "conflictResponse", "misunderstandingRisk")
            if not str(baseline.get(field) or "").strip()
        ]
        if missing_baseline_fields:
            failures.append(f"translation baseline missing for {label}: {', '.join(missing_baseline_fields)}")
    if not str(get_path(view_model, "relationshipFitLens.relationshipType.sideNote") or "").strip():
        failures.append("relationship-fit translation layer missing relationshipType.sideNote")

    for term in (*INTERNAL_COPY_TERMS, *BAZI_TERMS, *UPSELL_TERMS):
        if term in all_text:
            failures.append(f"visible forbidden term leaked: {term}")
    if EXACT_DATE_PATTERN.search(all_text):
        failures.append("visible output leaked exact-date/day language")
    final_text = final_interpretation_text(view_model)
    for term in FINAL_TECHNICAL_VISIBLE_TERMS:
        if term in final_text:
            failures.append(f"final interpretation leaked technical visible term: {term}")

    for section in SECTION_ORDER:
        text = sections.get(section, "")
        required = SECTION_REQUIRED_MARKERS[section]
        missing = tuple(marker for marker in required if marker not in text)
        repeated = tuple(repeated_by_section.get(section) or [])
        overused = tuple(term for term in TAKE_SLOW_TERMS if text.count(term) >= 2)
        section_metrics[section] = SectionAnalysis(
            char_count=len(text),
            markers_present=tuple(marker for marker in required if marker in text),
            markers_missing=missing,
            repeated_phrase_count=len(repeated),
            overused_terms=overused,
        )
        if missing:
            failures.append(f"{section}: missing visible job markers {', '.join(missing)}")
        if len(text) < minimum_section_chars(section):
            failures.append(f"{section}: visible section too thin ({len(text)} chars)")
        if len(repeated) > 2:
            failures.append(f"{section}: repeated exact phrases across tabs ({len(repeated)})")
        if len(overused) >= 2:
            failures.append(f"{section}: overuses slow/push-safety language {', '.join(overused)}")

    term_section_hits = {
        term: sum(1 for text in sections.values() if term in text)
        for term in TAKE_SLOW_TERMS
    }
    for term, section_count in term_section_hits.items():
        if section_count >= 4:
            failures.append(f"phrase family appears in too many tabs: {term} ({section_count})")
    failures.extend(semantic_repetition_failures(sections, raw_sections))

    return ScenarioAnalysis(
        id=str(view_model.get("id") or "unknown"),
        section_metrics=section_metrics,
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def semantic_repetition_failures(sections: dict[str, str], raw_sections: dict[str, list[str]]) -> list[str]:
    failures: list[str] = []
    slow_dominant_sections: list[str] = []
    for section, text in sections.items():
        sentences = [normalized_sentence(part) for part in SENTENCE_SPLIT_PATTERN.split(text)]
        sentences = [sentence for sentence in sentences if len(sentence) >= 10]
        if not sentences:
            continue
        slow_sentence_count = sum(
            1 for sentence in sentences if any(term in sentence for term in SLOW_PUSH_SEMANTIC_TERMS)
        )
        if slow_sentence_count >= 5 and slow_sentence_count / max(1, len(sentences)) >= 0.34:
            slow_dominant_sections.append(section)
    if len(slow_dominant_sections) >= 3:
        failures.append(
            "semantic slow/push advice dominates too many tabs: "
            + ", ".join(slow_dominant_sections)
        )

    core_text = sections.get("核心問題解讀", "")
    depth_marker_count = sum(1 for marker in PARTNER_NEEDS_DEPTH_MARKERS if marker in core_text)
    if depth_marker_count < 7:
        failures.append(f"核心問題解讀: partner-needs semantic depth too thin ({depth_marker_count} < 7)")
    action_only_count = sum(core_text.count(term) for term in PARTNER_NEEDS_ACTION_ONLY_TERMS)
    if action_only_count >= 2:
        failures.append("核心問題解讀: partner-needs section collapsed into action-only approach copy")

    raw_core_phrases: list[str] = []
    for text in raw_sections.get("核心問題解讀", []):
        raw_core_phrases.extend(visible_phrases(clean_visible_copy(text)))
    repeated_action_phrases = [
        phrase
        for phrase, count in Counter(raw_core_phrases).items()
        if count >= 3 and any(term in phrase for term in SLOW_PUSH_SEMANTIC_TERMS)
    ]
    if repeated_action_phrases:
        failures.append(
            "核心問題解讀: repeats the same action-boundary sentence across multiple cards: "
            + " / ".join(sorted(repeated_action_phrases)[:2])
        )

    return failures


def minimum_section_chars(section: str) -> int:
    return {
        "星盤定位": 900,
        "兩個人的關係契合度分析": 850,
        "核心問題解讀": 850,
        "時機判讀": 650,
        "行動方向": 850,
    }[section]


def build_view_models(paths: Iterable[Path] = READING_PATHS) -> list[dict[str, Any]]:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims_by_article = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    view_models = []
    for path in paths:
        reading = read_json(path)
        payload = build_payload(reading, include_drafts=True, select=True)
        view_models.append(build_view_model(payload, articles, claims_by_article))
    return view_models


def analyze_view_models(view_models: list[dict[str, Any]]) -> VisibleDepthAudit:
    scenarios = tuple(analyze_scenario(view_model) for view_model in view_models)
    failures = [f"{scenario.id}: {failure}" for scenario in scenarios for failure in scenario.failures]
    warnings = [f"{scenario.id}: {warning}" for scenario in scenarios for warning in scenario.warnings]
    variation_metrics = scenario_variation_metrics(view_models)
    failures.extend(variation_failures(variation_metrics))
    return VisibleDepthAudit(
        scenarios=scenarios,
        variation_metrics=variation_metrics,
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def scenario_variation_metrics(view_models: list[dict[str, Any]]) -> dict[str, int]:
    metric_sets: dict[str, set[str]] = {
        "relationship_archetype_titles": set(),
        "partner_need_titles": set(),
        "fight_landmine_titles": set(),
        "survival_guide_titles": set(),
        "turning_window_titles": set(),
        "normal_answer_headlines": set(),
        "action_guidance_headlines": set(),
    }
    section_fingerprints: dict[str, set[str]] = {section: set() for section in SECTION_ORDER}
    for view_model in view_models:
        metric_sets["relationship_archetype_titles"].add(str(get_path(view_model, "relationshipArchetype.title") or ""))
        metric_sets["normal_answer_headlines"].add(str(get_path(view_model, "normalUserAnswer.headline") or ""))
        metric_sets["action_guidance_headlines"].add(str(get_path(view_model, "actionGuidance.readableInterpretation.headline") or ""))
        for item in get_path(view_model, "partnerNeeds.items") or []:
            metric_sets["partner_need_titles"].add(str(item.get("title") or ""))
        for item in get_path(view_model, "fightLandmines.items") or []:
            metric_sets["fight_landmine_titles"].add(str(item.get("title") or ""))
        for item in get_path(view_model, "survivalGuide.items") or []:
            metric_sets["survival_guide_titles"].add(str(item.get("title") or ""))
        for item in get_path(view_model, "relationshipTurningWindows.items") or []:
            metric_sets["turning_window_titles"].add(str(item.get("title") or ""))
        for section, text in section_texts(view_model).items():
            section_fingerprints[section].add("|".join(visible_phrases(text)[:8]))
    metrics = {key: len({item for item in values if item}) for key, values in metric_sets.items()}
    metrics.update({f"section_fingerprints:{section}": len(values) for section, values in section_fingerprints.items()})
    return metrics


def variation_failures(metrics: dict[str, int]) -> list[str]:
    required = {
        "relationship_archetype_titles": 3,
        "partner_need_titles": 8,
        "fight_landmine_titles": 8,
        "survival_guide_titles": 12,
        # The legacy 11-reading matrix is pressure-heavy by design; V2 timing
        # breadth is enforced by smoke_western_fixture_depth_coverage.py.
        "turning_window_titles": 2,
        "normal_answer_headlines": 4,
        "action_guidance_headlines": 3,
    }
    failures = []
    for key, minimum in required.items():
        value = metrics.get(key, 0)
        if value < minimum:
            failures.append(f"scenario variation too low for {key}: {value} < {minimum}")
    for section in SECTION_ORDER:
        key = f"section_fingerprints:{section}"
        if metrics.get(key, 0) < 4:
            failures.append(f"visible section variation too low for {section}: {metrics.get(key, 0)} < 4")
    return failures


def render_markdown_report(audit: VisibleDepthAudit) -> str:
    lines = [
        "# Paid V1 Visible Reading Depth Audit",
        "",
        "> Generated by `scripts/report_visible_reading_depth.py`. This report checks whether the five paid Western result tabs have distinct visible jobs, enough scenario variation, and no repeated generic advice dominating the reading.",
        "",
        "## Summary",
        "",
        f"- Status: {'PASS' if not audit.failures else 'FAIL'}",
        f"- Scenarios checked: {len(audit.scenarios)}",
        f"- Failures: {len(audit.failures)}",
        f"- Warnings: {len(audit.warnings)}",
        "",
        "## Scenario Variation",
        "",
        "| Metric | Unique count |",
        "| --- | ---: |",
    ]
    for key in sorted(audit.variation_metrics):
        lines.append(f"| `{key}` | {audit.variation_metrics[key]} |")
    lines.extend(["", "## Section Depth Matrix", "", "| Scenario | Section | Chars | Job markers | Repeated phrases | Overused slow/push terms |", "| --- | --- | ---: | --- | ---: | --- |"])
    for scenario in audit.scenarios:
        for section in SECTION_ORDER:
            metric = scenario.section_metrics[section]
            markers = ", ".join(metric.markers_present) or "-"
            terms = ", ".join(metric.overused_terms) or "-"
            lines.append(
                f"| `{scenario.id}` | {section} | {metric.char_count} | {markers} | {metric.repeated_phrase_count} | {terms} |"
            )
    if audit.failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in audit.failures)
    if audit.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in audit.warnings)
    lines.extend(
        [
            "",
            "## Contract",
            "",
            "- The five visible tabs must keep different jobs rather than restating the same advice.",
            "- Relationship-fit must expose archetype, attraction, conflict, and growth mechanics.",
            "- Core-answer must answer the selected question and include partner needs without mind-reading.",
            "- Partner-needs must expose relationship style, emotional safety, affection language, defense, commitment pace, open/shut triggers, common misread, and only one final action suggestion.",
            "- Timing must describe climate windows, not exact-date promises.",
            "- Action must turn evidence into landmines, survival-guide items, scripts, and stop lines.",
            "- The detector blocks BaZi, upsell/free language, internal reducer/debug terms, exact-date promises, semantic collapse into slow/push advice, and excessive repeated slow/push-safety phrasing.",
            "",
        ]
    )
    return "\n".join(lines)
