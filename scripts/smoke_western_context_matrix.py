#!/usr/bin/env python3
"""
Generate and smoke-test the Western relationship-result context matrix.

This is intentionally not a long list of checked-in JSON files. The matrix is
generated in memory so each run proves the reducer still handles realistic
stage/question/contact/risk/precision variation.
"""

from __future__ import annotations

import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
)
from calc_western_spike import build_payload, read_json  # noqa: E402


ARTICLES = load_articles(DEFAULT_ARTICLES_PATH)
CLAIMS_BY_ARTICLE = load_claims_by_article(DEFAULT_CLAIMS_PATH)
SATURN_BOUNDARY_SOURCE_CLAIMS = {
    "western-aspects-saturn-pressure-001",
    "western-aspects-saturn-pressure-003",
}
SATURN_BOUNDARY_METHOD_CLAIM = "greene-saturn-defense-not-permanent-rejection"
QUESTION_SELECTOR_METHOD_CLAIMS = {
    "still-love-me": "valley-question-still-love-evidence-selector",
    "any-chance": "valley-question-any-chance-conditional-selector",
    "when-to-contact": "valley-question-when-to-contact-timing-selector",
    "what-did-i-do-wrong": "valley-question-self-blame-interaction-cycle-selector",
    "stay-or-let-go": "valley-question-stay-let-go-boundary-selector",
}
QUESTION_VISIBLE_COPY_MARKERS = {
    "still-love-me": "穩定回應",
    "any-chance": "修復條件",
    "when-to-contact": "短、輕、沒有要求",
    "what-did-i-do-wrong": "可調整的互動",
    "stay-or-let-go": "讓你更累",
}
QUESTION_EVIDENCE_HIGHLIGHT_TITLE_MARKERS = {
    "still-love-me": "穩定回應",
    "any-chance": "修復條件",
    "when-to-contact": "開口",
    "what-did-i-do-wrong": "可調整的互動",
    "stay-or-let-go": "等待條件",
}
NORMAL_USER_REQUIRED_BLOCKS = ["directAnswer", "whyThisMatters", "whatToWatch", "nextStep", "stopLine"]
NORMAL_USER_QUESTION_MARKERS = {
    "still-love-me": ("反應", "穩定延續"),
    "any-chance": ("機會", "條件"),
    "when-to-contact": ("開口", "短、輕"),
    "what-did-i-do-wrong": ("責任", "調整"),
    "stay-or-let-go": ("等待", "累"),
}

STAGES = ["ambiguous", "cold-war", "broke-up-recent", "broke-up-long", "crisis"]
QUESTIONS = ["still-love-me", "any-chance", "when-to-contact", "what-did-i-do-wrong", "stay-or-let-go"]
CONTACT_STATUSES = ["blocked", "no-contact", "occasional-contact", "still-in-contact", "living-or-working-together"]
EMOTIONAL_RISKS = ["calm", "anxious", "self-blaming", "desperate", "unsafe-or-overwhelmed"]
PRECISION_STATES = ["full", "missing_city", "no_birth_time"]
CONTACT_POLICY_FIXTURES = {
    "blocked": {
        "expectedRule": "western-rule-when-to-contact-blocked",
        "actionScale": 0,
        "actionMode": "boundary_only",
        "canSuggestDirectContact": False,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "blockedActions": {
            "alternate_account_contact",
            "repeated_messages",
            "third_party_pressure",
            "emotional_confrontation",
        },
        "expectedClaim": "context-contact-status-004",
        "expectedMethodClaim": "valley-blocked-contact-hard-boundary",
        "expectedMethodClaims": {
            "valley-contact-status-action-scale",
            "valley-blocked-contact-hard-boundary",
        },
        "headline": "先不要聯絡",
        "copyIncludes": ["先守住彼此的界線", "不繞路找他", "不要換帳號"],
    },
    "no-contact": {
        "expectedRule": "western-rule-when-to-contact-no-contact-pressure",
        "actionScale": 1,
        "actionMode": "observe_or_single_low_stimulation_test",
        "canSuggestDirectContact": True,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "blockedActions": {
            "repeated_messages",
            "long_explanation",
            "asking_for_answer_now",
            "emotional_confrontation",
        },
        "expectedClaim": "context-contact-status-005",
        "expectedMethodClaim": "valley-no-contact-lowers-action-speed",
        "expectedMethodClaims": {
            "valley-contact-status-action-scale",
            "valley-no-contact-lowers-action-speed",
            "gottman-no-contact-low-stimulation-bid",
        },
        "headline": "先看，再決定要不要開口",
        "copyIncludes": ["一句短、輕、沒有要求的訊息", "送出後先停下來看反應"],
    },
    "occasional-contact": {
        "expectedRule": "western-rule-when-to-contact-occasional-contact",
        "actionScale": 2,
        "actionMode": "small_bid_response_led",
        "canSuggestDirectContact": True,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": False,
        "blockedActions": {
            "turning_reply_into_commitment",
            "rapid_escalation",
            "relationship_definition_push",
        },
        "expectedClaim": "context-contact-status-006",
        "expectedMethodClaim": "gottman-contact-as-bid-not-proof",
        "expectedMethodClaims": {
            "valley-contact-status-action-scale",
            "gottman-contact-as-bid-not-proof",
            "gottman-limited-reply-existing-channel-repair",
        },
        "headline": "跟著回應走，不要加速",
        "copyIncludes": ["偶爾回覆代表還有一點互動空間", "不要把一次回應放大成復合訊號"],
    },
    "still-in-contact": {
        "expectedRule": "western-rule-when-to-contact-still-in-contact-friction",
        "actionScale": 3,
        "actionMode": "tone_repair_in_existing_channel",
        "canSuggestDirectContact": True,
        "requiresEasyExit": False,
        "requiresSharedSpaceBoundary": False,
        "blockedActions": {
            "forcing_relationship_definition",
            "long_pressure_message",
            "testing_loyalty",
        },
        "expectedClaim": "context-contact-status-007",
        "expectedMethodClaim": "gottman-repair-tone-before-content",
        "expectedMethodClaims": {
            "valley-contact-status-action-scale",
            "gottman-repair-tone-before-content",
            "gottman-limited-reply-existing-channel-repair",
        },
        "headline": "在原本對話裡放輕",
        "copyIncludes": ["原本的對話", "沒有逼問的事", "能聊天不等於已經能談復合"],
    },
    "living-or-working-together": {
        "expectedRule": "western-rule-when-to-contact-shared-space-boundary",
        "actionScale": 2,
        "actionMode": "shared_space_boundary",
        "canSuggestDirectContact": True,
        "requiresEasyExit": True,
        "requiresSharedSpaceBoundary": True,
        "blockedActions": {
            "public_confrontation",
            "using_shared_space_as_pressure",
            "relationship_definition_push",
        },
        "expectedClaim": "context-contact-status-008",
        "expectedMethodClaim": "valley-shared-space-discretion-boundary",
        "expectedMethodClaims": {
            "valley-contact-status-action-scale",
            "valley-shared-space-discretion-boundary",
        },
        "headline": "先保護共同場域",
        "copyIncludes": ["共同場合", "不要在共同場域逼談關係", "保留退路"],
    },
}
CONTACT_POLICY_STATE_CLAIMS = {
    str(expectation["expectedClaim"])
    for expectation in CONTACT_POLICY_FIXTURES.values()
}
CONTACT_POLICY_FORBIDDEN_COPY = (
    "保證",
    "一定成功",
    "一定回覆",
    "偷偷",
    "繞過",
    "換帳號聯絡",
    "找朋友傳話",
    "逼他回答",
)
LEGACY_TERMS = ("bazi", "八字", "配偶星", "日主", "四柱", "十神")
AWKWARD_QUESTION_COPY = (
    "互動氣候",
    "timing",
    "timing band",
    "timing 壓力",
    "timing climate",
    "reducer",
    "selector",
    "better",
    "neutral",
    "avoid",
    "入口",
    "窗口",
    "低壓",
    "壓力群組",
    "溝通群組",
    "情緒風險",
    "情緒風險比 timing",
    "這題不能被寫成",
    "這個問題不能被寫成",
    "命盤替你承受壓力",
    "免費頁",
    "免費版",
    "免費結果",
    "付費報告",
    "完整報告",
    "不給精準日",
    "高壓狀態",
    "推到高壓",
    "降壓",
    "消耗界線",
    "先看消耗",
    "需要翻譯",
    "修復槓桿",
    "行動尺度",
    "開口門檻",
    "精準證據",
    "orb 約",
    "施壓",
    "action climate",
    "低壓重啟",
    "等低壓",
    "低壓試探",
    "低需求",
    "可不回",
    "直接推出精準",
    "訊息寫得多完美",
    "用崩潰訊息求答案",
    "等待包裝成命定",
    "未來掃描",
    "把自己放到更低的位置",
    "責任審判",
    "壓力測試",
    "不新增會讓對方更防衛的刺激",
    "不把整段關係一次攤開",
)
FATALISTIC_QUESTION_COPY = (
    "這段關係一定會復合",
    "你們一定會復合",
    "一定會分手",
    "一定沒有機會",
    "一定沒機會",
    "注定分開",
    "注定復合",
    "保證會復合",
    "保證對方會回來",
    "永久結束",
    "他一定還愛你",
    "他一定不愛你",
    "某天聯絡一定成功",
    "聯絡一定成功",
)
REPETITIVE_QUESTION_COPY_LIMITS = {
    "壓力": 3,
    "節奏": 2,
    "防衛": 2,
    "牽動": 2,
}

