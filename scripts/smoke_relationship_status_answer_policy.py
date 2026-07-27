#!/usr/bin/env python3
"""Smoke-test relationship-status answer policies and visible routing."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
    read_json,
)
from readable_interpretation.zh_tw import sanitize_public_answer_text  # noqa: E402
from relationship_status_answer_policy import (  # noqa: E402
    POLICY_VERSION,
    all_relationship_status_answer_policies,
    resolve_relationship_status_answer_policy,
)
from structured_runtime import load_structured_kb  # noqa: E402


BASE_READING_PATH = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
STAGES = ("ambiguous", "broke-up-recent", "broke-up-long", "cold-war", "crisis")
QUESTIONS = ("still-love-me", "any-chance", "when-to-contact", "what-did-i-do-wrong", "stay-or-let-go")
CONTACTS = ("blocked", "no-contact", "occasional-contact", "still-in-contact", "living-or-working-together")
SECTION_IDS = ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction")

EXPECTED_QUESTION_REWRITES = {
    "ambiguous": {
        "still-love-me": "他是不是有認真可能？",
        "any-chance": "這段曖昧會不會往關係發展？",
        "when-to-contact": "什麼時候適合讓互動更清楚？",
        "what-did-i-do-wrong": "為什麼他會忽冷忽熱？",
        "stay-or-let-go": "這段曖昧值得繼續觀察嗎？",
    },
    "broke-up-recent": {
        "when-to-contact": "什麼時間點比較容易恢復互動？",
    },
    "broke-up-long": {
        "any-chance": "這段緣分是否還有現實延續性？",
        "stay-or-let-go": "你該繼續等，還是慢慢放下？",
    },
    "cold-war": {
        "when-to-contact": "現在開口會加分還是扣分？",
    },
    "crisis": {
        "any-chance": "關係能不能修復？",
        "what-did-i-do-wrong": "你們反覆吵架的核心模式是什麼？",
    },
}

EXPECTED_STAGE_TRACKS = {
    "ambiguous": {"serious_potential", "hot_cold_pattern", "relationship_development"},
    "broke-up-recent": {"remaining_feeling", "reconciliation_potential", "contact_readiness", "breakup_cause"},
    "broke-up-long": {"realistic_continuation", "partner_current_view", "wait_or_release", "reopen_contact"},
    "cold-war": {"proactive_contact_likelihood", "cold_war_stuck_point", "contact_gain_or_loss", "restore_interaction"},
    "crisis": {"conflict_cycle", "partner_continuation_intent", "repairability", "deescalation_next_step"},
}

FORBIDDEN_INTERNAL_TERMS = (
    "relationshipStatusAnswerPolicy",
    "relationshipContextStoryline",
    "relationshipThesis",
    "stageLabel",
    "resolvedTracks",
    "副動力",
    "通道未斷",
    "通道受阻",
    "在「",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def visible_final_text(view_model: dict[str, Any]) -> str:
    sections = ((view_model.get("finalInterpretation") or {}).get("sections") or {})
    parts: list[str] = []
    for section_id in SECTION_IDS:
        section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else {}
        for field in ("headline", "meaning", "body", "nextMove", "caution"):
            parts.append(str(section.get(field) or ""))
    return sanitize_public_answer_text("\n".join(parts))


def assert_policy_shape() -> None:
    policies = all_relationship_status_answer_policies()
    require(set(policies) == set(STAGES), f"policy stages mismatch: {sorted(policies)}")
    for stage, policy in policies.items():
        label = f"policy:{stage}"
        require(policy.get("primaryTracks"), f"{label}: primaryTracks missing")
        require(policy.get("suppressedTracks"), f"{label}: suppressedTracks missing")
        require(set((policy.get("questionRewrites") or {})) == set(QUESTIONS), f"{label}: question rewrites incomplete")
        require(set((policy.get("pageTopicRules") or {})) == set(SECTION_IDS), f"{label}: page topic rules incomplete")
        require(policy.get("requiredBoundaries"), f"{label}: requiredBoundaries missing")
        require(policy.get("forbiddenVisibleEmphasis"), f"{label}: forbiddenVisibleEmphasis missing")


def assert_resolver_matrix() -> None:
    for stage in STAGES:
        for question in QUESTIONS:
            for contact in CONTACTS:
                policy = resolve_relationship_status_answer_policy(
                    {
                        "relationship_stage": stage,
                        "main_question": question,
                        "contact_status": contact,
                        "desired_outcome": "reconnect" if question in {"still-love-me", "when-to-contact"} else "decide",
                    },
                    {},
                )
                label = f"{stage}|{question}|{contact}"
                require(policy.get("version") == POLICY_VERSION, f"{label}: wrong policy version")
                require(policy.get("questionRewrite"), f"{label}: question rewrite missing")
                require(policy.get("resolvedTracks"), f"{label}: resolved tracks missing")
                require(policy.get("evidenceClusterKeys"), f"{label}: evidence clusters missing")
                require(not set(policy.get("resolvedTracks") or []) & set(policy.get("suppressedTracks") or []), f"{label}: suppressed track resolved")
                for track in EXPECTED_STAGE_TRACKS[stage]:
                    require(
                        track in set(policy.get("primaryTracks") or []),
                        f"{label}: stage primary track {track} missing",
                    )

    ambiguous_still = resolve_relationship_status_answer_policy(
        {"relationship_stage": "ambiguous", "main_question": "still-love-me", "contact_status": "still-in-contact"},
        {},
    )
    require("reconciliation_potential" not in ambiguous_still.get("resolvedTracks", []), "ambiguous still-love-me should not route to reconciliation")
    require("wait_or_release" in ambiguous_still.get("suppressedTracks", []), "ambiguous should suppress wait/release by default")

    recent_timing = resolve_relationship_status_answer_policy(
        {"relationship_stage": "broke-up-recent", "main_question": "when-to-contact", "contact_status": "occasional-contact"},
        {},
    )
    require("恢復互動" in recent_timing.get("questionRewrite", ""), "recent breakup timing wording must use restore-interaction language")
    require("會復合" not in recent_timing.get("questionRewrite", ""), "recent breakup timing wording must not promise reconciliation")

    long_boundary = resolve_relationship_status_answer_policy(
        {"relationship_stage": "broke-up-long", "main_question": "stay-or-let-go", "contact_status": "no-contact"},
        {},
    )
    require(any("懷念不等於現實延續" in item for item in long_boundary.get("requiredBoundaries") or []), "broke-up-long boundary missing")

    crisis_repair = resolve_relationship_status_answer_policy(
        {"relationship_stage": "crisis", "main_question": "any-chance", "contact_status": "still-in-contact"},
        {},
    )
    require("repairability" in crisis_repair.get("resolvedTracks", []), "crisis any-chance must prioritize repairability")
    require("conflict_cycle" in crisis_repair.get("resolvedTracks", []), "crisis any-chance must keep conflict-cycle topic")


def assert_visible_runtime_samples() -> None:
    base_fixture = read_json(BASE_READING_PATH)
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    for stage in STAGES:
        for question in QUESTIONS:
            fixture = copy.deepcopy(base_fixture)
            fixture["reading_id"] = f"status-policy-{stage}-{question}"
            context = fixture.setdefault("context", {})
            context["relationship_stage"] = stage
            context["main_question"] = question
            context["contact_status"] = "still-in-contact"
            context["emotional_risk"] = "calm"
            view_model = build_view_model(fixture, articles, claims, structured_kb)
            policy = view_model.get("relationshipStatusAnswerPolicy") or {}
            expected_rewrite = EXPECTED_QUESTION_REWRITES.get(stage, {}).get(question) or policy.get("questionRewrite")
            label = f"{stage}|{question}"

            require(policy.get("version") == POLICY_VERSION, f"{label}: view model policy missing")
            require(view_model.get("reading", {}).get("question") == expected_rewrite, f"{label}: reading question not policy rewrite")
            answer_layer = ((view_model.get("westernRelationshipCaseFile") or {}).get("answerLayer") or {})
            require(answer_layer.get("selectedQuestion") == expected_rewrite, f"{label}: answer layer question not policy rewrite")
            blueprint_policy = (view_model.get("readingBlueprint") or {}).get("statusAnswerPolicy") or {}
            require(blueprint_policy.get("questionRewrite") == expected_rewrite, f"{label}: blueprint policy missing rewrite")
            storyline_policy = (view_model.get("relationshipContextStoryline") or {}).get("statusAnswerPolicy") or {}
            require(storyline_policy.get("questionRewrite") == expected_rewrite, f"{label}: storyline policy missing rewrite")

            chapters = [str(chapter.get("title") or "") for chapter in (view_model.get("readingBlueprint") or {}).get("chapters") or []]
            for expected_title in (policy.get("sectionTitleOverrides") or {}).values():
                require(str(expected_title) in chapters, f"{label}: chapter title {expected_title!r} missing from {chapters}")

            visible_text = visible_final_text(view_model)
            for forbidden in FORBIDDEN_INTERNAL_TERMS:
                require(forbidden not in visible_text, f"{label}: visible text leaked {forbidden!r}")
            if stage == "ambiguous":
                for forbidden in ("復合機會", "放下還是等待", "第三者"):
                    require(forbidden not in visible_text, f"{label}: ambiguous visible text over-emphasized {forbidden!r}")
            if stage == "crisis":
                for forbidden in ("分手後", "追回", "復合機會"):
                    require(forbidden not in visible_text, f"{label}: crisis visible text became breakup-oriented with {forbidden!r}")


def main() -> int:
    assert_policy_shape()
    assert_resolver_matrix()
    assert_visible_runtime_samples()
    print("Relationship status answer policy smoke passed.")
    print(f"Statuses: {len(STAGES)}; resolver combos: {len(STAGES) * len(QUESTIONS) * len(CONTACTS)}; visible samples: {len(STAGES) * len(QUESTIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
