"""Prose-free semantic plan for native Traditional Chinese realization."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from .final_narrative_composition import SECTION_COMPOSITION_RULES
from .final_narrative_fact_contract import FACT_KEY_PATTERN, fact_id
from .final_narrative_page_grammar import VISIBLE_FIELDS
from .final_narrative_realization import REALIZATION_PURPOSES, RealizationPurpose
from .final_narrative_semantic_domains import is_unknown_signal, parse_relationship_signal


FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION = "final-narrative-reader-meaning-frame-v1"
CertaintyLevel = Literal["observed", "conditional", "bounded", "unknown"]
CERTAINTY_LEVELS: tuple[CertaintyLevel, ...] = (
    "observed",
    "conditional",
    "bounded",
    "unknown",
)
SIGNAL_ROLES = {
    "attraction-signal",
    "friction-signal",
    "growth-signal",
    "evidence-signal",
}
ASPECT_BEHAVIORS = {
    "conjunction": "intensifies-together",
    "sextile": "cooperates-easily",
    "trine": "flows-naturally",
    "square": "activates-conflict",
    "opposition": "polarizes-response",
    "quincunx": "misaligns-rhythm",
}
FRAME_KEYS = {
    "version",
    "sectionId",
    "field",
    "role",
    "sceneKey",
    "valueKey",
    "sourceFactId",
    "sourceBindingFingerprint",
    "purpose",
    "certainty",
    "evidenceIds",
    "qualifiers",
    "actorPerson",
    "receiverPerson",
    "pairKey",
    "direction",
    "aspect",
    "aspectBehavior",
}
FORBIDDEN_FRAME_PROSE_KEYS = {
    "text",
    "copy",
    "headline",
    "meaning",
    "body",
    "nextMove",
    "caution",
    "summary",
    "title",
    "label",
    "advice",
    "sentence",
    "template",
}


class ReaderMeaningFrameError(ValueError):
    """Raised when a realization frame contains prose or loses fact ownership."""


@dataclass(frozen=True)
class ReaderMeaningFrame:
    version: str
    section_id: str
    field: str
    role: str
    scene_key: str
    value_key: str
    source_fact_id: str
    source_binding_fingerprint: str
    purpose: RealizationPurpose
    certainty: CertaintyLevel
    evidence_ids: tuple[str, ...]
    qualifiers: tuple[str, ...]
    actor_person: str = ""
    receiver_person: str = ""
    pair_key: str = ""
    direction: str = ""
    aspect: str = ""
    aspect_behavior: str = ""

    def as_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "sectionId": self.section_id,
            "field": self.field,
            "role": self.role,
            "sceneKey": self.scene_key,
            "valueKey": self.value_key,
            "sourceFactId": self.source_fact_id,
            "sourceBindingFingerprint": self.source_binding_fingerprint,
            "purpose": self.purpose,
            "certainty": self.certainty,
            "evidenceIds": list(self.evidence_ids),
            "qualifiers": list(self.qualifiers),
            "actorPerson": self.actor_person,
            "receiverPerson": self.receiver_person,
            "pairKey": self.pair_key,
            "direction": self.direction,
            "aspect": self.aspect,
            "aspectBehavior": self.aspect_behavior,
        }

    def validate(self) -> None:
        errors = reader_meaning_frame_errors(self.as_payload())
        if errors:
            raise ReaderMeaningFrameError("; ".join(errors))


def stable_ascii_key(value: str) -> bool:
    return bool(value and FACT_KEY_PATTERN.fullmatch(value))


def reader_meaning_frame_errors(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    extra_keys = set(payload) - FRAME_KEYS
    if extra_keys:
        errors.append(f"unsupported frame keys: {sorted(extra_keys)}")
    prose_keys = set(payload) & FORBIDDEN_FRAME_PROSE_KEYS
    if prose_keys:
        errors.append(f"visible prose entered meaning frame: {sorted(prose_keys)}")
    if payload.get("version") != FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION:
        errors.append("meaning-frame version is stale")

    section_id = str(payload.get("sectionId") or "")
    field = str(payload.get("field") or "")
    role = str(payload.get("role") or "")
    scene_key = str(payload.get("sceneKey") or "")
    value_key = str(payload.get("valueKey") or "")
    source_fact_id = str(payload.get("sourceFactId") or "")
    source_binding_fingerprint = str(payload.get("sourceBindingFingerprint") or "")
    purpose = str(payload.get("purpose") or "")
    certainty = str(payload.get("certainty") or "")

    section_rule = SECTION_COMPOSITION_RULES.get(section_id)
    if section_rule is None:
        errors.append(f"unknown frame section: {section_id}")
    if field not in VISIBLE_FIELDS:
        errors.append(f"unknown frame field: {field}")
    if section_rule is not None:
        owner = section_rule.role_owners.get(role)
        if owner is None:
            errors.append(f"role is not owned by {section_id}: {role}")
        elif owner.field != field:
            errors.append(f"role {role} is owned by {owner.field}, not {field}")
    for label, value in (
        ("role", role),
        ("sceneKey", scene_key),
        ("valueKey", value_key),
        ("sourceFactId", source_fact_id),
    ):
        if not stable_ascii_key(value):
            errors.append(f"{label} must be a stable ASCII key")
    if stable_ascii_key(role) and stable_ascii_key(value_key):
        expected_fact_id = fact_id(section_id, role, value_key)
        if source_fact_id != expected_fact_id:
            errors.append("sourceFactId does not match section, role, and valueKey")
    if not re.fullmatch(r"[a-f0-9]{64}", source_binding_fingerprint):
        errors.append("sourceBindingFingerprint must be a SHA-256 value")
    if purpose not in REALIZATION_PURPOSES:
        errors.append(f"unsupported realization purpose: {purpose}")
    if certainty not in CERTAINTY_LEVELS:
        errors.append(f"unsupported certainty level: {certainty}")

    evidence_ids = [str(item or "") for item in payload.get("evidenceIds") or []]
    qualifiers = [str(item or "") for item in payload.get("qualifiers") or []]
    if not evidence_ids or any(not item.strip() for item in evidence_ids):
        errors.append("meaning frame requires non-empty evidence ids")
    if any(not stable_ascii_key(item) for item in qualifiers):
        errors.append("meaning-frame qualifiers must be stable ASCII keys")

    actor = str(payload.get("actorPerson") or "")
    receiver = str(payload.get("receiverPerson") or "")
    pair_key = str(payload.get("pairKey") or "")
    direction = str(payload.get("direction") or "")
    aspect = str(payload.get("aspect") or "")
    aspect_behavior = str(payload.get("aspectBehavior") or "")
    signal_fields = (actor, receiver, pair_key, direction, aspect, aspect_behavior)
    if role in SIGNAL_ROLES and not is_unknown_signal(value_key):
        try:
            signal = parse_relationship_signal(value_key)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            expected = (
                signal.actor_person,
                signal.receiver_person,
                signal.pair_key,
                signal.direction_key,
                signal.aspect,
                ASPECT_BEHAVIORS[signal.aspect],
            )
            if signal_fields != expected:
                errors.append("signal meaning-frame fields do not match valueKey")
    elif any(signal_fields):
        errors.append("non-signal frame contains relationship-signal fields")
    return errors


def frame_from_fact(
    fact: Mapping[str, Any],
    *,
    scene_key: str,
    purpose: RealizationPurpose,
    certainty: CertaintyLevel = "bounded",
) -> ReaderMeaningFrame:
    section_id = str(fact.get("sectionId") or "")
    role = str(fact.get("role") or "")
    value_key = str(fact.get("valueKey") or "")
    section_rule = SECTION_COMPOSITION_RULES.get(section_id)
    owner = section_rule.role_owners.get(role) if section_rule is not None else None
    field = owner.field if owner is not None else ""

    signal_payload = {
        "actor_person": "",
        "receiver_person": "",
        "pair_key": "",
        "direction": "",
        "aspect": "",
        "aspect_behavior": "",
    }
    if role in SIGNAL_ROLES and not is_unknown_signal(value_key):
        signal = parse_relationship_signal(value_key)
        signal_payload = {
            "actor_person": signal.actor_person,
            "receiver_person": signal.receiver_person,
            "pair_key": signal.pair_key,
            "direction": signal.direction_key,
            "aspect": signal.aspect,
            "aspect_behavior": ASPECT_BEHAVIORS[signal.aspect],
        }

    frame = ReaderMeaningFrame(
        version=FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION,
        section_id=section_id,
        field=field,
        role=role,
        scene_key=scene_key,
        value_key=value_key,
        source_fact_id=str(fact.get("id") or ""),
        source_binding_fingerprint=str(fact.get("sourceBindingFingerprint") or ""),
        purpose=purpose,
        certainty=certainty,
        evidence_ids=tuple(str(item) for item in fact.get("evidenceIds") or []),
        qualifiers=tuple(str(item) for item in fact.get("qualifiers") or []),
        **signal_payload,
    )
    frame.validate()
    return frame


def meaning_frame_contract_payload() -> dict[str, Any]:
    return {
        "version": FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION,
        "requiredKeys": sorted(FRAME_KEYS),
        "forbiddenProseKeys": sorted(FORBIDDEN_FRAME_PROSE_KEYS),
        "purposes": list(REALIZATION_PURPOSES),
        "certaintyLevels": list(CERTAINTY_LEVELS),
        "aspectBehaviors": dict(sorted(ASPECT_BEHAVIORS.items())),
        "signalRoles": sorted(SIGNAL_ROLES),
    }


__all__ = [
    "ASPECT_BEHAVIORS",
    "CERTAINTY_LEVELS",
    "FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION",
    "FORBIDDEN_FRAME_PROSE_KEYS",
    "FRAME_KEYS",
    "ReaderMeaningFrame",
    "ReaderMeaningFrameError",
    "frame_from_fact",
    "meaning_frame_contract_payload",
    "reader_meaning_frame_errors",
]
