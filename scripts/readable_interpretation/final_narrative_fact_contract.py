"""Typed, fact-only boundary for the final reader-language renderer.

Phase 1 made this contract mandatory before visible copy could be composed.
Phase 2 makes it the only semantic input accepted by the five visible section
renderers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

from .schema import FinalNarrativeFact, FinalNarrativeFactContract
from .final_narrative_semantic_coverage import (
    FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    semantic_policy_alignment_errors,
)
from .final_narrative_story_arc import (
    FINAL_NARRATIVE_STORY_ARC_VERSION,
    story_arc_contract_errors,
    story_arc_fact_errors,
)


FINAL_NARRATIVE_FACT_CONTRACT_VERSION = "final-narrative-fact-contract-v4"
FINAL_NARRATIVE_FACT_RENDERER_MODE = "fact-only"
FINAL_FACT_SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)
FACT_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.:>|-]*$")
FACT_RECORD_KEYS = {
    "id",
    "sectionId",
    "role",
    "valueKey",
    "sourceSlot",
    "sourceBindingFingerprint",
    "evidenceIds",
    "qualifiers",
}
FORBIDDEN_PROSE_KEYS = {
    "text",
    "copy",
    "headline",
    "meaning",
    "body",
    "nextMove",
    "caution",
    "summary",
    "label",
    "title",
    "advice",
    "proposition",
}
UNKNOWN_VALUE_KEYS = {
    "unknown",
    "none",
    "unresolved",
    "not-calculated",
    "not_calculated",
}


FINAL_NARRATIVE_FACT_POLICIES: dict[str, dict[str, tuple[str, ...]]] = {
    "chart-positioning": {
        "requiredRoles": (
            "user-emotional-need",
            "user-communication-style",
            "partner-pressure-response",
            "precision-mode",
        ),
        "allowedRoles": (
            "user-emotional-need",
            "user-communication-style",
            "partner-pressure-response",
            "precision-mode",
        ),
        "allowedSourceSlots": (
            "personAEmotionalNeed",
            "personACommunicationStyle",
            "personBPressureResponse",
            "precisionMode",
        ),
    },
    "relationship-fit": {
        "requiredRoles": (
            "relationship-archetype",
            "primary-dynamic",
            "attraction-signal",
            "friction-signal",
            "growth-signal",
        ),
        "allowedRoles": (
            "relationship-archetype",
            "primary-dynamic",
            "secondary-dynamic",
            "attraction-signal",
            "friction-signal",
            "growth-signal",
        ),
        "allowedSourceSlots": (
            "archetypeTitle",
            "primaryDynamicKey",
            "secondaryDynamicKeys",
            "attractionSignals",
            "frictionSignals",
            "growthSignals",
        ),
    },
    "core-answer": {
        "requiredRoles": (
            "question",
            "relationship-stage",
            "contact-status",
            "answer-track",
            "central-dynamic",
            "partner-relationship-need",
            "evidence-signal",
            "observable-sign",
            "uncertainty-level",
        ),
        "allowedRoles": (
            "question",
            "relationship-stage",
            "contact-status",
            "answer-track",
            "central-dynamic",
            "partner-relationship-need",
            "evidence-signal",
            "observable-sign",
            "uncertainty-level",
        ),
        "allowedSourceSlots": (
            "questionKey",
            "relationshipStage",
            "contactStatus",
            "answerTrackKeys",
            "centralDynamicKey",
            "partnerRelationshipNeedKey",
            "answerEvidenceSignals",
            "observableSigns",
            "uncertaintyLevel",
        ),
    },
    "timing-reading": {
        "requiredRoles": (
            "question",
            "contact-status",
            "timing-posture",
            "recommended-action",
            "timing-band",
            "contact-posture",
            "precise-dates-available",
        ),
        "allowedRoles": (
            "question",
            "contact-status",
            "timing-posture",
            "recommended-action",
            "timing-band",
            "contact-posture",
            "precise-dates-available",
            "timing-window",
        ),
        "allowedSourceSlots": (
            "questionKey",
            "contactStatus",
            "timingPostureKey",
            "recommendedAction",
            "topBand",
            "contactPostureKey",
            "preciseDatesAvailable",
            "topWindowKey",
        ),
    },
    "action-direction": {
        "requiredRoles": (
            "question",
            "contact-status",
            "action-purpose",
            "action-mode",
            "completion-boundary",
            "repair-lever",
            "stop-condition",
            "contact-posture",
            "blocked-action",
        ),
        "allowedRoles": (
            "question",
            "contact-status",
            "action-purpose",
            "action-mode",
            "completion-boundary",
            "repair-lever",
            "stop-condition",
            "contact-posture",
            "blocked-action",
        ),
        "allowedSourceSlots": (
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
    },
}


class FinalNarrativeFactContractError(ValueError):
    """Raised when typed final-narrative facts are stale or invalid."""


def unique_strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            output.append(text)
            seen.add(text)
    return output


def canonical_value_key(value: Any) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    text = re.sub(r"[^a-z0-9.:>|-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-.:|")
    return text or "unknown"


def fact_id(section_id: str, role: str, value_key: str) -> str:
    return f"{canonical_value_key(section_id)}.{canonical_value_key(role)}.{canonical_value_key(value_key)}"


def make_fact(
    *,
    section_id: str,
    role: str,
    value_key: Any,
    source_slot: str,
    evidence_ids: Iterable[Any],
    qualifiers: Iterable[Any] = (),
) -> FinalNarrativeFact:
    normalized_value = canonical_value_key(value_key)
    return {
        "id": fact_id(section_id, role, normalized_value),
        "sectionId": section_id,  # type: ignore[typeddict-item]
        "role": canonical_value_key(role),
        "valueKey": normalized_value,
        "sourceSlot": str(source_slot),
        "evidenceIds": unique_strings(evidence_ids),
        "qualifiers": [canonical_value_key(item) for item in unique_strings(qualifiers)],
    }


def source_spec_fingerprint(spec: dict[str, Any]) -> str:
    evidence_identity = [
        {
            "id": str(item.get("id") or ""),
            "domain": str(item.get("domain") or ""),
            "conceptKey": str(item.get("conceptKey") or ""),
        }
        for item in spec.get("evidence") or []
        if isinstance(item, dict)
    ]
    encoded = json.dumps(
        {
            "sectionId": spec.get("sectionId"),
            "context": spec.get("context") or {},
            "semanticSlots": spec.get("semanticSlots") or {},
            "conceptKeys": spec.get("conceptKeys") or [],
            "evidence": evidence_identity,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def source_binding_fingerprint(fact: dict[str, Any], spec: dict[str, Any]) -> str:
    slots = spec.get("semanticSlots") if isinstance(spec.get("semanticSlots"), dict) else {}
    source_slot = str(fact.get("sourceSlot") or "")
    encoded = json.dumps(
        {
            "role": str(fact.get("role") or ""),
            "valueKey": str(fact.get("valueKey") or ""),
            "qualifiers": [str(item) for item in fact.get("qualifiers") or []],
            "sourceSlot": source_slot,
            "sourceValue": slots.get(source_slot),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def bind_facts_to_source(facts: Iterable[dict[str, Any]], spec: dict[str, Any]) -> None:
    for fact in facts:
        fact["sourceBindingFingerprint"] = source_binding_fingerprint(fact, spec)


def is_unknown_value(value_key: str) -> bool:
    return (
        value_key in UNKNOWN_VALUE_KEYS
        or value_key.endswith(".unknown")
        or value_key.endswith(":unknown")
        or value_key.endswith(".unresolved")
        or value_key.endswith(":unresolved")
    )


def validate_fact_section(
    section: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    section_id = str(section.get("sectionId") or "")
    policy = FINAL_NARRATIVE_FACT_POLICIES.get(section_id)
    errors: list[str] = []
    warnings: list[str] = []
    if not policy:
        return {"status": "invalid", "errors": [f"unknown fact section: {section_id}"], "warnings": []}
    if str(spec.get("sectionId") or "") != section_id:
        errors.append("fact section does not match source spec")
    expected_fingerprint = source_spec_fingerprint(spec)
    if section.get("sourceSpecFingerprint") != expected_fingerprint:
        errors.append("source spec fingerprint is stale")

    facts = [item for item in section.get("facts") or [] if isinstance(item, dict)]
    if not facts:
        errors.append("facts are empty")
    allowed_roles = set(policy.get("allowedRoles") or ())
    allowed_slots = set(policy.get("allowedSourceSlots") or ())
    evidence_ids = {
        str(item.get("id") or "")
        for item in spec.get("evidence") or []
        if isinstance(item, dict) and item.get("id")
    }
    ids: list[str] = []
    roles: set[str] = set()
    unknown_ids: list[str] = []
    for index, fact in enumerate(facts):
        extra_keys = set(fact) - FACT_RECORD_KEYS
        if extra_keys:
            errors.append(f"fact[{index}] has unsupported keys: {sorted(extra_keys)}")
        prose_keys = set(fact) & FORBIDDEN_PROSE_KEYS
        if prose_keys:
            errors.append(f"fact[{index}] contains prose keys: {sorted(prose_keys)}")
        current_id = str(fact.get("id") or "")
        role = str(fact.get("role") or "")
        value_key = str(fact.get("valueKey") or "")
        source_slot = str(fact.get("sourceSlot") or "")
        owned_evidence = set(unique_strings(fact.get("evidenceIds") or []))
        ids.append(current_id)
        roles.add(role)
        if not FACT_KEY_PATTERN.fullmatch(current_id):
            errors.append(f"fact[{index}] id is not a stable ASCII key")
        if not FACT_KEY_PATTERN.fullmatch(value_key):
            errors.append(f"fact[{index}] valueKey is not a stable ASCII key")
        if current_id != fact_id(section_id, role, value_key):
            errors.append(f"fact[{index}] id does not match section, role, and valueKey")
        if role not in allowed_roles:
            errors.append(f"fact[{index}] role is not owned by {section_id}: {role}")
        if source_slot not in allowed_slots:
            errors.append(f"fact[{index}] sourceSlot is not owned by {section_id}: {source_slot}")
        if fact.get("sourceBindingFingerprint") != source_binding_fingerprint(fact, spec):
            errors.append(f"fact[{index}] source binding fingerprint is stale")
        if not owned_evidence:
            errors.append(f"fact[{index}] has no evidence")
        if not owned_evidence <= evidence_ids:
            errors.append(f"fact[{index}] references unowned evidence: {sorted(owned_evidence - evidence_ids)}")
        qualifiers = [str(item) for item in fact.get("qualifiers") or []]
        if any(not FACT_KEY_PATTERN.fullmatch(item) for item in qualifiers):
            errors.append(f"fact[{index}] has a non-ASCII qualifier")
        if is_unknown_value(value_key):
            unknown_ids.append(current_id)

    if len(ids) != len(set(ids)):
        errors.append("fact ids are not unique")
    missing_roles = sorted(set(policy.get("requiredRoles") or ()) - roles)
    if missing_roles:
        errors.append(f"required fact roles missing: {missing_roles}")
    selected_ids = unique_strings(section.get("selectedFactIds") or [])
    if not selected_ids:
        errors.append("selectedFactIds is empty")
    if not set(selected_ids) <= set(ids):
        errors.append(f"selectedFactIds reference unknown facts: {sorted(set(selected_ids) - set(ids))}")
    diagnostics = section.get("diagnostics") if isinstance(section.get("diagnostics"), dict) else {}
    if set(unique_strings(diagnostics.get("unknownFactIds") or [])) != set(unknown_ids):
        errors.append("unknown fact diagnostics do not match facts")
    if unknown_ids:
        warnings.append(f"unknown fact values require diagnostics: {len(unknown_ids)}")
    return {"status": "invalid" if errors else "valid", "errors": errors, "warnings": warnings}


def validate_final_narrative_fact_contract(
    contract: dict[str, Any],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if contract.get("version") != FINAL_NARRATIVE_FACT_CONTRACT_VERSION:
        errors.append(f"unsupported fact contract version: {contract.get('version')}")
    if contract.get("rendererMode") != FINAL_NARRATIVE_FACT_RENDERER_MODE:
        errors.append(f"unsupported fact renderer mode: {contract.get('rendererMode')}")
    if contract.get("semanticCoverageVersion") != FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION:
        errors.append(
            f"unsupported semantic coverage version: {contract.get('semanticCoverageVersion')}"
        )
    if contract.get("storyArcVersion") != FINAL_NARRATIVE_STORY_ARC_VERSION:
        errors.append(f"unsupported story arc version: {contract.get('storyArcVersion')}")
    if contract.get("factsRequired") is not True:
        errors.append("factsRequired must be true")
    if contract.get("visibleProseAllowedInFacts") is not False:
        errors.append("visibleProseAllowedInFacts must be false")
    sections = contract.get("sections") if isinstance(contract.get("sections"), dict) else {}
    if set(sections) != set(FINAL_FACT_SECTION_IDS):
        errors.append(f"fact section set mismatch: {sorted(sections)}")
    if set(specs) != set(FINAL_FACT_SECTION_IDS):
        errors.append(f"source spec section set mismatch: {sorted(specs)}")
    errors.extend(semantic_policy_alignment_errors(FINAL_NARRATIVE_FACT_POLICIES))
    errors.extend(
        story_arc_contract_errors(
            FINAL_NARRATIVE_FACT_POLICIES,
            FINAL_NARRATIVE_ROLE_DISPOSITIONS,
        )
    )
    for section_id in FINAL_FACT_SECTION_IDS:
        section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else {}
        spec = specs.get(section_id) if isinstance(specs.get(section_id), dict) else {}
        result = validate_fact_section(section, spec)
        for error in result.get("errors") or []:
            errors.append(f"{section_id}: {error}")
        for warning in result.get("warnings") or []:
            warnings.append(f"{section_id}: {warning}")
    errors.extend(story_arc_fact_errors(sections))
    return {
        "status": "invalid" if errors else "valid",
        "errors": errors,
        "warnings": warnings,
        "sectionCount": len(sections),
    }


def build_final_narrative_fact_contract(
    specs: dict[str, dict[str, Any]],
    facts_by_section: dict[str, list[FinalNarrativeFact]],
    *,
    compatibility_prose_slots: dict[str, Iterable[str]],
) -> FinalNarrativeFactContract:
    sections: dict[str, Any] = {}
    for section_id in FINAL_FACT_SECTION_IDS:
        facts = facts_by_section.get(section_id) or []
        spec = specs.get(section_id) or {}
        bind_facts_to_source(facts, spec)
        unknown_ids = [str(item.get("id") or "") for item in facts if is_unknown_value(str(item.get("valueKey") or ""))]
        section = {
            "sectionId": section_id,
            "sourceSpecFingerprint": source_spec_fingerprint(spec),
            "facts": facts,
            "selectedFactIds": unique_strings(item.get("id") for item in facts),
            "diagnostics": {
                "unknownFactIds": unknown_ids,
                "compatibilityProseSlots": unique_strings(compatibility_prose_slots.get(section_id) or []),
            },
        }
        section["validation"] = validate_fact_section(section, spec)
        sections[section_id] = section
    contract: FinalNarrativeFactContract = {
        "version": FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
        "rendererMode": FINAL_NARRATIVE_FACT_RENDERER_MODE,
        "semanticCoverageVersion": FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
        "storyArcVersion": FINAL_NARRATIVE_STORY_ARC_VERSION,
        "factsRequired": True,
        "visibleProseAllowedInFacts": False,
        "sections": sections,
    }
    contract["validation"] = validate_final_narrative_fact_contract(contract, specs)
    return contract


def refresh_final_narrative_fact_contract(
    contract: dict[str, Any],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Refresh source fingerprints after a deterministic public-copy transform."""

    sections = contract.get("sections") if isinstance(contract.get("sections"), dict) else {}
    for section_id in FINAL_FACT_SECTION_IDS:
        section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else None
        spec = specs.get(section_id) if isinstance(specs.get(section_id), dict) else {}
        if section is None:
            continue
        bind_facts_to_source(
            [item for item in section.get("facts") or [] if isinstance(item, dict)],
            spec,
        )
        section["sourceSpecFingerprint"] = source_spec_fingerprint(spec)
        section["validation"] = validate_fact_section(section, spec)
    contract["validation"] = validate_final_narrative_fact_contract(contract, specs)
    return contract


