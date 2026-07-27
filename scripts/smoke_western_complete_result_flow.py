#!/usr/bin/env python3
"""
Smoke-test the Western-only complete relationship reading contract.

This intentionally runs the same local bridge the API prototype uses:
ReadingInput -> calc_western_spike -> complete_relationship_result_runtime.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Iterable


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
ALL_CLAIM_IDS = {
    str(claim.get("claim_id") or claim.get("id") or "")
    for claims in CLAIMS_BY_ARTICLE.values()
    for claim in claims
}
LEGACY_KEYS = {"relationshipCaseFile", "baziCompatibilityDiagnosis", "bazi"}
LEGACY_TERMS = ("bazi", "八字", "配偶星", "日主", "四柱", "十神")
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
AWKWARD_PROFILE_COPY = (
    "這個功能的表達語氣",
    "功能的表達語氣",
    "這個功能",
    "Moon 的安全感",
    "Venus 的被重視",
    "Moon/Venus",
    "適合什麼",
    "不適合什麼",
)
REPETITIVE_QUESTION_COPY_LIMITS = {
    "壓力": 3,
    "節奏": 2,
    "防衛": 2,
    "牽動": 2,
}
PAIR_TEMPLATE_SOURCE_IDS = {
    "western-aspects-sun-venus",
    "western-aspects-moon-mars",
    "western-aspects-venus-venus",
    "western-aspects-mercury-jupiter",
    "western-aspects-moon-moon",
    "western-aspects-mars-mars",
    "western-aspects-mercury-sun",
    "western-aspects-sun-mars",
    "western-aspects-venus-mars",
    "western-aspects-moon-venus",
    "western-aspects-sun-moon",
    "western-aspects-moon-saturn",
    "western-aspects-venus-saturn",
    "western-aspects-mars-saturn",
    "western-aspects-sun-saturn",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_question_selector(answer: dict[str, Any], question_key: str) -> None:
    expected_claim_id = QUESTION_SELECTOR_METHOD_CLAIMS[question_key]
    answer_selector = answer.get("questionSelector") or {}
    assert_true(answer_selector.get("version") == "western-question-selector-v1", f"{question_key} answer selector missing")
    assert_true(answer_selector.get("questionKey") == question_key, f"{question_key} answer selector question mismatch")
    assert_true(
        expected_claim_id in set(answer.get("questionMethodClaimIds") or []),
        f"{question_key} answer missing selector method claim",
    )
    assert_true(
        expected_claim_id in set(answer_selector.get("methodClaimIds") or []),
        f"{question_key} answer selector missing method claim",
    )
    evidence_selector = ((answer.get("evidenceContract") or {}).get("questionSelector") or {})
    assert_true(evidence_selector.get("version") == "western-question-selector-v1", f"{question_key} evidence selector missing")
    assert_true(evidence_selector.get("questionKey") == question_key, f"{question_key} evidence selector question mismatch")
    assert_true(
        evidence_selector.get("role") == "evidence_weighting_policy",
        f"{question_key} evidence selector role mismatch",
    )
    assert_true(
        expected_claim_id in set(evidence_selector.get("methodClaimIds") or []),
        f"{question_key} evidence selector missing method claim",
    )
    assert_true(evidence_selector.get("evidenceClusterKeys"), f"{question_key} evidence selector missing cluster keys")


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
        assert_true(phrase not in value, f"{label} still contains awkward question copy: {phrase} / {value}")


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


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def build_vm(reading: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = build_payload(reading, include_drafts=True, select=True)
    view_model = build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)
    assert_no_legacy_contract_aliases(view_model)
    return payload, view_model


def assert_no_legacy_bazi_payload(payload: dict[str, Any], view_model: dict[str, Any]) -> None:
    for key in walk(payload):
        if isinstance(key, str):
            assert_true(key not in LEGACY_KEYS, f"legacy key leaked into calculation payload: {key}")
    for key in walk(view_model):
        if isinstance(key, str):
            assert_true(key not in LEGACY_KEYS, f"legacy key leaked into view model: {key}")

    rendered = json.dumps(view_model, ensure_ascii=False).lower()
    for term in LEGACY_TERMS:
        assert_true(term.lower() not in rendered, f"legacy BaZi term leaked into view model: {term}")


def assert_no_legacy_contract_aliases(view_model: dict[str, Any]) -> None:
    blueprint = view_model.get("readingBlueprint") or {}
    for key in ("freeChapters", "paidExpansionPlan", "lockedQuestions"):
        assert_true(key not in blueprint, f"legacy readingBlueprint alias should be absent: {key}")
    assert_true("lockedRows" not in view_model, "legacy lockedRows alias should be absent")
    forbidden_keys = {
        "freeChapters",
        "freeSummary",
        "lockedQuestions",
        "lockedRows",
        "paidBoundary",
        "paidDetailLocked",
        "paidExpansionPlan",
        "paidUnlock",
        "preciseDatesAvailableInFree",
    }
    for item in walk(view_model):
        if isinstance(item, dict):
            leaked = sorted(key for key in item if key in forbidden_keys)
            assert_true(not leaked, f"legacy complete-result contract key leaked: {', '.join(leaked)}")


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


def assert_house_angle_precision_gate(gate: dict[str, Any], expected_status: str, label: str) -> None:
    assert_true(gate.get("version") == "house-angle-precision-gate-v1", f"{label} precision gate version missing")
    assert_true(gate.get("status") == expected_status, f"{label} precision gate status mismatch: {gate}")
    assert_true(gate.get("role") == "precision_context_layer", f"{label} precision gate role mismatch")
    assert_true(gate.get("requiresReliableBirthTime") is True, f"{label} must require birth time")
    assert_true(gate.get("requiresReliableLocation") is True, f"{label} must require location")
    assert_true(gate.get("canCreateAstrologyConclusion") is False, f"{label} must not create conclusions")
    assert_true(gate.get("requiresCalculatedHouseOrAngleEvidence") is True, f"{label} must require calculated evidence")
    assert_true(gate.get("contextLayerOnly") is True, f"{label} must be contextual only")
    claim_ids = set(gate.get("sourceClaimIds") or [])
    assert_true("western-houses-angles-foundation-004" in claim_ids, f"{label} missing Hand house/angle gate claim")
    assert_true("western-precision-birth-data-quality-002" in claim_ids, f"{label} missing birth-time precision claim")
    assert_true("western-precision-birth-data-quality-003" in claim_ids, f"{label} missing location precision claim")
    if expected_status == "allowed_by_precision":
        assert_true(gate.get("allowsAngles") is True, f"{label} should allow angles")
        assert_true(gate.get("allowsNatalHouses") is True, f"{label} should allow natal houses")
        assert_true(gate.get("allowsHouseOverlaysByPrecision") is True, f"{label} should allow overlays by precision")
        assert_true(not gate.get("blockedClaims"), f"{label} should not block house/angle claims")
    else:
        assert_true(gate.get("allowsAngles") is False, f"{label} should block angles")
        assert_true(gate.get("allowsNatalHouses") is False, f"{label} should block natal houses")
        assert_true(gate.get("allowsHouseOverlaysByPrecision") is False, f"{label} should block overlays by precision")
        assert_true("house_overlays" in set(gate.get("blockedClaims") or []), f"{label} should block overlays")


def assert_case_house_angle_precision(case: dict[str, Any], expected_status: str) -> None:
    clusters = case.get("evidenceClusters") or {}
    for cluster_name in ("birthDataQuality", "angleHouseFramework", "houseRelationshipFactors"):
        gate = (clusters.get(cluster_name) or {}).get("houseAnglePrecisionGate") or {}
        assert_house_angle_precision_gate(gate, expected_status, cluster_name)
    overlay_gate = (case.get("houseOverlayLayer") or {}).get("precisionGate") or {}
    assert_house_angle_precision_gate(overlay_gate, expected_status, "houseOverlayLayer")
    if expected_status == "allowed_by_precision":
        assert_true(
            (case.get("houseOverlayLayer") or {}).get("status") == "not_available",
            "full precision should still declare house overlay engine unavailable",
        )
        assert_true(overlay_gate.get("houseOverlayCalculationAvailable") is False, "overlay calculation availability should be explicit")


def assert_contact_action_boundary_trace(
    contact_policy: dict[str, Any],
    *,
    status_key: str,
    expected_method_claim: str,
    expected_source_claim: str,
    expected_action_scale: int,
    expected_action_mode: str,
    can_suggest_direct_contact: bool,
) -> None:
    boundary = contact_policy.get("contactActionBoundary") or {}
    assert_true(boundary.get("version") == "contact-action-boundary-v1", f"{status_key} boundary trace missing")
    assert_true(boundary.get("statusKey") == status_key, f"{status_key} boundary status mismatch")
    assert_true(boundary.get("actionScale") == expected_action_scale, f"{status_key} boundary action scale mismatch")
    assert_true(boundary.get("actionMode") == expected_action_mode, f"{status_key} boundary action mode mismatch")
    assert_true(boundary.get("canSuggestDirectContact") is can_suggest_direct_contact, f"{status_key} boundary contact permission mismatch")
    assert_true(boundary.get("requiresCalculationSupport") is True, f"{status_key} boundary should require calculation support")
    assert_true(boundary.get("timingCanOverrideBoundary") is False, f"{status_key} timing should not override boundary")
    assert_true(boundary.get("canCreateAstrologyConclusion") is False, f"{status_key} boundary should not create astrology conclusions")
    assert_true(boundary.get("canOverrideRealWorldBoundary") is False, f"{status_key} boundary should not override real-world boundaries")
    assert_true(expected_source_claim in set(boundary.get("sourceClaimIds") or []), f"{status_key} boundary source claim missing")
    assert_true(expected_method_claim in set(boundary.get("methodClaimIds") or []), f"{status_key} boundary method claim missing")


def assert_relationship_profiles(view_model: dict[str, Any], *, precision_limited: bool = False) -> None:
    profiles = view_model.get("relationshipProfiles") or {}
    assert_true(profiles.get("version") == "relationship-profiles-v1", "relationshipProfiles version mismatch")
    assert_true(profiles.get("principle"), "relationshipProfiles principle missing")
    for person_key in ("personA", "personB"):
        person = profiles.get(person_key) or {}
        assert_true(person.get("headline"), f"{person_key} profile headline missing")
        assert_true(person.get("summary"), f"{person_key} profile summary missing")
        assert_true(len(person.get("cards") or []) >= 5, f"{person_key} profile cards missing")
        assert_true(person.get("suitableFor"), f"{person_key} suitableFor missing")
        assert_true(person.get("doesNotFit"), f"{person_key} doesNotFit missing")
        for card in person.get("cards") or []:
            assert_true(card.get("placement"), f"{person_key} profile placement missing")
            assert_true(card.get("suitableFor"), f"{person_key} profile suitableFor missing")
            assert_true(card.get("doesNotFit"), f"{person_key} profile doesNotFit missing")
            assert_true(card.get("relationshipUse"), f"{person_key} profile relationshipUse missing")
            readable = card.get("readableInterpretation") or {}
            assert_true(readable.get("version") == "readable-interpretation-v1", f"{person_key} readable card version missing")
            assert_true(readable.get("module") == "person_function_sign", f"{person_key} readable card module mismatch")
            assert_true(readable.get("meaning"), f"{person_key} readable card meaning missing")
            assert_true(readable.get("body"), f"{person_key} readable card body missing")
            assert_true(readable.get("stuckPattern"), f"{person_key} readable card stuckPattern missing")
            visible_copy = " ".join(
                str(value or "")
                for value in (
                    readable.get("meaning"),
                    readable.get("body"),
                    readable.get("stuckPattern"),
                    card.get("naturalResponse"),
                    card.get("tensionPattern"),
                )
            )
            for phrase in AWKWARD_PROFILE_COPY:
                assert_true(phrase not in visible_copy, f"{person_key} profile card still has awkward copy: {phrase}")
            assert_true("這張卡看的是" in str(readable.get("meaning") or ""), f"{person_key} profile meaning should explain card purpose")
            assert_true("落在" in str(readable.get("meaning") or ""), f"{person_key} profile meaning should explain sign placement")
            if person_key == "personB":
                assert_true("對方" not in str(readable.get("body") or ""), f"{person_key} body should use native pronoun copy")
                assert_true("對方" not in str(readable.get("stuckPattern") or ""), f"{person_key} stuck pattern should use native pronoun copy")
    fit = profiles.get("fitSummary") or {}
    assert_true(fit.get("headline"), "relationship profile fit headline missing")
    assert_true(fit.get("summary"), "relationship profile fit summary missing")
    safety_language = fit.get("safetyValidationLanguage") or {}
    assert_true(safety_language.get("category") == "safetyValidationLanguage", "safetyValidationLanguage cluster missing from fit summary")
    assert_true(safety_language.get("source") == "western-safety-validation-language", "safetyValidationLanguage source mismatch")
    assert_true(len(safety_language.get("pairs") or []) >= 4, "safetyValidationLanguage pair comparison missing")
    assert_true(
        "western-safety-validation-language-003" in (safety_language.get("claimIds") or []),
        "safetyValidationLanguage claim support missing",
    )
    fit_readable = fit.get("readableInterpretation") or {}
    assert_true(fit_readable.get("version") == "readable-interpretation-v1", "relationship profile fit readable version missing")
    assert_true(fit_readable.get("module") == "fit_summary", "relationship profile fit readable module mismatch")
    assert_true(fit_readable.get("body"), "relationship profile fit readable body missing")
    fit_summary_copy = " ".join(
        str(value or "")
        for value in (
            profiles.get("principle"),
            fit.get("summary"),
            fit_readable.get("headline"),
            fit_readable.get("body"),
        )
    )
    assert_true("需要翻譯" not in fit_summary_copy, "relationship profile fit summary still uses internal wording")
    assert_true("需要更多翻譯" not in fit_summary_copy, "relationship profile fit headline still uses awkward wording")
    assert_true("壓力反應容易誤會" not in fit_summary_copy, "relationship profile fit summary still uses awkward pressure wording")
    fit_count = sum(len(fit.get(key) or []) for key in ("natural", "effort", "friction"))
    assert_true(fit_count >= 3, "relationship profile fit items missing")
    assert_true(
        any(item.get("point") == "MoonVenus" for bucket in ("natural", "effort", "friction") for item in fit.get(bucket) or []),
        "Moon/Venus safety-validation fit item missing",
    )
    assert_true("safetyValidationLanguage" in (profiles.get("sourceClusters") or []), "safetyValidationLanguage source cluster missing")
    for bucket in ("natural", "effort", "friction"):
        for item in fit.get(bucket) or []:
            item_readable = item.get("readableInterpretation") or {}
            assert_true(item_readable.get("version") == "readable-interpretation-v1", f"{bucket} fit item readable version missing")
            assert_true(item_readable.get("module") == "fit_summary_item", f"{bucket} fit item readable module mismatch")
            assert_true(item_readable.get("body"), f"{bucket} fit item readable body missing")
            body = str(item_readable.get("body") or "")
            assert_true("你比較用" not in body, f"{bucket} fit item still uses translated formula: {body}")
            assert_true("處理界線與壓力" not in body, f"{bucket} fit item has awkward Saturn translation: {body}")
            assert_true("這一項比較容易互相懂" not in body, f"{bucket} fit item still uses old literal wording: {body}")
            assert_true("對話和空間處理" not in body, f"{bucket} fit item still uses awkward Air formula: {body}")
            assert_true("土星這一塊" not in body, f"{bucket} fit item still starts from astrology label: {body}")
            assert_true("壓力反應容易誤會" not in body, f"{bucket} fit item still uses awkward pressure wording: {body}")
            assert_true(item.get("relationLabel") != "需要翻譯", f"{bucket} fit item relation label still uses internal wording")
            assert_true("需要翻譯" not in str(item.get("title") or ""), f"{bucket} fit item title still uses internal wording")
            assert_true("翻譯清楚" not in str(item.get("nextMove") or ""), f"{bucket} fit item nextMove still uses awkward translation copy")
            assert_true(item.get("nextMove"), f"{bucket} fit item nextMove missing")
    assert_true(fit.get("atomId") == "western-atom-element-comparison", "relationship profile fit atom mismatch")
    assert_true(fit.get("claimSupport"), "relationship profile fit claim support missing")
    assert_true(profiles.get("answerBridge"), "relationship profile answer bridge missing")
    if precision_limited:
        assert_true(profiles.get("precisionWarnings"), "precision-limited profile should expose warnings")


def assert_readable_question_answer(view_model: dict[str, Any]) -> None:
    assert_native_question_copy((view_model.get("reading") or {}).get("answer"), "reading answer")
    assert_question_copy_density(view_model)
    for metric in view_model.get("metrics") or []:
        assert_native_question_copy(metric.get("label"), "metric label")
        assert_native_question_copy(metric.get("value"), "metric value")
        assert_native_question_copy(metric.get("helper"), "metric helper")
    for row in included_reading_rows(view_model):
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
    answer = sections.get("answer") or {}
    answer_guidance = view_model.get("answerGuidance") or {}
    answer_block = answer.get("readableInterpretation") or {}
    assert_true(answer.get("version") == "answer-guidance-v1", "readable answer guidance version missing")
    assert_true(answer_guidance.get("version") == "answer-guidance-v1", "top-level answer guidance missing")
    assert_question_selector_trace(answer, question_key, "readable answer guidance")
    assert_question_selector_trace(answer_guidance, question_key, "top-level answer guidance")
    assert_question_selector_trace(answer_block, question_key, "answer readable block")
    assert_true(answer_block.get("module") == "question_answer", "answer readable module mismatch")
    assert_true(answer_block.get("headline"), "answer readable headline missing")
    assert_true(answer_block.get("body"), "answer readable body missing")
    assert_true(answer_block.get("nextMove"), "answer readable nextMove missing")
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
    assert_true(action_block.get("module") == "question_action", "action readable module mismatch")
    assert_true(action_block.get("headline"), "action readable headline missing")
    assert_true(action_block.get("body"), "action readable body missing")
    assert_true(action_block.get("nextMove"), "action readable nextMove missing")
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
    assert_true(timing_block.get("module") == "question_timing", "timing readable module mismatch")
    assert_true(timing_block.get("headline"), "timing readable headline missing")
    assert_true(timing_block.get("body"), "timing readable body missing")
    assert_true(timing_block.get("nextMove"), "timing readable nextMove missing")
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
    thoughts = sections.get("thoughts") or []
    assert_true(len(thoughts) == len(view_model.get("thoughts") or []), "readable thought count mismatch")
    for item in thoughts:
        assert_native_question_copy(item.get("body"), "thought body")
        assert_question_selector_trace(item, question_key, "thought item")
        block = item.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "thought readable block")
        assert_true(block.get("module") == "question_thought", "thought readable module mismatch")
        assert_true(block.get("body"), "thought readable body missing")
        assert_native_question_copy(block.get("body"), "thought readable body")
        assert_native_question_copy(block.get("nextMove"), "thought nextMove")
        assert_true(block.get("nextMove"), "thought readable nextMove missing")
    for card in view_model.get("reasons") or []:
        assert_native_question_copy(card.get("body"), "reason body")
        assert_question_selector_trace(card, question_key, "reason card")
        block = card.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "reason readable block")
        assert_true(block.get("module") == "question_reason", "reason readable module mismatch")
        assert_true(block.get("body"), "reason readable body missing")
        assert_native_question_copy(block.get("body"), "reason readable body")
        assert_native_question_copy(card.get("nextMove"), "reason nextMove")
        assert_true(card.get("nextMove"), "reason nextMove missing")
    chance = view_model.get("chance") or {}
    for note in chance.get("notes") or []:
        assert_native_question_copy(note, "chance note")
    assert_question_selector_trace(chance, question_key, "chance payload")
    chance_readable = chance.get("readableInterpretation") or {}
    assert_question_selector_trace(chance_readable, question_key, "chance readable block")
    assert_true(chance_readable.get("module") == "question_chance", "chance readable module mismatch")
    assert_true(chance_readable.get("body"), "chance readable body missing")
    assert_native_question_copy(chance_readable.get("body"), "chance readable body")
    assert_native_question_copy(chance.get("nextMove"), "chance nextMove")
    assert_true(chance.get("nextMove"), "chance nextMove missing")
    for step in view_model.get("timeline") or []:
        assert_native_question_copy(step.get("body"), "timeline body")
        assert_question_selector_trace(step, question_key, "timeline step")
        block = step.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "timeline readable block")
        assert_true(block.get("module") == "question_timeline", "timeline readable module mismatch")
        assert_true(block.get("body"), "timeline readable body missing")
        assert_native_question_copy(block.get("body"), "timeline readable body")
        assert_native_question_copy(step.get("nextMove"), "timeline nextMove")
        assert_true(step.get("nextMove"), "timeline nextMove missing")
    donts = sections.get("donts") or []
    assert_true(len(donts) == len(view_model.get("donts") or []), "readable dont count mismatch")
    for item in donts:
        assert_native_question_copy(item.get("body"), "boundary body")
        assert_question_selector_trace(item, question_key, "boundary item")
        block = item.get("readableInterpretation") or {}
        assert_question_selector_trace(block, question_key, "boundary readable block")
        assert_true(block.get("module") == "question_boundary", "boundary readable module mismatch")
        assert_true(block.get("body"), "boundary readable body missing")
        assert_native_question_copy(block.get("body"), "boundary readable body")


def assert_no_visible_angle_or_house_claims(case: dict[str, Any]) -> None:
    for person_key in ("personA", "personB"):
        needs = ((case.get("identityLayer") or {}).get(person_key) or {}).get("needs") or []
        for item in needs:
            assert_true(item.get("point") != "Desc", f"{person_key} Desc leaked into identity needs")
            assert_true(item.get("house") is None, f"{person_key} house leaked into identity needs")

    for category, items in (case.get("synastryLayer") or {}).items():
        for item in items or []:
            points = {item.get("personAPoint"), item.get("personBPoint")}
            if points.intersection({"Asc", "Desc"}):
                precision = item.get("precision") or {}
                assert_true(
                    precision.get("display") == "blocked",
                    f"unblocked angle evidence leaked in {category}: {item}",
                )


def assert_blueprint_is_western_only(view_model: dict[str, Any]) -> None:
    blueprint = view_model.get("readingBlueprint") or {}
    assert_true(blueprint.get("version") == "reading-blueprint-v1", "readingBlueprint version mismatch")
    assert_true(blueprint.get("chapterOrder") == ["thoughts", "reasons", "chance"], "question blueprint chapter order mismatch")
    chapters = blueprint_chapters(blueprint)
    assert_true(len(chapters) == 3, "reading blueprint must have exactly three chapters")
    assert_true(len(blueprint.get("chapters") or []) == 3, "readingBlueprint.chapters alias missing")
    assert_true(len(view_model.get("includedReadingRows") or []) >= 4, "includedReadingRows alias missing")
    for chapter in chapters:
        assert_true(bool(chapter.get("methodBoundary")), f"{chapter.get('id')}: methodBoundary missing")
        for item in chapter.get("evidence") or []:
            source = str(item.get("source") or "")
            system = str(item.get("system") or "western")
            assert_true(not source.startswith("bazi"), f"BaZi source leaked into blueprint: {source}")
            assert_true(system == "western", f"non-Western evidence leaked into blueprint: {system}")


def assert_sun_moon_asc_profile_cluster(
    case: dict[str, Any],
    *,
    expected_item_count: int | None = None,
    expected_blocked_count: int | None = None,
    expected_reliable_ascendant: bool | None = None,
    min_low_moon_confidence: int = 0,
) -> None:
    cluster = (case.get("evidenceClusters") or {}).get("sunMoonAscProfile") or {}
    assert_true(cluster.get("atomId") == "western-atom-sun-moon-asc-profile", "sunMoonAscProfile atom mismatch")
    assert_true(cluster.get("source") == "western-sun-moon-asc-profile-george-bloch", "sunMoonAscProfile source mismatch")
    assert_true(cluster.get("claimSupport"), "sunMoonAscProfile claim support missing")
    assert_true(
        "western-sun-moon-asc-profile-george-bloch-001" in (cluster.get("claimIds") or []),
        "sunMoonAscProfile primary claim missing",
    )
    assert_true(cluster.get("hasSunMoonProfile") is True, "sunMoonAscProfile should preserve Sun/Moon profile")
    assert_true(cluster.get("hasBothPeopleProfile") is True, "sunMoonAscProfile should include both people")
    assert_true(cluster.get("profilePoints"), "sunMoonAscProfile profile points missing")
    if expected_item_count is not None:
        assert_true(cluster.get("itemCount") == expected_item_count, f"sunMoonAscProfile item count mismatch: {cluster}")
    if expected_blocked_count is not None:
        assert_true(cluster.get("blockedCount") == expected_blocked_count, f"sunMoonAscProfile blocked count mismatch: {cluster}")
    if expected_reliable_ascendant is not None:
        assert_true(
            cluster.get("hasReliableAscendant") is expected_reliable_ascendant,
            f"sunMoonAscProfile reliable Ascendant mismatch: {cluster}",
        )
    assert_true(
        int(cluster.get("lowMoonConfidenceCount") or 0) >= min_low_moon_confidence,
        f"sunMoonAscProfile low Moon confidence too low: {cluster}",
    )


def full_birth_data_smoke() -> None:
    reading = read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json")
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    assert_blueprint_is_western_only(view_model)
    assert_relationship_profiles(view_model)
    assert_readable_question_answer(view_model)

    case = case_file(view_model)
    assert_true(case.get("version") == "western-relationship-case-file-v1", "case file version mismatch")
    answer = case.get("answerLayer", {})
    assert_true(answer.get("ruleId"), "structured reading rule did not match")
    assert_true(answer.get("questionBlueprintId") == "western-relationship-result-v1", "question blueprint id missing")
    assert_true(answer.get("rulesetId") == "western-relationship-result-v1", "ruleset id missing")
    assert_true(answer.get("questionSourceArticleId") == "context-question-still-love-me", "question source article missing")
    assert_true(answer.get("questionClaimIds"), "question claim ids missing")
    assert_question_selector(answer, "still-love-me")
    assert_true(answer.get("answerContract"), "question answer contract missing")
    evidence_contract = answer.get("evidenceContract") or {}
    assert_true(evidence_contract.get("version") == "western-answer-evidence-contract-v1", "answer evidence contract missing")
    assert_true(evidence_contract.get("calculationEvidence"), "answer evidence contract must include calculation evidence")
    assert_true(evidence_contract.get("currentTransitEvidence"), "answer evidence contract must include current transit evidence")
    context_modifier = evidence_contract.get("contextModifier") or {}
    assert_true(context_modifier.get("role") == "action_modifier_only", "context modifier role should be action-only")
    assert_true(context_modifier.get("canCreateAstrologyConclusion") is False, "context must not create astrology conclusions")
    assert_true(context_modifier.get("requiresCalculationEvidenceForConclusion") is True, "context contract should require calculation evidence")
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
    assert_true(context_modifier.get("stageKey") == "cold-war", "answer evidence contract must preserve relationship stage")
    assert_true(context_modifier.get("contactStatusKey") == "no-contact", "answer evidence contract must preserve contact status")
    assert_true(context_modifier.get("actionBoundary"), "answer evidence contract must explain context boundary")
    assert_true(context_modifier.get("contactActionScale") == 1, "no-contact contract should lower action scale")
    assert_true(context_modifier.get("contactActionMode") == "observe_or_single_low_stimulation_test", "no-contact action mode mismatch")
    assert_true(context_modifier.get("requiresEasyExit") is True, "no-contact contract should require easy exit")
    assert_true(context_modifier.get("timingCanOverrideBoundary") is False, "timing should not override contact boundary")
    assert_true("repeated_messages" in set(context_modifier.get("contactBlockedActions") or []), "no-contact blocked action missing")
    assert_true(
        evidence_contract.get("precision", {}).get("timingPrecision") in {"analysis_datetime", "analysis_date_noon_fallback"},
        "answer evidence contract must declare timing precision",
    )
    communication = (case.get("synastryLayer") or {}).get("communication") or []
    assert_true(communication, "Mercury communication evidence missing in full-data scenario")
    assert_true(
        any({item.get("personAPoint"), item.get("personBPoint")}.intersection({"Mercury"}) for item in communication),
        "communication layer does not include Mercury evidence",
    )
    clusters = case.get("evidenceClusters") or {}
    assert_case_house_angle_precision(case, "allowed_by_precision")
    assert_true(clusters.get("pressure", {}).get("atomId"), "structured pressure atom missing")
    assert_true(clusters.get("repair", {}).get("claimSupport"), "cluster claim support missing")
    assert_true(clusters.get("currentTransits", {}).get("atomId"), "structured currentTransits atom missing")
    assert_true(clusters.get("currentTransits", {}).get("claimSupport"), "currentTransits claim support missing")
    assert_true(clusters.get("timingWindowBand", {}).get("atomId"), "structured timingWindowBand atom missing")
    assert_true(clusters.get("timingWindowBand", {}).get("claimSupport"), "timingWindowBand claim support missing")
    timing_contact = clusters.get("timingContactReducer", {})
    assert_true(timing_contact.get("atomId") == "western-atom-timing-contact-reducer", "timingContactReducer atom missing")
    assert_true(timing_contact.get("source") == "western-contact-timing-action-reducers", "timingContactReducer source mismatch")
    assert_true(timing_contact.get("claimSupport"), "timingContactReducer claim support missing")
    assert_true(timing_contact.get("recommendedAction") in {"avoid_push", "low_pressure_message", "observe_for_soft_window", "observe_only", "not_calculated"}, "timingContactReducer action invalid")
    assert_true(timing_contact.get("contactInstruction"), "timingContactReducer instruction missing")
    assert_exact_timing_policy(timing_contact, "timingContactReducer")
    assert_exact_timing_policy((case.get("timingLayer") or {}).get("windowScan", {}), "timing window scan")
    assert_true(clusters.get("birthDataQuality", {}).get("atomId"), "structured birthDataQuality atom missing")
    assert_true(clusters.get("birthDataQuality", {}).get("overallQuality") == "high", "full-data precision cluster should be high")
    assert_true(clusters.get("birthDataQuality", {}).get("claimSupport"), "birthDataQuality claim support missing")
    assert_true(clusters.get("identityNeeds", {}).get("atomId"), "structured identityNeeds atom missing")
    assert_true(clusters.get("identityNeeds", {}).get("claimSupport"), "identityNeeds claim support missing")
    assert_true(clusters.get("identityNeeds", {}).get("hasBothPeopleNeeds") is True, "identityNeeds should include both people")
    assert_true(clusters.get("relationshipStage", {}).get("atomId"), "structured relationshipStage atom missing")
    assert_true(clusters.get("relationshipStage", {}).get("claimSupport"), "relationshipStage claim support missing")
    assert_true(clusters.get("relationshipStage", {}).get("stageKey") == "cold-war", "relationshipStage should reflect context stage")
    assert_true(clusters.get("contactStatus", {}).get("atomId"), "structured contactStatus atom missing")
    assert_true(clusters.get("contactStatus", {}).get("claimSupport"), "contactStatus claim support missing")
    assert_true(clusters.get("contactStatus", {}).get("isNoContact") is True, "contactStatus should reflect no-contact")
    contact_policy = clusters.get("contactSituationPolicy", {})
    assert_true(contact_policy.get("atomId") == "western-atom-contact-situation-policy", "structured contactSituationPolicy atom missing")
    assert_true(contact_policy.get("source") == "context-contact-status", "contactSituationPolicy source mismatch")
    assert_true(contact_policy.get("claimSupport"), "contactSituationPolicy claim support missing")
    assert_true(contact_policy.get("statusKey") == "no-contact", "contactSituationPolicy should reflect no-contact")
    assert_true(contact_policy.get("actionScale") == 1, "no-contact action scale mismatch")
    assert_true(contact_policy.get("actionMode") == "observe_or_single_low_stimulation_test", "no-contact action mode mismatch")
    assert_true(contact_policy.get("canSuggestDirectContact") is True, "no-contact should allow only context-gated direct contact")
    assert_true(contact_policy.get("requiresCalculationSupport") is True, "contact policy should require calculation support")
    assert_true(contact_policy.get("timingCanOverrideBoundary") is False, "contact policy should block timing override")
    assert_true("valley-no-contact-lowers-action-speed" in set(contact_policy.get("methodClaimIds") or []), "no-contact method claim missing")
    assert_contact_action_boundary_trace(
        contact_policy,
        status_key="no-contact",
        expected_method_claim="valley-no-contact-lowers-action-speed",
        expected_source_claim="context-contact-status-005",
        expected_action_scale=1,
        expected_action_mode="observe_or_single_low_stimulation_test",
        can_suggest_direct_contact=True,
    )
    action_guidance = view_model.get("actionGuidance") or {}
    action_readable = action_guidance.get("readableInterpretation") or {}
    assert_true(action_guidance.get("statusKey") == "no-contact", "no-contact action guidance status mismatch")
    assert_true(action_readable.get("module") == "question_action", "no-contact action readable missing")
    assert_true("先看" in str(action_readable.get("headline") or ""), "no-contact action should tell user to check reality first")
    assert_true(clusters.get("emotionalRisk", {}).get("atomId"), "structured emotionalRisk atom missing")
    assert_true(clusters.get("emotionalRisk", {}).get("claimSupport"), "emotionalRisk claim support missing")
    assert_true(clusters.get("desiredOutcome", {}).get("atomId"), "structured desiredOutcome atom missing")
    assert_true(clusters.get("desiredOutcome", {}).get("claimSupport"), "desiredOutcome claim support missing")
    assert_true(clusters.get("methodOrder", {}).get("atomId"), "structured methodOrder atom missing")
    assert_true(clusters.get("methodOrder", {}).get("hasNatalBeforeSynastry") is True, "methodOrder should enforce natal before synastry")
    assert_true(clusters.get("methodOrder", {}).get("claimSupport"), "methodOrder claim support missing")
    assert_true(clusters.get("relationshipPotential", {}).get("atomId"), "structured relationshipPotential atom missing")
    assert_true(clusters.get("relationshipPotential", {}).get("claimSupport"), "relationshipPotential claim support missing")
    assert_true(clusters.get("relationshipPotential", {}).get("itemCount", 0) >= 10, "relationshipPotential should include both people")
    assert_sun_moon_asc_profile_cluster(
        case,
        expected_item_count=6,
        expected_blocked_count=0,
        expected_reliable_ascendant=True,
    )
    assert_true(clusters.get("elementComparison", {}).get("atomId"), "structured elementComparison atom missing")
    assert_true(clusters.get("elementComparison", {}).get("claimSupport"), "elementComparison claim support missing")
    assert_true(clusters.get("luminaryComparison", {}).get("atomId"), "structured luminaryComparison atom missing")
    assert_true(clusters.get("luminaryComparison", {}).get("claimSupport"), "luminaryComparison claim support missing")
    assert_true(clusters.get("aspectPriority", {}).get("atomId"), "structured aspectPriority atom missing")
    assert_true(clusters.get("aspectPriority", {}).get("hasDirectionality") is True, "aspectPriority should preserve directionality")
    assert_true(clusters.get("aspectPriority", {}).get("claimSupport"), "aspectPriority claim support missing")
    aspect_function = clusters.get("aspectFunctionCombination", {})
    assert_true(aspect_function.get("atomId") == "western-atom-aspect-function-combination", "aspectFunctionCombination atom missing")
    assert_true(aspect_function.get("source") == "western-aspect-function-combination-reducers", "aspectFunctionCombination source mismatch")
    assert_true(aspect_function.get("claimSupport"), "aspectFunctionCombination claim support missing")
    assert_true(aspect_function.get("itemCount", 0) >= 1, "aspectFunctionCombination should select supported combinations")
    assert_true(aspect_function.get("selectedCombinations"), "aspectFunctionCombination selected combinations missing")
    assert_true(aspect_function.get("selectedPairs"), "aspectFunctionCombination selected pairs missing")
    contact_modifier = clusters.get("aspectContactModifier", {})
    assert_true(contact_modifier.get("atomId"), "aspectContactModifier atom missing")
    assert_true(contact_modifier.get("source") == "western-aspect-contact-type-modifiers", "aspectContactModifier source mismatch")
    assert_true(contact_modifier.get("claimSupport"), "aspectContactModifier claim support missing")
    assert_true(contact_modifier.get("itemCount", 0) >= 1, "aspectContactModifier should summarize selected synastry contacts")
    assert_true(contact_modifier.get("dominantContactType") in {"conjunction", "soft", "hard", "minor", "other"}, "aspectContactModifier dominant type invalid")
    assert_true(contact_modifier.get("selectedModifiers"), "aspectContactModifier selected modifiers missing")
    pair_template = clusters.get("aspectPairContactTemplate", {})
    assert_true(pair_template.get("atomId"), "aspectPairContactTemplate atom missing")
    assert_true(pair_template.get("claimSupport"), "aspectPairContactTemplate claim support missing")
    assert_true(pair_template.get("itemCount", 0) >= 1, "aspectPairContactTemplate should summarize selected pair templates")
    assert_true(pair_template.get("hasPairTemplate") is True, "aspectPairContactTemplate should mark available template")
    assert_true(pair_template.get("selectedTemplates"), "aspectPairContactTemplate selected templates missing")
    pair_phrase_method = clusters.get("aspectPairPhraseTemplateMethod", {})
    assert_true(pair_phrase_method.get("atomId") == "western-atom-aspect-pair-phrase-template-method", "aspectPairPhraseTemplateMethod atom missing")
    assert_true(pair_phrase_method.get("source") == "western-aspect-pair-contact-phrase-templates", "aspectPairPhraseTemplateMethod source mismatch")
    assert_true(pair_phrase_method.get("claimSupport"), "aspectPairPhraseTemplateMethod claim support missing")
    synthesis_cross_check = clusters.get("aspectSynthesisCrossCheck", {})
    assert_true(synthesis_cross_check.get("atomId") == "western-atom-aspect-synthesis-cross-check", "aspectSynthesisCrossCheck atom missing")
    assert_true(synthesis_cross_check.get("source") == "western-aspect-synthesis-george-bloch", "aspectSynthesisCrossCheck source mismatch")
    assert_true(synthesis_cross_check.get("claimSupport"), "aspectSynthesisCrossCheck claim support missing")
    for combination in aspect_function.get("selectedCombinations") or []:
        assert_true(combination.get("sourceClaimId") in ALL_CLAIM_IDS, "combination source claim missing")
        assert_true(combination.get("functionSynthesis"), "combination synthesis missing")
        assert_true(combination.get("reducerInstruction"), "combination reducer instruction missing")
        assert_true(len(combination.get("pointStyles") or []) == 2, "combination point styles missing")
        assert_true((combination.get("contactModifier") or {}).get("source") == "western-aspect-contact-type-modifiers", "combination contact modifier missing")
        assert_true((combination.get("precision") or {}).get("display") in {"allowed", "allowed_with_uncertainty"}, "combination precision gate invalid")
    assert_true(clusters.get("ascendantImpression", {}).get("atomId"), "structured ascendantImpression atom missing")
    assert_true(clusters.get("ascendantImpression", {}).get("itemCount") == 2, "full-data ascendantImpression should be allowed")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("atomId"), "structured houseRelationshipFactors atom missing")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("itemCount", 0) > 0, "full-data houseRelationshipFactors should expose natal houses")
    assert_true(clusters.get("relationshipChartLayer", {}).get("atomId"), "structured relationshipChartLayer atom missing")
    assert_true(clusters.get("relationshipChartLayer", {}).get("itemCount") == 0, "relationshipChartLayer should stay deferred in free V0")
    consultation_safety = clusters.get("consultationSafety", {})
    consultation_claim_ids = cluster_claim_ids(consultation_safety)
    assert_true(consultation_safety.get("atomId"), "structured consultationSafety atom missing")
    assert_true(consultation_safety.get("hasPrivacyBoundary") is True, "consultationSafety should enforce privacy boundary")
    assert_true(consultation_safety.get("limitsThirdPartyInnerState") is True, "consultationSafety should limit third-party inner states")
    assert_true(consultation_safety.get("preservesClientAgency") is True, "consultationSafety should preserve client agency")
    assert_true(consultation_safety.get("blocksAbsolutePrediction") is True, "consultationSafety should block absolute prediction")
    assert_true(
        "western-consultation-ethics-004" in consultation_claim_ids,
        "consultationSafety third-party source claim missing",
    )
    assert_true(
        "western-consultation-ethics-005" in consultation_claim_ids,
        "consultationSafety client-agency source claim missing",
    )
    assert_true(
        "western-consultation-ethics-006" in consultation_claim_ids,
        "consultationSafety context-not-conclusion source claim missing",
    )
    assert_true(
        "absent_person_confession" in set(consultation_safety.get("blockedInterpretationClaims") or []),
        "consultationSafety absent-person confession block missing",
    )
    assert_true(
        "fear_based_instruction" in set(consultation_safety.get("blockedActionClaims") or []),
        "consultationSafety fear-based action block missing",
    )
    nonfatal_safety = clusters.get("nonfatalSynastrySafety", {})
    assert_true(nonfatal_safety.get("atomId") == "western-atom-nonfatal-synastry-safety", "structured nonfatalSynastrySafety atom missing")
    assert_true(nonfatal_safety.get("source") == "western-modern-nonfatal-synastry", "nonfatalSynastrySafety source mismatch")
    assert_true(nonfatal_safety.get("claimSupport"), "nonfatalSynastrySafety claim support missing")
    assert_true(nonfatal_safety.get("hasNoGuaranteedOutcome") is True, "nonfatalSynastrySafety should block guaranteed outcomes")
    assert_true(nonfatal_safety.get("hardAspectsArePressureNotVerdict") is True, "nonfatalSynastrySafety should keep hard aspects nonfatal")
    assert_true(nonfatal_safety.get("requiresConditionalConclusion") is True, "nonfatalSynastrySafety should require conditional conclusions")
    assert_true("guaranteed_breakup" in set(nonfatal_safety.get("blockedOutcomeClaims") or []), "guaranteed breakup block missing")
    function_template_claims = {
        "moonSignEmotionalSafety": "western-relationship-function-sign-templates-002",
        "mercurySignCommunicationRepair": "western-relationship-function-sign-templates-003",
        "venusSignAffectionStyle": "western-relationship-function-sign-templates-004",
        "marsSignPursuitConflict": "western-relationship-function-sign-templates-005",
        "saturnSignDefenseDelay": "western-relationship-function-sign-templates-006",
    }
    function_method_claims = {
        "moonSignEmotionalSafety": "hand-moon-emotional-containment-belonging",
        "mercurySignCommunicationRepair": "hand-mercury-communication-translation-map",
        "venusSignAffectionStyle": "hand-venus-voluntary-attraction-harmony",
        "marsSignPursuitConflict": "hand-mars-individuality-action-conflict",
        "saturnSignDefenseDelay": "hand-saturn-limits-reality-structure",
    }
    for key, point in (
        ("moonSignEmotionalSafety", "Moon"),
        ("mercurySignCommunicationRepair", "Mercury"),
        ("venusSignAffectionStyle", "Venus"),
        ("marsSignPursuitConflict", "Mars"),
        ("saturnSignDefenseDelay", "Saturn"),
    ):
        cluster = clusters.get(key, {})
        assert_true(cluster.get("atomId"), f"{key} atom missing")
        assert_true(cluster.get("claimSupport"), f"{key} claim support missing")
        assert_true(cluster.get("point") == point, f"{key} point mismatch")
        assert_true(cluster.get("itemCount") == 2, f"{key} should include both people")
        assert_true(cluster.get("hasBothPeopleStyle") is True, f"{key} should include both people styles")
        claim_ids = set(str(claim_id) for claim_id in cluster.get("claimIds") or [])
        assert_true(function_template_claims[key] in claim_ids, f"{key} function template claim missing")
        method_claim_ids = set(str(claim_id) for claim_id in cluster.get("methodClaimIds") or [])
        assert_true(function_method_claims[key] in method_claim_ids, f"{key} Hand function method claim missing")
        assert_true(
            "george-bloch-function-elements-moon-through-saturn" in method_claim_ids,
            f"{key} George/Bloch function element method claim missing",
        )
        if key == "saturnSignDefenseDelay":
            assert_true(SATURN_BOUNDARY_SOURCE_CLAIMS.issubset(claim_ids), "saturnSignDefenseDelay Greene source claims missing")
            assert_true(SATURN_BOUNDARY_METHOD_CLAIM in method_claim_ids, "saturnSignDefenseDelay Greene method claim missing")
            assert_saturn_process_boundary(cluster, key)
        assert_true(any(claim_id.startswith("western-individual-sign-meanings-hand-") for claim_id in claim_ids), f"{key} selected sign claim missing")
        assert_true(any(claim_id.startswith("western-function-element-templates-") for claim_id in claim_ids), f"{key} function element claim missing")
        assert_true(any(claim_id.startswith("western-function-modality-templates-") for claim_id in claim_ids), f"{key} function modality claim missing")
        for style in cluster.get("personStyles") or []:
            assert_true(style.get("element"), f"{key} person style element missing")
            assert_true(style.get("elementStyle"), f"{key} person style element style missing")
            assert_true(style.get("modality"), f"{key} person style modality missing")
            assert_true(style.get("modalityStyle"), f"{key} person style modality style missing")
    element_matrix = clusters.get("functionElementMatrix", {})
    assert_true(element_matrix.get("atomId") == "western-atom-function-element-matrix", "functionElementMatrix atom missing")
    assert_true(element_matrix.get("claimSupport"), "functionElementMatrix claim support missing")
    assert_true(
        "george-bloch-function-elements-moon-through-saturn" in set(element_matrix.get("methodClaimIds") or []),
        "functionElementMatrix George/Bloch function element method claim missing",
    )
    assert_true(element_matrix.get("itemCount") == 10, "functionElementMatrix should include both people across five points")
    assert_true(sum(int(element_matrix.get(key) or 0) for key in ("fireCount", "earthCount", "airCount", "waterCount")) == 10, "functionElementMatrix counts should sum to 10")
    modality_matrix = clusters.get("functionModalityMatrix", {})
    assert_true(modality_matrix.get("atomId") == "western-atom-function-modality-matrix", "functionModalityMatrix atom missing")
    assert_true(modality_matrix.get("claimSupport"), "functionModalityMatrix claim support missing")
    assert_true(modality_matrix.get("itemCount") == 10, "functionModalityMatrix should include both people across five points")
    assert_true(sum(int(modality_matrix.get(key) or 0) for key in ("cardinalCount", "fixedCount", "mutableCount")) == 10, "functionModalityMatrix counts should sum to 10")
    aspect_items = [
        item
        for items in (case.get("synastryLayer") or {}).values()
        for item in items or []
        if str(item.get("source") or "").startswith("western-aspects-")
    ]
    assert_true(aspect_items, "aspect article evidence missing")
    assert_true(all(item.get("atomId") for item in aspect_items), "aspect evidence atom ids missing")
    assert_true(all(item.get("claimIds") for item in aspect_items), "aspect evidence claim ids missing")
    assert_true(all(item.get("contactType") for item in aspect_items), "aspect evidence contactType missing")
    assert_true(
        all((item.get("contactModifier") or {}).get("source") == "western-aspect-contact-type-modifiers" for item in aspect_items),
        "aspect evidence contact modifier source missing",
    )
    assert_true(
        all((item.get("contactModifier") or {}).get("claimSupport") for item in aspect_items),
        "aspect evidence contact modifier claim support missing",
    )
    templated_items = [item for item in aspect_items if str(item.get("source") or "") in PAIR_TEMPLATE_SOURCE_IDS]
    assert_true(templated_items, "pair-contact template evidence missing")
    assert_true(
        all(
            (item.get("pairContactTemplate") or {}).get("source")
            in {"western-aspect-pair-contact-phrase-templates", str(item.get("source") or "")}
            for item in templated_items
        ),
        "pair-contact template source missing",
    )
    assert_true(
        all((item.get("pairContactTemplate") or {}).get("claimSupport") for item in templated_items),
        "pair-contact template claim support missing",
    )
    full_data_pair_sources = {str(item.get("source") or "") for item in aspect_items}
    required_pair_sources = {
        "western-aspects-sun-venus",
        "western-aspects-moon-mars",
        "western-aspects-mercury-sun",
    }
    missing_pair_sources = required_pair_sources - full_data_pair_sources
    assert_true(not missing_pair_sources, f"source-backed pair family evidence missing: {sorted(missing_pair_sources)}")


def when_to_contact_reducer_smoke() -> None:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "smoke-when-to-contact"
    reading["context"]["main_question"] = "when-to-contact"
    reading["context"]["emotional_risk"] = "calm"
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    assert_relationship_profiles(view_model)
    case = case_file(view_model)
    clusters = case.get("evidenceClusters") or {}
    answer = case.get("answerLayer") or {}
    assert_true(answer.get("ruleId") == "western-rule-when-to-contact-no-contact-pressure", "when-to-contact should use contact-aware pressure rule")
    assert_true(answer.get("questionSourceArticleId") == "context-question-when-to-contact", "when-to-contact blueprint source missing")
    assert_question_selector(answer, "when-to-contact")
    assert_true(clusters.get("currentTransits", {}).get("hasAllowedTiming") is True, "timing cluster should expose allowed timing")
    assert_saturn_process_boundary(clusters.get("timingSaturnPressure", {}), "timingSaturnPressure")
    assert_true(clusters.get("timingContactReducer", {}).get("recommendedAction") in {"avoid_push", "low_pressure_message", "observe_for_soft_window", "observe_only", "not_calculated"}, "when-to-contact contact timing action invalid")
    assert_exact_timing_policy(clusters.get("timingContactReducer", {}), "contact timing reducer")
    assert_true(clusters.get("birthDataQuality", {}).get("hasPrecisionLimit") is False, "full-data precision should not limit timing")
    assert_true(
        any("行運" in item or "短期" in item or "行動氣候" in item for item in answer.get("because") or []),
        "when-to-contact answer should include timing evidence",
    )


def blocked_contact_status_smoke() -> None:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "smoke-blocked-when-to-contact"
    reading["context"]["main_question"] = "when-to-contact"
    reading["context"]["contact_status"] = "blocked"
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    assert_relationship_profiles(view_model)
    case = case_file(view_model)
    clusters = case.get("evidenceClusters") or {}
    answer = case.get("answerLayer") or {}
    contact_status = clusters.get("contactStatus", {})
    assert_true(contact_status.get("isBlocked") is True, "blocked contact status should be reflected")
    assert_true(
        "context-contact-status-004" in cluster_claim_ids(contact_status),
        "blocked contact status should carry hard-boundary source claim",
    )
    contact_policy = clusters.get("contactSituationPolicy", {})
    assert_true(contact_policy.get("statusKey") == "blocked", "blocked contact policy should preserve status")
    assert_true(
        "context-contact-status-004" in cluster_claim_ids(contact_policy),
        "blocked contact policy should carry hard-boundary source claim",
    )
    assert_true(contact_policy.get("actionScale") == 0, "blocked contact policy should force action scale zero")
    assert_true(contact_policy.get("actionMode") == "boundary_only", "blocked contact action mode mismatch")
    assert_true(contact_policy.get("canSuggestDirectContact") is False, "blocked contact should not suggest direct contact")
    assert_true(contact_policy.get("timingCanOverrideBoundary") is False, "blocked contact timing override should be false")
    assert_true("valley-blocked-contact-hard-boundary" in set(contact_policy.get("methodClaimIds") or []), "blocked contact method claim missing")
    assert_contact_action_boundary_trace(
        contact_policy,
        status_key="blocked",
        expected_method_claim="valley-blocked-contact-hard-boundary",
        expected_source_claim="context-contact-status-004",
        expected_action_scale=0,
        expected_action_mode="boundary_only",
        can_suggest_direct_contact=False,
    )
    assert_true("alternate_account_contact" in set(contact_policy.get("blockedActions") or []), "blocked contact bypass action missing")
    action_guidance = view_model.get("actionGuidance") or {}
    action_readable = action_guidance.get("readableInterpretation") or {}
    assert_true(action_guidance.get("statusKey") == "blocked", "blocked action guidance status mismatch")
    assert_true(action_readable.get("headline") == "先不要聯絡", "blocked action readable should forbid contact")
    assert_true("不要換帳號" in str(action_readable.get("nextMove") or ""), "blocked action should block bypass contact")
    assert_true(answer.get("ruleId") == "western-rule-when-to-contact-blocked", "blocked contact should select blocked timing rule")


def ambiguous_stage_smoke() -> None:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "smoke-ambiguous-any-chance"
    reading["context"]["relationship_stage"] = "ambiguous"
    reading["context"]["main_question"] = "any-chance"
    reading["context"]["contact_status"] = "occasional-contact"
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    assert_relationship_profiles(view_model)
    case = case_file(view_model)
    clusters = case.get("evidenceClusters") or {}
    answer = case.get("answerLayer") or {}
    assert_true(clusters.get("relationshipStage", {}).get("isAmbiguousStage") is True, "ambiguous stage should be reflected")
    contact_policy = clusters.get("contactSituationPolicy", {})
    assert_true(contact_policy.get("statusKey") == "occasional-contact", "occasional contact policy should preserve status")
    assert_true(contact_policy.get("actionScale") == 2, "occasional contact action scale mismatch")
    assert_true(contact_policy.get("actionMode") == "small_bid_response_led", "occasional contact action mode mismatch")
    assert_true(contact_policy.get("requiresEasyExit") is True, "occasional contact should require easy exit")
    action_guidance = view_model.get("actionGuidance") or {}
    action_readable = action_guidance.get("readableInterpretation") or {}
    assert_true(action_guidance.get("statusKey") == "occasional-contact", "occasional action guidance status mismatch")
    assert_true("跟著回應走" in str(action_readable.get("headline") or ""), "occasional action should follow response")
    assert_true(answer.get("ruleId") == "western-rule-any-chance-ambiguous-clarity", "ambiguous chance should select clarity rule")


def shared_space_contact_status_smoke() -> None:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "smoke-shared-space-when-to-contact"
    reading["context"]["main_question"] = "when-to-contact"
    reading["context"]["contact_status"] = "living-or-working-together"
    reading["context"]["emotional_risk"] = "calm"
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    assert_relationship_profiles(view_model)
    case = case_file(view_model)
    clusters = case.get("evidenceClusters") or {}
    answer = case.get("answerLayer") or {}
    contact_policy = clusters.get("contactSituationPolicy", {})
    assert_true(answer.get("ruleId") == "western-rule-when-to-contact-shared-space-boundary", "shared-space contact should select boundary rule")
    assert_true(contact_policy.get("statusKey") == "living-or-working-together", "shared-space contact policy should preserve status")
    assert_true(contact_policy.get("actionScale") == 2, "shared-space action scale mismatch")
    assert_true(contact_policy.get("actionMode") == "shared_space_boundary", "shared-space action mode mismatch")
    assert_true(contact_policy.get("requiresSharedSpaceBoundary") is True, "shared-space policy should require shared-space boundary")
    assert_true("public_confrontation" in set(contact_policy.get("blockedActions") or []), "shared-space blocked action missing")
    action_guidance = view_model.get("actionGuidance") or {}
    action_readable = action_guidance.get("readableInterpretation") or {}
    assert_true(action_guidance.get("statusKey") == "living-or-working-together", "shared-space action guidance status mismatch")
    assert_true("共同場域" in str(action_readable.get("headline") or ""), "shared-space action should protect shared space")


def blank_birthplace_smoke() -> None:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "smoke-blank-birthplace"
    reading["person_a"]["birth_place"] = ""
    reading["person_b"]["birth_place"] = ""
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    assert_relationship_profiles(view_model, precision_limited=True)
    case = case_file(view_model)
    quality = case.get("inputQuality") or {}
    assert_true(quality.get("personA", {}).get("precision") == "location_fallback", "personA should use location_fallback")
    assert_true(quality.get("personB", {}).get("precision") == "location_fallback", "personB should use location_fallback")
    clusters = case.get("evidenceClusters") or {}
    assert_true(clusters.get("birthDataQuality", {}).get("hasPrecisionLimit") is True, "blank birthplace should set precision limit")
    assert_true(clusters.get("birthDataQuality", {}).get("locationFallbackCount") == 2, "blank birthplace should count both location fallbacks")
    assert_case_house_angle_precision(case, "blocked_by_location")
    assert_true(clusters.get("ascendantImpression", {}).get("blockedCount") == 1, "blank birthplace should block ascendantImpression")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("blockedCount") == 1, "blank birthplace should block houseRelationshipFactors")
    assert_sun_moon_asc_profile_cluster(
        case,
        expected_item_count=4,
        expected_blocked_count=2,
        expected_reliable_ascendant=False,
    )
    assert_true((case.get("houseOverlayLayer") or {}).get("status") == "blocked_by_location", "house overlays should be blocked by location")
    assert_true(
        "reliable birth cities" in str((case.get("houseOverlayLayer") or {}).get("reason") or ""),
        "location guardrail reason should come from structured guardrails",
    )
    assert_no_visible_angle_or_house_claims(case)


def no_birth_time_smoke() -> None:
    reading = copy.deepcopy(read_json(ROOT / "examples" / "readings" / "cold-war-still-love-me.json"))
    reading["reading_id"] = "smoke-no-birth-time"
    reading["person_a"]["birth_time"] = None
    reading["person_b"]["birth_time"] = None
    payload, view_model = build_vm(reading)
    assert_no_legacy_bazi_payload(payload, view_model)
    case = case_file(view_model)
    quality = case.get("inputQuality") or {}
    assert_true(quality.get("personA", {}).get("precision") == "date_only", "personA should be date_only")
    assert_true(quality.get("personB", {}).get("precision") == "date_only", "personB should be date_only")
    clusters = case.get("evidenceClusters") or {}
    assert_true(clusters.get("birthDataQuality", {}).get("hasPrecisionLimit") is True, "no birth time should set precision limit")
    assert_true(clusters.get("birthDataQuality", {}).get("dateOnlyCount") == 2, "no birth time should count both date-only charts")
    assert_case_house_angle_precision(case, "blocked_by_birth_time")
    assert_true(clusters.get("moonSignEmotionalSafety", {}).get("lowConfidenceCount", 0) >= 2, "date-only Moon sign styles should be low confidence")
    assert_true(clusters.get("ascendantImpression", {}).get("blockedCount") == 1, "no birth time should block ascendantImpression")
    assert_true(clusters.get("houseRelationshipFactors", {}).get("blockedCount") == 1, "no birth time should block houseRelationshipFactors")
    assert_sun_moon_asc_profile_cluster(
        case,
        expected_item_count=4,
        expected_blocked_count=2,
        expected_reliable_ascendant=False,
        min_low_moon_confidence=2,
    )
    assert_true(clusters.get("identityNeeds", {}).get("lowConfidenceCount", 0) >= 2, "date-only identity Moon needs should be low confidence")
    assert_true(quality.get("personA", {}).get("moonConfidence") == "low", "personA Moon confidence should be low")
    assert_true(quality.get("personB", {}).get("moonConfidence") == "low", "personB Moon confidence should be low")
    assert_true((case.get("houseOverlayLayer") or {}).get("status") == "blocked_by_birth_time", "house overlays should be blocked by birth time")
    assert_true(
        "reliable birth times" in str((case.get("houseOverlayLayer") or {}).get("reason") or ""),
        "birth-time guardrail reason should come from structured guardrails",
    )
    for person_key in ("personA", "personB"):
        needs = ((case.get("identityLayer") or {}).get(person_key) or {}).get("needs") or []
        for item in needs:
            if item.get("point") == "Moon":
                assert_true(item.get("confidence") == "low", f"{person_key} date-only Moon need must be low confidence")
    assert_no_visible_angle_or_house_claims(case)


def main() -> int:
    full_birth_data_smoke()
    when_to_contact_reducer_smoke()
    blocked_contact_status_smoke()
    ambiguous_stage_smoke()
    shared_space_contact_status_smoke()
    blank_birthplace_smoke()
    no_birth_time_smoke()
    print(
        "Western complete-result flow smoke passed: "
        "full-data, contact-aware, context-aware, blank birthplace, and no-birth-time scenarios."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
