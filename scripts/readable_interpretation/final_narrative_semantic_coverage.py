"""Semantic coverage contract for the final reader-language layer.

Every typed fact role must have an explicit realization purpose. Page renderers
also use ``SectionFactReader`` so an emitted role cannot be silently ignored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FactDisposition = Literal[
    "reader-language",
    "composition-control",
    "routing-control",
    "safety-control",
]

FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION = "final-narrative-semantic-coverage-v2"


FINAL_NARRATIVE_ROLE_DISPOSITIONS: dict[str, dict[str, FactDisposition]] = {
    "chart-positioning": {
        "user-emotional-need": "reader-language",
        "user-communication-style": "reader-language",
        "partner-pressure-response": "reader-language",
        "precision-mode": "safety-control",
    },
    "relationship-fit": {
        "relationship-archetype": "reader-language",
        "primary-dynamic": "reader-language",
        "secondary-dynamic": "reader-language",
        "attraction-signal": "reader-language",
        "friction-signal": "reader-language",
        "growth-signal": "reader-language",
    },
    "core-answer": {
        "question": "routing-control",
        "relationship-stage": "routing-control",
        "contact-status": "routing-control",
        "answer-track": "composition-control",
        "central-dynamic": "composition-control",
        "partner-relationship-need": "composition-control",
        "evidence-signal": "reader-language",
        "observable-sign": "reader-language",
        "uncertainty-level": "safety-control",
    },
    "timing-reading": {
        "question": "routing-control",
        "contact-status": "routing-control",
        "timing-posture": "composition-control",
        "recommended-action": "reader-language",
        "timing-band": "reader-language",
        "contact-posture": "routing-control",
        "precise-dates-available": "safety-control",
        "timing-window": "reader-language",
    },
    "action-direction": {
        "question": "routing-control",
        "contact-status": "routing-control",
        "action-purpose": "reader-language",
        "action-mode": "reader-language",
        "completion-boundary": "reader-language",
        "repair-lever": "composition-control",
        "stop-condition": "safety-control",
        "contact-posture": "routing-control",
        "blocked-action": "safety-control",
    },
}


class FinalNarrativeSemanticCoverageError(ValueError):
    """Raised when a typed fact has no controlled realization path."""


def semantic_policy_alignment_errors(
    policies: dict[str, dict[str, tuple[str, ...]]],
) -> list[str]:
    errors: list[str] = []
    if set(policies) != set(FINAL_NARRATIVE_ROLE_DISPOSITIONS):
        errors.append(
            "semantic coverage section mismatch: "
            f"policies={sorted(policies)} registry={sorted(FINAL_NARRATIVE_ROLE_DISPOSITIONS)}"
        )
    for section_id, policy in policies.items():
        allowed = set(policy.get("allowedRoles") or ())
        registered = set(FINAL_NARRATIVE_ROLE_DISPOSITIONS.get(section_id) or {})
        if allowed != registered:
            errors.append(
                f"{section_id}: semantic role registry mismatch: "
                f"missing={sorted(allowed - registered)} extra={sorted(registered - allowed)}"
            )
    return errors


@dataclass
class SectionFactReader:
    """Section-scoped fact access with one-pass semantic consumption."""

    contract: Any
    section_id: str
    accessed_roles: set[str] = field(default_factory=set)
    consumed_fact_ids: set[str] = field(default_factory=set)
    unknown_fallbacks: list[dict[str, str]] = field(default_factory=list)

    def _registered_roles(self) -> dict[str, FactDisposition]:
        roles = FINAL_NARRATIVE_ROLE_DISPOSITIONS.get(self.section_id)
        if roles is None:
            raise FinalNarrativeSemanticCoverageError(f"unknown final narrative section: {self.section_id}")
        return roles

    def records(self, role: str) -> list[dict[str, Any]]:
        if role not in self._registered_roles():
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: renderer requested unregistered role: {role}"
            )
        if role in self.accessed_roles:
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: semantic role consumed more than once: {role}"
            )
        self.accessed_roles.add(role)
        records = self.contract.facts(self.section_id, role)
        duplicate_ids = {
            str(item.get("id") or "")
            for item in records
            if item.get("id") and str(item.get("id")) in self.consumed_fact_ids
        }
        if duplicate_ids:
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: semantic facts consumed more than once: {sorted(duplicate_ids)}"
            )
        self.consumed_fact_ids.update(
            str(item.get("id") or "") for item in records if item.get("id")
        )
        return records

    def values(self, role: str) -> list[str]:
        return [
            str(item.get("valueKey") or "")
            for item in self.records(role)
            if item.get("valueKey")
        ]

    def first(self, role: str, *, required: bool = False, default: str = "") -> str:
        values = self.values(role)
        if values:
            return values[0]
        if required:
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: required realization fact is missing: {role}"
            )
        return default

    def disposition(self, role: str) -> FactDisposition:
        roles = self._registered_roles()
        if role not in roles:
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: role has no semantic disposition: {role}"
            )
        return roles[role]

    def record_unknown_fallback(self, role: str, value: str, fallback_id: str) -> None:
        if role not in self._registered_roles():
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: fallback requested for unregistered role: {role}"
            )
        self.unknown_fallbacks.append(
            {"role": role, "value": value, "fallbackId": fallback_id}
        )

    def record_known_fallback(self, role: str, value: str, fallback_id: str) -> None:
        raise FinalNarrativeSemanticCoverageError(
            f"{self.section_id}:{role}: known value used fallback {fallback_id}: {value}"
        )

    def fallback_diagnostics(self) -> dict[str, Any]:
        return {
            "knownFallbackCount": 0,
            "unknownFallbackCount": len(self.unknown_fallbacks),
            "unknownFallbacks": list(self.unknown_fallbacks),
        }

    def assert_complete(self) -> None:
        emitted_facts = self.contract.facts(self.section_id)
        emitted_roles = {str(item.get("role") or "") for item in emitted_facts if item.get("role")}
        unhandled = emitted_roles - self.accessed_roles
        if unhandled:
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: emitted facts were not realized: {sorted(unhandled)}"
            )
        emitted_ids = {str(item.get("id") or "") for item in emitted_facts if item.get("id")}
        unconsumed_ids = emitted_ids - self.consumed_fact_ids
        if unconsumed_ids:
            raise FinalNarrativeSemanticCoverageError(
                f"{self.section_id}: emitted fact IDs were not consumed: {sorted(unconsumed_ids)}"
            )


def require_supported_value(
    *,
    section_id: str,
    role: str,
    value: str,
    supported: set[str] | frozenset[str] | tuple[str, ...] | list[str],
) -> str:
    if value not in supported:
        raise FinalNarrativeSemanticCoverageError(
            f"{section_id}:{role}: unsupported value: {value or '<empty>'}"
        )
    return value