def refresh_fact_contracts_in_payload(value: Any) -> None:
    """Refresh every copied section bundle in a recursively transformed payload."""

    if isinstance(value, dict):
        specs = value.get("sections") if isinstance(value.get("sections"), dict) else {}
        contract = value.get("finalNarrativeFacts") if isinstance(value.get("finalNarrativeFacts"), dict) else None
        if contract is not None and set(specs) == set(FINAL_FACT_SECTION_IDS):
            refresh_final_narrative_fact_contract(contract, specs)
            bundle_validation = value.get("validation") if isinstance(value.get("validation"), dict) else {}
            fact_validation = contract.get("validation") if isinstance(contract.get("validation"), dict) else {}
            bundle_validation["factContractStatus"] = str(fact_validation.get("status") or "invalid")
            bundle_validation["factContractVersion"] = str(contract.get("version") or "")
            value["validation"] = bundle_validation
        for child in value.values():
            if isinstance(child, (dict, list)):
                refresh_fact_contracts_in_payload(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                refresh_fact_contracts_in_payload(child)


@dataclass(frozen=True)
class ValidatedFinalNarrativeFactContract:
    contract: dict[str, Any]
    sections: dict[str, dict[str, Any]]

    @classmethod
    def from_contract(
        cls,
        contract: dict[str, Any] | None,
        specs: dict[str, dict[str, Any]],
    ) -> "ValidatedFinalNarrativeFactContract":
        source = contract if isinstance(contract, dict) else {}
        validation = validate_final_narrative_fact_contract(source, specs)
        if validation.get("status") != "valid":
            raise FinalNarrativeFactContractError(
                "Invalid final narrative fact contract: "
                + "; ".join(str(item) for item in validation.get("errors") or [])
            )
        sections = source.get("sections") if isinstance(source.get("sections"), dict) else {}
        return cls(contract=source, sections=sections)

    def facts(self, section_id: str, role: str | None = None) -> list[dict[str, Any]]:
        section = self.sections.get(section_id) if isinstance(self.sections.get(section_id), dict) else {}
        facts = [item for item in section.get("facts") or [] if isinstance(item, dict)]
        if role is None:
            return facts
        return [item for item in facts if item.get("role") == role]

    def diagnostics(self, section_id: str) -> dict[str, Any]:
        section = self.sections.get(section_id) if isinstance(self.sections.get(section_id), dict) else {}
        diagnostics = section.get("diagnostics")
        return diagnostics if isinstance(diagnostics, dict) else {}
