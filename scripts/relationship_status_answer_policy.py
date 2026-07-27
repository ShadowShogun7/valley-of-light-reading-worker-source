#!/usr/bin/env python3
"""Relationship-status owned answer routing for paid relationship readings.

The policy decides what the reading is allowed to emphasize for the user's
current relationship state. It is not evidence: downstream astrology layers
still need chart and timing support before making a conclusion.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


POLICY_VERSION = "relationship-status-answer-policy-v1"

STAGE_ORDER = ("ambiguous", "broke-up-recent", "broke-up-long", "cold-war", "crisis")

DEFAULT_TRACK = "relationship_direction"

STATUS_POLICIES: dict[str, dict[str, Any]] = {
    "ambiguous": {
        "stageKey": "ambiguous",
        "readerLabel": "曖昧 / 不確定關係",
        "stagePremise": "這段關係還沒有被清楚定義，所以重點是看好感能不能變成穩定行動。",
        "primaryTracks": ["serious_potential", "hot_cold_pattern", "relationship_development"],
        "secondaryTracks": ["attraction_evidence", "emotional_safety", "communication_pattern", "timing_window"],
        "suppressedTracks": ["reconciliation_potential", "wait_or_release", "breakup_cause", "third_party"],
        "allowedExceptions": {
            "reconciliation_potential": ["main_question:any-chance", "desired_outcome:reconcile"],
            "wait_or_release": ["main_question:stay-or-let-go"],
            "third_party": ["evidence:third_party"],
        },
        "questionRewrites": {
            "still-love-me": "他是不是有認真可能？",
            "any-chance": "這段曖昧會不會往關係發展？",
            "when-to-contact": "什麼時候適合讓互動更清楚？",
            "what-did-i-do-wrong": "為什麼他會忽冷忽熱？",
            "stay-or-let-go": "這段曖昧值得繼續觀察嗎？",
        },
        "questionTracks": {
            "still-love-me": ["serious_potential", "attraction_evidence", "emotional_safety"],
            "any-chance": ["relationship_development", "serious_potential", "repair_condition"],
            "when-to-contact": ["relationship_development", "timing_window", "contact_boundary"],
            "what-did-i-do-wrong": ["hot_cold_pattern", "communication_pattern", "pressure_risk"],
            "stay-or-let-go": ["serious_potential", "relationship_development", "self_protection"],
        },
        "sectionTitleOverrides": {
            "thoughts": "他有沒有認真可能",
            "reasons": "為什麼忽冷忽熱",
            "chance": "會不會往關係發展",
        },
        "pageTopicRules": {
            "chart-positioning": "只看兩個人在曖昧裡怎麼靠近和保留，不下承諾結論。",
            "relationship-fit": "只看火花、相處節奏和能不能變穩。",
            "core-answer": "回答這段曖昧有沒有被認真對待的跡象。",
            "timing-reading": "只看什麼時候適合讓互動更清楚，不逼關係名稱。",
            "action-direction": "下一步只做一個能讓關係更清楚的小動作。",
        },
        "requiredBoundaries": [
            "不要把火花直接說成承諾。",
            "不要把曖昧寫成分手後復合問題。",
        ],
        "forbiddenVisibleEmphasis": ["復合機會", "放下還是等待", "第三者"],
        "evidenceClusterWeights": {
            "attraction": 1.1,
            "communication": 1.1,
            "emotionalSafety": 1.0,
            "pressure": 0.85,
            "repair": 0.7,
            "timingContactReducer": 0.9,
            "contactSituationPolicy": 0.9,
        },
        "finalNarrative": {
            "fitHeadline": "火花要看能不能變穩",
            "coreHeadline": "先看他有沒有把曖昧往前帶",
            "timingHeadline": "時機不是逼定義，是讓互動清楚一點",
            "actionHeadline": "下一步讓關係多一點清楚",
        },
    },
    "broke-up-recent": {
        "stageKey": "broke-up-recent",
        "readerLabel": "剛分手",
        "stagePremise": "剛分開時情緒還在動，先看在意、卡點和恢復互動的條件。",
        "primaryTracks": ["remaining_feeling", "reconciliation_potential", "contact_readiness", "breakup_cause"],
        "secondaryTracks": ["attraction_evidence", "pressure_risk", "emotional_safety", "timing_window"],
        "suppressedTracks": ["exact_reconciliation_date", "fatalistic_prediction", "third_party"],
        "allowedExceptions": {
            "third_party": ["evidence:third_party"],
        },
        "questionRewrites": {
            "still-love-me": "他心裡還有我嗎？",
            "any-chance": "你們還有沒有復合機會？",
            "when-to-contact": "什麼時間點比較容易恢復互動？",
            "what-did-i-do-wrong": "分手真正卡住的原因是什麼？",
            "stay-or-let-go": "現在該等一等，還是先把自己穩住？",
        },
        "questionTracks": {
            "still-love-me": ["remaining_feeling", "attraction_evidence", "emotional_safety"],
            "any-chance": ["reconciliation_potential", "repair_condition", "pressure_risk"],
            "when-to-contact": ["contact_readiness", "timing_window", "contact_boundary"],
            "what-did-i-do-wrong": ["breakup_cause", "communication_pattern", "pressure_risk"],
            "stay-or-let-go": ["reconciliation_potential", "self_protection", "repair_condition"],
        },
        "sectionTitleOverrides": {
            "thoughts": "他心裡還有沒有你",
            "reasons": "分手真正卡住的地方",
            "chance": "恢復互動的機會",
        },
        "pageTopicRules": {
            "chart-positioning": "只看兩個人在分手初期各自怎麼安定或退開。",
            "relationship-fit": "只看吸引、摩擦和分手前的相處循環。",
            "core-answer": "回答他是否仍被牽動，以及復合條件被什麼壓住。",
            "timing-reading": "只看什麼時段比較容易恢復互動，不承諾復合日期。",
            "action-direction": "下一步先讓情緒降下來，再留一個很小的互動入口。",
        },
        "requiredBoundaries": [
            "不要用分手後第一波情緒替整段關係定論。",
            "不要把短暫回覆寫成復合保證。",
            "不要說什麼時候會復合，改說什麼時間點比較容易恢復互動。",
        ],
        "forbiddenVisibleEmphasis": ["什麼時候會復合", "一定會復合", "保證復合"],
        "evidenceClusterWeights": {
            "attraction": 1.05,
            "repair": 1.15,
            "pressure": 1.0,
            "communication": 1.0,
            "timingContactReducer": 1.1,
            "contactSituationPolicy": 1.0,
        },
        "finalNarrative": {
            "fitHeadline": "先看分開前的相處循環",
            "coreHeadline": "先看在意還能不能回到互動",
            "timingHeadline": "時機看恢復互動，不看保證復合",
            "actionHeadline": "下一步先讓情緒降下來",
        },
    },
    "broke-up-long": {
        "stageKey": "broke-up-long",
        "readerLabel": "分手一段時間",
        "stagePremise": "時間拉長後，重點不是回到以前，而是這段緣分還有沒有現實延續性。",
        "primaryTracks": ["realistic_continuation", "partner_current_view", "wait_or_release", "reopen_contact"],
        "secondaryTracks": ["attraction_evidence", "repair_condition", "self_protection", "timing_window"],
        "suppressedTracks": ["quick_reconciliation", "hope_only_language", "exact_reconciliation_date", "third_party"],
        "allowedExceptions": {
            "quick_reconciliation": ["evidence:strong_repair", "contact:still-in-contact"],
            "third_party": ["evidence:third_party"],
        },
        "questionRewrites": {
            "still-love-me": "他現在怎麼看待你？",
            "any-chance": "這段緣分是否還有現實延續性？",
            "when-to-contact": "如果要重新開口，適合怎麼做？",
            "what-did-i-do-wrong": "過去真正卡住的是哪一種互動？",
            "stay-or-let-go": "你該繼續等，還是慢慢放下？",
        },
        "questionTracks": {
            "still-love-me": ["partner_current_view", "realistic_continuation", "attraction_evidence"],
            "any-chance": ["realistic_continuation", "reopen_contact", "repair_condition"],
            "when-to-contact": ["reopen_contact", "timing_window", "contact_boundary"],
            "what-did-i-do-wrong": ["partner_current_view", "communication_pattern", "pressure_risk"],
            "stay-or-let-go": ["wait_or_release", "self_protection", "realistic_continuation"],
        },
        "sectionTitleOverrides": {
            "thoughts": "他現在怎麼看待你",
            "reasons": "還有沒有現實延續性",
            "chance": "要等、放下，還是重新開口",
        },
        "pageTopicRules": {
            "chart-positioning": "只看分開久了仍會牽動彼此的底層位置。",
            "relationship-fit": "只看舊模式是否有可能換成新的靠近方式。",
            "core-answer": "回答這段緣分是否還有現實延續性。",
            "timing-reading": "只看重新開口是否有空間，不把懷念寫成機會。",
            "action-direction": "下一步要有界線，不用等待換答案。",
        },
        "requiredBoundaries": [
            "懷念不等於現實延續。",
            "想念不等於值得繼續等。",
            "重新開口要看是否有新的互動條件，不是回到舊關係。",
        ],
        "forbiddenVisibleEmphasis": ["很快復合", "只要等就會回來", "命定等待"],
        "evidenceClusterWeights": {
            "repair": 1.1,
            "contactSituationPolicy": 1.15,
            "timingContactReducer": 1.0,
            "pressure": 1.0,
            "attraction": 0.9,
            "emotionalSafety": 1.0,
        },
        "finalNarrative": {
            "fitHeadline": "分開久了要看新的靠近方式",
            "coreHeadline": "先看有沒有現實延續性",
            "timingHeadline": "重新開口要比以前更輕",
            "actionHeadline": "下一步要先保住你的界線",
        },
    },
    "cold-war": {
        "stageKey": "cold-war",
        "readerLabel": "冷戰 / 斷聯中",
        "stagePremise": "冷戰裡重點不是逼答案，而是看沉默能不能慢慢變回可以說話。",
        "primaryTracks": ["proactive_contact_likelihood", "cold_war_stuck_point", "contact_gain_or_loss", "restore_interaction", "timing_window"],
        "secondaryTracks": ["pressure_risk", "communication_pattern", "contact_boundary", "emotional_safety"],
        "suppressedTracks": ["force_answer", "instant_reconciliation", "third_party"],
        "allowedExceptions": {
            "third_party": ["evidence:third_party"],
        },
        "questionRewrites": {
            "still-love-me": "他會不會主動聯絡？",
            "any-chance": "冷戰還有沒有機會變軟？",
            "when-to-contact": "現在開口會加分還是扣分？",
            "what-did-i-do-wrong": "冷戰真正卡住的點是什麼？",
            "stay-or-let-go": "要等他主動，還是先停在界線內？",
        },
        "questionTracks": {
            "still-love-me": ["proactive_contact_likelihood", "restore_interaction", "emotional_safety"],
            "any-chance": ["restore_interaction", "cold_war_stuck_point", "repair_condition"],
            "when-to-contact": ["contact_gain_or_loss", "timing_window", "contact_boundary"],
            "what-did-i-do-wrong": ["cold_war_stuck_point", "communication_pattern", "pressure_risk"],
            "stay-or-let-go": ["contact_boundary", "restore_interaction", "self_protection"],
        },
        "sectionTitleOverrides": {
            "thoughts": "他會不會主動聯絡",
            "reasons": "冷戰真正卡住的點",
            "chance": "怎麼恢復互動",
        },
        "pageTopicRules": {
            "chart-positioning": "只看冷戰裡各自怎麼保護自己。",
            "relationship-fit": "只看沉默是否能變回可以說話。",
            "core-answer": "回答他會不會主動，以及沉默卡在哪裡。",
            "timing-reading": "強化聯絡時機：現在開口是加分、扣分，還是應先停。",
            "action-direction": "下一步是恢復互動，不是逼出答案。",
        },
        "requiredBoundaries": [
            "不要逼答案，先恢復互動。",
            "如果被封鎖，不能建議繞路聯絡。",
            "冷戰不等於結束，但沉默也不能被當成承諾。",
        ],
        "forbiddenVisibleEmphasis": ["逼他回答", "直接攤牌", "繞路聯絡"],
        "evidenceClusterWeights": {
            "contactSituationPolicy": 1.25,
            "timingContactReducer": 1.2,
            "communication": 1.1,
            "pressure": 1.05,
            "repair": 1.0,
            "attraction": 0.8,
        },
        "finalNarrative": {
            "fitHeadline": "冷戰先看沉默能不能變軟",
            "coreHeadline": "先看他會不會自然回到互動",
            "timingHeadline": "時機要看開口會加分還是扣分",
            "actionHeadline": "下一步是恢復互動，不是逼答案",
        },
    },
    "crisis": {
        "stageKey": "crisis",
        "readerLabel": "還在一起但很不穩",
        "stagePremise": "你們還在關係裡，重點是看惡性循環能不能下降，而不是直接套分手後語言。",
        "primaryTracks": ["conflict_cycle", "partner_continuation_intent", "repairability", "deescalation_next_step"],
        "secondaryTracks": ["pressure_risk", "communication_pattern", "emotional_safety", "repair_condition"],
        "suppressedTracks": ["reconciliation_potential", "post_breakup_waiting", "wait_or_release", "third_party"],
        "allowedExceptions": {
            "reconciliation_potential": ["desired_outcome:reconcile", "main_question:any-chance"],
            "wait_or_release": ["main_question:stay-or-let-go"],
            "third_party": ["evidence:third_party"],
        },
        "questionRewrites": {
            "still-love-me": "他現在是否還想繼續？",
            "any-chance": "關係能不能修復？",
            "when-to-contact": "下一步怎麼降低惡性循環？",
            "what-did-i-do-wrong": "你們反覆吵架的核心模式是什麼？",
            "stay-or-let-go": "這段關係還能修，還是已經太傷？",
        },
        "questionTracks": {
            "still-love-me": ["partner_continuation_intent", "emotional_safety", "pressure_risk"],
            "any-chance": ["repairability", "conflict_cycle", "repair_condition"],
            "when-to-contact": ["deescalation_next_step", "timing_window", "contact_boundary"],
            "what-did-i-do-wrong": ["conflict_cycle", "communication_pattern", "pressure_risk"],
            "stay-or-let-go": ["repairability", "self_protection", "conflict_cycle"],
        },
        "sectionTitleOverrides": {
            "thoughts": "他是否還想繼續",
            "reasons": "反覆吵架的核心模式",
            "chance": "關係能不能修復",
        },
        "pageTopicRules": {
            "chart-positioning": "只看還在一起時各自怎麼急、怎麼退、怎麼保護自己。",
            "relationship-fit": "只看吸引和衝突循環，不把危機直接寫成分手結論。",
            "core-answer": "回答關係是否還想繼續，以及修復條件在哪裡。",
            "timing-reading": "只看什麼時候適合降溫，不把時機變成逼結論。",
            "action-direction": "下一步只做降低惡性循環的一件事。",
        },
        "requiredBoundaries": [
            "不要把還在一起的危機直接寫成已經結束的分析。",
            "先看惡性循環能不能下降。",
            "不要用一次爭執替整段關係下最後結論。",
        ],
        "forbiddenVisibleEmphasis": ["復合機會", "放下還是等待", "分手後怎麼追回"],
        "evidenceClusterWeights": {
            "pressure": 1.25,
            "communication": 1.2,
            "repair": 1.15,
            "emotionalSafety": 1.1,
            "timingContactReducer": 0.85,
            "contactSituationPolicy": 0.85,
            "attraction": 0.8,
        },
        "finalNarrative": {
            "fitHeadline": "先看反覆吵架的核心模式",
            "coreHeadline": "先看關係還能不能修",
            "timingHeadline": "時機是用來降溫，不是逼結論",
            "actionHeadline": "下一步只降低一個惡性循環",
        },
    },
}


TRACK_EVIDENCE_CLUSTERS: dict[str, tuple[str, ...]] = {
    "serious_potential": ("attraction", "emotionalSafety", "communication"),
    "hot_cold_pattern": ("communication", "pressure", "emotionalSafety"),
    "relationship_development": ("attraction", "repair", "contactSituationPolicy"),
    "remaining_feeling": ("attraction", "emotionalSafety", "pressure"),
    "reconciliation_potential": ("repair", "pressure", "attraction"),
    "contact_readiness": ("timingContactReducer", "contactSituationPolicy", "pressure"),
    "breakup_cause": ("communication", "pressure", "emotionalSafety"),
    "realistic_continuation": ("repair", "contactSituationPolicy", "pressure"),
    "partner_current_view": ("attraction", "emotionalSafety", "communication"),
    "wait_or_release": ("pressure", "repair", "emotionalSafety", "contactSituationPolicy"),
    "reopen_contact": ("timingContactReducer", "contactSituationPolicy", "communication"),
    "proactive_contact_likelihood": ("contactSituationPolicy", "timingContactReducer", "emotionalSafety"),
    "cold_war_stuck_point": ("communication", "pressure", "contactSituationPolicy"),
    "contact_gain_or_loss": ("timingContactReducer", "pressure", "contactSituationPolicy"),
    "restore_interaction": ("repair", "communication", "contactSituationPolicy"),
    "conflict_cycle": ("pressure", "communication", "emotionalSafety"),
    "partner_continuation_intent": ("repair", "emotionalSafety", "pressure"),
    "repairability": ("repair", "pressure", "emotionalSafety"),
    "deescalation_next_step": ("communication", "pressure", "timingContactReducer"),
    "attraction_evidence": ("attraction",),
    "pressure_risk": ("pressure",),
    "emotional_safety": ("emotionalSafety",),
    "communication_pattern": ("communication",),
    "repair_condition": ("repair",),
    "timing_window": ("timingContactReducer", "timingWindowBand"),
    "contact_boundary": ("contactSituationPolicy", "contactStatus"),
    "self_protection": ("consultationSafety", "emotionalRisk", "contactSituationPolicy"),
    DEFAULT_TRACK: ("attraction", "pressure", "repair"),
}


TRACK_LABELS: dict[str, str] = {
    "serious_potential": "他是不是有認真可能",
    "hot_cold_pattern": "忽冷忽熱的原因",
    "relationship_development": "曖昧能不能往關係發展",
    "remaining_feeling": "他心裡還有沒有你",
    "reconciliation_potential": "復合機會",
    "contact_readiness": "恢復互動的時機",
    "breakup_cause": "分手真正卡住的原因",
    "realistic_continuation": "現實延續性",
    "partner_current_view": "他現在怎麼看待你",
    "wait_or_release": "要繼續等還是慢慢放下",
    "reopen_contact": "重新開口的方式",
    "proactive_contact_likelihood": "他會不會主動聯絡",
    "cold_war_stuck_point": "冷戰卡住的點",
    "contact_gain_or_loss": "現在開口加分還是扣分",
    "restore_interaction": "如何恢復互動",
    "conflict_cycle": "反覆吵架的核心模式",
    "partner_continuation_intent": "他是否還想繼續",
    "repairability": "關係能不能修復",
    "deescalation_next_step": "怎麼降低惡性循環",
    "attraction_evidence": "吸引力線索",
    "pressure_risk": "壓力風險",
    "emotional_safety": "情緒安全感",
    "communication_pattern": "溝通模式",
    "repair_condition": "修復條件",
    "timing_window": "時機與節奏",
    "contact_boundary": "聯絡邊界",
    "self_protection": "自我保護",
    DEFAULT_TRACK: "關係方向",
}


def _unique(items: list[str] | tuple[str, ...]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = str(item or "").strip()
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _policy_for_stage(stage_key: str) -> dict[str, Any]:
    policy = STATUS_POLICIES.get(stage_key) or STATUS_POLICIES["cold-war"]
    return deepcopy(policy)


def _condition_supported(condition: str, context: dict[str, Any], evidence_clusters: dict[str, dict[str, Any]] | None) -> bool:
    kind, _, value = str(condition).partition(":")
    if not kind or not value:
        return False
    if kind == "main_question":
        return str(context.get("main_question") or "") == value
    if kind == "desired_outcome":
        return str(context.get("desired_outcome") or "") == value
    if kind == "contact":
        return str(context.get("contact_status") or "") == value
    if kind == "evidence":
        clusters = evidence_clusters or {}
        if value == "third_party":
            return bool(clusters.get("thirdParty") or clusters.get("third_party"))
        if value == "strong_repair":
            repair = clusters.get("repair") or {}
            try:
                return float(repair.get("strongestStrength") or 0) >= 0.7
            except (TypeError, ValueError):
                return False
    return False


def _track_suppressed(
    track: str,
    policy: dict[str, Any],
    context: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]] | None,
) -> bool:
    suppressed = {str(item) for item in policy.get("suppressedTracks") or []}
    if track not in suppressed:
        return False
    exceptions = ((policy.get("allowedExceptions") or {}).get(track) or [])
    return not any(_condition_supported(str(condition), context, evidence_clusters) for condition in exceptions)


def evidence_clusters_for_tracks(tracks: list[str] | tuple[str, ...]) -> list[str]:
    clusters: list[str] = []
    for track in tracks:
        clusters.extend(TRACK_EVIDENCE_CLUSTERS.get(str(track), TRACK_EVIDENCE_CLUSTERS[DEFAULT_TRACK]))
    return _unique(clusters)


def resolve_relationship_status_answer_policy(
    context: dict[str, Any],
    evidence_clusters: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the resolved status-owned answer policy for one reading."""

    stage_key = str(context.get("relationship_stage") or "cold-war")
    question_key = str(context.get("main_question") or "")
    contact_key = str(context.get("contact_status") or "")
    policy = _policy_for_stage(stage_key)
    question_tracks = [
        str(item)
        for item in ((policy.get("questionTracks") or {}).get(question_key) or [])
        if item
    ]
    if not question_tracks:
        question_tracks = [str(item) for item in (policy.get("primaryTracks") or [])[:3] if item]
    primary_tracks = _unique([
        *question_tracks,
        *[str(item) for item in policy.get("primaryTracks") or []],
        DEFAULT_TRACK,
    ])
    resolved_tracks = [
        track
        for track in primary_tracks
        if not _track_suppressed(track, policy, context, evidence_clusters)
    ][:5]
    if not resolved_tracks:
        resolved_tracks = [DEFAULT_TRACK]
    suppressed_active = [
        str(track)
        for track in policy.get("suppressedTracks") or []
        if _track_suppressed(str(track), policy, context, evidence_clusters)
    ]
    evidence_cluster_keys = evidence_clusters_for_tracks(resolved_tracks)
    question_rewrite = str((policy.get("questionRewrites") or {}).get(question_key) or "")
    if not question_rewrite:
        question_rewrite = str((policy.get("questionRewrites") or {}).get("any-chance") or "這段關係現在最需要看什麼？")
    return {
        "version": POLICY_VERSION,
        "stageKey": stage_key,
        "questionKey": question_key,
        "contactKey": contact_key,
        "readerLabel": str(policy.get("readerLabel") or stage_key),
        "stagePremise": str(policy.get("stagePremise") or ""),
        "primaryTracks": [str(item) for item in policy.get("primaryTracks") or []],
        "secondaryTracks": [str(item) for item in policy.get("secondaryTracks") or []],
        "resolvedTracks": resolved_tracks,
        "resolvedTrackLabels": [TRACK_LABELS.get(track, track) for track in resolved_tracks],
        "suppressedTracks": suppressed_active,
        "suppressedTrackLabels": [TRACK_LABELS.get(track, track) for track in suppressed_active],
        "questionRewrite": question_rewrite,
        "sectionTitleOverrides": dict(policy.get("sectionTitleOverrides") or {}),
        "pageTopicRules": dict(policy.get("pageTopicRules") or {}),
        "requiredBoundaries": [str(item) for item in policy.get("requiredBoundaries") or []],
        "forbiddenVisibleEmphasis": [str(item) for item in policy.get("forbiddenVisibleEmphasis") or []],
        "evidenceClusterWeights": dict(policy.get("evidenceClusterWeights") or {}),
        "evidenceClusterKeys": evidence_cluster_keys,
        "finalNarrative": dict(policy.get("finalNarrative") or {}),
        "role": "status_owned_answer_topic_policy",
        "canCreateAstrologyConclusion": False,
    }


def relationship_status_policy_section_title(policy: dict[str, Any], chapter_id: str, fallback: str | None = None) -> str:
    overrides = policy.get("sectionTitleOverrides") if isinstance(policy, dict) else {}
    if isinstance(overrides, dict) and overrides.get(chapter_id):
        return str(overrides.get(chapter_id))
    return str(fallback or chapter_id)


def all_relationship_status_answer_policies() -> dict[str, dict[str, Any]]:
    return deepcopy(STATUS_POLICIES)
