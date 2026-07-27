"""Section-owned semantic contracts for the paid relationship reading.

The final composer consumes only validated contracts from this module. Global
storyline data may route the context-owned specs, but it cannot write or
override reader-facing paragraphs.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from .final_narrative_fact_contract import (
    build_final_narrative_fact_contract,
    canonical_value_key,
    make_fact,
)
from .schema import NarrativeEvidence, RelationshipCaseModelTrace, SectionNarrativeSpec


LEGACY_SECTION_NARRATIVE_SPEC_VERSION = "section-narrative-spec-v1"
EVIDENCE_DEPTH_SECTION_NARRATIVE_SPEC_VERSION = "section-narrative-spec-v2"
SECTION_NARRATIVE_SPEC_VERSION = "section-narrative-spec-v4"
SECTION_NARRATIVE_RENDERER_VERSION = "section-spec-renderer-v6"
RELATIONSHIP_CASE_MODEL_TRACE_VERSION = "relationship-case-model-trace-v1"
SUPPORTED_SECTION_NARRATIVE_SPEC_VERSIONS = (
    LEGACY_SECTION_NARRATIVE_SPEC_VERSION,
    EVIDENCE_DEPTH_SECTION_NARRATIVE_SPEC_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
)
SECTION_NARRATIVE_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)
CASE_MODEL_TRACE_SECTION_IDS = (
    "core-answer",
    "timing-reading",
    "action-direction",
)


SECTION_NARRATIVE_POLICIES: dict[str, dict[str, Any]] = {
    "chart-positioning": {
        "purpose": "Describe each person's relationship needs and pressure response as the chart-only baseline.",
        "allowedContextKeys": (),
        "allowedEvidenceDomains": ("userNatal", "partnerNatal", "method"),
        "requiredEvidenceDomains": ("userNatal", "partnerNatal"),
        "requiredSlots": (
            "personAEmotionalNeed",
            "personACommunicationStyle",
            "personBPressureResponse",
            "precisionMode",
        ),
        "allowedSlots": (
            "personAEmotionalNeed",
            "personACommunicationStyle",
            "personBPressureResponse",
            "precisionMode",
        ),
        "forbiddenConceptKeys": (
            "relationship_archetype",
            "relationship_outcome",
            "status_storyline",
            "contact_state",
            "timing_window",
            "next_action",
        ),
    },
    "relationship-fit": {
        "purpose": "Describe the chart-owned relationship type, attraction, friction, and repair potential.",
        "allowedContextKeys": (),
        "allowedEvidenceDomains": ("synastry", "method"),
        "requiredEvidenceDomains": ("synastry",),
        "requiredSlots": (
            "archetypeTitle",
            "attractionKeys",
            "frictionKeys",
            "growthKeys",
            "primaryDynamicKey",
            "attractionSignals",
            "frictionSignals",
            "growthSignals",
            "fitSignature",
        ),
        "allowedSlots": (
            "archetypeTitle",
            "attractionKeys",
            "frictionKeys",
            "growthKeys",
            "primaryDynamicKey",
            "secondaryDynamicKeys",
            "attractionSignals",
            "frictionSignals",
            "growthSignals",
            "fitSignature",
        ),
        "forbiddenConceptKeys": (
            "status_storyline",
            "question_answer",
            "contact_state",
            "timing_window",
            "next_action",
        ),
    },
    "core-answer": {
        "purpose": "Answer the selected question with a chart-backed thesis and observable conditions.",
        "allowedContextKeys": ("stageKey", "questionKey", "contactKey"),
        "allowedEvidenceDomains": (
            "userNatal",
            "partnerNatal",
            "synastry",
            "relationshipContext",
            "answerPolicy",
            "method",
        ),
        "requiredEvidenceDomains": ("synastry", "relationshipContext", "answerPolicy"),
        "requiredSlots": (
            "questionKey",
            "relationshipStage",
            "contactStatus",
            "answerTrackKeys",
            "centralDynamicKey",
            "partnerRelationshipNeedKey",
            "observableSignKeys",
            "observableSigns",
            "centralEvidenceSignal",
            "answerEvidenceSignals",
        ),
        "allowedSlots": (
            "questionKey",
            "relationshipStage",
            "contactStatus",
            "questionRewrite",
            "answerTrackKeys",
            "centralDynamicKey",
            "secondaryDynamicKey",
            "partnerRelationshipNeedKey",
            "observableSignKeys",
            "observableSigns",
            "uncertaintyLevel",
            "centralEvidenceSignal",
            "answerEvidenceSignals",
        ),
        "forbiddenConceptKeys": (
            "archetype_exposition",
            "exact_timing",
            "step_by_step_action",
        ),
    },
    "timing-reading": {
        "purpose": "Set the current pace from timing and contact constraints without promising an outcome.",
        "allowedContextKeys": ("stageKey", "questionKey", "contactKey"),
        "allowedEvidenceDomains": ("timing", "relationshipContext", "method"),
        "requiredEvidenceDomains": ("timing", "relationshipContext"),
        "requiredSlots": (
            "questionKey",
            "contactStatus",
            "timingPostureKey",
            "recommendedAction",
            "topBand",
            "contactPostureKey",
        ),
        "allowedSlots": (
            "questionKey",
            "contactStatus",
            "timingPostureKey",
            "recommendedAction",
            "topBand",
            "contactPostureKey",
            "preciseDatesAvailable",
            "topWindowKey",
            "sampleCount",
        ),
        "forbiddenConceptKeys": (
            "relationship_archetype",
            "core_answer",
            "action_script",
            "guaranteed_outcome",
        ),
    },
    "action-direction": {
        "purpose": "Choose one bounded action, its completion point, and an explicit stop condition.",
        "allowedContextKeys": ("stageKey", "questionKey", "contactKey"),
        "allowedEvidenceDomains": ("synastry", "relationshipContext", "actionPolicy", "method"),
        "requiredEvidenceDomains": ("relationshipContext", "actionPolicy"),
        "requiredSlots": (
            "questionKey",
            "contactStatus",
            "actionPurposeKey",
            "actionMode",
            "completionBoundaryKey",
            "repairLeverKey",
            "stopConditionKey",
            "blockedActions",
        ),
        "allowedSlots": (
            "questionKey",
            "contactStatus",
            "actionPurposeKey",
            "actionMode",
            "completionBoundaryKey",
            "repairLeverKey",
            "stopConditionKey",
            "contactPostureKey",
            "blockedActions",
        ),
        "forbiddenConceptKeys": (
            "archetype_exposition",
            "core_answer",
            "timing_forecast",
            "relationship_outcome",
        ),
    },
}


LEGACY_REQUIRED_SLOTS: dict[str, tuple[str, ...]] = {
    "chart-positioning": (
        "personAEmotionalNeed",
        "personACommunicationStyle",
        "personBPressureResponse",
    ),
    "relationship-fit": (
        "archetypeTitle",
        "attractionKeys",
        "frictionKeys",
        "growthKeys",
        "primaryDynamicKey",
    ),
    "core-answer": (
        "questionKey",
        "answerTrackKeys",
        "centralDynamicKey",
        "observableSignKeys",
        "observableSigns",
    ),
    "timing-reading": (
        "timingPostureKey",
        "recommendedAction",
        "topBand",
        "contactPostureKey",
    ),
    "action-direction": (
        "actionMode",
        "repairLeverKey",
        "stopConditionKey",
        "blockedActions",
    ),
}


DYNAMIC_PAIR_PRIORITY: dict[str, tuple[str, ...]] = {
    "emotional_safety": ("Moon-Moon", "Moon-Venus", "Sun-Moon", "Moon-Saturn", "Moon-Mars"),
    "saturn_pressure": ("Moon-Saturn", "Venus-Saturn", "Sun-Saturn", "Mercury-Saturn", "Mars-Saturn"),
    "communication_repair": ("Mercury-Mercury", "Mercury-Sun", "Mercury-Mars", "Mercury-Saturn"),
    "attraction_pursuit": ("Venus-Mars", "Sun-Mars", "Sun-Venus", "Moon-Venus", "Venus-Venus"),
    "action_conflict": ("Mercury-Mars", "Moon-Mars", "Mars-Mars", "Mars-Saturn", "Sun-Mars"),
    "identity_rhythm": ("Sun-Moon", "Sun-Venus", "Sun-Mars", "Mercury-Sun", "Sun-Saturn"),
    "outer_intensity": ("Outer-planet intensity",),
}


DOMAIN_CONCEPT_KEYS = {
    "userNatal": "user_relationship_pattern",
    "partnerNatal": "partner_relationship_pattern",
    "synastry": "relationship_dynamic",
    "timing": "timing_activation",
    "relationshipContext": "context_constraint",
    "answerPolicy": "question_answer",
    "actionPolicy": "next_action",
    "method": "method_boundary",
}


ARCHETYPE_FACT_KEYS = {
    "前世因緣感型": "past-life-intensity",
    "命中貴人型": "growth-support",
    "溝通修復型": "communication-repair",
    "彼此牽動型": "mutual-activation",
    "靈魂伴侶型": "emotional-familiarity",
    "磨合成長型": "growth-through-friction",
    "歡喜冤家型": "fast-spark-conflict",
    "高吸引高摩擦型": "high-attraction-high-friction",
    "自然吸引型": "natural-attraction",
    "慢熱安全感型": "slow-safety",
}


FINAL_FACT_COMPATIBILITY_PROSE_SLOTS: dict[str, tuple[str, ...]] = {
    section_id: () for section_id in SECTION_NARRATIVE_IDS
}


def unique_strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            output.append(text)
            seen.add(text)
    return output


def string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return unique_strings(value)


def number(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def recursively_collect(value: Any, key: str) -> list[str]:
    collected: list[Any] = []
    if isinstance(value, dict):
        if isinstance(value.get(key), list):
            collected.extend(value.get(key) or [])
        for child in value.values():
            if isinstance(child, (dict, list)):
                collected.extend(recursively_collect(child, key))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                collected.extend(recursively_collect(child, key))
    return unique_strings(collected)


def normalize_evidence_packet(packet: dict[str, Any]) -> NarrativeEvidence:
    domain = str(packet.get("domain") or "method")
    return {
        "id": str(packet.get("id") or f"evidence-{domain}"),
        "domain": domain,
        "role": str(packet.get("role") or "supports"),
        "conceptKey": DOMAIN_CONCEPT_KEYS.get(domain, domain),
        "source": str(packet.get("source") or domain),
        "proposition": str(packet.get("proposition") or "").strip(),
        "confidence": round(number(packet.get("confidence"), 0.5), 3),
        "relevance": round(number(packet.get("relevance"), 0.5), 3),
        "sourceClaimIds": string_list(packet.get("sourceClaimIds")),
        "methodClaimIds": string_list(packet.get("methodClaimIds")),
        "evidenceClusterKeys": string_list(packet.get("evidenceClusterKeys")),
    }


def synthetic_evidence(
    *,
    evidence_id: str,
    domain: str,
    source: str,
    proposition: str,
    payload: dict[str, Any],
    role: str = "supports",
) -> NarrativeEvidence:
    return {
        "id": evidence_id,
        "domain": domain,
        "role": role,
        "conceptKey": DOMAIN_CONCEPT_KEYS.get(domain, domain),
        "source": source,
        "proposition": proposition,
        "confidence": 0.8,
        "relevance": 0.8,
        "sourceClaimIds": recursively_collect(payload, "sourceClaimIds"),
        "methodClaimIds": recursively_collect(payload, "methodClaimIds"),
        "evidenceClusterKeys": recursively_collect(payload, "evidenceClusterKeys"),
    }


def evidence_by_domain(evidence: list[NarrativeEvidence], domains: Iterable[str]) -> list[NarrativeEvidence]:
    allowed = set(domains)
    return [item for item in evidence if item.get("domain") in allowed]


def evidence_ids_for_domains(spec: dict[str, Any], domains: Iterable[str]) -> list[str]:
    allowed = set(domains)
    return unique_strings(
        item.get("id")
        for item in spec.get("evidence") or []
        if isinstance(item, dict) and item.get("domain") in allowed
    )


def owned_evidence_ids(spec: dict[str, Any], values: Iterable[Any], fallback_domains: Iterable[str]) -> list[str]:
    allowed = {
        str(item.get("id") or "")
        for item in spec.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    selected = [value for value in unique_strings(values) if value in allowed]
    return selected or evidence_ids_for_domains(spec, fallback_domains)


def profile_card_fact_key(
    relationship_profiles: dict[str, Any],
    person_key: str,
    points: Iterable[str],
) -> str:
    profile = relationship_profiles.get(person_key) if isinstance(relationship_profiles.get(person_key), dict) else {}
    cards = [item for item in profile.get("cards") or [] if isinstance(item, dict)]
    for point in points:
        card = next((item for item in cards if str(item.get("point") or "") == point), None)
        if not card:
            continue
        sign = canonical_value_key(card.get("sign"))
        return f"{canonical_value_key(point)}.{sign}"
    return "unknown"


def planet_role_fact_key(value: Any, planet: str) -> str:
    raw = str(value or "").strip()
    if not raw or raw in {"unknown", "none", "unresolved"}:
        return f"{planet}.unknown"
    return raw


def archetype_fact_key(title: Any) -> str:
    return ARCHETYPE_FACT_KEYS.get(str(title or ""), "unknown")


def timing_window_fact_key(window: dict[str, Any]) -> str:
    period = str(window.get("periodLabel") or window.get("windowLabel") or "")
    match = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(上旬|中旬|下旬)", period)
    period_key = "not-calculated"
    if match:
        third = {"上旬": "early", "中旬": "mid", "下旬": "late"}[match.group(3)]
        period_key = f"{match.group(1)}-{int(match.group(2)):02d}-{third}"
    title = str(window.get("title") or window.get("categoryLabel") or "")
    category = next(
        (
            value
            for marker, value in (
                ("柔和", "softening"),
                ("擦槍走火", "conflict-risk"),
                ("溝通", "communication-opening"),
                ("承諾", "boundary-pressure"),
                ("責任", "boundary-pressure"),
                ("界線", "boundary-pressure"),
            )
            if marker in title
        ),
        "general-climate",
    )
    pair = canonical_value_key(f"{window.get('transitPoint')}-{window.get('natalPoint')}")
    aspect = canonical_value_key(window.get("aspect"))
    return f"{period_key}|{category}|{pair}|{aspect}"


def evidence_trace(evidence: list[NarrativeEvidence]) -> dict[str, list[str]]:
    return {
        "evidenceIds": unique_strings(item.get("id") for item in evidence),
        "sourceClaimIds": unique_strings(
            claim_id
            for item in evidence
            for claim_id in item.get("sourceClaimIds") or []
        ),
        "methodClaimIds": unique_strings(
            claim_id
            for item in evidence
            for claim_id in item.get("methodClaimIds") or []
        ),
        "evidenceClusterKeys": unique_strings(
            key
            for item in evidence
            for key in item.get("evidenceClusterKeys") or []
        ),
    }


def is_empty_slot(value: Any) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, (list, tuple, dict, set)) and not value:
        return True
    return False


def validate_semantic_signals(
    value: Any,
    *,
    slot_name: str,
    evidence_ids: set[str],
    expected_source_kind: str | None = None,
    maximum: int = 3,
) -> list[str]:
    errors: list[str] = []
    signals = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
    if not signals:
        return [f"semantic slot {slot_name} has no structured signals"]
    if len(signals) > maximum:
        errors.append(f"semantic slot {slot_name} exceeds {maximum} signals")
    required_keys = {
        "key",
        "pairKey",
        "sourceKind",
        "directionKey",
        "strengthBand",
        "evidenceIds",
    }
    seen: set[str] = set()
    for index, signal in enumerate(signals):
        if not isinstance(signal, dict):
            errors.append(f"semantic slot {slot_name}[{index}] is not an object")
            continue
        missing = sorted(key for key in required_keys if is_empty_slot(signal.get(key)))
        if missing:
            errors.append(f"semantic slot {slot_name}[{index}] missing {missing}")
        key = str(signal.get("key") or "")
        if key in seen:
            errors.append(f"semantic slot {slot_name} repeats signal {key}")
        seen.add(key)
        if expected_source_kind and signal.get("sourceKind") != expected_source_kind:
            errors.append(
                f"semantic slot {slot_name}[{index}] has sourceKind {signal.get('sourceKind')}, expected {expected_source_kind}"
            )
        owned_ids = set(string_list(signal.get("evidenceIds")))
        if not owned_ids <= evidence_ids:
            errors.append(
                f"semantic slot {slot_name}[{index}] references unowned evidence {sorted(owned_ids - evidence_ids)}"
            )
    return errors


def validate_section_narrative_spec(spec: SectionNarrativeSpec) -> dict[str, Any]:
    section_id = str(spec.get("sectionId") or "")
    policy = SECTION_NARRATIVE_POLICIES.get(section_id)
    errors: list[str] = []
    warnings: list[str] = []
    if not policy:
        return {"status": "invalid", "errors": [f"unknown sectionId: {section_id}"], "warnings": []}

    spec_version = str(spec.get("version") or "")
    if spec_version not in SUPPORTED_SECTION_NARRATIVE_SPEC_VERSIONS:
        errors.append(f"unsupported version: {spec.get('version')}")
    if spec.get("purpose") != policy.get("purpose"):
        errors.append("purpose does not match section policy")

    context = spec.get("context") if isinstance(spec.get("context"), dict) else {}
    allowed_context = set(policy.get("allowedContextKeys") or ())
    for key, value in context.items():
        if value and key not in allowed_context:
            errors.append(f"context key {key} is forbidden")

    slots = spec.get("semanticSlots") if isinstance(spec.get("semanticSlots"), dict) else {}
    allowed_slots = set(policy.get("allowedSlots") or ())
    required_slots = set(
        LEGACY_REQUIRED_SLOTS.get(section_id) or ()
        if spec_version == LEGACY_SECTION_NARRATIVE_SPEC_VERSION
        else policy.get("requiredSlots") or ()
    )
    unknown_slots = set(slots) - allowed_slots
    if unknown_slots:
        errors.append(f"unknown semantic slots: {sorted(unknown_slots)}")
    for key in sorted(required_slots):
        if is_empty_slot(slots.get(key)):
            errors.append(f"required semantic slot {key} is empty")

    concepts = set(string_list(spec.get("conceptKeys")))
    forbidden = set(policy.get("forbiddenConceptKeys") or ())
    if set(string_list(spec.get("forbiddenConceptKeys"))) != forbidden:
        errors.append("declared forbidden concepts do not match section policy")
    collisions = concepts & forbidden
    if collisions:
        errors.append(f"forbidden concepts present: {sorted(collisions)}")

    evidence = [item for item in spec.get("evidence") or [] if isinstance(item, dict)]
    if not evidence:
        errors.append("owned evidence is empty")
    allowed_domains = set(policy.get("allowedEvidenceDomains") or ())
    actual_domains = {str(item.get("domain") or "") for item in evidence}
    invalid_domains = sorted(actual_domains - allowed_domains)
    if invalid_domains:
        errors.append(f"forbidden evidence domains: {invalid_domains}")
    missing_domains = sorted(set(policy.get("requiredEvidenceDomains") or ()) - actual_domains)
    if missing_domains:
        errors.append(f"required evidence domains missing: {missing_domains}")
    evidence_ids = [str(item.get("id") or "") for item in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("evidence ids are not unique")
    if any(not evidence_id for evidence_id in evidence_ids):
        errors.append("evidence id is empty")
    if any(number(item.get("confidence"), 0.0) < 0.5 for item in evidence):
        warnings.append("one or more evidence items have confidence below 0.5")

    depth_spec_versions = {
        EVIDENCE_DEPTH_SECTION_NARRATIVE_SPEC_VERSION,
        SECTION_NARRATIVE_SPEC_VERSION,
    }
    if spec_version in depth_spec_versions and section_id == "relationship-fit":
        for slot_name, source_kind in (
            ("attractionSignals", "attraction"),
            ("frictionSignals", "friction"),
            ("growthSignals", "growth"),
        ):
            errors.extend(
                validate_semantic_signals(
                    slots.get(slot_name),
                    slot_name=slot_name,
                    evidence_ids=set(evidence_ids),
                    expected_source_kind=source_kind,
                )
            )
        if not str(slots.get("fitSignature") or "").strip():
            errors.append("semantic slot fitSignature is empty")
    if spec_version in depth_spec_versions and section_id == "core-answer":
        errors.extend(
            validate_semantic_signals(
                slots.get("centralEvidenceSignal"),
                slot_name="centralEvidenceSignal",
                evidence_ids=set(evidence_ids),
                maximum=1,
            )
        )
        errors.extend(
            validate_semantic_signals(
                slots.get("answerEvidenceSignals"),
                slot_name="answerEvidenceSignals",
                evidence_ids=set(evidence_ids),
                maximum=2,
            )
        )
        central_signal = slots.get("centralEvidenceSignal") if isinstance(slots.get("centralEvidenceSignal"), dict) else {}
        answer_signals = [item for item in slots.get("answerEvidenceSignals") or [] if isinstance(item, dict)]
        if central_signal and str(central_signal.get("key") or "") not in {
            str(item.get("key") or "") for item in answer_signals
        }:
            errors.append("centralEvidenceSignal is not included in answerEvidenceSignals")

    trace = spec.get("trace") if isinstance(spec.get("trace"), dict) else {}
    if set(string_list(trace.get("evidenceIds"))) != set(evidence_ids):
        errors.append("trace evidenceIds do not match owned evidence")
    if not string_list(trace.get("sourceClaimIds")) and not string_list(trace.get("methodClaimIds")):
        errors.append("trace has no source or method claim ids")

    case_model_trace = spec.get("caseModelTrace") if isinstance(spec.get("caseModelTrace"), dict) else {}
    if spec_version == SECTION_NARRATIVE_SPEC_VERSION and section_id in CASE_MODEL_TRACE_SECTION_IDS:
        required_case_fields = (
            "caseModelVersion",
            "primaryDynamicKey",
            "secondaryDynamicKey",
            "secondaryRole",
            "grammarId",
        )
        if case_model_trace.get("version") != RELATIONSHIP_CASE_MODEL_TRACE_VERSION:
            errors.append("caseModelTrace version is missing or invalid")
        if case_model_trace.get("sectionId") != section_id:
            errors.append("caseModelTrace sectionId does not match section")
        for field in required_case_fields:
            if not str(case_model_trace.get(field) or "").strip():
                errors.append(f"caseModelTrace {field} is empty")
        if case_model_trace.get("grammarMode") not in {"explicit", "composed"}:
            errors.append("caseModelTrace grammarMode is invalid")
        if not string_list(case_model_trace.get("caseEvidenceIds")):
            errors.append("caseModelTrace caseEvidenceIds is empty")
    if spec_version == SECTION_NARRATIVE_SPEC_VERSION and section_id not in CASE_MODEL_TRACE_SECTION_IDS:
        if case_model_trace:
            errors.append("caseModelTrace is forbidden for this section")

    return {"status": "invalid" if errors else "valid", "errors": errors, "warnings": warnings}


def build_spec(
    *,
    section_id: str,
    context: dict[str, str],
    semantic_slots: dict[str, Any],
    concept_keys: list[str],
    evidence: list[NarrativeEvidence],
    case_model_trace: RelationshipCaseModelTrace | None = None,
) -> SectionNarrativeSpec:
    policy = SECTION_NARRATIVE_POLICIES[section_id]
    spec: SectionNarrativeSpec = {
        "version": SECTION_NARRATIVE_SPEC_VERSION,
        "sectionId": section_id,  # type: ignore[typeddict-item]
        "purpose": str(policy["purpose"]),
        "context": context,
        "semanticSlots": semantic_slots,
        "conceptKeys": unique_strings(concept_keys),
        "forbiddenConceptKeys": list(policy.get("forbiddenConceptKeys") or ()),
        "evidence": evidence,
        "trace": evidence_trace(evidence),
    }
    if case_model_trace:
        spec["caseModelTrace"] = case_model_trace
    spec["validation"] = validate_section_narrative_spec(spec)
    return spec


def relationship_case_model_trace(
    relationship_case_model: dict[str, Any],
    *,
    section_id: str,
) -> RelationshipCaseModelTrace:
    primary = relationship_case_model.get("primaryDynamic") if isinstance(relationship_case_model.get("primaryDynamic"), dict) else {}
    secondaries = [item for item in relationship_case_model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    secondary = secondaries[0] if secondaries else {}
    interaction = relationship_case_model.get("dynamicInteractionPlan") if isinstance(relationship_case_model.get("dynamicInteractionPlan"), dict) else {}
    return {
        "version": RELATIONSHIP_CASE_MODEL_TRACE_VERSION,
        "caseModelVersion": str(relationship_case_model.get("version") or ""),
        "sectionId": section_id,
        "primaryDynamicKey": str(interaction.get("primaryKey") or primary.get("key") or ""),
        "secondaryDynamicKey": str(interaction.get("secondaryKey") or secondary.get("key") or ""),
        "secondaryRole": str(interaction.get("secondaryRole") or secondary.get("role") or ""),
        "grammarId": str(interaction.get("grammarId") or ""),
        "grammarMode": str(interaction.get("grammarMode") or ""),  # type: ignore[typeddict-item]
        "caseEvidenceIds": unique_strings(interaction.get("evidenceIds") or []),
    }


def item_keys(payload: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        keys.extend(
            str(value)
            for value in (
                item.get("pairKey"),
                item.get("themeKey"),
                item.get("id"),
                item.get("title"),
            )
            if value
        )
    return unique_strings(keys)


def signal_strength_band(value: Any) -> str:
    strength = number(value, 0.0)
    if strength >= 0.78:
        return "dominant"
    if strength >= 0.52:
        return "clear"
    if strength > 0:
        return "supporting"
    return "unrated"


def narrative_signal_items(
    payload: dict[str, Any],
    *,
    source_kind: str,
    evidence_id: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        pair_key = str(item.get("pairKey") or item.get("themeKey") or item.get("title") or "unknown")
        point_a = str(item.get("personAPoint") or "unknown")
        point_b = str(item.get("personBPoint") or "unknown")
        aspect_key = str(item.get("aspect") or "unknown")
        contact_type = str(item.get("contactType") or "unknown")
        direction_key = f"personA:{point_a}>personB:{point_b}"
        identity = f"{source_kind}:{pair_key}:{direction_key}:{aspect_key}:{contact_type}"
        if identity in seen:
            continue
        seen.add(identity)
        strength = round(number(item.get("strength"), 0.0), 3)
        output.append(
            {
                "key": identity,
                "pairKey": pair_key,
                "sourceKind": source_kind,
                "personAPoint": point_a,
                "personBPoint": point_b,
                "directionKey": direction_key,
                "aspectKey": aspect_key,
                "contactType": contact_type,
                "strength": strength,
                "strengthBand": signal_strength_band(strength),
                "everydaySignal": str(item.get("everydaySignal") or "").strip(),
                "meaning": str(item.get("meaning") or "").strip(),
                "advice": str(item.get("advice") or "").strip(),
                "evidenceIds": [evidence_id],
            }
        )
        if len(output) >= limit:
            break
    if output:
        return output
    fallback_key = str(payload.get("key") or source_kind or "unknown")
    return [
        {
            "key": f"{source_kind}:{fallback_key}:unresolved",
            "pairKey": fallback_key,
            "sourceKind": source_kind,
            "personAPoint": "unknown",
            "personBPoint": "unknown",
            "directionKey": "unknown",
            "aspectKey": "unknown",
            "contactType": "unknown",
            "strength": 0.0,
            "strengthBand": "unrated",
            "everydaySignal": str(payload.get("summary") or "").strip(),
            "meaning": str(payload.get("doesNotProve") or "").strip(),
            "advice": "",
            "evidenceIds": [evidence_id],
        }
    ]


def signal_priority_for_dynamic(signal: dict[str, Any], dynamic_key: str) -> tuple[int, int, float, int]:
    pair_key = str(signal.get("pairKey") or "")
    priority = DYNAMIC_PAIR_PRIORITY.get(dynamic_key) or ()
    pair_rank = priority.index(pair_key) if pair_key in priority else len(priority) + 1
    source_kind = str(signal.get("sourceKind") or "")
    preferred_source = {
        "emotional_safety": "attraction",
        "saturn_pressure": "friction",
        "communication_repair": "friction",
        "attraction_pursuit": "attraction",
        "action_conflict": "friction",
        "identity_rhythm": "attraction",
        "outer_intensity": "friction",
    }.get(dynamic_key, "friction")
    return (
        0 if pair_key in priority else 1,
        0 if source_kind == preferred_source else 1,
        -number(signal.get("strength"), 0.0),
        pair_rank,
    )


def answer_evidence_signals(
    signals: list[dict[str, Any]],
    *,
    central_dynamic_key: str,
    secondary_dynamic_key: str,
    excluded_signal_keys: set[str] | None = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    ranked = sorted(signals, key=lambda item: signal_priority_for_dynamic(item, central_dynamic_key))
    excluded = excluded_signal_keys or set()
    unclaimed = [item for item in ranked if str(item.get("key") or "") not in excluded]
    candidates = unclaimed or ranked
    output: list[dict[str, Any]] = []
    seen_pairs: set[str] = set()
    for signal in candidates:
        pair_key = str(signal.get("pairKey") or "unknown")
        if pair_key in seen_pairs:
            continue
        output.append(signal)
        seen_pairs.add(pair_key)
        if len(output) >= limit:
            return output
    if secondary_dynamic_key and secondary_dynamic_key != "none":
        for signal in sorted(signals, key=lambda item: signal_priority_for_dynamic(item, secondary_dynamic_key)):
            pair_key = str(signal.get("pairKey") or "unknown")
            if pair_key not in seen_pairs:
                output.append(signal)
                break
    return output[:limit] or signals[:1]


def fit_signature(*signal_groups: list[dict[str, Any]]) -> str:
    return "|".join(
        str(signal.get("key") or "unknown")
        for group in signal_groups
        for signal in group
    )


def chart_dynamic_keys(*payloads: dict[str, Any]) -> list[str]:
    counts: dict[str, int] = {}
    priority = (
        "emotional_safety",
        "saturn_pressure",
        "communication_repair",
        "attraction_pursuit",
        "action_conflict",
        "identity_rhythm",
        "outer_intensity",
    )
    for payload in payloads:
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            pair_key = str(item.get("pairKey") or item.get("title") or "")
            points = set(pair_key.replace("–", "-").split("-"))
            keys: list[str] = []
            if "Moon" in points:
                keys.append("emotional_safety")
            if "Saturn" in points:
                keys.append("saturn_pressure")
            if "Mercury" in points:
                keys.append("communication_repair")
            if "Venus" in points and points & {"Mars", "Sun", "Moon"}:
                keys.append("attraction_pursuit")
            if "Mars" in points:
                keys.append("action_conflict")
            if "Sun" in points:
                keys.append("identity_rhythm")
            if points & {"Uranus", "Neptune", "Pluto"}:
                keys.append("outer_intensity")
            for key in keys:
                counts[key] = counts.get(key, 0) + 1
    return sorted(counts, key=lambda key: (-counts[key], priority.index(key)))


def build_section_narrative_specs(
    *,
    question_key: str,
    stage_key: str,
    contact_key: str,
    relationship_profiles: dict[str, Any],
    relationship_archetype: dict[str, Any],
    attraction_dynamics: dict[str, Any],
    conflict_dynamics: dict[str, Any],
    growth_dynamics: dict[str, Any],
    relationship_thesis: dict[str, Any],
    relationship_case_model: dict[str, Any],
    status_answer_policy: dict[str, Any],
    timing_guidance: dict[str, Any],
    action_guidance: dict[str, Any],
    relationship_turning_windows: dict[str, Any] | None = None,
    relationship_theme: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = [
        normalize_evidence_packet(item)
        for item in relationship_thesis.get("evidencePacket") or []
        if isinstance(item, dict)
    ]
    packet.append(
        synthetic_evidence(
            evidence_id="E-answer-policy",
            domain="answerPolicy",
            source="relationship-status-answer-policy",
            proposition="The status policy selects answer tracks and boundaries but cannot create astrology evidence.",
            payload=status_answer_policy,
            role="routes",
        )
    )
    packet.append(
        synthetic_evidence(
            evidence_id="E-action-policy",
            domain="actionPolicy",
            source="contact-action-policy",
            proposition="The action policy limits action size and blocked actions for the current contact state.",
            payload=action_guidance,
            role="limits",
        )
    )

    baseline = relationship_profiles.get("translationBaseline") if isinstance(relationship_profiles.get("translationBaseline"), dict) else {}
    person_a = baseline.get("personA") if isinstance(baseline.get("personA"), dict) else {}
    person_b = baseline.get("personB") if isinstance(baseline.get("personB"), dict) else {}
    primary = relationship_case_model.get("primaryDynamic") if isinstance(relationship_case_model.get("primaryDynamic"), dict) else {}
    secondary = [item for item in relationship_case_model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    repair = relationship_case_model.get("repairLever") if isinstance(relationship_case_model.get("repairLever"), dict) else {}
    timing_posture = relationship_case_model.get("timingPosture") if isinstance(relationship_case_model.get("timingPosture"), dict) else {}
    contact_posture = relationship_case_model.get("contactPosture") if isinstance(relationship_case_model.get("contactPosture"), dict) else {}
    risk_posture = relationship_case_model.get("riskPosture") if isinstance(relationship_case_model.get("riskPosture"), dict) else {}
    observable_signs = [item for item in relationship_thesis.get("observableSigns") or [] if isinstance(item, dict)]
    uncertainty = relationship_thesis.get("uncertainty") if isinstance(relationship_thesis.get("uncertainty"), dict) else {}
    turning_windows = relationship_turning_windows if isinstance(relationship_turning_windows, dict) else {}
    top_timing_window = next(
        (item for item in turning_windows.get("items") or [] if isinstance(item, dict)),
        {},
    )
    top_timing_window_key = timing_window_fact_key(top_timing_window) if top_timing_window else "not-calculated"
    requested_timing_action = canonical_value_key(
        timing_guidance.get("recommendedAction") or "not-calculated"
    )
    requested_timing_posture = canonical_value_key(
        timing_posture.get("key") or requested_timing_action
    )
    effective_timing_action = (
        "avoid-push" if contact_key == "blocked" else requested_timing_action
    )
    effective_timing_posture = (
        "avoid-push" if contact_key == "blocked" else requested_timing_posture
    )
    chart_dynamics = chart_dynamic_keys(attraction_dynamics, conflict_dynamics, growth_dynamics)
    chart_primary_dynamic = str((relationship_theme or {}).get("themeKey") or (chart_dynamics[0] if chart_dynamics else "unknown"))
    chart_secondary_dynamics = [key for key in chart_dynamics if key != chart_primary_dynamic]

    method_evidence = evidence_by_domain(packet, ("method",))
    chart_evidence = [
        synthetic_evidence(
            evidence_id="E-profile-user",
            domain="userNatal",
            source="relationship-profiles-person-a",
            proposition="Person A natal relationship profile.",
            payload=relationship_profiles.get("personA") or {},
        ),
        synthetic_evidence(
            evidence_id="E-profile-partner",
            domain="partnerNatal",
            source="relationship-profiles-person-b",
            proposition="Person B natal relationship profile.",
            payload=relationship_profiles.get("personB") or {},
        ),
        *method_evidence,
    ]
    fit_evidence = [
        synthetic_evidence(
            evidence_id="E-relationship-fit",
            domain="synastry",
            source="relationship-insight-layer",
            proposition="Chart-owned archetype, attraction, friction, and growth evidence.",
            payload={
                "relationshipArchetype": relationship_archetype,
                "attractionDynamics": attraction_dynamics,
                "conflictDynamics": conflict_dynamics,
                "growthDynamics": growth_dynamics,
            },
        ),
        *method_evidence,
    ]
    core_evidence = evidence_by_domain(
        packet,
        ("userNatal", "partnerNatal", "synastry", "relationshipContext", "answerPolicy", "method"),
    )
    if not evidence_by_domain(core_evidence, ("synastry",)):
        core_evidence.insert(0, fit_evidence[0])
    timing_evidence = evidence_by_domain(packet, ("timing", "relationshipContext", "method"))
    action_evidence = evidence_by_domain(packet, ("synastry", "relationshipContext", "actionPolicy", "method"))

    fit_synastry_evidence_id = str((fit_evidence[0] if fit_evidence else {}).get("id") or "E-relationship-fit")
    core_synastry_evidence_id = str(
        next(
            (item.get("id") for item in core_evidence if item.get("domain") == "synastry" and item.get("id")),
            fit_synastry_evidence_id,
        )
    )
    attraction_signals = narrative_signal_items(
        attraction_dynamics,
        source_kind="attraction",
        evidence_id=fit_synastry_evidence_id,
    )
    friction_signals = narrative_signal_items(
        conflict_dynamics,
        source_kind="friction",
        evidence_id=fit_synastry_evidence_id,
    )
    growth_signals = narrative_signal_items(
        growth_dynamics,
        source_kind="growth",
        evidence_id=fit_synastry_evidence_id,
    )
    fit_owned_signal_keys = {
        str(signal.get("key") or "")
        for signal in (
            *attraction_signals[:1],
            *friction_signals[:1],
            *growth_signals[:1],
        )
        if str(signal.get("key") or "")
    }
    central_dynamic_key = str(relationship_thesis.get("centralDynamicKey") or primary.get("key") or "unknown")
    secondary_dynamic_key = str((secondary[0] if secondary else {}).get("key") or "none")
    core_signal_pool = [
        *narrative_signal_items(
            attraction_dynamics,
            source_kind="attraction",
            evidence_id=core_synastry_evidence_id,
            limit=8,
        ),
        *narrative_signal_items(
            conflict_dynamics,
            source_kind="friction",
            evidence_id=core_synastry_evidence_id,
            limit=8,
        ),
        *narrative_signal_items(
            growth_dynamics,
            source_kind="growth",
            evidence_id=core_synastry_evidence_id,
            limit=8,
        ),
    ]
    selected_answer_signals = answer_evidence_signals(
        core_signal_pool,
        central_dynamic_key=central_dynamic_key,
        secondary_dynamic_key=secondary_dynamic_key,
        excluded_signal_keys=fit_owned_signal_keys,
    )
    central_evidence_signal = selected_answer_signals[0]

    specs = {
        "chart-positioning": build_spec(
            section_id="chart-positioning",
            context={},
            semantic_slots={
                "personAEmotionalNeed": planet_role_fact_key(
                    person_a.get("emotionalNeed"), "moon"
                ),
                "personACommunicationStyle": planet_role_fact_key(
                    person_a.get("communicationStyle"), "mercury"
                ),
                "personBPressureResponse": planet_role_fact_key(
                    person_b.get("conflictResponse"), "mars"
                ),
                "precisionMode": "chart-only",
            },
            concept_keys=["individual_relationship_style", "emotional_need", "communication_style", "pressure_response"],
            evidence=chart_evidence,
        ),
        "relationship-fit": build_spec(
            section_id="relationship-fit",
            context={},
            semantic_slots={
                "archetypeTitle": str(relationship_archetype.get("title") or "unknown"),
                "attractionKeys": item_keys(attraction_dynamics) or [str(attraction_dynamics.get("key") or "unknown")],
                "frictionKeys": item_keys(conflict_dynamics) or [str(conflict_dynamics.get("key") or "unknown")],
                "growthKeys": item_keys(growth_dynamics) or [str(growth_dynamics.get("key") or "unknown")],
                "primaryDynamicKey": chart_primary_dynamic,
                "secondaryDynamicKeys": chart_secondary_dynamics,
                "attractionSignals": attraction_signals,
                "frictionSignals": friction_signals,
                "growthSignals": growth_signals,
                "fitSignature": fit_signature(attraction_signals, friction_signals, growth_signals),
            },
            concept_keys=["relationship_archetype", "attraction_pattern", "friction_pattern", "repair_potential", "relationship_dynamic"],
            evidence=fit_evidence,
        ),
        "core-answer": build_spec(
            section_id="core-answer",
            context={"stageKey": stage_key, "questionKey": question_key, "contactKey": contact_key},
            semantic_slots={
                "questionKey": question_key,
                "relationshipStage": stage_key,
                "contactStatus": contact_key,
                "questionRewrite": str(status_answer_policy.get("questionRewrite") or question_key),
                "answerTrackKeys": string_list(status_answer_policy.get("resolvedTracks")),
                "centralDynamicKey": central_dynamic_key,
                "secondaryDynamicKey": secondary_dynamic_key,
                "partnerRelationshipNeedKey": planet_role_fact_key(
                    profile_card_fact_key(relationship_profiles, "personB", ("Moon",)),
                    "moon",
                ),
                "observableSignKeys": [
                    canonical_value_key(item.get("key") or f"observable-{index}")
                    for index, item in enumerate(observable_signs, start=1)
                ],
                "observableSigns": [
                    {
                        "key": canonical_value_key(item.get("key") or f"observable-{index}"),
                        "behavior": str(item.get("behavior") or ""),
                        "valence": str(item.get("valence") or "ambiguous"),
                        "evidenceIds": string_list(item.get("evidenceIds")),
                    }
                    for index, item in enumerate(observable_signs, start=1)
                ],
                "uncertaintyLevel": str(uncertainty.get("level") or "unknown"),
                "centralEvidenceSignal": central_evidence_signal,
                "answerEvidenceSignals": selected_answer_signals,
            },
            concept_keys=["question_answer", "relationship_thesis", "observable_condition", "context_constraint"],
            evidence=core_evidence,
            case_model_trace=relationship_case_model_trace(
                relationship_case_model,
                section_id="core-answer",
            ),
        ),
        "timing-reading": build_spec(
            section_id="timing-reading",
            context={"stageKey": stage_key, "questionKey": question_key, "contactKey": contact_key},
            semantic_slots={
                "questionKey": question_key,
                "contactStatus": contact_key,
                "timingPostureKey": effective_timing_posture,
                "recommendedAction": effective_timing_action,
                "topBand": str(timing_guidance.get("topBand") or "neutral"),
                "contactPostureKey": str(contact_posture.get("key") or contact_key or "unknown"),
                "preciseDatesAvailable": bool(timing_guidance.get("preciseDatesAvailable")),
                "topWindowKey": top_timing_window_key,
                "sampleCount": int(timing_guidance.get("sampleCount") or 0),
            },
            concept_keys=["timing_activation", "contact_state", "current_pace", "method_boundary"],
            evidence=timing_evidence,
            case_model_trace=relationship_case_model_trace(
                relationship_case_model,
                section_id="timing-reading",
            ),
        ),
        "action-direction": build_spec(
            section_id="action-direction",
            context={"stageKey": stage_key, "questionKey": question_key, "contactKey": contact_key},
            semantic_slots={
                "questionKey": question_key,
                "contactStatus": contact_key,
                "actionPurposeKey": str(action_guidance.get("actionMode") or "observe"),
                "actionMode": str(action_guidance.get("actionMode") or "observe"),
                "completionBoundaryKey": str(action_guidance.get("actionMode") or "observe"),
                "repairLeverKey": str(repair.get("key") or "unknown"),
                "stopConditionKey": str(risk_posture.get("key") or contact_posture.get("key") or "standard-boundary"),
                "contactPostureKey": str(contact_posture.get("key") or contact_key or "unknown"),
                "blockedActions": string_list(action_guidance.get("blockedActions")),
            },
            concept_keys=[
                "action_purpose",
                "next_action",
                "completion_boundary",
                "stop_condition",
            ],
            evidence=action_evidence,
            case_model_trace=relationship_case_model_trace(
                relationship_case_model,
                section_id="action-direction",
            ),
        ),
    }

    chart_spec = specs["chart-positioning"]
    fit_spec = specs["relationship-fit"]
    core_spec = specs["core-answer"]
    timing_spec = specs["timing-reading"]
    action_spec = specs["action-direction"]

    chart_user_evidence = evidence_ids_for_domains(chart_spec, ("userNatal",))
    chart_partner_evidence = evidence_ids_for_domains(chart_spec, ("partnerNatal",))
    fit_synastry_evidence = evidence_ids_for_domains(fit_spec, ("synastry",))
    core_answer_policy_evidence = evidence_ids_for_domains(core_spec, ("answerPolicy",))
    core_synastry_evidence = evidence_ids_for_domains(core_spec, ("synastry",))
    core_partner_evidence = evidence_ids_for_domains(core_spec, ("partnerNatal",))
    core_context_evidence = evidence_ids_for_domains(core_spec, ("relationshipContext", "method"))
    timing_signal_evidence = evidence_ids_for_domains(timing_spec, ("timing",))
    timing_context_evidence = evidence_ids_for_domains(timing_spec, ("relationshipContext", "method"))
    action_policy_evidence = evidence_ids_for_domains(action_spec, ("actionPolicy",))
    action_synastry_evidence = evidence_ids_for_domains(action_spec, ("synastry",))
    action_context_evidence = evidence_ids_for_domains(action_spec, ("relationshipContext", "method"))

    facts_by_section = {
        "chart-positioning": [
            make_fact(
                section_id="chart-positioning",
                role="user-emotional-need",
                value_key=planet_role_fact_key(
                    profile_card_fact_key(relationship_profiles, "personA", ("Moon",)),
                    "moon",
                ),
                source_slot="personAEmotionalNeed",
                evidence_ids=chart_user_evidence,
            ),
            make_fact(
                section_id="chart-positioning",
                role="user-communication-style",
                value_key=planet_role_fact_key(
                    profile_card_fact_key(relationship_profiles, "personA", ("Mercury",)),
                    "mercury",
                ),
                source_slot="personACommunicationStyle",
                evidence_ids=chart_user_evidence,
            ),
            make_fact(
                section_id="chart-positioning",
                role="partner-pressure-response",
                value_key=planet_role_fact_key(
                    profile_card_fact_key(
                        relationship_profiles,
                        "personB",
                        ("Mars", "Saturn"),
                    ),
                    "mars",
                ),
                source_slot="personBPressureResponse",
                evidence_ids=chart_partner_evidence,
            ),
            make_fact(
                section_id="chart-positioning",
                role="precision-mode",
                value_key=chart_spec.get("semanticSlots", {}).get("precisionMode") or "chart-only",
                source_slot="precisionMode",
                evidence_ids=chart_user_evidence or chart_partner_evidence,
            ),
        ],
        "relationship-fit": [
            make_fact(
                section_id="relationship-fit",
                role="relationship-archetype",
                value_key=archetype_fact_key(relationship_archetype.get("title")),
                source_slot="archetypeTitle",
                evidence_ids=fit_synastry_evidence,
            ),
            make_fact(
                section_id="relationship-fit",
                role="primary-dynamic",
                value_key=chart_primary_dynamic,
                source_slot="primaryDynamicKey",
                evidence_ids=fit_synastry_evidence,
            ),
            *[
                make_fact(
                    section_id="relationship-fit",
                    role="secondary-dynamic",
                    value_key=key,
                    source_slot="secondaryDynamicKeys",
                    evidence_ids=fit_synastry_evidence,
                )
                for key in chart_secondary_dynamics[:1]
            ],
            *[
                make_fact(
                    section_id="relationship-fit",
                    role="attraction-signal",
                    value_key=signal.get("key"),
                    source_slot="attractionSignals",
                    evidence_ids=owned_evidence_ids(fit_spec, signal.get("evidenceIds") or [], ("synastry",)),
                    qualifiers=(signal.get("strengthBand"), signal.get("directionKey")),
                )
                for signal in attraction_signals[:1]
            ],
            *[
                make_fact(
                    section_id="relationship-fit",
                    role="friction-signal",
                    value_key=signal.get("key"),
                    source_slot="frictionSignals",
                    evidence_ids=owned_evidence_ids(fit_spec, signal.get("evidenceIds") or [], ("synastry",)),
                    qualifiers=(signal.get("strengthBand"), signal.get("directionKey")),
                )
                for signal in friction_signals[:1]
            ],
            *[
                make_fact(
                    section_id="relationship-fit",
                    role="growth-signal",
                    value_key=signal.get("key"),
                    source_slot="growthSignals",
                    evidence_ids=owned_evidence_ids(fit_spec, signal.get("evidenceIds") or [], ("synastry",)),
                    qualifiers=(signal.get("strengthBand"), signal.get("directionKey")),
                )
                for signal in growth_signals[:1]
            ],
        ],
        "core-answer": [
            make_fact(
                section_id="core-answer",
                role="question",
                value_key=question_key,
                source_slot="questionKey",
                evidence_ids=core_answer_policy_evidence,
            ),
            make_fact(
                section_id="core-answer",
                role="relationship-stage",
                value_key=stage_key,
                source_slot="relationshipStage",
                evidence_ids=core_context_evidence or core_answer_policy_evidence,
            ),
            make_fact(
                section_id="core-answer",
                role="contact-status",
                value_key=contact_key,
                source_slot="contactStatus",
                evidence_ids=core_context_evidence or core_answer_policy_evidence,
            ),
            *[
                make_fact(
                    section_id="core-answer",
                    role="answer-track",
                    value_key=key,
                    source_slot="answerTrackKeys",
                    evidence_ids=core_answer_policy_evidence,
                )
                for key in string_list(status_answer_policy.get("resolvedTracks"))
            ],
            make_fact(
                section_id="core-answer",
                role="central-dynamic",
                value_key=central_dynamic_key,
                source_slot="centralDynamicKey",
                evidence_ids=core_synastry_evidence,
            ),
            make_fact(
                section_id="core-answer",
                role="partner-relationship-need",
                value_key=planet_role_fact_key(
                    profile_card_fact_key(relationship_profiles, "personB", ("Moon",)),
                    "moon",
                ),
                source_slot="partnerRelationshipNeedKey",
                evidence_ids=core_partner_evidence,
            ),
            *[
                make_fact(
                    section_id="core-answer",
                    role="evidence-signal",
                    value_key=signal.get("key"),
                    source_slot="answerEvidenceSignals",
                    evidence_ids=owned_evidence_ids(core_spec, signal.get("evidenceIds") or [], ("synastry",)),
                    qualifiers=(signal.get("sourceKind"), signal.get("strengthBand")),
                )
                for signal in selected_answer_signals[:1]
            ],
            *[
                make_fact(
                    section_id="core-answer",
                    role="observable-sign",
                    value_key=item.get("key") or f"observable-{index}",
                    source_slot="observableSigns",
                    evidence_ids=owned_evidence_ids(
                        core_spec,
                        item.get("evidenceIds") or [],
                        ("synastry", "relationshipContext"),
                    ),
                    qualifiers=(item.get("valence"),),
                )
                for index, item in enumerate(observable_signs[:1], start=1)
            ],
            make_fact(
                section_id="core-answer",
                role="uncertainty-level",
                value_key=uncertainty.get("level") or "unknown",
                source_slot="uncertaintyLevel",
                evidence_ids=core_context_evidence or core_synastry_evidence,
            ),
        ],
        "timing-reading": [
            make_fact(
                section_id="timing-reading",
                role="question",
                value_key=question_key,
                source_slot="questionKey",
                evidence_ids=timing_context_evidence,
            ),
            make_fact(
                section_id="timing-reading",
                role="contact-status",
                value_key=contact_key,
                source_slot="contactStatus",
                evidence_ids=timing_context_evidence or timing_signal_evidence,
            ),
            make_fact(
                section_id="timing-reading",
                role="timing-posture",
                value_key=effective_timing_posture,
                source_slot="timingPostureKey",
                evidence_ids=timing_signal_evidence,
            ),
            make_fact(
                section_id="timing-reading",
                role="recommended-action",
                value_key=effective_timing_action,
                source_slot="recommendedAction",
                evidence_ids=timing_signal_evidence,
            ),
            make_fact(
                section_id="timing-reading",
                role="timing-band",
                value_key=timing_guidance.get("topBand") or "neutral",
                source_slot="topBand",
                evidence_ids=timing_signal_evidence,
            ),
            make_fact(
                section_id="timing-reading",
                role="contact-posture",
                value_key=contact_posture.get("key") or contact_key or "unknown",
                source_slot="contactPostureKey",
                evidence_ids=timing_context_evidence,
            ),
            make_fact(
                section_id="timing-reading",
                role="precise-dates-available",
                value_key="available" if timing_guidance.get("preciseDatesAvailable") else "unavailable",
                source_slot="preciseDatesAvailable",
                evidence_ids=timing_signal_evidence,
            ),
            *(
                [
                    make_fact(
                        section_id="timing-reading",
                        role="timing-window",
                        value_key=top_timing_window_key,
                        source_slot="topWindowKey",
                        evidence_ids=timing_signal_evidence,
                    )
                ]
                if top_timing_window_key != "not-calculated"
                else []
            ),
        ],
        "action-direction": [
            make_fact(
                section_id="action-direction",
                role="question",
                value_key=question_key,
                source_slot="questionKey",
                evidence_ids=action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="contact-status",
                value_key=contact_key,
                source_slot="contactStatus",
                evidence_ids=action_context_evidence or action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="action-purpose",
                value_key=action_guidance.get("actionMode") or "observe",
                source_slot="actionPurposeKey",
                evidence_ids=action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="action-mode",
                value_key=action_guidance.get("actionMode") or "observe",
                source_slot="actionMode",
                evidence_ids=action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="completion-boundary",
                value_key=action_guidance.get("actionMode") or "observe",
                source_slot="completionBoundaryKey",
                evidence_ids=action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="repair-lever",
                value_key=repair.get("key") or "unknown",
                source_slot="repairLeverKey",
                evidence_ids=action_synastry_evidence or action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="stop-condition",
                value_key=risk_posture.get("key") or contact_posture.get("key") or "standard-boundary",
                source_slot="stopConditionKey",
                evidence_ids=action_context_evidence or action_policy_evidence,
            ),
            make_fact(
                section_id="action-direction",
                role="contact-posture",
                value_key=contact_posture.get("key") or contact_key or "unknown",
                source_slot="contactPostureKey",
                evidence_ids=action_context_evidence or action_policy_evidence,
            ),
            *[
                make_fact(
                    section_id="action-direction",
                    role="blocked-action",
                    value_key=key,
                    source_slot="blockedActions",
                    evidence_ids=action_policy_evidence,
                )
                for key in string_list(action_guidance.get("blockedActions"))
            ],
        ],
    }
    fact_contract = build_final_narrative_fact_contract(
        specs,
        facts_by_section,
        compatibility_prose_slots=FINAL_FACT_COMPATIBILITY_PROSE_SLOTS,
    )
    validation = validate_section_narrative_specs(specs)
    fact_validation = fact_contract.get("validation") if isinstance(fact_contract.get("validation"), dict) else {}
    validation["factContractStatus"] = str(fact_validation.get("status") or "invalid")
    validation["factContractVersion"] = str(fact_contract.get("version") or "")
    if fact_validation.get("status") != "valid":
        validation["status"] = "invalid"
        validation["errors"] = [
            *validation.get("errors", []),
            *(f"finalNarrativeFacts: {item}" for item in fact_validation.get("errors") or []),
        ]
    validation["warnings"] = [
        *validation.get("warnings", []),
        *(f"finalNarrativeFacts: {item}" for item in fact_validation.get("warnings") or []),
    ]
    return {
        "version": SECTION_NARRATIVE_SPEC_VERSION,
        "rendererConsumesSpecs": True,
        "rendererVersion": SECTION_NARRATIVE_RENDERER_VERSION,
        "sections": specs,
        "finalNarrativeFacts": fact_contract,
        "validation": validation,
    }


def validate_section_narrative_specs(specs: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if set(specs) != set(SECTION_NARRATIVE_IDS):
        errors.append(f"section set mismatch: {sorted(specs)}")
    for section_id in SECTION_NARRATIVE_IDS:
        spec = specs.get(section_id) if isinstance(specs.get(section_id), dict) else {}
        result = validate_section_narrative_spec(spec)  # type: ignore[arg-type]
        for error in result.get("errors") or []:
            errors.append(f"{section_id}: {error}")
        for warning in result.get("warnings") or []:
            warnings.append(f"{section_id}: {warning}")
    return {
        "status": "invalid" if errors else "valid",
        "errors": errors,
        "warnings": warnings,
        "sectionCount": len(specs),
    }
