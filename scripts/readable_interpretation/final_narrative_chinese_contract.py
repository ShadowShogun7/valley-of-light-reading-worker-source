"""Versioned native Traditional Chinese realization contract.

R0/R1 use this contract to audit the current renderer without changing its
visible output. Later realization phases can promote the same checks to hard
runtime release gates after every catalog entry has been migrated.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Iterable

from .copy_contract import reader_meta_narration_hits
from .final_narrative_semantic_domains import PLANET_FUNCTIONS


FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION = "final-narrative-native-zh-tw-contract-v1"
FINAL_NARRATIVE_NATIVE_ZH_TW_LOCALE = "zh-Hant-TW"
FINAL_NARRATIVE_NATIVE_ZH_TW_ROLLOUT_MODE = "baseline-observation"


@dataclass(frozen=True)
class NativeChinesePattern:
    id: str
    pattern: str
    severity: str
    description: str


@dataclass(frozen=True)
class NativeChineseIssue:
    id: str
    severity: str
    match: str
    message: str

    def as_payload(self) -> dict[str, str]:
        return asdict(self)


class NativeChineseContractError(ValueError):
    """Raised when reader-facing Chinese violates the native-language contract."""


INTERNAL_SEMANTIC_LABELS = tuple(dict.fromkeys(PLANET_FUNCTIONS.values()))

NATIVE_CHINESE_PATTERNS = (
    NativeChinesePattern(
        id="aspect-tone-fragment",
        pattern=(
            r"(?:吸引|摩擦|調整空間)?"
            r"(?:集中|輕鬆|自然|易卡|拉扯|錯拍|疊高|可調|可解)時"
        ),
        severity="failure",
        description="相位語意標籤被當成可見中文片段。",
    ),
    NativeChinesePattern(
        id="mechanical-salience-template",
        pattern=(
            r"(?:你的|他的)[^，。！？；]{1,24}一明顯，"
            r"(?:你的|他的)[^，。！？；]{1,24}也會被帶動"
        ),
        severity="failure",
        description="內部功能名詞被插入「一明顯／被帶動」模板。",
    ),
    NativeChinesePattern(
        id="mechanical-trigger-template",
        pattern=r"(?:你的|他的)[^，。！？；]{1,24}會牽動(?:你的|他的)",
        severity="failure",
        description="抽象功能名詞以「牽動」模板直接組句。",
    ),
    NativeChinesePattern(
        id="double-possessive-chain",
        pattern=r"的方式的反應",
        severity="failure",
        description="連續所有格造成不自然中文。",
    ),
    NativeChinesePattern(
        id="repeated-conjunction-chain",
        pattern=r"[^，。！？；]{0,16}(?:和|與)[^，。！？；]{1,16}(?:和|與)[^，。！？；]{1,20}",
        severity="warning",
        description="同一短句連續使用連接詞，可能是機械式名詞串接。",
    ),
)

NATIVE_CHINESE_STYLE_RULES = (
    "每句只承擔一個讀者能立即理解的重點。",
    "句子必須有清楚的人物、動作或可觀察反應。",
    "內部行星功能、相位與規則標籤不得直接出現在可見文案。",
    "相位只決定完整句型，不得以形容詞片段插入模板。",
    "保留人物方向、條件與不確定性，不用抽象術語取代關係行為。",
    "所有新增語意都必須有已核准文案；缺少文案時必須失敗，不得使用通用 fallback。",
    "標題直接說明關係內容，不解說頁面、方法或閱讀順序。",
)

MAXIMUM_NATIVE_SENTENCE_CHARACTERS_WARNING = 52
MAXIMUM_NATIVE_SENTENCE_CLAUSES_WARNING = 4
SENTENCE_SPLIT = re.compile(r"[。！？!?]+")


def native_contract_payload() -> dict[str, object]:
    return {
        "version": FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION,
        "locale": FINAL_NARRATIVE_NATIVE_ZH_TW_LOCALE,
        "rolloutMode": FINAL_NARRATIVE_NATIVE_ZH_TW_ROLLOUT_MODE,
        "runtimePolicy": {
            "approvedCatalogRequired": True,
            "genericFallbackAllowed": False,
            "internalSemanticLabelsVisible": False,
            "runtimeLlmAllowed": False,
        },
        "internalSemanticLabels": list(INTERNAL_SEMANTIC_LABELS),
        "antiPatterns": [asdict(item) for item in NATIVE_CHINESE_PATTERNS],
        "styleRules": list(NATIVE_CHINESE_STYLE_RULES),
        "warningThresholds": {
            "maximumSentenceCharacters": MAXIMUM_NATIVE_SENTENCE_CHARACTERS_WARNING,
            "maximumSentenceClauses": MAXIMUM_NATIVE_SENTENCE_CLAUSES_WARNING,
        },
    }


def native_contract_fingerprint() -> str:
    encoded = json.dumps(
        native_contract_payload(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def native_contract_errors() -> list[str]:
    errors: list[str] = []
    payload = native_contract_payload()
    pattern_ids = [item.id for item in NATIVE_CHINESE_PATTERNS]
    if payload.get("version") != FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION:
        errors.append("native Chinese contract version mismatch")
    if payload.get("locale") != "zh-Hant-TW":
        errors.append("native Chinese locale must be zh-Hant-TW")
    if len(pattern_ids) != len(set(pattern_ids)):
        errors.append("native Chinese anti-pattern ids are not unique")
    if any(item.severity not in {"failure", "warning"} for item in NATIVE_CHINESE_PATTERNS):
        errors.append("native Chinese anti-pattern severity is invalid")
    for item in NATIVE_CHINESE_PATTERNS:
        try:
            re.compile(item.pattern)
        except re.error as exc:
            errors.append(f"invalid native Chinese pattern {item.id}: {exc}")
    if not INTERNAL_SEMANTIC_LABELS or any(not item.strip() for item in INTERNAL_SEMANTIC_LABELS):
        errors.append("internal semantic label registry is empty or malformed")
    return errors


def audit_native_zh_tw_text(text: str) -> tuple[NativeChineseIssue, ...]:
    value = str(text or "").strip()
    if not value:
        return (
            NativeChineseIssue(
                id="empty-visible-copy",
                severity="failure",
                match="",
                message="可見文案不可為空。",
            ),
        )

    issues: list[NativeChineseIssue] = []
    for label in INTERNAL_SEMANTIC_LABELS:
        if label in value:
            issues.append(
                NativeChineseIssue(
                    id="internal-semantic-label",
                    severity="failure",
                    match=label,
                    message="內部行星功能標籤不可直接顯示給讀者。",
                )
            )
    for definition in NATIVE_CHINESE_PATTERNS:
        match = re.search(definition.pattern, value)
        if match:
            issues.append(
                NativeChineseIssue(
                    id=definition.id,
                    severity=definition.severity,
                    match=match.group(0),
                    message=definition.description,
                )
            )
    for match in reader_meta_narration_hits(value):
        issues.append(
            NativeChineseIssue(
                id="reader-meta-narration",
                severity="failure",
                match=match,
                message="頁面或閱讀流程說明不可進入關係解讀。",
            )
        )
    for raw_sentence in SENTENCE_SPLIT.split(value):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        if len(sentence) > MAXIMUM_NATIVE_SENTENCE_CHARACTERS_WARNING:
            issues.append(
                NativeChineseIssue(
                    id="long-native-sentence",
                    severity="warning",
                    match=sentence,
                    message=f"句子超過 {MAXIMUM_NATIVE_SENTENCE_CHARACTERS_WARNING} 字，需要人工檢查。",
                )
            )
        clause_count = len([item for item in re.split(r"[，；;]", sentence) if item.strip()])
        if clause_count > MAXIMUM_NATIVE_SENTENCE_CLAUSES_WARNING:
            issues.append(
                NativeChineseIssue(
                    id="overloaded-native-sentence",
                    severity="warning",
                    match=sentence,
                    message=f"句子包含 {clause_count} 個分句，需要拆分或重寫。",
                )
            )
    return tuple(issues)


def validate_native_zh_tw_text(text: str, *, identity: str) -> None:
    failures = [issue for issue in audit_native_zh_tw_text(text) if issue.severity == "failure"]
    if failures:
        details = "; ".join(f"{item.id}: {item.match}" for item in failures)
        raise NativeChineseContractError(f"{identity}: {details}")


def issue_ids(issues: Iterable[NativeChineseIssue]) -> set[str]:
    return {item.id for item in issues}


__all__ = [
    "FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION",
    "FINAL_NARRATIVE_NATIVE_ZH_TW_LOCALE",
    "FINAL_NARRATIVE_NATIVE_ZH_TW_ROLLOUT_MODE",
    "INTERNAL_SEMANTIC_LABELS",
    "NATIVE_CHINESE_PATTERNS",
    "NATIVE_CHINESE_STYLE_RULES",
    "NativeChineseContractError",
    "NativeChineseIssue",
    "audit_native_zh_tw_text",
    "issue_ids",
    "native_contract_errors",
    "native_contract_fingerprint",
    "native_contract_payload",
    "validate_native_zh_tw_text",
]
