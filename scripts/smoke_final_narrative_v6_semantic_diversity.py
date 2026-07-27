#!/usr/bin/env python3
"""Semantic diversity checks for final relationship narratives."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FINAL_NARRATIVE_COMPOSER_VERSION,
    FinalNarrativeComposer,
    FinalNarrativeSemanticInput,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    build_final_narrative_fact_contract,
    make_fact,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    core_answer_sentence_trace,
)
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    QUESTION_HEADLINES,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (  # noqa: E402
    timing_sentence_trace,
)
from readable_interpretation.section_narrative_spec import (  # noqa: E402
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
    build_spec,
    synthetic_evidence,
    validate_section_narrative_specs,
)


SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
SECTION_IDS = ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction")
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
QUESTIONS = ("still-love-me", "any-chance", "when-to-contact", "what-did-i-do-wrong", "stay-or-let-go")
STAGES = ("cold-war", "broke-up-recent", "broke-up-long", "crisis", "ambiguous")
CONTACTS = ("blocked", "no-contact", "occasional-contact", "still-in-contact", "living-or-working-together")
DYNAMICS = (
    "emotional_safety",
    "saturn_pressure",
    "communication_repair",
    "attraction_pursuit",
    "action_conflict",
    "identity_rhythm",
    "outer_intensity",
)
SECONDARY_ROLES = ("amplifier", "blocker", "repairLever", "softener", "timingActivator")
RISKS = ("standard", "anxiety_guard", "self_blame_guard", "stability_first", "safety_first")
TIMING = ("avoid_push", "low_pressure_message", "observe_for_soft_window", "observe_only", "not_calculated")

SYNTHETIC_FACT_ROLES = {
    "chart-positioning": (
        ("user-emotional-need", "personAEmotionalNeed"),
        ("user-communication-style", "personACommunicationStyle"),
        ("partner-pressure-response", "personBPressureResponse"),
        ("precision-mode", "precisionMode"),
    ),
    "relationship-fit": (
        ("relationship-archetype", "archetypeTitle"),
        ("primary-dynamic", "primaryDynamicKey"),
        ("secondary-dynamic", "secondaryDynamicKeys"),
        ("attraction-signal", "attractionSignals"),
        ("friction-signal", "frictionSignals"),
        ("growth-signal", "growthSignals"),
    ),
    "core-answer": (
        ("question", "questionKey"),
        ("relationship-stage", "relationshipStage"),
        ("contact-status", "contactStatus"),
        ("answer-track", "answerTrackKeys"),
        ("central-dynamic", "centralDynamicKey"),
        ("partner-relationship-need", "partnerRelationshipNeedKey"),
        ("evidence-signal", "answerEvidenceSignals"),
        ("observable-sign", "observableSigns"),
        ("uncertainty-level", "uncertaintyLevel"),
    ),
    "timing-reading": (
        ("question", "questionKey"),
        ("contact-status", "contactStatus"),
        ("timing-posture", "timingPostureKey"),
        ("recommended-action", "recommendedAction"),
        ("timing-band", "topBand"),
        ("contact-posture", "contactPostureKey"),
        ("precise-dates-available", "preciseDatesAvailable"),
        ("timing-window", "topWindowKey"),
    ),
    "action-direction": (
        ("question", "questionKey"),
        ("contact-status", "contactStatus"),
        ("action-purpose", "actionPurposeKey"),
        ("action-mode", "actionMode"),
        ("completion-boundary", "completionBoundaryKey"),
        ("repair-lever", "repairLeverKey"),
        ("stop-condition", "stopConditionKey"),
        ("contact-posture", "contactPostureKey"),
        ("blocked-action", "blockedActions"),
    ),
}

SYNTHETIC_ANSWER_TRACKS = {
    "still-love-me": "remaining-feeling",
    "any-chance": "reconciliation-potential",
    "when-to-contact": "contact-readiness",
    "what-did-i-do-wrong": "breakup-cause",
    "stay-or-let-go": "wait-or-release",
}

SYNTHETIC_CONTACT_POSTURES = {
    "blocked": "boundary-first",
    "no-contact": "observe-channel",
    "occasional-contact": "test-low-pressure",
    "still-in-contact": "watch-initiation",
    "living-or-working-together": "protect-shared-space",
}

FORBIDDEN_TERMS = (
    "判讀",
    "副動力",
    "承接度",
    "承接量",
    "可觀察",
    "通道未斷",
    "通道受阻",
    "壓力測試",
    "行動速度",
    "關係答案",
    "relationshipThesis",
    "relationshipCaseModel",
    "dynamicInteractionPlan",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def synthetic_fact_contract(sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    facts_by_section = {}
    for section_id, role_slots in SYNTHETIC_FACT_ROLES.items():
        evidence_ids = [
            str(item.get("id") or "")
            for item in sections[section_id].get("evidence") or []
            if isinstance(item, dict) and item.get("id")
        ]
        require(bool(evidence_ids), f"{section_id}: synthetic facts require evidence")
        slots = sections[section_id].get("semanticSlots") or {}

        def value_for(role: str, source_slot: str) -> Any:
            overrides = {
                "user-emotional-need": "moon.virgo",
                "user-communication-style": "mercury.libra",
                "partner-pressure-response": "mars.cancer",
                "relationship-archetype": "growth-through-friction",
            }
            if role in overrides:
                return overrides[role]
            value = slots.get(source_slot)
            if role == "precise-dates-available":
                return "available" if value is True else "unavailable"
            if isinstance(value, list):
                value = value[0] if value else "unknown"
            if isinstance(value, dict):
                return value.get("key") or "unknown"
            return value or "unknown"

        facts_by_section[section_id] = [
            make_fact(
                section_id=section_id,
                role=role,
                value_key=value_for(role, source_slot),
                source_slot=source_slot,
                evidence_ids=[evidence_ids[0]],
            )
            for role, source_slot in role_slots
        ]
    return build_final_narrative_fact_contract(
        sections,
        facts_by_section,
        compatibility_prose_slots={section_id: () for section_id in SECTION_IDS},
    )


def section(view_model: dict[str, Any], section_id: str) -> dict[str, str]:
    source = (((view_model.get("finalInterpretation") or {}).get("sections") or {}).get(section_id) or {})
    return {field: str(source.get(field) or "") for field in VISIBLE_FIELDS}


def final_fact_value(view_model: dict[str, Any], section_id: str, role: str) -> str:
    contract = ((view_model.get("finalInterpretation") or {}).get("factContract") or {})
    section_contract = ((contract.get("sections") or {}).get(section_id) or {})
    for fact in section_contract.get("facts") or []:
        if isinstance(fact, dict) and fact.get("role") == role:
            return str(fact.get("valueKey") or "")
    return ""


def field_values(view_models: Iterable[dict[str, Any]], section_id: str, field: str) -> list[str]:
    return [section(view_model, section_id).get(field, "") for view_model in view_models]


def section_signatures(view_models: Iterable[dict[str, Any]], section_id: str) -> set[tuple[str, ...]]:
    return {
        tuple(normalize(fields.get(field)) for field in VISIBLE_FIELDS)
        for fields in (section(view_model, section_id) for view_model in view_models)
    }


def final_sentences(view_models: Iterable[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for view_model in view_models:
        for section_id in SECTION_IDS:
            if section_id == "relationship-fit":
                continue
            fields = section(view_model, section_id)
            for value in fields.values():
                for sentence in re.split(r"[。！？!?]\s*", value):
                    normalized = normalize(sentence)
                    if len(normalized) >= 14:
                        counter[normalized] += 1
    return counter


def assert_generated_diversity(view_models: list[dict[str, Any]]) -> None:
    failures: list[str] = []
    body_minimums = {
        "chart-positioning": 4,
        "relationship-fit": 10,
        "core-answer": 10,
        "timing-reading": 24,
        # The action body owns one completion boundary and therefore varies by
        # the selected action mode.
        "action-direction": 5,
    }
    for section_id, minimum in body_minimums.items():
        unique_bodies = len(set(field_values(view_models, section_id, "body")))
        if unique_bodies < minimum:
            failures.append(f"{section_id}: body variation too low: {unique_bodies} < {minimum}")

    full_section_minimums = {
        "chart-positioning": 5,
        "relationship-fit": 10,
        "core-answer": 28,
        "timing-reading": 28,
        "action-direction": 28,
    }
    for section_id, minimum in full_section_minimums.items():
        unique_sections = len(section_signatures(view_models, section_id))
        if unique_sections < minimum:
            failures.append(
                f"{section_id}: full-page variation too low: {unique_sections} < {minimum}"
            )

    core_headlines_by_track: dict[str, set[str]] = defaultdict(set)
    core_tracks_by_headline: dict[str, set[str]] = defaultdict(set)
    for view_model in view_models:
        headline = section(view_model, "core-answer")["headline"]
        trace = core_answer_sentence_trace(headline)
        if not trace or trace.get("role") != "answer-track":
            failures.append(f"core-answer: untraceable headline: {headline}")
            continue
        track = str(trace.get("valueKey") or "")
        core_headlines_by_track[track].add(headline)
        core_tracks_by_headline[headline].add(track)
    if len(core_headlines_by_track) < 10:
        failures.append(
            f"core-answer: selected answer-track coverage too low: {len(core_headlines_by_track)} < 10"
        )
    for track, headlines in core_headlines_by_track.items():
        if len(headlines) != 1:
            failures.append(
                f"core-answer: one answer track produced multiple headlines: {track} -> {sorted(headlines)}"
            )
    for headline, tracks in core_tracks_by_headline.items():
        if len(tracks) != 1:
            failures.append(
                f"core-answer: different answer tracks collapsed into one headline: {headline} <- {sorted(tracks)}"
            )

    headline_minimums = {
        # Action headlines own the selected question only. Mode, response, and
        # stop-condition variation belongs to their dedicated fields.
        "action-direction": len(QUESTIONS),
        "relationship-fit": 8,
    }
    for section_id, minimum in headline_minimums.items():
        unique_headlines = len(set(field_values(view_models, section_id, "headline")))
        if unique_headlines < minimum:
            failures.append(f"{section_id}: headline variation too low: {unique_headlines} < {minimum}")

    sentences = final_sentences(view_models)
    stable_section_boundaries = {
        "目前資料不足以支持指定日期，重點放在互動條件是否成熟",
        "這些是常見反應，真正怎麼相處仍要看兩個人的實際選擇",
    }
    repeated = [
        (sentence, count)
        for sentence, count in sentences.items()
        if count > 30
        and sentence not in stable_section_boundaries
        and (timing_sentence_trace(sentence) or {}).get("role")
        != "precise-dates-available"
        and (core_answer_sentence_trace(sentence) or {}).get("role")
        != "uncertainty-level"
    ]
    if repeated:
        detail = "; ".join(f"{count}x {sentence[:60]}" for sentence, count in sorted(repeated, key=lambda item: item[1], reverse=True)[:8])
        failures.append(f"sentence-slot repetition too high: {detail}")

    for view_model in view_models:
        text = "\n".join(
            field
            for section_id in SECTION_IDS
            for field in section(view_model, section_id).values()
        )
        for term in FORBIDDEN_TERMS:
            if term in text:
                failures.append(f"{view_model.get('id')}: forbidden final term leaked: {term}")

    contact_to_action_meanings: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for view_model in view_models:
        context = view_model.get("context") or {}
        contact = str(context.get("contact_status") or "")
        repair_lever = final_fact_value(view_model, "action-direction", "repair-lever")
        action_meaning = normalize(section(view_model, "action-direction").get("meaning"))
        if contact and repair_lever and action_meaning:
            contact_to_action_meanings[contact][repair_lever].add(action_meaning)
    for contact, dynamic_map in contact_to_action_meanings.items():
        if len(dynamic_map) >= 3:
            meaning_count = len({value for values in dynamic_map.values() for value in values})
            if meaning_count != 1:
                failures.append(
                    f"{contact}: hidden repair lever leaked into action-page meaning"
                )

    source_metrics = {
        "actionGuidance.body": len({
            normalize((((vm.get("actionGuidance") or {}).get("readableInterpretation") or {}).get("body")))
            for vm in view_models
        }),
        "actionGuidance.nextMove": len({
            normalize((((vm.get("actionGuidance") or {}).get("readableInterpretation") or {}).get("nextMove")))
            for vm in view_models
        }),
        "fightLandmines.firstTrigger": len({
            normalize(((((vm.get("fightLandmines") or {}).get("items") or [{}])[0] or {}).get("trigger")))
            for vm in view_models
        }),
        "survivalGuide.firstBody": len({
            normalize(((((vm.get("survivalGuide") or {}).get("items") or [{}])[0] or {}).get("body")))
            for vm in view_models
        }),
    }
    source_minimums = {
        "actionGuidance.body": 30,
        "actionGuidance.nextMove": 30,
        "fightLandmines.firstTrigger": 14,
        "survivalGuide.firstBody": 8,
    }
    for key, minimum in source_minimums.items():
        if source_metrics.get(key, 0) < minimum:
            failures.append(f"upstream source variation too low for {key}: {source_metrics.get(key, 0)} < {minimum}")

    require(not failures, "generated semantic diversity failed:\n- " + "\n- ".join(failures[:20]))


def synthetic_composer_records(limit: int = 875) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    signal_pairs = {
        "emotional_safety": ("Moon-Venus", "Moon", "Venus", "attraction"),
        "saturn_pressure": ("Venus-Saturn", "Venus", "Saturn", "friction"),
        "communication_repair": ("Mercury-Saturn", "Mercury", "Saturn", "friction"),
        "attraction_pursuit": ("Venus-Mars", "Venus", "Mars", "attraction"),
        "action_conflict": ("Mercury-Mars", "Mercury", "Mars", "friction"),
        "identity_rhythm": ("Sun-Moon", "Sun", "Moon", "attraction"),
        "outer_intensity": ("Outer-planet intensity", "Pluto", "Moon", "friction"),
    }

    def semantic_signal(
        dynamic_key: str,
        *,
        evidence_id: str,
        source_kind: str | None = None,
        aspect_key: str = "Square",
        contact_type: str = "hard",
    ) -> dict[str, Any]:
        pair_key, point_a, point_b, default_kind = signal_pairs[dynamic_key]
        kind = source_kind or default_kind
        key = (
            f"{kind}:{pair_key}:personA:{point_a}>personB:{point_b}:"
            f"{aspect_key}:{contact_type}"
        )
        return {
            "key": key,
            "pairKey": pair_key,
            "sourceKind": kind,
            "personAPoint": point_a,
            "personBPoint": point_b,
            "directionKey": f"personA:{point_a}>personB:{point_b}",
            "aspectKey": aspect_key,
            "contactType": contact_type,
            "strength": 0.82,
            "strengthBand": "dominant",
            "everydaySignal": "靠近時會出現一個可以被看見的反應。",
            "meaning": "這個反應要放回現實互動理解。",
            "advice": "一次只處理一件事。",
            "evidenceIds": [evidence_id],
        }

    aspects = (
        ("Conjunction", "conjunction"),
        ("Sextile", "soft"),
        ("Trine", "soft"),
        ("Square", "hard"),
        ("Opposition", "hard"),
    )
    partner_moon_signs = (
        "aries",
        "taurus",
        "gemini",
        "cancer",
        "leo",
        "virgo",
        "libra",
        "scorpio",
        "sagittarius",
        "capricorn",
        "aquarius",
        "pisces",
    )
    for question_index, question in enumerate(QUESTIONS):
        for stage_index, stage in enumerate(STAGES):
            for contact_index, contact in enumerate(CONTACTS):
                for index, dynamic in enumerate(DYNAMICS):
                    secondary = DYNAMICS[(index + 2) % len(DYNAMICS)]
                    role = SECONDARY_ROLES[(index + len(question)) % len(SECONDARY_ROLES)]
                    risk = RISKS[(index + len(stage)) % len(RISKS)]
                    timing = TIMING[(index + len(contact)) % len(TIMING)]
                    effective_timing = "avoid_push" if contact == "blocked" else timing
                    timing_month = 7 + ((index + len(question) + len(stage) + len(contact)) % 6)
                    timing_third = ("early", "mid", "late")[(index + len(stage) + len(contact)) % 3]
                    timing_category = (
                        "softening",
                        "conflict-risk",
                        "communication-opening",
                        "boundary-pressure",
                        "general-climate",
                    )[(index + len(question) + len(stage)) % 5]
                    timing_window_key = (
                        f"2026-{timing_month:02d}-{timing_third}|{timing_category}|venus-moon|square"
                    )
                    method_payload = {"methodClaimIds": ["synthetic-phase2-method"]}

                    def evidence(section_id: str, domain: str) -> dict[str, Any]:
                        return synthetic_evidence(
                            evidence_id=f"{section_id}-{domain}",
                            domain=domain,
                            source="synthetic-phase2",
                            proposition=f"Synthetic {domain} evidence for composer stress testing.",
                            payload=method_payload,
                        )

                    def case_model_trace(section_id: str) -> dict[str, Any]:
                        return {
                            "version": "relationship-case-model-trace-v1",
                            "caseModelVersion": "relationship-case-model-v1",
                            "sectionId": section_id,
                            "primaryDynamicKey": dynamic,
                            "secondaryDynamicKey": secondary,
                            "secondaryRole": role,
                            "grammarId": f"synthetic-{dynamic}-{secondary}-{role}",
                            "grammarMode": "composed",
                            "caseEvidenceIds": ["synthetic-primary", "synthetic-secondary"],
                        }

                    fit_attraction = semantic_signal("emotional_safety", evidence_id="fit-synastry", source_kind="attraction")
                    fit_friction = semantic_signal(dynamic, evidence_id="fit-synastry", source_kind="friction")
                    fit_growth = semantic_signal("communication_repair", evidence_id="fit-synastry", source_kind="growth")
                    core_aspect, core_contact_type = aspects[
                        (stage_index + contact_index) % len(aspects)
                    ]
                    core_signal = semantic_signal(
                        dynamic,
                        evidence_id="core-synastry",
                        aspect_key=core_aspect,
                        contact_type=core_contact_type,
                    )
                    partner_moon_sign = partner_moon_signs[
                        (
                            question_index
                            + stage_index
                            + contact_index
                            + index
                        )
                        % len(partner_moon_signs)
                    ]

                    action_mode = {
                        "blocked": "boundary-only",
                        "no-contact": "observe-or-single-low-stimulation-test",
                        "occasional-contact": "small-bid-response-led",
                        "still-in-contact": "tone-repair-in-existing-channel",
                        "living-or-working-together": "shared-space-boundary",
                    }[contact]
                    sections = {
                        "chart-positioning": build_spec(
                            section_id="chart-positioning",
                            context={},
                            semantic_slots={
                                "personAEmotionalNeed": "你需要對方回應清楚，心裡才不會一直懸著",
                                "personACommunicationStyle": "你需要先想清楚再開口",
                                "personBPressureResponse": "他緊張時會先把反應收起來",
                                "precisionMode": "chart-only",
                            },
                            concept_keys=["individual_relationship_style"],
                            evidence=[
                                evidence("chart", "userNatal"),
                                evidence("chart", "partnerNatal"),
                                evidence("chart", "method"),
                            ],
                        ),
                        "relationship-fit": build_spec(
                            section_id="relationship-fit",
                            context={},
                            semantic_slots={
                                "archetypeTitle": "需要磨合的關係",
                                "attractionKeys": ["synthetic-attraction"],
                                "frictionKeys": ["synthetic-friction"],
                                "growthKeys": ["synthetic-growth"],
                                "primaryDynamicKey": dynamic,
                                "secondaryDynamicKeys": [secondary],
                                "attractionSignals": [fit_attraction],
                                "frictionSignals": [fit_friction],
                                "growthSignals": [fit_growth],
                                "fitSignature": "|".join(
                                    str(item.get("key") or "")
                                    for item in (fit_attraction, fit_friction, fit_growth)
                                ),
                            },
                            concept_keys=["relationship_dynamic"],
                            evidence=[evidence("fit", "synastry"), evidence("fit", "method")],
                        ),
                        "core-answer": build_spec(
                            section_id="core-answer",
                            context={"stageKey": stage, "questionKey": question, "contactKey": contact},
                            semantic_slots={
                                "questionKey": question,
                                "relationshipStage": stage,
                                "contactStatus": contact,
                                "questionRewrite": question,
                                "answerTrackKeys": [SYNTHETIC_ANSWER_TRACKS[question]],
                                "centralDynamicKey": dynamic,
                                "secondaryDynamicKey": secondary,
                                "partnerRelationshipNeedKey": f"moon.{partner_moon_sign}",
                                "observableSignKeys": ["partner-continues-without-prompt", "reply-only-after-user-prompt"],
                                "observableSigns": [
                                    {"key": "partner-continues-without-prompt", "behavior": f"{dynamic} 的第一個實際反應是否變穩"},
                                    {"key": "reply-only-after-user-prompt", "behavior": f"{secondary} 是否讓對話更容易被接住"},
                                ],
                                "uncertaintyLevel": "medium",
                                "centralEvidenceSignal": core_signal,
                                "answerEvidenceSignals": [core_signal],
                            },
                            concept_keys=["question_answer"],
                            evidence=[
                                evidence("core", "synastry"),
                                evidence("core", "relationshipContext"),
                                evidence("core", "answerPolicy"),
                                evidence("core", "method"),
                            ],
                            case_model_trace=case_model_trace("core-answer"),
                        ),
                        "timing-reading": build_spec(
                            section_id="timing-reading",
                            context={"stageKey": stage, "questionKey": question, "contactKey": contact},
                            semantic_slots={
                                "questionKey": question,
                                "contactStatus": contact,
                                "timingPostureKey": effective_timing,
                                "recommendedAction": effective_timing,
                                "topBand": "neutral",
                                "contactPostureKey": SYNTHETIC_CONTACT_POSTURES[contact],
                                "preciseDatesAvailable": False,
                                "sampleCount": 0,
                                "topWindowKey": timing_window_key,
                            },
                            concept_keys=["timing_activation"],
                            evidence=[
                                evidence("timing", "timing"),
                                evidence("timing", "relationshipContext"),
                                evidence("timing", "method"),
                            ],
                            case_model_trace=case_model_trace("timing-reading"),
                        ),
                        "action-direction": build_spec(
                            section_id="action-direction",
                            context={"stageKey": stage, "questionKey": question, "contactKey": contact},
                            semantic_slots={
                                "questionKey": question,
                                "contactStatus": contact,
                                "actionPurposeKey": action_mode,
                                "actionMode": action_mode,
                                "completionBoundaryKey": action_mode,
                                "repairLeverKey": dynamic,
                                "stopConditionKey": risk,
                                "contactPostureKey": SYNTHETIC_CONTACT_POSTURES[contact],
                                "blockedActions": ["long-explanation"],
                            },
                            concept_keys=["next_action"],
                            evidence=[
                                evidence("action", "relationshipContext"),
                                evidence("action", "actionPolicy"),
                                evidence("action", "method"),
                            ],
                            case_model_trace=case_model_trace("action-direction"),
                        ),
                    }
                    section_specs = {
                        "version": SECTION_NARRATIVE_SPEC_VERSION,
                        "rendererConsumesSpecs": True,
                        "rendererVersion": SECTION_NARRATIVE_RENDERER_VERSION,
                        "sections": sections,
                        "finalNarrativeFacts": synthetic_fact_contract(sections),
                        "validation": validate_section_narrative_specs(sections),
                    }
                    semantic = FinalNarrativeSemanticInput(
                        question_key=question,
                        stage_key=stage,
                        contact_key=contact,
                        section_specs=section_specs,
                    )
                    composer = FinalNarrativeComposer.from_semantic_input(semantic)
                    records.append(
                        {
                            "id": f"{question}:{stage}:{contact}:{dynamic}:{secondary}:{role}",
                            "sections": {
                                section_id: composer.render_section(section_id)
                                for section_id in SECTION_IDS
                            },
                        }
                    )
                    if len(records) >= limit:
                        return records
    return records


def assert_synthetic_stress(records: list[dict[str, Any]]) -> None:
    failures: list[str] = []
    require(len(records) >= 200, f"synthetic stress matrix too small: {len(records)} < 200")
    for section_id in SECTION_IDS:
        bodies = [
            normalize(getattr(record["sections"][section_id], "body", ""))
            for record in records
        ]
        unique = len(set(bodies))
        minimum = {
            "chart-positioning": 1,
            "relationship-fit": 6,
            "core-answer": 35,
            "timing-reading": 40,
            "action-direction": 5,
        }[section_id]
        if unique < minimum:
            failures.append(f"synthetic {section_id} bodies too repetitive: {unique} < {minimum}")
    action_full_pages = {
        tuple(
            normalize(getattr(record["sections"]["action-direction"], field, ""))
            for field in VISIBLE_FIELDS
        )
        for record in records
    }
    if len(action_full_pages) < 120:
        failures.append(
            f"synthetic action full pages too repetitive: {len(action_full_pages)} < 120"
        )
    action_headlines_by_question: dict[str, set[str]] = defaultdict(set)
    for record in records:
        question = str(record["id"]).split(":", 1)[0]
        headline = normalize(getattr(record["sections"]["action-direction"], "headline", ""))
        action_headlines_by_question[question].add(headline)
        expected = {normalize(value) for value in QUESTION_HEADLINES[question]}
        if headline not in expected:
            failures.append(f"synthetic action headline escaped question ownership: {question}: {headline}")
    selected_headlines = {
        headline
        for question in QUESTIONS
        for headline in action_headlines_by_question[question]
    }
    if any(not action_headlines_by_question[question] for question in QUESTIONS):
        failures.append("synthetic action headline coverage is incomplete")
    if len(selected_headlines) != len(QUESTIONS):
        failures.append(
            "synthetic action headlines collapse across question-owned values: "
            f"{len(selected_headlines)} < {len(QUESTIONS)}"
        )
    require(not failures, "synthetic semantic stress failed:\n- " + "\n- ".join(failures[:20]))


def main() -> int:
    failures: list[str] = []
    generated_scenarios = read_json(SCENARIOS_PATH)
    synthetic_records = synthetic_composer_records()
    try:
        require(
            FINAL_NARRATIVE_COMPOSER_VERSION == "final-narrative-composer-v21",
            "composer version is not V21",
        )
        assert_generated_diversity(generated_scenarios)
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_synthetic_stress(synthetic_records)
    except AssertionError as exc:
        failures.append(str(exc))
    if failures:
        print("Final narrative V21 semantic diversity smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Final narrative V21 semantic diversity smoke passed")
    print(f"- generated scenarios: {len(generated_scenarios)}")
    print(f"- synthetic combinations checked: {len(synthetic_records)}")
    print("- non-boundary sentence repeat ceiling: <= 30 across the fixture corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
