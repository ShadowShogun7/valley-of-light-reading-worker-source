"""Controlled reader-language realization primitives.

Semantic copy is selected by an explicit purpose, never by a random or hashed
clause choice.  A form must be a complete thought so renderers do not assemble
independent sentence fragments at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence


RealizationPurpose = Literal["direct", "situational", "relational"]
REALIZATION_PURPOSES: tuple[RealizationPurpose, ...] = (
    "direct",
    "situational",
    "relational",
)


class FinalNarrativeRealizationError(ValueError):
    """Raised when controlled semantic copy is missing or malformed."""


@dataclass(frozen=True)
class RealizationForms:
    direct: str
    situational: str
    relational: str

    def for_purpose(self, purpose: RealizationPurpose) -> str:
        return getattr(self, purpose)

    def validate(self, identity: str) -> None:
        values = [self.direct.strip(), self.situational.strip(), self.relational.strip()]
        if any(not value for value in values):
            raise FinalNarrativeRealizationError(f"{identity}: all realization forms are required")
        normalized = {"".join(value.split()).rstrip("。！？") for value in values}
        if len(normalized) != len(REALIZATION_PURPOSES):
            raise FinalNarrativeRealizationError(f"{identity}: realization forms are not distinct")


def realize(
    catalog: Mapping[str, RealizationForms],
    value_key: str,
    purpose: RealizationPurpose,
    *,
    identity: str,
) -> str:
    forms = catalog.get(value_key)
    if forms is None:
        raise FinalNarrativeRealizationError(f"{identity}: unsupported realization value: {value_key}")
    forms.validate(f"{identity}:{value_key}")
    return forms.for_purpose(purpose)


def select_context_variant(values: Sequence[str], index: int, *, identity: str) -> str:
    """Select a full copy variant from an explicit semantic-domain index."""

    if not values:
        raise FinalNarrativeRealizationError(f"{identity}: no controlled variants")
    return str(values[index % len(values)])


def domain_index(value: str, domain: Sequence[str], *, identity: str) -> int:
    try:
        return tuple(domain).index(value)
    except ValueError as exc:
        raise FinalNarrativeRealizationError(
            f"{identity}: value is outside controlled domain: {value}"
        ) from exc


__all__ = [
    "FinalNarrativeRealizationError",
    "REALIZATION_PURPOSES",
    "RealizationForms",
    "RealizationPurpose",
    "domain_index",
    "realize",
    "select_context_variant",
]