REQUIRED_CONTEXT_CLUSTERS = [
    "relationshipStage",
    "contactStatus",
    "contactSituationPolicy",
    "emotionalRisk",
    "desiredOutcome",
]
REQUIRED_SUSKIN_CLUSTERS = [
    "methodOrder",
    "relationshipPotential",
    "elementComparison",
    "luminaryComparison",
    "ascendantImpression",
    "houseRelationshipFactors",
    "aspectPriority",
    "relationshipChartLayer",
    "consultationSafety",
    "nonfatalSynastrySafety",
]
REQUIRED_HAND_FUNCTION_CLUSTERS = [
    "moonSignEmotionalSafety",
    "mercurySignCommunicationRepair",
    "venusSignAffectionStyle",
    "marsSignPursuitConflict",
    "saturnSignDefenseDelay",
    "functionElementMatrix",
    "functionModalityMatrix",
    "aspectContactModifier",
    "aspectPairContactTemplate",
    "aspectPairPhraseTemplateMethod",
    "aspectSynthesisCrossCheck",
    "aspectFunctionCombination",
]
REQUIRED_TIMING_SELECTOR_CLUSTERS = [
    "timingWindowBand",
    "timingMercuryCommunication",
    "timingVenusSoftening",
    "timingMarsActivation",
    "timingSaturnPressure",
    "timingMoonWeather",
    "timingContactReducer",
]
REQUIRED_METHOD_TRACE_CLAIMS = {
    "profile": {
        "george-bloch-synthesis-salient-themes-first",
        "burk-moon-safety-survival-connection-boundaries",
        "skymates-venus-mars-relating-styles-context-bound",
    },
    "fit": {
        "george-bloch-relationship-comparison-wants-needs",
        "george-bloch-synthesis-salient-themes-first",
        "burk-moon-safety-survival-connection-boundaries",
        "skymates-interaspect-selection-priority-procedure",
        "skymates-venus-mars-relating-styles-context-bound",
    },
    "timing": {
        "hand-transits-easy-difficult-neutrality",
        "hand-transits-inner-planet-reinforcement-timing",
    },
    "action": {
        "hand-transits-easy-difficult-neutrality",
        "hand-transits-inner-planet-reinforcement-timing",
        "skymates-venus-mars-relating-styles-context-bound",
    },
}
THOUGHTS_SOURCES = {
    "western-synastry-method-order",
    "western-natal-relationship-potential",
    "western-interchart-aspect-priorities",
    "western-function-element-templates",
    "western-function-modality-templates",
    "western-aspect-function-combination-reducers",
}
REASONS_SOURCES = {
    "western-initial-comparison-elements",
    "western-interchart-aspect-priorities",
    "western-function-element-templates",
    "western-function-modality-templates",
    "western-aspect-function-combination-reducers",
}
CHANCE_SOURCES = {
    "western-consultation-ethics",
    "western-modern-nonfatal-synastry",
    "western-relationship-chart-layer",
    "western-function-element-templates",
    "western-function-modality-templates",
    "western-aspect-function-combination-reducers",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_question_selector_trace(payload: dict[str, Any], question_key: str, label: str) -> None:
    expected_claim_id = QUESTION_SELECTOR_METHOD_CLAIMS[question_key]
    selector = payload.get("questionSelector") or {}
    assert_true(selector.get("version") == "western-question-selector-v1", f"{label} selector missing")
    assert_true(selector.get("questionKey") == question_key, f"{label} selector question mismatch")
    assert_true(
        selector.get("role") == "evidence_weighting_policy",
        f"{label} selector role mismatch",
    )
    assert_true(
        expected_claim_id in set(selector.get("methodClaimIds") or []),
        f"{label} selector missing method claim {expected_claim_id}",
    )
    assert_true(selector.get("evidenceClusterKeys"), f"{label} selector missing evidence clusters")
    if payload.get("methodClaimIds") is not None:
        assert_true(
            expected_claim_id in set(payload.get("methodClaimIds") or []),
            f"{label} payload methodClaimIds missing selector claim",
        )
    if payload.get("evidenceClusterKeys") is not None:
        assert_true(payload.get("evidenceClusterKeys"), f"{label} payload evidenceClusterKeys empty")
    if payload.get("selectorEvidenceClusterKeys") is not None:
        assert_true(payload.get("selectorEvidenceClusterKeys"), f"{label} payload selectorEvidenceClusterKeys empty")


def visible_question_copy(view_model: dict[str, Any]) -> str:
    readable = view_model.get("readableQuestionAnswer") or {}
    sections = readable.get("sections") or {}
    parts: list[str] = []
    parts.append(str((view_model.get("reading") or {}).get("answer") or ""))
    answer = sections.get("answer") or {}
    answer_block = answer.get("readableInterpretation") or {}
    parts.extend(str(answer_block.get(key) or "") for key in ("headline", "meaning", "body", "nextMove", "caution"))
    normal_answer = view_model.get("normalUserAnswer") or answer.get("normalUserAnswer") or {}
    parts.extend(str(normal_answer.get(key) or "") for key in ("headline", "directAnswer", "whyThisMatters", "nextStep", "stopLine", "evidenceBridge"))
    parts.extend(str(item or "") for item in normal_answer.get("whatToWatch") or [])
    for highlight in answer.get("evidenceHighlights") or []:
        parts.extend(str(highlight.get(key) or "") for key in ("title", "body"))
    for item in sections.get("thoughts") or []:
        parts.append(str(item.get("body") or ""))
        parts.append(str((item.get("readableInterpretation") or {}).get("body") or ""))
    for card in view_model.get("reasons") or []:
        parts.extend(str(card.get(key) or "") for key in ("label", "body", "nextMove"))
    chance = view_model.get("chance") or {}
    parts.extend(str(note or "") for note in chance.get("notes") or [])
    parts.append(str(chance.get("nextMove") or ""))
    for step in view_model.get("timeline") or []:
        parts.extend(str(step.get(key) or "") for key in ("range", "title", "body", "nextMove"))
    for item in sections.get("donts") or []:
        parts.append(str(item.get("body") or ""))
    return "\n".join(parts)


def assert_question_family_visible_marker(view_model: dict[str, Any], question_key: str) -> None:
    expected_marker = QUESTION_VISIBLE_COPY_MARKERS[question_key]
    copy = visible_question_copy(view_model)
    assert_true(
        expected_marker in copy,
        f"{question_key} visible question copy missing selector-specific marker: {expected_marker}",
    )


def assert_primary_answer_question_marker(view_model: dict[str, Any], question_key: str) -> None:
    answer_guidance = view_model.get("answerGuidance") or {}
    short_answer = str(answer_guidance.get("shortAnswer") or "")
    answer_body = str(((answer_guidance.get("readableInterpretation") or {}).get("body")) or "")
    expected_marker = QUESTION_VISIBLE_COPY_MARKERS[question_key]
    title_marker = QUESTION_EVIDENCE_HIGHLIGHT_TITLE_MARKERS[question_key]
    highlight_titles = "\n".join(str(item.get("title") or "") for item in answer_guidance.get("evidenceHighlights") or [])
    assert_true(
        expected_marker in short_answer,
        f"{question_key} answerGuidance.shortAnswer missing primary question marker: {expected_marker}",
    )
    assert_true(
        expected_marker in answer_body,
        f"{question_key} answer readable body missing primary question marker: {expected_marker}",
    )
    assert_true(
        title_marker in highlight_titles,
        f"{question_key} answer evidence highlights missing question title marker: {title_marker}",
    )


def assert_normal_user_answer(view_model: dict[str, Any], question_key: str) -> None:
    answer_guidance = view_model.get("answerGuidance") or {}
    normal = view_model.get("normalUserAnswer") or {}
    nested = answer_guidance.get("normalUserAnswer") or {}
    assert_true(normal.get("version") == "normal-user-answer-v1", f"{question_key} normalUserAnswer missing")
    assert_true(nested.get("version") == "normal-user-answer-v1", f"{question_key} nested normalUserAnswer missing")
    assert_true(normal.get("questionKey") == question_key, f"{question_key} normalUserAnswer questionKey mismatch")
    for key in ("directAnswer", "whyThisMatters", "nextStep", "stopLine", "evidenceBridge"):
        value = str(normal.get(key) or "")
        assert_true(value, f"{question_key} normalUserAnswer {key} missing")
        assert_true(len(value) <= 120, f"{question_key} normalUserAnswer {key} too long: {value}")
        assert_native_question_copy(value, f"{question_key} normalUserAnswer {key}")
    watch_items = [str(item or "") for item in normal.get("whatToWatch") or []]
    assert_true(len(watch_items) >= 2, f"{question_key} normalUserAnswer whatToWatch too thin")
    for item in watch_items:
        assert_true(len(item) <= 95, f"{question_key} normalUserAnswer watch item too long: {item}")
        assert_native_question_copy(item, f"{question_key} normalUserAnswer watch item")
    blocks = normal.get("blocks") or []
    assert_true([block.get("key") for block in blocks[:5]] == NORMAL_USER_REQUIRED_BLOCKS, f"{question_key} normalUserAnswer blocks out of order")
    combined = "\n".join([str(normal.get("headline") or ""), str(normal.get("directAnswer") or ""), str(normal.get("whyThisMatters") or ""), *watch_items])
    for marker in NORMAL_USER_QUESTION_MARKERS[question_key]:
        assert_true(marker in combined, f"{question_key} normalUserAnswer missing marker {marker}: {combined}")
    if question_key == "when-to-contact":
        assert_true("指定日期" in combined or "指定日期" in str(normal.get("evidenceBridge") or ""), "when-to-contact should explicitly avoid exact dates")
    if question_key == "still-love-me":
        assert_true(
            any(marker in combined for marker in ("現實回應", "穩定回應", "穩定延續", "持續回應", "自然延伸")),
            "still-love-me should use observable response framing",
        )
    if question_key == "what-did-i-do-wrong":
        assert_true("全部責任" in combined or "怪到自己" in combined, "what-did-i-do-wrong should reduce self-blame")


def included_reading_rows(view_model: dict[str, Any]) -> list[dict[str, Any]]:
    rows = view_model.get("includedReadingRows") or []
    return [row for row in rows if isinstance(row, dict)]


def blueprint_chapters(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    chapters = blueprint.get("chapters") or []
    return [chapter for chapter in chapters if isinstance(chapter, dict)]


def assert_exact_timing_policy(value: dict[str, Any], label: str) -> None:
    policy = value.get("exactTimingPolicy") or {}
    assert_true(value.get("preciseDatesAvailable") is False, f"{label} should expose preciseDatesAvailable=false")
    assert_true(policy.get("preciseDatesAvailable") is False, f"{label} exactTimingPolicy should block precise dates")


def assert_saturn_process_boundary(cluster: dict[str, Any], label: str) -> None:
    boundary = cluster.get("saturnProcessBoundary") or {}
    assert_true(boundary.get("version") == "saturn-nonfatal-process-boundary-v1", f"{label} Saturn boundary missing")
    assert_true(boundary.get("role") == "pressure_process_not_fate", f"{label} Saturn boundary role mismatch")
    assert_true(boundary.get("canCreatePermanentOutcome") is False, f"{label} Saturn boundary must not create permanent outcomes")
    assert_true(boundary.get("canProveInnerState") is False, f"{label} Saturn boundary must not prove inner state")
    blocked = set(boundary.get("cannotClaim") or [])
    for key in ("permanent_rejection", "doomed_relationship", "fated_waiting", "secret_love_proof"):
        assert_true(key in blocked, f"{label} Saturn boundary missing blocked claim {key}")
    assert_true(
        SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(set(boundary.get("sourceClaimIds") or [])),
        f"{label} Saturn source claims missing",
    )
    assert_true(
        SATURN_BOUNDARY_METHOD_CLAIM in set(boundary.get("methodClaimIds") or []),
        f"{label} Saturn method claim missing",
    )


def assert_native_question_copy(text: Any, label: str) -> None:
    value = str(text or "")
    for phrase in AWKWARD_QUESTION_COPY:
        assert_true(phrase not in value, f"{label} still contains awkward question copy: {phrase}")


def visible_question_copy_parts(view_model: dict[str, Any]) -> list[str]:
    parts: list[str] = [str((view_model.get("reading") or {}).get("answer") or "")]
    for metric in view_model.get("metrics") or []:
        parts.extend(str(metric.get(key) or "") for key in ("label", "value", "helper"))
    for row in included_reading_rows(view_model):
        parts.append(str(row.get("title") or ""))
        parts.extend(str(item or "") for item in row.get("preview") or [])
    readable = view_model.get("readableQuestionAnswer") or {}
    sections = readable.get("sections") or {}
    answer = sections.get("answer") or view_model.get("answerGuidance") or {}
    answer_readable = answer.get("readableInterpretation") or {}
    parts.extend(str(answer.get(key) or "") for key in ("shortAnswer", "nextMove"))
    parts.extend(str(answer_readable.get(key) or "") for key in ("body", "nextMove", "meaning", "headline", "caution"))
    for highlight in answer.get("evidenceHighlights") or []:
        parts.extend(str(highlight.get(key) or "") for key in ("title", "body"))
    action = sections.get("action") or view_model.get("actionGuidance") or {}
    action_readable = action.get("readableInterpretation") or {}
    parts.extend(str(action.get(key) or "") for key in ("nextMove",))
    parts.extend(str(action_readable.get(key) or "") for key in ("body", "nextMove", "meaning", "headline", "caution"))
    timing = sections.get("timing") or view_model.get("timingGuidance") or {}
    timing_readable = timing.get("readableInterpretation") or {}
    parts.extend(str(timing.get(key) or "") for key in ("nextMove",))
    parts.extend(str(timing_readable.get(key) or "") for key in ("body", "nextMove", "meaning", "headline", "caution"))
    for signal in timing.get("selectedSignals") or []:
        parts.extend(str(signal.get(key) or "") for key in ("title", "body"))
    for item in sections.get("thoughts") or []:
        parts.append(str(item.get("body") or ""))
        block = item.get("readableInterpretation") or {}
        parts.extend(str(block.get(key) or "") for key in ("body", "nextMove", "meaning", "headline"))
    for card in view_model.get("reasons") or []:
        parts.extend(str(card.get(key) or "") for key in ("label", "body", "nextMove"))
        block = card.get("readableInterpretation") or {}
        parts.extend(str(block.get(key) or "") for key in ("body", "nextMove", "meaning", "headline"))
    chance = view_model.get("chance") or {}
    parts.extend(str(note or "") for note in chance.get("notes") or [])
    parts.append(str(chance.get("nextMove") or ""))
    chance_readable = chance.get("readableInterpretation") or {}
    parts.extend(str(chance_readable.get(key) or "") for key in ("body", "nextMove", "meaning", "headline"))
    for step in view_model.get("timeline") or []:
        parts.extend(str(step.get(key) or "") for key in ("title", "body", "nextMove"))
        block = step.get("readableInterpretation") or {}
        parts.extend(str(block.get(key) or "") for key in ("body", "nextMove", "meaning", "headline"))
    for item in sections.get("donts") or []:
        parts.append(str(item.get("body") or ""))
        block = item.get("readableInterpretation") or {}
        parts.extend(str(block.get(key) or "") for key in ("body", "nextMove", "meaning", "headline"))
    return parts


def assert_question_copy_density(view_model: dict[str, Any]) -> None:
    rendered = "\n".join(visible_question_copy_parts(view_model))
    for phrase in FATALISTIC_QUESTION_COPY:
        assert_true(phrase not in rendered, f"question copy contains fatalistic outcome claim: {phrase}")
    for term, limit in REPETITIVE_QUESTION_COPY_LIMITS.items():
        count = rendered.count(term)
        assert_true(count <= limit, f"question copy repeats `{term}` {count} time(s), limit {limit}")


def desired_outcome_for(question: str) -> str:
    if question in {"still-love-me", "any-chance", "when-to-contact"}:
        return "reconnect"
    if question == "stay-or-let-go":
        return "decide"
    return "understand"


def build_matrix_reading(
    base_reading: dict[str, Any],
    *,
    stage: str,
    question: str,
    contact_status: str,
    emotional_risk: str,
    precision_state: str,
) -> dict[str, Any]:
    reading = copy.deepcopy(base_reading)
    reading["reading_id"] = f"matrix-{stage}-{question}-{contact_status}-{emotional_risk}-{precision_state}"
    context = reading.setdefault("context", {})
    context["relationship_stage"] = stage
    context["main_question"] = question
    context["contact_status"] = contact_status
    context["desired_outcome"] = desired_outcome_for(question)
    context["emotional_risk"] = emotional_risk
    context["timing_scan_days"] = 0

    if precision_state == "missing_city":
        reading["person_a"]["birth_place"] = ""
        reading["person_b"]["birth_place"] = ""
    elif precision_state == "no_birth_time":
        reading["person_a"]["birth_time"] = None
        reading["person_b"]["birth_time"] = None
    return reading


def build_vm(reading: dict[str, Any]) -> dict[str, Any]:
    payload = build_payload(reading, include_drafts=True, select=True)
    view_model = build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)
    rendered = json.dumps(view_model, ensure_ascii=False).lower()
    for term in LEGACY_TERMS:
        assert_true(term.lower() not in rendered, f"legacy BaZi term leaked into matrix view model: {term}")
    return view_model


def case_file(view_model: dict[str, Any]) -> dict[str, Any]:
    case = view_model.get("westernRelationshipCaseFile")
    assert_true(isinstance(case, dict), "westernRelationshipCaseFile missing")
    return case


def cluster_claim_ids(cluster: dict[str, Any]) -> set[str]:
    claim_ids = {str(claim_id) for claim_id in cluster.get("claimIds") or [] if claim_id}
    for support in cluster.get("claimSupport") or []:
        if isinstance(support, dict):
            claim_id = support.get("claimId") or support.get("claim_id")
            if claim_id:
                claim_ids.add(str(claim_id))
    return claim_ids


def assert_house_angle_precision_gate(case: dict[str, Any], expected_status: str) -> None:
    clusters = case.get("evidenceClusters") or {}
    gates = [
        (clusters.get("birthDataQuality") or {}).get("houseAnglePrecisionGate") or {},
        (clusters.get("angleHouseFramework") or {}).get("houseAnglePrecisionGate") or {},
        (clusters.get("houseRelationshipFactors") or {}).get("houseAnglePrecisionGate") or {},
        (case.get("houseOverlayLayer") or {}).get("precisionGate") or {},
    ]
    for gate in gates:
        assert_true(gate.get("version") == "house-angle-precision-gate-v1", "house/angle precision gate version missing")
        assert_true(gate.get("status") == expected_status, f"house/angle precision gate status mismatch: {gate}")
        assert_true(gate.get("canCreateAstrologyConclusion") is False, "house/angle gate must not create conclusions")
        assert_true(gate.get("requiresCalculatedHouseOrAngleEvidence") is True, "house/angle gate must require calculated evidence")
        assert_true("western-houses-angles-foundation-004" in set(gate.get("sourceClaimIds") or []), "Hand house/angle gate claim missing")
        if expected_status == "allowed_by_precision":
            assert_true(gate.get("allowsAngles") is True, "full precision should allow angles")
            assert_true(gate.get("allowsNatalHouses") is True, "full precision should allow natal houses")
        else:
            assert_true(gate.get("allowsAngles") is False, "limited precision should block angles")
            assert_true("house_overlays" in set(gate.get("blockedClaims") or []), "limited precision should block overlays")


def assert_contact_action_boundary_trace(contact_policy: dict[str, Any], expectation: dict[str, Any], contact_status: str) -> None:
    boundary = contact_policy.get("contactActionBoundary") or {}
    assert_true(boundary.get("version") == "contact-action-boundary-v1", f"{contact_status}: contact action boundary trace missing")
    assert_true(boundary.get("statusKey") == contact_status, f"{contact_status}: boundary status mismatch")
    assert_true(boundary.get("actionScale") == expectation["actionScale"], f"{contact_status}: boundary action scale mismatch")
    assert_true(boundary.get("actionMode") == expectation["actionMode"], f"{contact_status}: boundary action mode mismatch")
    assert_true(
        boundary.get("canSuggestDirectContact") is expectation["canSuggestDirectContact"],
        f"{contact_status}: boundary direct-contact permission mismatch",
    )
    assert_true(boundary.get("requiresCalculationSupport") is True, f"{contact_status}: boundary must require calculation support")
    assert_true(boundary.get("timingCanOverrideBoundary") is False, f"{contact_status}: timing must not override boundary trace")
    assert_true(boundary.get("canCreateAstrologyConclusion") is False, f"{contact_status}: contact boundary must not create conclusions")
    assert_true(boundary.get("canOverrideRealWorldBoundary") is False, f"{contact_status}: contact boundary must not override real boundary")
    assert_true(expectation["expectedClaim"] in set(boundary.get("sourceClaimIds") or []), f"{contact_status}: boundary source claim missing")
    assert_true(expectation["expectedMethodClaim"] in set(boundary.get("methodClaimIds") or []), f"{contact_status}: boundary method claim missing")
    if contact_status == "blocked":
        assert_true(boundary.get("isHardBoundary") is True, "blocked: boundary should be hard")
        assert_true(boundary.get("canSuggestDirectContact") is False, "blocked: direct contact should be false")
        for action in ("alternate_account_contact", "third_party_pressure", "repeated_messages"):
            assert_true(action in set(boundary.get("blockedActions") or []), f"blocked: boundary missing {action}")
    if contact_status == "no-contact":
        assert_true(boundary.get("isHardBoundary") is False, "no-contact: boundary should not be hard")
        assert_true(boundary.get("isLowStimulationOnly") is True, "no-contact: should be low-stimulation only")
        assert_true(boundary.get("requiresEasyExit") is True, "no-contact: should require easy exit")
        for action in ("long_explanation", "asking_for_answer_now", "repeated_messages"):
            assert_true(action in set(boundary.get("blockedActions") or []), f"no-contact: boundary missing {action}")


def assert_relationship_profiles(view_model: dict[str, Any], precision_state: str) -> None:
    profiles = view_model.get("relationshipProfiles") or {}
    assert_true(profiles.get("version") == "relationship-profiles-v1", "relationshipProfiles version mismatch")
    for person_key in ("personA", "personB"):
        cards = (profiles.get(person_key) or {}).get("cards") or []
        assert_true(len(cards) >= 5, f"{person_key} profile cards missing")
        for card in cards:
            readable = card.get("readableInterpretation") or {}
            assert_true(readable.get("module") == "person_function_sign", f"{person_key} readable card module mismatch")
            assert_true(readable.get("body"), f"{person_key} readable card body missing")
            assert_true(readable.get("stuckPattern"), f"{person_key} readable card stuckPattern missing")
    fit = profiles.get("fitSummary") or {}
    fit_readable = fit.get("readableInterpretation") or {}
    assert_true(fit_readable.get("module") == "fit_summary", "profile fit readable module mismatch")
    fit_summary_copy = " ".join(
        str(value or "")
        for value in (
            profiles.get("principle"),
            fit.get("summary"),
            fit_readable.get("headline"),
            fit_readable.get("body"),
        )
    )
    assert_true("需要翻譯" not in fit_summary_copy, "profile fit summary still uses internal wording")
    assert_true("需要更多翻譯" not in fit_summary_copy, "profile fit headline still uses awkward wording")
    assert_true("壓力反應容易誤會" not in fit_summary_copy, "profile fit summary still uses awkward pressure wording")
    for bucket in ("natural", "effort", "friction"):
        for item in fit.get(bucket) or []:
            item_readable = item.get("readableInterpretation") or {}
            assert_true(item_readable.get("module") == "fit_summary_item", f"{bucket} readable fit item module mismatch")
            body = str(item_readable.get("body") or "")
            assert_true("你比較用" not in body, f"{bucket} readable fit item still uses translated formula")
            assert_true("處理界線與壓力" not in body, f"{bucket} readable fit item has awkward Saturn translation")
            assert_true("這一項比較容易互相懂" not in body, f"{bucket} readable fit item still uses old literal wording")
            assert_true("對話和空間處理" not in body, f"{bucket} readable fit item still uses awkward Air formula")
            assert_true("土星這一塊" not in body, f"{bucket} readable fit item still starts from astrology label")
            assert_true("壓力反應容易誤會" not in body, f"{bucket} readable fit item still uses awkward pressure wording")
            assert_true(item.get("relationLabel") != "需要翻譯", f"{bucket} readable fit item relation label still uses internal wording")
            assert_true("需要翻譯" not in str(item.get("title") or ""), f"{bucket} readable fit item title still uses internal wording")
            assert_true("翻譯清楚" not in str(item.get("nextMove") or ""), f"{bucket} readable fit item nextMove still uses awkward translation copy")
            assert_true(item.get("nextMove"), f"{bucket} readable fit item nextMove missing")
    assert_true(fit.get("atomId") == "western-atom-element-comparison", "profile fit atom mismatch")
    assert_true(fit.get("claimSupport"), "profile fit claim support missing")
    assert_true(profiles.get("answerBridge"), "profile answer bridge missing")
    if precision_state != "full":
        assert_true(profiles.get("precisionWarnings"), "precision-limited profile warnings missing")


def assert_readable_question_answer(view_model: dict[str, Any]) -> None:
    assert_native_question_copy((view_model.get("reading") or {}).get("answer"), "reading answer")
    assert_question_copy_density(view_model)
    repeated_theme_key = str(((view_model.get("answerGuidance") or {}).get("relationshipTheme") or {}).get("themeKey") or "")
    metrics = view_model.get("metrics") or []
    if repeated_theme_key:
        assert_true(len(metrics) >= 4, "theme-derived metrics missing")
        assert_true(
            all(metric.get("themeKey") == repeated_theme_key for metric in metrics[:4]),
            f"metrics should carry dominant repeated theme {repeated_theme_key}: {metrics}",
        )
        generic_metric_labels = {"卡住程度", "關係條件"}
        assert_true(
            generic_metric_labels.isdisjoint({str(metric.get("label") or "") for metric in metrics[:4]}),
            f"theme-derived metrics should not keep generic labels: {metrics}",
        )
    for metric in view_model.get("metrics") or []:
        assert_native_question_copy(metric.get("label"), "metric label")
        assert_native_question_copy(metric.get("value"), "metric value")
        assert_native_question_copy(metric.get("helper"), "metric helper")
    rows = included_reading_rows(view_model)
    if repeated_theme_key:
        assert_true(len(rows) >= 3, "theme-derived included rows missing")
        assert_true(
            all(row.get("themeKey") == repeated_theme_key for row in rows[:3]),
            f"included rows should carry dominant repeated theme {repeated_theme_key}: {rows}",
        )
    for row in rows:
        assert_native_question_copy(row.get("title"), "included reading row title")
        for preview in row.get("preview") or []:
            assert_native_question_copy(preview, "included reading row preview")
    readable = view_model.get("readableQuestionAnswer") or {}
    assert_true(readable.get("version") == "readable-question-answer-v1", "readable question answer version missing")
    question_key = str((view_model.get("context") or {}).get("main_question") or "")
    assert_true(question_key in QUESTION_SELECTOR_METHOD_CLAIMS, f"unknown readable question key: {question_key}")
    assert_question_family_visible_marker(view_model, question_key)
    assert_primary_answer_question_marker(view_model, question_key)
    assert_normal_user_answer(view_model, question_key)
    assert_question_selector_trace(readable, question_key, "readable question answer")
    sections = readable.get("sections") or {}
    assert_true(sections.get("thoughts"), "readable thoughts missing")
    assert_true(sections.get("donts"), "readable boundaries missing")
    answer = sections.get("answer") or {}
    answer_guidance = view_model.get("answerGuidance") or {}
    answer_block = answer.get("readableInterpretation") or {}
    assert_true(answer.get("version") == "answer-guidance-v1", "readable answer guidance version missing")
    assert_true(answer_guidance.get("version") == "answer-guidance-v1", "top-level answer guidance missing")
    assert_question_selector_trace(answer, question_key, "readable answer guidance")
    assert_question_selector_trace(answer_guidance, question_key, "top-level answer guidance")
    assert_question_selector_trace(answer_block, question_key, "answer readable block")
    assert_true(answer_block.get("module") == "question_answer", "readable answer module mismatch")
    assert_true(answer_block.get("headline"), "readable answer headline missing")
    assert_true(answer_block.get("body"), "readable answer body missing")
    assert_true(answer_block.get("nextMove"), "readable answer nextMove missing")
    assert_native_question_copy(answer_block.get("headline"), "answer readable headline")
    assert_native_question_copy(answer_block.get("meaning"), "answer readable meaning")
    assert_native_question_copy(answer_block.get("body"), "answer readable body")
    assert_native_question_copy(answer_block.get("nextMove"), "answer readable nextMove")
    assert_native_question_copy(answer_block.get("caution"), "answer readable caution")
    assert_true(len(answer.get("evidenceHighlights") or []) >= 3, "answer evidence highlights missing")
    answer_copy = "\n".join(
        [
            *(str(answer_block.get(key) or "") for key in ("headline", "meaning", "body", "nextMove", "caution")),
            *(str(highlight.get(key) or "") for highlight in answer.get("evidenceHighlights") or [] for key in ("title", "body")),
        ]
    )
    for forbidden in ("免費", "付費", "完整報告", "付費報告", "reducer", "selector", "soft_tone", "boundary_only"):
        assert_true(forbidden not in answer_copy, f"answer readable leaked forbidden copy: {forbidden}")
    action = sections.get("action") or {}
    action_guidance = view_model.get("actionGuidance") or {}
    action_block = action.get("readableInterpretation") or {}
    assert_true(action, "readable action guidance missing")
    assert_true(action_guidance, "top-level action guidance missing")
    assert_question_selector_trace(action, question_key, "readable action guidance")
    assert_question_selector_trace(action_guidance, question_key, "top-level action guidance")
    assert_question_selector_trace(action_block, question_key, "action readable block")
    assert_true(action_block.get("module") == "question_action", "readable action module mismatch")
    assert_true(action_block.get("headline"), "readable action headline missing")
    assert_true(action_block.get("body"), "readable action body missing")
    assert_true(action_block.get("nextMove"), "readable action nextMove missing")
    assert_native_question_copy(action_block.get("headline"), "action readable headline")
    assert_native_question_copy(action_block.get("meaning"), "action readable meaning")
    assert_native_question_copy(action_block.get("body"), "action readable body")
    assert_native_question_copy(action_block.get("nextMove"), "action readable nextMove")
    assert_native_question_copy(action_block.get("caution"), "action readable caution")
    action_copy = "\n".join(
        str(action_block.get(key) or "")
        for key in ("headline", "meaning", "body", "nextMove", "caution")
    )
    assert_true("action_scale" not in action_copy, "action readable leaked action_scale")
    assert_true("boundary_only" not in action_copy, "action readable leaked boundary_only")
    assert_true("contactSituationPolicy" not in action_copy, "action readable leaked contact policy key")
    timing = sections.get("timing") or {}
    timing_guidance = view_model.get("timingGuidance") or {}
    timing_block = timing.get("readableInterpretation") or {}
    assert_true(timing, "readable timing guidance missing")
    assert_true(timing_guidance, "top-level timing guidance missing")
    assert_question_selector_trace(timing, question_key, "readable timing guidance")
    assert_question_selector_trace(timing_guidance, question_key, "top-level timing guidance")
    assert_question_selector_trace(timing_block, question_key, "timing readable block")
    assert_true(timing_block.get("module") == "question_timing", "readable timing module mismatch")
    assert_true(timing_block.get("headline"), "readable timing headline missing")
    assert_true(timing_block.get("body"), "readable timing body missing")
    assert_true(timing_block.get("nextMove"), "readable timing nextMove missing")
    assert_true(timing.get("preciseDatesAvailable") is False, "timing guidance should block precise dates")
    assert_native_question_copy(timing_block.get("headline"), "timing readable headline")
    assert_native_question_copy(timing_block.get("meaning"), "timing readable meaning")
    assert_native_question_copy(timing_block.get("body"), "timing readable body")
    assert_native_question_copy(timing_block.get("nextMove"), "timing readable nextMove")
    assert_native_question_copy(timing_block.get("caution"), "timing readable caution")
    for signal in timing.get("selectedSignals") or []:
        assert_native_question_copy(signal.get("title"), "timing signal title")
        assert_native_question_copy(signal.get("body"), "timing signal body")
    timing_copy = "\n".join(
        str(timing_block.get(key) or "")
        for key in ("headline", "meaning", "body", "nextMove", "caution")
    )
    assert_true("avoid_push" not in timing_copy, "timing readable leaked avoid_push")
    assert_true("low_pressure" not in timing_copy, "timing readable leaked low_pressure")
    assert_true("not_calculated" not in timing_copy, "timing readable leaked not_calculated")
    assert_true("timing" not in timing_copy.lower(), "timing readable leaked timing")
    for item in sections.get("thoughts") or []:
        assert_native_question_copy(item.get("body"), "thought body")
        assert_question_selector_trace(item, question_key, "thought item")
        block = item.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "thought readable block")
        assert_true(block.get("module") == "question_thought", "readable thought module mismatch")
        assert_native_question_copy(block.get("body"), "thought readable body")
        assert_native_question_copy(block.get("nextMove"), "thought nextMove")
        assert_true(block.get("nextMove"), "readable thought nextMove missing")
    for card in view_model.get("reasons") or []:
        assert_native_question_copy(card.get("body"), "reason body")
        assert_question_selector_trace(card, question_key, "reason card")
        block = card.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "reason readable block")
        assert_true(block.get("module") == "question_reason", "readable reason module mismatch")
        assert_native_question_copy(block.get("body"), "reason readable body")
        assert_native_question_copy(card.get("nextMove"), "reason nextMove")
        assert_true(card.get("nextMove"), "readable reason nextMove missing")
    if repeated_theme_key:
        reason_cards = view_model.get("reasons") or []
        assert_true(len(reason_cards) >= 3, "theme-derived reason cards missing")
        assert_true(
            all(card.get("themeKey") == repeated_theme_key for card in reason_cards[:3]),
            f"reason cards should follow dominant repeated theme {repeated_theme_key}: {reason_cards}",
        )
        assert_true(
            all(card.get("relationshipThemeLabel") for card in reason_cards[:3]),
            "theme-derived reason cards missing relationshipThemeLabel",
        )
    chance = view_model.get("chance") or {}
    sections_chance = sections.get("chance") or {}
    assert_question_selector_trace(chance, question_key, "chance payload")
    assert_question_selector_trace(sections_chance, question_key, "readable chance section")
    if repeated_theme_key:
        chance_theme = chance.get("relationshipTheme") or {}
        sections_chance_theme = sections_chance.get("relationshipTheme") or {}
        assert_true(
            chance_theme.get("themeKey") == repeated_theme_key,
            f"chance notes should follow dominant repeated theme {repeated_theme_key}: {chance_theme}",
        )
        assert_true(
            sections_chance_theme.get("themeKey") == repeated_theme_key,
            f"readable chance section should carry dominant repeated theme {repeated_theme_key}: {sections_chance_theme}",
        )
    for note in chance.get("notes") or []:
        assert_native_question_copy(note, "chance note")
    assert_true((chance.get("readableInterpretation") or {}).get("module") == "question_chance", "readable chance module mismatch")
    assert_question_selector_trace(chance.get("readableInterpretation") or {}, question_key, "chance readable block")
    assert_native_question_copy((chance.get("readableInterpretation") or {}).get("body"), "chance readable body")
    assert_native_question_copy(chance.get("nextMove"), "chance nextMove")
    assert_true(chance.get("nextMove"), "readable chance nextMove missing")
    timeline_steps = view_model.get("timeline") or []
    sections_timeline = sections.get("timeline") or []
    if repeated_theme_key:
        assert_true(len(timeline_steps) >= 3, "theme-derived timeline steps missing")
        assert_true(
            all(step.get("themeKey") == repeated_theme_key for step in timeline_steps[:3]),
            f"timeline should follow dominant repeated theme {repeated_theme_key}: {timeline_steps}",
        )
        assert_true(
            all(step.get("relationshipThemeLabel") for step in timeline_steps[:3]),
            "theme-derived timeline steps missing relationshipThemeLabel",
        )
        assert_true(
            all(step.get("themeKey") == repeated_theme_key for step in sections_timeline[:3]),
            f"readable timeline section should carry dominant repeated theme {repeated_theme_key}: {sections_timeline}",
        )
    for step in timeline_steps:
        assert_native_question_copy(step.get("body"), "timeline body")
        assert_question_selector_trace(step, question_key, "timeline step")
        block = step.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "timeline readable block")
        assert_true(block.get("module") == "question_timeline", "readable timeline module mismatch")
        assert_native_question_copy(block.get("body"), "timeline readable body")
        assert_native_question_copy(step.get("nextMove"), "timeline nextMove")
        assert_true(step.get("nextMove"), "readable timeline nextMove missing")
    boundary_items = sections.get("donts") or []
    if repeated_theme_key:
        assert_true(len(boundary_items) >= 3, "theme-derived boundary items missing")
        assert_true(
            all(item.get("themeKey") == repeated_theme_key for item in boundary_items[:3]),
            f"readable boundaries should carry dominant repeated theme {repeated_theme_key}: {boundary_items}",
        )
    for item in boundary_items:
        assert_native_question_copy(item.get("body"), "boundary body")
        assert_question_selector_trace(item, question_key, "boundary item")
        block = item.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "boundary readable block")
        assert_true(block.get("module") == "question_boundary", "readable boundary module mismatch")
        assert_native_question_copy(block.get("body"), "boundary readable body")


