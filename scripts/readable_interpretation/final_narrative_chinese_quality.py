"""R6 hard release gates for final reader-facing Traditional Chinese.

The page catalogs remain responsible for approved wording and exact semantic
traces. This module is the shared final boundary: every rendered field must
pass the same readability, page-ownership, and historical-regression policy.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Mapping

from .final_narrative_chinese_contract import audit_native_zh_tw_text
from .final_narrative_page_grammar import VISIBLE_FIELDS


FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION = (
    "final-narrative-native-zh-tw-r6-hard-gate-v6"
)
FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_MODE = "hard-release"

SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)

KNOWN_READER_REGRESSION_PHRASES = (
    "一有好感就會想做點什麼，不太只停在心裡",
    "下一步只做一件事：只說一件可以回答的小事",
    "下一步的大小",
    "下一頁再看這些習慣放在一起時，哪裡自然、哪裡容易卡住",
    "他回話的速度和語氣也容易跟著變快",
    "你一有靠近的動作，就很容易碰到他接收與表達好感的方式",
    "你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案",
    "你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案。",
    "你先談做法和後果，才相信問題能處理；對方只談感覺時，你們容易各自錯過重點。",
    "你希望關係能誠實談方向，也能保留各自的生活。",
    "偶爾回覆只代表通道未斷，還不能當成穩定投入",
    "偶爾回覆還不能直接當成穩定投入",
    "副動力要用來分辨值得等待和繼續消耗",
    "反而讓互動進入防衛",
    "只說一件可以回答的小事",
    "喜歡的節奏接近時",
    "單一星盤線索或單次訊息替整段關係下結論",
    "在「剛分手 / 情緒未穩」裡",
    "承諾和距離感會讓回應變得比較保守",
    "把距離直接解讀成不在乎",
    "機會要看舊循環有沒有變小",
    "比較值得調整的是",
    "比較值得調整的是把話說短，只處理一件對方能回的小事",
    "溫柔很容易被接住",
    "現實支撐",
    "理解彼此原本的親密關係節奏",
    "當你需要確認、他需要退開時，彼此很容易把保護誤讀成拒絕",
    "繞路靠近",
    "能接的份量",
    "行動速度就容易變急，互動很快從想處理變成對抗或升溫",
    "觀察位置",
    "語氣安不安全",
    "語氣是否安全",
    "這一步只確認在意有沒有放進行動",
    "避免推進速度又把對方推進防衛",
    "關係有機會透過耐心、規則和實際行動慢慢穩住",
    "集中時，你的靠近和處理衝突的速度一明顯，他的表達好感的方式也會被帶動。",
)

FORBIDDEN_VISIBLE_TERMS = (
    "relationshipThesis",
    "relationshipCaseModel",
    "dynamicInteractionPlan",
    "primaryDynamic",
    "secondaryDynamics",
    "evidencePacket",
    "methodClaim",
    "sourceClaim",
    "selector",
    "reducer",
    "timing band",
    "timing climate",
    "birth_time",
    "noon fallback",
    "date_noon_fallback",
    "承接度",
    "方法邊界",
    "關係生存指南",
    "這組動力",
    "判斷：",
    "關係型態：",
    "穩定投入",
    "互動意願",
    "現實訊號",
    "觀察條件",
    "反應模式",
    "副動力",
    "互動承受度",
    "下一步的大小",
    "把動作變小",
    "現在不是繞路靠近的時機",
    "比較值得調整的是",
    "繼續推進",
    "收小",
    "關係答案",
    "修復方向",
    "通道未斷",
    "低刺激",
    "可觀察條件",
    "行動要留在能確認的範圍",
)

PAGE_FORBIDDEN_MARKERS = {
    "chart-positioning": (
        "復合",
        "分手",
        "冷戰",
        "封鎖",
        "聯絡時機",
        "現在適合聯絡",
    ),
    "relationship-fit": (
        "冷戰",
        "剛分開",
        "分開一段時間",
        "封鎖",
        "目前沒有聯絡",
        "現在適合聯絡",
        "他會主動聯絡",
    ),
    "core-answer": ("你們比較像「", "關係型態："),
    "timing-reading": (
        "你們比較像「",
        "吸引的地方",
        "卡住的地方",
        "對他來說",
    ),
    "action-direction": (
        "你們比較像「",
        "吸引的地方",
        "目前比較可信的答案",
    ),
}

ABSTRACT_ACTION_PHRASES = (
    "適度調整",
    "維持彈性",
    "改善互動",
    "持續觀察",
    "再看看",
    "順其自然",
    "做好自己",
    "採取適當行動",
    "降低張力",
)

UNNATURAL_ASSEMBLY_PATTERNS = (
    (
        "abstract-causal-assembly",
        r"會牽動你們",
        "不可用抽象名詞拼接兩個人的反應。",
    ),
    (
        "abstract-initiation-motion",
        r"主動性(?:開始)?回到(?:雙方|兩個人)",
        "必須直接說明誰主動做了什麼。",
    ),
    (
        "abstract-analysis-noun",
        r"關鍵變數",
        "讀者文案不可用分析模型名詞代替具體相處變化。",
    ),
    (
        "abstract-mutual-escalation",
        r"反應容易互相加重",
        "必須說明實際升高的是壓力、衝突或距離。",
    ),
    (
        "unnatural-action-adjective",
        r"簡單而短",
        "行動句必須直接說出只談幾件事或訊息多長。",
    ),
    (
        "unclear-continuation-subject",
        r"(?:自己延續|另外找你說話)",
        "必須直接說明對方是否主動開口或延續話題。",
    ),
    (
        "abstract-initiation-label",
        r"主動性",
        "必須直接說明誰主動開口、回覆或安排下一次互動。",
    ),
    (
        "unnatural-weight-metaphor",
        r"(?:小事|事情).{0,5}(?:一起)?變重",
        "必須直接說明小事變成爭執、壓力或誤會。",
    ),
    (
        "answer-as-event",
        r"(?:相同答案|這題目前就缺少新的條件)",
        "不可把答案寫成會重複或缺少條件的抽象事件。",
    ),
    (
        "abstract-defense-cover",
        r"自我保護蓋過",
        "必須直接說明一方防備後，原本的問題如何談不下去。",
    ),
    (
        "abstract-self-expression",
        r"自然表現自己",
        "必須直接說明表達想法、感受或個性的行為。",
    ),
    (
        "self-referential-pronoun",
        r"你(?:會|比較|更)[^，。]{0,12}(?:你的說法|你的速度|你的感受|你是否在意他)",
        "第二人稱反應不可誤用成回應自己的說法、速度或感受。",
    ),
    (
        "attraction-defense-splice",
        r"(?:感到有壓力|沒有被尊重|不安或受傷)[^。]{0,10}(?:吸引和敏感|這份吸引|好感)",
        "吸引與防備不可用無轉折的通用尾句直接拼接。",
    ),
    (
        "unnatural-attraction-collocation",
        r"(?:感到被吸引和注意|感到明顯的好感和火花)",
        "吸引句必須使用自然的感受與行動搭配。",
    ),
    (
        "dangling-routine-action",
        r"(?:把這個做法留在日常|在日常裡持續做到)",
        "調整句必須說清楚要維持的行動，不可留下無對象的做到。",
    ),
    (
        "technical-fit-unknown",
        r"不足以指定最適合你們",
        "未知揭露要用日常中文說明目前還看不出答案。",
    ),
)

READER_ANCHOR_PATTERN = (
    r"(?:你|他|自己|對方|你們|彼此|雙方|兩個人|一方|另一方|兩邊|一起|關係|互動|對話|訊息|聯絡|"
    r"回應|回覆|沉默|共同|目前|現在|這段|分開|出生|資料|好感|安全感|壓力|"
    r"問題|話題|氣氛|行動|感受|承諾|責任|界線|接觸|靠近|主動|反應|答案|"
    r"這題|線索|結果|相處|爭執|選擇|情緒|工作|日常|未來|小事|這次|原本|"
    r"時段|一天|精細時機|時機|期待|管道|場合|往來|誤會|2026\s*年)"
)

UNMARKED_POLARITY_PATTERN = (
    r"(?:比較|較|更)?(?:容易|能|可以)[^，；。！？]{0,16}"
    r"(?:放鬆|開口|靠近|接住|說開|自然)[^，；。！？]{0,4}[，；]"
    r"[^，；。！？]{0,5}(?:雙方|彼此|你們|兩邊)[^，；。！？]{0,12}"
    r"(?:頂住|衝突|變硬|防衛)"
)
CONTRAST_MARKER_PATTERN = r"(?:但|仍|卻|不過)"
ACTION_COMMAND_PATTERN = (
    r"(?:停止|不要|不再|只傳|只用|先傳|見面|維持|澄清|修正|道歉|說明|"
    r"處理|開口|保持|完成|問|停)"
)
ACTION_STOP_PATTERN = r"(?:如果|只要|當|若|出現)"
TIMING_DATE_PATTERN = r"\d{4}\s*年"
CORE_NEXT_MOVE_QUESTION_FRAGMENT_PATTERN = r"(?:會不會|是不是|是否)"
SENTENCE_SPLIT = re.compile(r"[。！？!?]+")


@dataclass(frozen=True)
class NativeChineseHardGateIssue:
    id: str
    match: str
    message: str

    def as_payload(self) -> dict[str, str]:
        return asdict(self)


class NativeChineseHardGateError(ValueError):
    """Raised when final reader copy violates an R6 hard release rule."""


def normalized_phrase(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip("。！？!?；;")


def field_sentences(value: str) -> list[str]:
    return [item.strip() for item in SENTENCE_SPLIT.split(str(value or "")) if item.strip()]


def hard_quality_contract_payload() -> dict[str, object]:
    return {
        "version": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "extends": "final-narrative-native-zh-tw-contract-v1",
        "locale": "zh-Hant-TW",
        "rolloutMode": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_MODE,
        "baseIssuePolicy": "all-fail-release",
        "readerAnchorPattern": READER_ANCHOR_PATTERN,
        "unmarkedPolarityPattern": UNMARKED_POLARITY_PATTERN,
        "contrastMarkerPattern": CONTRAST_MARKER_PATTERN,
        "actionCommandPattern": ACTION_COMMAND_PATTERN,
        "actionStopPattern": ACTION_STOP_PATTERN,
        "timingDatePattern": TIMING_DATE_PATTERN,
        "coreNextMoveQuestionFragmentPattern": CORE_NEXT_MOVE_QUESTION_FRAGMENT_PATTERN,
        "knownReaderRegressionPhrases": list(KNOWN_READER_REGRESSION_PHRASES),
        "forbiddenVisibleTerms": list(FORBIDDEN_VISIBLE_TERMS),
        "pageForbiddenMarkers": {
            section_id: list(values)
            for section_id, values in PAGE_FORBIDDEN_MARKERS.items()
        },
        "abstractActionPhrases": list(ABSTRACT_ACTION_PHRASES),
        "unnaturalAssemblyPatterns": [
            {"id": issue_id, "pattern": pattern, "message": message}
            for issue_id, pattern, message in UNNATURAL_ASSEMBLY_PATTERNS
        ],
        "fieldRequirements": {
            "allHeadlines": "single-complete-thought-without-colon-splicing",
            "allNonHeadlineSentences": "reader-anchor-required",
            "relationship-fit.body": "adjacent-sentences-must-not-repeat-the-same-opening",
            "timing-reading.body": "dated-window-requires-explicit-pair-subject",
            "core-answer.nextMove": "complete-observable-condition-not-question-fragment",
            "action-direction.body": "completion-boundary-required",
            "action-direction.nextMove": "concrete-command-required",
            "action-direction.caution": "stopping-condition-required",
        },
        "releaseInvariants": {
            "allCatalogSentencesChecked": True,
            "allComposedFieldsChecked": True,
            "allBaseWarningsAreFailures": True,
            "knownReaderRegressionsAllowed": False,
            "pageTopicLeaksAllowed": False,
        },
    }


def hard_quality_contract_fingerprint() -> str:
    encoded = json.dumps(
        hard_quality_contract_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hard_quality_contract_errors() -> list[str]:
    payload = hard_quality_contract_payload()
    errors: list[str] = []
    if payload.get("version") != FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION:
        errors.append("R6 hard-quality contract version mismatch")
    if payload.get("rolloutMode") != "hard-release":
        errors.append("R6 hard-quality contract is not in hard-release mode")
    if set(PAGE_FORBIDDEN_MARKERS) != set(SECTION_IDS):
        errors.append("R6 page-scope registry is incomplete")
    if len(KNOWN_READER_REGRESSION_PHRASES) != 37:
        errors.append("R6 reader-regression registry count changed")
    if len(set(KNOWN_READER_REGRESSION_PHRASES)) != len(
        KNOWN_READER_REGRESSION_PHRASES
    ):
        errors.append("R6 reader-regression registry contains duplicate exact phrases")
    for identity, pattern in (
        ("reader-anchor", READER_ANCHOR_PATTERN),
        ("unmarked-polarity", UNMARKED_POLARITY_PATTERN),
        ("contrast-marker", CONTRAST_MARKER_PATTERN),
        ("action-command", ACTION_COMMAND_PATTERN),
        ("action-stop", ACTION_STOP_PATTERN),
        ("timing-date", TIMING_DATE_PATTERN),
        ("core-next-move-question-fragment", CORE_NEXT_MOVE_QUESTION_FRAGMENT_PATTERN),
        *(
            (f"unnatural-assembly:{issue_id}", pattern)
            for issue_id, pattern, _message in UNNATURAL_ASSEMBLY_PATTERNS
        ),
    ):
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(f"invalid R6 {identity} pattern: {exc}")
    return errors


def audit_hard_native_zh_tw_field(
    section_id: str,
    field: str,
    text: str,
    *,
    include_base_contract: bool = True,
) -> tuple[NativeChineseHardGateIssue, ...]:
    value = str(text or "").strip()
    issues: list[NativeChineseHardGateIssue] = []
    if section_id not in SECTION_IDS:
        issues.append(
            NativeChineseHardGateIssue(
                id="unknown-result-page",
                match=section_id,
                message="未知結果頁不可繞過 R6 中文品質檢查。",
            )
        )
    if field not in VISIBLE_FIELDS:
        issues.append(
            NativeChineseHardGateIssue(
                id="unknown-visible-field",
                match=field,
                message="未知可見欄位不可繞過 R6 中文品質檢查。",
            )
        )
    if include_base_contract:
        for issue in audit_native_zh_tw_text(value):
            issues.append(
                NativeChineseHardGateIssue(
                    id=issue.id,
                    match=issue.match,
                    message=f"R6 將原始 {issue.severity} 提升為發佈失敗：{issue.message}",
                )
            )
    normalized = normalized_phrase(value)
    for phrase in KNOWN_READER_REGRESSION_PHRASES:
        current = normalized_phrase(phrase)
        if current and current in normalized:
            issues.append(
                NativeChineseHardGateIssue(
                    id="known-reader-regression",
                    match=phrase,
                    message="已知讀者回報文案不可重新進入結果頁。",
                )
            )
    for term in FORBIDDEN_VISIBLE_TERMS:
        current = normalized_phrase(term)
        if current and current in normalized:
            issues.append(
                NativeChineseHardGateIssue(
                    id="technical-or-abstract-visible-term",
                    match=term,
                    message="技術標籤或抽象內部用語不可進入可見文案。",
                )
            )
    for marker in PAGE_FORBIDDEN_MARKERS.get(section_id, ()):
        if marker and marker in value:
            issues.append(
                NativeChineseHardGateIssue(
                    id="page-topic-leak",
                    match=marker,
                    message=f"{section_id} 出現其他頁面才擁有的主題。",
                )
            )

    if field == "headline" and "：" in value:
        issues.append(
            NativeChineseHardGateIssue(
                id="stitched-headline",
                match="：",
                message="標題必須是一個完整意思，不可用冒號拼接通用標籤。",
            )
        )
    for issue_id, pattern, message in UNNATURAL_ASSEMBLY_PATTERNS:
        match = re.search(pattern, value)
        if match:
            issues.append(
                NativeChineseHardGateIssue(
                    id=issue_id,
                    match=match.group(0),
                    message=message,
                )
            )

    if section_id == "relationship-fit" and field == "body":
        sentences = field_sentences(value)
        for left, right in zip(sentences, sentences[1:]):
            shared_prefix = 0
            for left_character, right_character in zip(left, right):
                if left_character != right_character:
                    break
                shared_prefix += 1
            if shared_prefix >= 7:
                issues.append(
                    NativeChineseHardGateIssue(
                        id="repeated-sentence-opening",
                        match=left[:shared_prefix],
                        message="同一段相鄰句不可用相同人物動作重複開頭。",
                    )
                )

    for sentence in field_sentences(value):
        compact = normalized_phrase(sentence)
        if (
            field != "headline"
            and len(compact) >= 12
            and not re.search(READER_ANCHOR_PATTERN, sentence)
        ):
            issues.append(
                NativeChineseHardGateIssue(
                    id="missing-reader-anchor",
                    match=sentence,
                    message="完整句缺少可理解的人物、互動事件或資料主詞。",
                )
            )
        if re.search(UNMARKED_POLARITY_PATTERN, sentence) and not re.search(
            CONTRAST_MARKER_PATTERN,
            sentence,
        ):
            issues.append(
                NativeChineseHardGateIssue(
                    id="unmarked-polarity-shift",
                    match=sentence,
                    message="正向與負向反應被直接接在一起，缺少清楚轉折。",
                )
            )
        if (
            section_id == "timing-reading"
            and field == "body"
            and re.search(TIMING_DATE_PATTERN, sentence)
            and "你們" not in sentence
        ):
            issues.append(
                NativeChineseHardGateIssue(
                    id="timing-window-missing-pair-subject",
                    match=sentence,
                    message="日期時機句必須明確說出受到影響的是你們的互動。",
                )
            )

    if (
        section_id == "core-answer"
        and field == "nextMove"
        and re.search(CORE_NEXT_MOVE_QUESTION_FRAGMENT_PATTERN, value)
    ):
        match = re.search(CORE_NEXT_MOVE_QUESTION_FRAGMENT_PATTERN, value)
        issues.append(
            NativeChineseHardGateIssue(
                id="question-fragment-as-guidance",
                match=match.group(0) if match else value,
                message="核心答案的觀察條件必須寫成完整判斷，不可留下問句片段。",
            )
        )

    if section_id == "action-direction":
        for phrase in ABSTRACT_ACTION_PHRASES:
            if phrase in value:
                issues.append(
                    NativeChineseHardGateIssue(
                        id="abstract-action-language",
                        match=phrase,
                        message="行動頁必須說出具體可執行動作，不可只給抽象方向。",
                    )
                )
        if field == "body" and "完成" not in value:
            issues.append(
                NativeChineseHardGateIssue(
                    id="missing-completion-boundary",
                    match=value,
                    message="行動頁必須說清楚做到哪裡，這一步就已經完成。",
                )
            )
        if field == "nextMove" and not re.search(ACTION_COMMAND_PATTERN, value):
            issues.append(
                NativeChineseHardGateIssue(
                    id="missing-concrete-command",
                    match=value,
                    message="行動頁下一步缺少具體可執行動詞。",
                )
            )
        if field == "caution" and not re.search(ACTION_STOP_PATTERN, value):
            issues.append(
                NativeChineseHardGateIssue(
                    id="missing-stopping-condition",
                    match=value,
                    message="行動頁缺少清楚的停止條件。",
                )
            )

    unique: dict[tuple[str, str], NativeChineseHardGateIssue] = {}
    for issue in issues:
        unique[(issue.id, issue.match)] = issue
    return tuple(unique.values())


def validate_hard_native_zh_tw_field(section_id: str, field: str, text: str) -> None:
    issues = audit_hard_native_zh_tw_field(section_id, field, text)
    if issues:
        details = "; ".join(f"{item.id}: {item.match}" for item in issues)
        raise NativeChineseHardGateError(f"{section_id}:{field}: {details}")


def validate_hard_native_zh_tw_section(
    section_id: str,
    rendered: Mapping[str, str],
) -> None:
    if set(rendered) != set(VISIBLE_FIELDS):
        raise NativeChineseHardGateError(
            f"{section_id}: visible field set is incomplete: {sorted(rendered)}"
        )
    for field in VISIBLE_FIELDS:
        validate_hard_native_zh_tw_field(section_id, field, str(rendered.get(field) or ""))


__all__ = [
    "ABSTRACT_ACTION_PHRASES",
    "FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_MODE",
    "FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION",
    "FORBIDDEN_VISIBLE_TERMS",
    "KNOWN_READER_REGRESSION_PHRASES",
    "NativeChineseHardGateError",
    "NativeChineseHardGateIssue",
    "PAGE_FORBIDDEN_MARKERS",
    "SECTION_IDS",
    "UNNATURAL_ASSEMBLY_PATTERNS",
    "audit_hard_native_zh_tw_field",
    "field_sentences",
    "hard_quality_contract_errors",
    "hard_quality_contract_fingerprint",
    "hard_quality_contract_payload",
    "normalized_phrase",
    "validate_hard_native_zh_tw_field",
    "validate_hard_native_zh_tw_section",
]
