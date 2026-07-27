#!/usr/bin/env python3
"""Verify the Phase 2 spec-consumer boundary and one-input behavior."""

from __future__ import annotations

import copy
import hashlib
import json
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
from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FinalNarrativeComposer,
    FinalNarrativeSemanticInput,
    SectionNarrativeSpecError,
)
from structured_runtime import load_structured_kb  # noqa: E402


BASE_READING_PATH = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
COMPOSER_PATH = ROOT / "scripts" / "readable_interpretation" / "final_narrative_composer.py"
ZH_TW_PATH = ROOT / "scripts" / "readable_interpretation" / "zh_tw.py"
SECTION_IDS = ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction")
CONTEXT_FREE_IDS = ("chart-positioning", "relationship-fit")
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def section_fingerprint(view_model: dict[str, Any], section_id: str) -> str:
    section = (((view_model.get("finalInterpretation") or {}).get("sections") or {}).get(section_id) or {})
    return stable_hash({field: str(section.get(field) or "") for field in VISIBLE_FIELDS})


def build_case(
    reading: dict[str, Any],
    *,
    stage: str,
    question: str,
    contact: str,
    articles: dict[str, Any],
    claims: dict[str, Any],
    structured_kb: dict[str, Any],
) -> dict[str, Any]:
    fixture = copy.deepcopy(reading)
    fixture["reading_id"] = f"phase2-{stage}-{question}-{contact}-{fixture.get('reading_id', 'case')}"
    context = fixture.setdefault("context", {})
    context["relationship_stage"] = stage
    context["main_question"] = question
    context["contact_status"] = contact
    context["emotional_risk"] = "calm"
    return build_view_model(fixture, articles, claims, structured_kb)


def assert_source_boundary() -> None:
    composer_source = COMPOSER_PATH.read_text(encoding="utf-8")
    zh_source = ZH_TW_PATH.read_text(encoding="utf-8")
    for forbidden in ("section_directives", "context_story_", "story_bridge", "self.directive", "story_field"):
        require(forbidden not in composer_source, f"composer still exposes global paragraph path: {forbidden}")
    for forbidden in ("combined_directives", "section_directives=combined_directives"):
        require(forbidden not in zh_source, f"final renderer still merges paragraph overrides: {forbidden}")
    require("section_specs=section_specs" in zh_source, "final renderer does not pass specs into the composer")


def assert_fail_fast(view_model: dict[str, Any]) -> None:
    context = view_model.get("context") or {}
    valid_bundle = copy.deepcopy(view_model.get("sectionNarrativeSpecs") or {})
    invalid_bundle = copy.deepcopy(valid_bundle)
    invalid_bundle["sections"]["chart-positioning"]["context"]["contactKey"] = "no-contact"
    semantic = FinalNarrativeSemanticInput(
        question_key=str(context.get("main_question") or ""),
        stage_key=str(context.get("relationship_stage") or ""),
        contact_key=str(context.get("contact_status") or ""),
        section_specs=invalid_bundle,
    )
    try:
        FinalNarrativeComposer.from_semantic_input(semantic)
    except SectionNarrativeSpecError:
        pass
    else:
        raise AssertionError("invalid chart context reached the visible composer")


def assert_one_input_behavior(
    base_reading: dict[str, Any],
    *,
    articles: dict[str, Any],
    claims: dict[str, Any],
    structured_kb: dict[str, Any],
) -> dict[str, Any]:
    base = build_case(
        base_reading,
        stage="cold-war",
        question="still-love-me",
        contact="no-contact",
        articles=articles,
        claims=claims,
        structured_kb=structured_kb,
    )
    variants = {
        "stage": build_case(
            base_reading,
            stage="broke-up-long",
            question="still-love-me",
            contact="no-contact",
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        ),
        "question": build_case(
            base_reading,
            stage="cold-war",
            question="any-chance",
            contact="no-contact",
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        ),
        "contact": build_case(
            base_reading,
            stage="cold-war",
            question="still-love-me",
            contact="blocked",
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        ),
    }
    for axis, variant in variants.items():
        for section_id in CONTEXT_FREE_IDS:
            require(
                section_fingerprint(base, section_id) == section_fingerprint(variant, section_id),
                f"{axis} leaked into context-free {section_id}",
            )
    require(
        section_fingerprint(base, "core-answer") != section_fingerprint(variants["question"], "core-answer"),
        "question change did not alter the core answer",
    )
    require(
        section_fingerprint(base, "timing-reading") != section_fingerprint(variants["contact"], "timing-reading"),
        "contact change did not alter timing",
    )
    require(
        section_fingerprint(base, "action-direction") != section_fingerprint(variants["contact"], "action-direction"),
        "contact change did not alter the action",
    )
    require(
        any(
            section_fingerprint(base, section_id) != section_fingerprint(variants["stage"], section_id)
            for section_id in ("core-answer", "timing-reading", "action-direction")
        ),
        "stage change did not alter any context-owned section",
    )
    return base


def assert_chart_input_behavior(base: dict[str, Any]) -> None:
    context = base.get("context") or {}
    original_bundle = copy.deepcopy(base.get("sectionNarrativeSpecs") or {})
    changed_bundle = copy.deepcopy(original_bundle)
    chart_slots = changed_bundle["sections"]["chart-positioning"]["semanticSlots"]
    chart_slots["personAEmotionalNeed"] = "你需要很明確的陪伴，才容易真正放鬆"
    chart_slots["personACommunicationStyle"] = "你習慣先整理好重點，再直接說出需要"
    chart_slots["personBPressureResponse"] = "他有壓力時會先拉開距離，等情緒平穩才回來談"
    fit_slots = changed_bundle["sections"]["relationship-fit"]["semanticSlots"]
    fit_slots["archetypeTitle"] = "溝通修復型"
    fit_slots["primaryDynamicKey"] = "communication_repair"
    fit_slots["secondaryDynamicKeys"] = ["emotional_safety"]

    def composer(bundle: dict[str, Any]) -> FinalNarrativeComposer:
        return FinalNarrativeComposer.from_semantic_input(
            FinalNarrativeSemanticInput(
                question_key=str(context.get("main_question") or ""),
                stage_key=str(context.get("relationship_stage") or ""),
                contact_key=str(context.get("contact_status") or ""),
                section_specs=bundle,
            )
        )

    original = composer(original_bundle)
    require(
        original.fact_values("chart-positioning", "user-emotional-need"),
        "typed chart emotional-need fact is missing",
    )
    require(
        original.fact_values("relationship-fit", "relationship-archetype"),
        "typed relationship-archetype fact is missing",
    )
    try:
        composer(changed_bundle)
    except SectionNarrativeSpecError as exc:
        require("source spec fingerprint is stale" in str(exc), "stale prose slots failed for the wrong reason")
    else:
        raise AssertionError("legacy prose slots changed without updating the typed fact contract")


def main() -> int:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    base_reading = read_json(BASE_READING_PATH)
    assert_source_boundary()
    base = assert_one_input_behavior(
        base_reading,
        articles=articles,
        claims=claims,
        structured_kb=structured_kb,
    )
    assert_fail_fast(base)
    assert_chart_input_behavior(base)
    print("Section narrative Phase 2 smoke passed.")
    print("- missing or invalid specs fail before visible rendering")
    print("- chart-positioning and relationship-fit ignore context-only changes")
    print("- question, stage, and contact metamorphic behavior verified")
    print("- stale legacy prose slots cannot bypass the typed fact contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