def readable_action_contract(view_model: dict[str, Any]) -> dict[str, Any]:
    readable = view_model.get("readableQuestionAnswer") or {}
    sections = readable.get("sections") or {}
    action = sections.get("action") or view_model.get("actionGuidance") or {}
    block = action.get("readableInterpretation") or {}
    assert_true(block.get("module") == "question_action", "contact-policy fixture action module mismatch")
    assert_true(block.get("headline"), "contact-policy fixture action headline missing")
    assert_true(block.get("body"), "contact-policy fixture action body missing")
    assert_true(block.get("nextMove"), "contact-policy fixture action nextMove missing")
    return block


def assert_contact_policy_fixture(base_reading: dict[str, Any], contact_status: str) -> None:
    expectation = CONTACT_POLICY_FIXTURES[contact_status]
    reading = build_matrix_reading(
        base_reading,
        stage="cold-war",
        question="when-to-contact",
        contact_status=contact_status,
        emotional_risk="calm",
        precision_state="full",
    )
    view_model = build_vm(reading)
    case = case_file(view_model)
    rule_id = str((case.get("answerLayer") or {}).get("ruleId") or "")
    assert_true(
        rule_id == expectation["expectedRule"],
        f"{contact_status}: expected {expectation['expectedRule']}, got {rule_id}",
    )

    clusters = case.get("evidenceClusters") or {}
    contact_status_cluster = clusters.get("contactStatus") or {}
    contact_status_claim_ids = cluster_claim_ids(contact_status_cluster)
    contact_policy = clusters.get("contactSituationPolicy") or {}
    contact_policy_claim_ids = cluster_claim_ids(contact_policy)
    assert_true(contact_policy.get("statusKey") == contact_status, f"{contact_status}: contact policy status mismatch")
    assert_true(contact_policy.get("actionScale") == expectation["actionScale"], f"{contact_status}: action scale mismatch")
    assert_true(contact_policy.get("actionMode") == expectation["actionMode"], f"{contact_status}: action mode mismatch")
    assert_true(
        contact_policy.get("canSuggestDirectContact") is expectation["canSuggestDirectContact"],
        f"{contact_status}: direct-contact permission mismatch",
    )
    assert_true(
        contact_policy.get("requiresEasyExit") is expectation["requiresEasyExit"],
        f"{contact_status}: easy-exit requirement mismatch",
    )
    assert_true(
        contact_policy.get("requiresSharedSpaceBoundary") is expectation["requiresSharedSpaceBoundary"],
        f"{contact_status}: shared-space boundary requirement mismatch",
    )
    assert_true(contact_policy.get("timingCanOverrideBoundary") is False, f"{contact_status}: timing override should stay blocked")
    assert_true(expectation["expectedMethodClaim"] in set(contact_policy.get("methodClaimIds") or []), f"{contact_status}: contact policy method claim missing")
    missing_method_claims = sorted(set(expectation["expectedMethodClaims"]) - set(contact_policy.get("methodClaimIds") or []))
    assert_true(not missing_method_claims, f"{contact_status}: contact policy missing method claims {missing_method_claims}")
    assert_contact_action_boundary_trace(contact_policy, expectation, contact_status)
    blocked_actions = {str(item) for item in contact_policy.get("blockedActions") or []}
    missing_actions = sorted(expectation["blockedActions"] - blocked_actions)
    assert_true(not missing_actions, f"{contact_status}: missing blocked actions {missing_actions}")
    expected_claim = str(expectation["expectedClaim"])
    assert_true(
        expected_claim in contact_status_claim_ids,
        f"{contact_status}: contactStatus missing state claim {expected_claim}",
    )
    assert_true(
        expected_claim in contact_policy_claim_ids,
        f"{contact_status}: contactSituationPolicy missing state claim {expected_claim}",
    )
    unexpected_status_claims = sorted((CONTACT_POLICY_STATE_CLAIMS - {expected_claim}) & contact_status_claim_ids)
    unexpected_policy_claims = sorted((CONTACT_POLICY_STATE_CLAIMS - {expected_claim}) & contact_policy_claim_ids)
    assert_true(not unexpected_status_claims, f"{contact_status}: contactStatus leaked state claims {unexpected_status_claims}")
    assert_true(not unexpected_policy_claims, f"{contact_status}: contactSituationPolicy leaked state claims {unexpected_policy_claims}")

    action_block = readable_action_contract(view_model)
    assert_true(action_block.get("headline") == expectation["headline"], f"{contact_status}: action headline mismatch")
    visible_action_copy = "\n".join(
        str(action_block.get(key) or "")
        for key in ("headline", "meaning", "body", "nextMove", "caution")
    )
    for phrase in expectation["copyIncludes"]:
        assert_true(phrase in visible_action_copy, f"{contact_status}: action copy missing {phrase}")
    for phrase in CONTACT_POLICY_FORBIDDEN_COPY:
        assert_true(phrase not in visible_action_copy, f"{contact_status}: unsafe action copy leaked {phrase}")

    timing = (((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("timing") or {})
    timing_block = timing.get("readableInterpretation") or {}
    timing_guidance = view_model.get("timingGuidance") or {}
    assert_true(timing_guidance.get("preciseDatesAvailable") is False, f"{contact_status}: timing should block precise dates")
    assert_true(
        timing_guidance.get("recommendedAction") == "not_calculated",
        f"{contact_status}: disabled timing scan should not produce a contact action",
    )
    assert_true(
        "精準聯絡日" in str(timing_block.get("caution") or ""),
        f"{contact_status}: timing caution should block precise contact dates",
    )


def run_contact_policy_contract_checks() -> None:
    base = read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json")
    for contact_status in CONTACT_STATUSES:
        assert_contact_policy_fixture(base, contact_status)


def chapter_sources(view_model: dict[str, Any], chapter_id: str) -> set[str]:
    blueprint = view_model.get("readingBlueprint") or {}
    assert_true(len(blueprint.get("chapters") or []) == 3, "readingBlueprint.chapters alias missing")
    assert_true(len(view_model.get("includedReadingRows") or []) >= 4, "includedReadingRows alias missing")
    for chapter in blueprint_chapters(blueprint):
        assert_true(bool(chapter.get("methodBoundary")), f"{chapter.get('id')}: methodBoundary missing")
        if chapter.get("id") == chapter_id:
            return {str(item.get("source") or "") for item in chapter.get("evidence") or []}
    return set()


def assert_method_blueprint(view_model: dict[str, Any]) -> None:
    blueprint = view_model.get("readingBlueprint") or {}
    assert_true(blueprint.get("chapterOrder") == ["thoughts", "reasons", "chance"], "free chapter order changed")
    assert_true(THOUGHTS_SOURCES.issubset(chapter_sources(view_model, "thoughts")), "thoughts chapter missing Suskin method sources")
    assert_true(REASONS_SOURCES.issubset(chapter_sources(view_model, "reasons")), "reasons chapter missing Suskin comparison/aspect sources")
    assert_true(CHANCE_SOURCES.issubset(chapter_sources(view_model, "chance")), "chance chapter missing safety/relationship-chart boundary sources")


def assert_paid_v1_method_trace(case: dict[str, Any]) -> None:
    trace = case.get("methodTrace") or {}
    assert_true(trace.get("version") == "western-method-trace-v1", "paid V1 method trace missing")
    sections = {
        str(section.get("sectionId") or ""): section
        for section in trace.get("sections") or []
    }
    for section_id, required_claims in REQUIRED_METHOD_TRACE_CLAIMS.items():
        section = sections.get(section_id) or {}
        assert_true(section.get("status") == "covered", f"{section_id}: method trace not covered")
        method_claims = {str(claim_id) for claim_id in section.get("methodClaimIds") or []}
        missing_claims = sorted(required_claims - method_claims)
        assert_true(not missing_claims, f"{section_id}: method trace missing deeper digestion claims {missing_claims}")


def assert_clusters(case: dict[str, Any], reading: dict[str, Any], view_model: dict[str, Any], precision_state: str) -> None:
    clusters = case.get("evidenceClusters") or {}
    for key in [*REQUIRED_CONTEXT_CLUSTERS, *REQUIRED_SUSKIN_CLUSTERS, *REQUIRED_HAND_FUNCTION_CLUSTERS, *REQUIRED_TIMING_SELECTOR_CLUSTERS]:
        assert_true(clusters.get(key, {}).get("atomId"), f"{key} atom missing")

    answer_contract = (case.get("answerLayer") or {}).get("evidenceContract") or {}
    context_modifier = answer_contract.get("contextModifier") or {}
    assert_true(context_modifier.get("role") == "action_modifier_only", "context modifier role should be action-only")
    assert_true(context_modifier.get("canCreateAstrologyConclusion") is False, "context must not create astrology conclusions")
    assert_true(context_modifier.get("requiresCalculationEvidenceForConclusion") is True, "context should require calculation evidence")
    assert_true(context_modifier.get("requiresTransitEvidenceForTimingAction") is True, "timing action should require transit evidence")
    assert_true(
        "western-consultation-ethics-006" in set(context_modifier.get("sourceClaimIds") or []),
        "context modifier should cite context-not-conclusion claim",
    )
    assert_true(
        "western-consultation-ethics-007" in set(context_modifier.get("sourceClaimIds") or []),
        "context modifier should cite context evidence boundary claim",
    )
    assert_true(
        "valley-context-modifies-action-not-conclusion" in set(context_modifier.get("methodClaimIds") or []),
        "context modifier should cite context-not-conclusion method claim",
    )
    assert_true(
        "valley-context-boundary-trace-not-evidence" in set(context_modifier.get("methodClaimIds") or []),
        "context modifier should cite boundary-trace-not-evidence method claim",
    )
    context_boundary = context_modifier.get("contextEvidenceBoundary") or {}
    assert_true(context_boundary.get("version") == "context-evidence-boundary-v1", "context evidence boundary missing")
    assert_true(
        context_boundary.get("role") == "action_framing_tone_modifier_only",
        "context evidence boundary role mismatch",
    )
    assert_true(
        context_boundary.get("canCreateAstrologyConclusion") is False,
        "context evidence boundary must not create astrology conclusions",
    )
    assert_true(
        context_boundary.get("requiresCalculationEvidenceForConclusion") is True,
        "context evidence boundary should require calculation evidence",
    )
    assert_true(
        context_boundary.get("requiresTransitEvidenceForTimingAction") is True,
        "context evidence boundary should require transit evidence for timing action",
    )
    blocked_evidence = set(context_boundary.get("cannotSatisfyEvidenceFor") or [])
    for blocked_key in ("synastry_conclusion", "timing_action", "compatibility_claim", "third_party_inner_state"):
        assert_true(blocked_key in blocked_evidence, f"context boundary should block {blocked_key}")
    assert_true(
        "western-consultation-ethics-007" in set(context_boundary.get("sourceClaimIds") or []),
        "context evidence boundary source claim missing",
    )
    assert_true(
        "valley-context-modifies-action-not-conclusion" in set(context_boundary.get("methodClaimIds") or []),
        "context evidence boundary method claim missing",
    )
    assert_true(
        "valley-context-boundary-trace-not-evidence" in set(context_boundary.get("methodClaimIds") or []),
        "context evidence boundary trace method claim missing",
    )

    context = reading.get("context") or {}
    assert_true(clusters["relationshipStage"].get("stageKey") == context.get("relationship_stage"), "stage cluster mismatch")
    assert_true(clusters["contactStatus"].get("statusKey") == context.get("contact_status"), "contact cluster mismatch")
    contact_policy = clusters["contactSituationPolicy"]
    contact_status = context.get("contact_status")
    assert_true(contact_policy.get("statusKey") == contact_status, "contact policy cluster mismatch")
    assert_true(contact_policy.get("claimSupport"), "contact policy claim support missing")
    assert_true(contact_policy.get("timingCanOverrideBoundary") is False, "contact policy should block timing override")
    expectation = CONTACT_POLICY_FIXTURES[contact_status]
    expected_contact_claim = str(expectation["expectedClaim"])
    contact_status_claim_ids = cluster_claim_ids(clusters["contactStatus"])
    contact_policy_claim_ids = cluster_claim_ids(contact_policy)
    assert_true(
        expected_contact_claim in contact_status_claim_ids,
        f"{contact_status}: contactStatus missing state claim {expected_contact_claim}",
    )
    assert_true(
        expected_contact_claim in contact_policy_claim_ids,
        f"{contact_status}: contact policy missing state claim {expected_contact_claim}",
    )
    unexpected_status_claims = sorted((CONTACT_POLICY_STATE_CLAIMS - {expected_contact_claim}) & contact_status_claim_ids)
    unexpected_policy_claims = sorted((CONTACT_POLICY_STATE_CLAIMS - {expected_contact_claim}) & contact_policy_claim_ids)
    assert_true(not unexpected_status_claims, f"{contact_status}: contactStatus leaked state claims {unexpected_status_claims}")
    assert_true(not unexpected_policy_claims, f"{contact_status}: contact policy leaked state claims {unexpected_policy_claims}")
    assert_true(expectation["expectedMethodClaim"] in set(contact_policy.get("methodClaimIds") or []), f"{contact_status}: contact policy method claim missing")
    missing_method_claims = sorted(set(expectation["expectedMethodClaims"]) - set(contact_policy.get("methodClaimIds") or []))
    assert_true(not missing_method_claims, f"{contact_status}: contact policy missing method claims {missing_method_claims}")
    assert_contact_action_boundary_trace(contact_policy, expectation, contact_status)
    if contact_status == "blocked":
        assert_true(contact_policy.get("actionScale") == 0, "blocked contact policy should force action scale zero")
        assert_true(contact_policy.get("canSuggestDirectContact") is False, "blocked contact should not suggest direct contact")
    elif contact_status == "no-contact":
        assert_true(contact_policy.get("actionScale") == 1, "no-contact policy should lower action scale")
        assert_true(contact_policy.get("requiresEasyExit") is True, "no-contact policy should require easy exit")
    elif contact_status == "occasional-contact":
        assert_true(contact_policy.get("actionScale") == 2, "occasional-contact policy action scale mismatch")
        assert_true(contact_policy.get("actionMode") == "small_bid_response_led", "occasional-contact policy mode mismatch")
    elif contact_status == "still-in-contact":
        assert_true(contact_policy.get("actionScale") == 3, "still-in-contact policy action scale mismatch")
        assert_true(contact_policy.get("actionMode") == "tone_repair_in_existing_channel", "still-in-contact policy mode mismatch")
    elif contact_status == "living-or-working-together":
        assert_true(contact_policy.get("actionMode") == "shared_space_boundary", "shared-space policy mode mismatch")
        assert_true(contact_policy.get("requiresSharedSpaceBoundary") is True, "shared-space policy should preserve boundary")
    assert_true(clusters["emotionalRisk"].get("riskKey") == context.get("emotional_risk"), "risk cluster mismatch")
    assert_true(clusters["desiredOutcome"].get("outcomeKey") == context.get("desired_outcome"), "outcome cluster mismatch")
    assert_true(clusters["methodOrder"].get("hasNatalBeforeSynastry") is True, "method order should enforce natal before synastry")
    assert_true(clusters["aspectPriority"].get("hasDirectionality") is True, "aspect priority should preserve directionality")
    assert_true(clusters["relationshipChartLayer"].get("itemCount") == 0, "relationship chart layer should stay deferred")
    consultation_safety = clusters["consultationSafety"]
    consultation_claim_ids = cluster_claim_ids(consultation_safety)
    assert_true(consultation_safety.get("hasPrivacyBoundary") is True, "consultation safety privacy boundary missing")
    assert_true(consultation_safety.get("limitsThirdPartyInnerState") is True, "third-party inner-state boundary missing")
    assert_true(consultation_safety.get("preservesClientAgency") is True, "client agency boundary missing")
    assert_true(consultation_safety.get("blocksAbsolutePrediction") is True, "absolute prediction block missing")
    assert_true(
        "western-consultation-ethics-004" in consultation_claim_ids,
        "consultation safety missing third-party source claim",
    )
    assert_true(
        "western-consultation-ethics-005" in consultation_claim_ids,
        "consultation safety missing client-agency source claim",
    )
    assert_true(
        "western-consultation-ethics-006" in consultation_claim_ids,
        "consultation safety missing context-not-conclusion source claim",
    )
    assert_true(
        "absent_person_confession" in set(consultation_safety.get("blockedInterpretationClaims") or []),
        "absent-person confession block missing",
    )
    assert_true(
        "fear_based_instruction" in set(consultation_safety.get("blockedActionClaims") or []),
        "fear-based action block missing",
    )
    nonfatal_safety = clusters["nonfatalSynastrySafety"]
    assert_true(nonfatal_safety.get("atomId") == "western-atom-nonfatal-synastry-safety", "nonfatal synastry atom missing")
    assert_true(nonfatal_safety.get("source") == "western-modern-nonfatal-synastry", "nonfatal synastry source mismatch")
    assert_true(nonfatal_safety.get("claimSupport"), "nonfatal synastry claim support missing")
    assert_true(nonfatal_safety.get("hasNoGuaranteedOutcome") is True, "nonfatal synastry outcome policy missing")
    assert_true(nonfatal_safety.get("hardAspectsArePressureNotVerdict") is True, "hard-aspect nonfatal policy missing")
    assert_true(nonfatal_safety.get("requiresConditionalConclusion") is True, "conditional conclusion policy missing")
    assert_true("guaranteed_reunion" in set(nonfatal_safety.get("blockedOutcomeClaims") or []), "guaranteed reunion block missing")
    assert_true(clusters["moonSignEmotionalSafety"].get("point") == "Moon", "moon sign function cluster mismatch")
    assert_true(clusters["mercurySignCommunicationRepair"].get("point") == "Mercury", "mercury sign function cluster mismatch")
    assert_true(clusters["venusSignAffectionStyle"].get("point") == "Venus", "venus sign function cluster mismatch")
    assert_true(clusters["marsSignPursuitConflict"].get("point") == "Mars", "mars sign function cluster mismatch")
    assert_true(clusters["saturnSignDefenseDelay"].get("point") == "Saturn", "saturn sign function cluster mismatch")
    assert_true(
        SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(set(clusters["saturnSignDefenseDelay"].get("claimIds") or [])),
        "saturn sign function Greene source claims missing",
    )
    assert_saturn_process_boundary(clusters["saturnSignDefenseDelay"], "saturnSignDefenseDelay")
    assert_true(clusters["functionElementMatrix"].get("itemCount") >= 8, "function element matrix too thin")
    assert_true(clusters["functionModalityMatrix"].get("itemCount") >= 8, "function modality matrix too thin")
    assert_true(clusters["functionElementMatrix"].get("selectedElements"), "function element selections missing")
    assert_true(clusters["functionModalityMatrix"].get("selectedModalities"), "function modality selections missing")
    assert_true(clusters["aspectFunctionCombination"].get("source") == "western-aspect-function-combination-reducers", "aspect function combination source mismatch")
    assert_true(clusters["aspectFunctionCombination"].get("selectedCombinations"), "aspect function combinations missing")
    assert_true(
        (clusters["aspectFunctionCombination"].get("repeatedThemeReducer") or {}).get("version") == "repeated-theme-reducer-v1",
        "aspect function combination repeated-theme reducer missing",
    )
    assert_true(
        "burk-repeated-themes-outweigh-single-contacts"
        in set((clusters["aspectFunctionCombination"].get("repeatedThemeReducer") or {}).get("methodClaimIds") or []),
        "aspect function combination repeated-theme method claim missing",
    )
    assert_true(
        all((item.get("functionSynthesis") and len(item.get("pointStyles") or []) == 2) for item in clusters["aspectFunctionCombination"].get("selectedCombinations") or []),
        "aspect function combinations must include synthesis and point styles",
    )
    repeated_theme_key = str((clusters["aspectFunctionCombination"].get("repeatedThemeReducer") or {}).get("dominantRepeatedThemeKey") or "")
    if repeated_theme_key:
        answer_theme = ((case.get("answerLayer") or {}).get("repeatedThemeContext") or {})
        assert_true(answer_theme.get("themeKey") == repeated_theme_key, "answer layer repeated-theme context mismatch")
        for section_key in ("answerGuidance", "timingGuidance", "actionGuidance"):
            section_theme = ((view_model.get(section_key) or {}).get("relationshipTheme") or {})
            assert_true(
                section_theme.get("themeKey") == repeated_theme_key,
                f"{section_key} repeated-theme context mismatch: {section_theme}",
            )
        assert_true(
            repeated_theme_key
            == (((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("action") or {}).get("relationshipTheme", {}).get("themeKey"),
            "readable question action repeated-theme context mismatch",
        )
    assert_true((case.get("timingLayer") or {}).get("windowScan", {}).get("status") == "not_calculated", "context matrix should disable 60-day timing scan")
    assert_saturn_process_boundary(clusters["timingSaturnPressure"], "timingSaturnPressure")
    assert_true(clusters["timingContactReducer"].get("recommendedAction") == "not_calculated", "disabled timing scan should not invent contact timing action")
    assert_exact_timing_policy(clusters["timingContactReducer"], "timing contact reducer")

    quality = case.get("inputQuality") or {}
    if precision_state == "full":
        assert_house_angle_precision_gate(case, "allowed_by_precision")
        assert_true(quality.get("overall") == "high", "full precision matrix case should be high")
        assert_true(clusters["ascendantImpression"].get("itemCount") == 2, "full precision should allow Asc impressions")
        assert_true(clusters["houseRelationshipFactors"].get("itemCount", 0) > 0, "full precision should allow natal house factors")
    elif precision_state == "missing_city":
        assert_house_angle_precision_gate(case, "blocked_by_location")
        assert_true(quality.get("personA", {}).get("precision") == "location_fallback", "personA should use location_fallback")
        assert_true(quality.get("personB", {}).get("precision") == "location_fallback", "personB should use location_fallback")
        assert_true(clusters["ascendantImpression"].get("blockedCount") == 1, "missing city should block Asc impressions")
        assert_true(clusters["houseRelationshipFactors"].get("blockedCount") == 1, "missing city should block house factors")
    elif precision_state == "no_birth_time":
        assert_house_angle_precision_gate(case, "blocked_by_birth_time")
        assert_true(quality.get("personA", {}).get("precision") == "date_only", "personA should be date_only")
        assert_true(quality.get("personB", {}).get("precision") == "date_only", "personB should be date_only")
        assert_true(clusters["ascendantImpression"].get("blockedCount") == 1, "missing time should block Asc impressions")
        assert_true(clusters["houseRelationshipFactors"].get("blockedCount") == 1, "missing time should block house factors")


def assert_no_fallback(case: dict[str, Any]) -> str:
    rule_id = str((case.get("answerLayer") or {}).get("ruleId") or "")
    assert_true(rule_id, "matrix case did not select a reducer rule")
    assert_true(not rule_id.endswith("-fallback"), f"matrix case selected fallback rule: {rule_id}")
    return rule_id


def assert_target_rule(
    base_reading: dict[str, Any],
    *,
    stage: str,
    question: str,
    contact_status: str,
    emotional_risk: str,
    precision_state: str = "full",
    expected_rule: str,
) -> None:
    reading = build_matrix_reading(
        base_reading,
        stage=stage,
        question=question,
        contact_status=contact_status,
        emotional_risk=emotional_risk,
        precision_state=precision_state,
    )
    view_model = build_vm(reading)
    rule_id = str((case_file(view_model).get("answerLayer") or {}).get("ruleId") or "")
    assert_true(rule_id == expected_rule, f"expected {expected_rule}, got {rule_id}")


def run_matrix() -> Counter[str]:
    base = read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json")
    rule_counter: Counter[str] = Counter()
    generated = 0
    for stage_index, stage in enumerate(STAGES):
        for question_index, question in enumerate(QUESTIONS):
            for contact_index, contact_status in enumerate(CONTACT_STATUSES):
                emotional_risk = EMOTIONAL_RISKS[(stage_index + question_index + contact_index) % len(EMOTIONAL_RISKS)]
                precision_state = PRECISION_STATES[(stage_index + question_index + contact_index) % len(PRECISION_STATES)]
                reading = build_matrix_reading(
                    base,
                    stage=stage,
                    question=question,
                    contact_status=contact_status,
                    emotional_risk=emotional_risk,
                    precision_state=precision_state,
                )
                view_model = build_vm(reading)
                case = case_file(view_model)
                assert_clusters(case, reading, view_model, precision_state)
                assert_paid_v1_method_trace(case)
                assert_relationship_profiles(view_model, precision_state)
                assert_readable_question_answer(view_model)
                assert_method_blueprint(view_model)
                rule_counter[assert_no_fallback(case)] += 1
                generated += 1

    assert_true(generated == len(STAGES) * len(QUESTIONS) * len(CONTACT_STATUSES), "matrix count mismatch")
    return rule_counter


def run_targeted_rule_checks() -> None:
    base = read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json")
    friction = read_json(ROOT / "examples" / "readings" / "broke-up-long-any-chance.json")
    assert_target_rule(
        base,
        stage="cold-war",
        question="still-love-me",
        contact_status="still-in-contact",
        emotional_risk="calm",
        expected_rule="western-rule-still-love-live-contact-mixed-signals",
    )
    assert_target_rule(
        base,
        stage="cold-war",
        question="any-chance",
        contact_status="occasional-contact",
        emotional_risk="calm",
        expected_rule="western-rule-any-chance-occasional-contact-repair",
    )
    assert_target_rule(
        base,
        stage="crisis",
        question="any-chance",
        contact_status="living-or-working-together",
        emotional_risk="calm",
        expected_rule="western-rule-any-chance-live-contact-pressure",
    )
    assert_target_rule(
        base,
        stage="cold-war",
        question="when-to-contact",
        contact_status="occasional-contact",
        emotional_risk="desperate",
        expected_rule="western-rule-when-to-contact-soft-tone-safety",
    )
    assert_target_rule(
        base,
        stage="cold-war",
        question="when-to-contact",
        contact_status="occasional-contact",
        emotional_risk="calm",
        expected_rule="western-rule-when-to-contact-occasional-contact",
    )
    assert_target_rule(
        base,
        stage="cold-war",
        question="when-to-contact",
        contact_status="still-in-contact",
        emotional_risk="calm",
        expected_rule="western-rule-when-to-contact-still-in-contact-friction",
    )
    assert_target_rule(
        base,
        stage="crisis",
        question="when-to-contact",
        contact_status="living-or-working-together",
        emotional_risk="calm",
        expected_rule="western-rule-when-to-contact-shared-space-boundary",
    )
    assert_target_rule(
        friction,
        stage="broke-up-long",
        question="what-did-i-do-wrong",
        contact_status="no-contact",
        emotional_risk="calm",
        expected_rule="western-rule-what-wrong-safety-validation-language",
    )
    assert_target_rule(
        base,
        stage="cold-war",
        question="stay-or-let-go",
        contact_status="no-contact",
        emotional_risk="desperate",
        expected_rule="western-rule-stay-let-go-soft-tone-safety",
    )


def main() -> int:
    rule_counter = run_matrix()
    run_contact_policy_contract_checks()
    run_targeted_rule_checks()
    print("Western context matrix smoke passed")
    print(f"- generated scenarios: {len(STAGES) * len(QUESTIONS) * len(CONTACT_STATUSES)}")
    print("- selected rules:")
    for rule_id, count in rule_counter.most_common():
        print(f"  - {rule_id}: {count}")
    print(f"- contact policy fixture checks: {len(CONTACT_STATUSES)}")
    print("- targeted reducer checks: 9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
