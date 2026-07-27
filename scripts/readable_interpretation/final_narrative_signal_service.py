"""Shared prose-free relationship-signal semantics for final page realizers."""

from __future__ import annotations

from functools import lru_cache

from .final_narrative_semantic_domains import (
    ASPECT_KEYS,
    ATTRACTION_PAIR_KEYS,
    FRICTION_PAIR_KEYS,
    GROWTH_PAIR_KEYS,
    PERSON_KEYS,
    PLANET_KEYS,
    RelationshipSignal,
    parse_relationship_signal,
)


FINAL_NARRATIVE_SIGNAL_SERVICE_VERSION = "final-narrative-signal-service-v1"

SIGNAL_KIND_BY_ROLE = {
    "attraction-signal": "attraction",
    "friction-signal": "friction",
    "growth-signal": "growth",
    "evidence-signal": "evidence",
}

CANONICAL_ASPECT_POLARITY = {
    "conjunction": "conjunction",
    "sextile": "soft",
    "trine": "soft",
    "square": "hard",
    "opposition": "hard",
    "quincunx": "hard",
}

PAIR_DOMAINS = {
    "attraction": ATTRACTION_PAIR_KEYS,
    "friction": FRICTION_PAIR_KEYS,
    "growth": GROWTH_PAIR_KEYS,
}

OUTER_PLANETS = frozenset({"uranus", "neptune", "pluto", "outer"})


class FinalNarrativeSignalServiceError(ValueError):
    """Raised when a page attempts to realize an unsupported signal meaning."""


def pair_orientations(kind: str, pair_key: str) -> tuple[tuple[str, str], ...]:
    if kind not in PAIR_DOMAINS:
        raise FinalNarrativeSignalServiceError(f"unsupported signal kind: {kind}")
    if pair_key not in PAIR_DOMAINS[kind]:
        raise FinalNarrativeSignalServiceError(
            f"unsupported {kind} signal pair: {pair_key}"
        )
    if kind == "friction" and pair_key == "outer-planet-intensity":
        return tuple(
            (actor_planet, receiver_planet)
            for actor_planet in PLANET_KEYS
            for receiver_planet in PLANET_KEYS
            if actor_planet in OUTER_PLANETS or receiver_planet in OUTER_PLANETS
        )
    first, second = pair_key.split("-", 1)
    if first == second:
        return ((first, second),)
    return ((first, second), (second, first))


@lru_cache(maxsize=None)
def supported_relationship_signal_values(kind: str) -> tuple[str, ...]:
    if kind not in PAIR_DOMAINS:
        raise FinalNarrativeSignalServiceError(f"unsupported signal kind: {kind}")
    values: list[str] = []
    for pair_key in PAIR_DOMAINS[kind]:
        for actor_planet, receiver_planet in pair_orientations(kind, pair_key):
            for actor_person in PERSON_KEYS:
                receiver_person = "personb" if actor_person == "persona" else "persona"
                for aspect in ASPECT_KEYS:
                    values.append(
                        f"{kind}:{pair_key}:{actor_person}:{actor_planet}>"
                        f"{receiver_person}:{receiver_planet}:{aspect}:"
                        f"{CANONICAL_ASPECT_POLARITY[aspect]}"
                    )
    return tuple(values)


@lru_cache(maxsize=None)
def supported_evidence_signal_values() -> tuple[str, ...]:
    return tuple(
        value
        for kind in PAIR_DOMAINS
        for value in supported_relationship_signal_values(kind)
    )


def resolve_relationship_signal(
    value_key: str,
    *,
    expected_kind: str | None = None,
) -> RelationshipSignal:
    signal = parse_relationship_signal(value_key, expected_kind=expected_kind)
    if signal.kind not in PAIR_DOMAINS:
        raise FinalNarrativeSignalServiceError(
            f"unsupported relationship signal kind: {signal.kind}"
        )
    if (signal.actor_planet, signal.receiver_planet) not in pair_orientations(
        signal.kind,
        signal.pair_key,
    ):
        raise FinalNarrativeSignalServiceError(
            f"unsupported {signal.kind} signal direction: "
            f"{signal.actor_planet}>{signal.receiver_planet}"
        )
    expected_polarity = CANONICAL_ASPECT_POLARITY[signal.aspect]
    if signal.polarity != expected_polarity:
        raise FinalNarrativeSignalServiceError(
            f"non-canonical aspect polarity: {value_key}"
        )
    if value_key not in set(supported_relationship_signal_values(signal.kind)):
        raise FinalNarrativeSignalServiceError(
            f"unsupported relationship signal value: {value_key}"
        )
    return signal


__all__ = [
    "CANONICAL_ASPECT_POLARITY",
    "FINAL_NARRATIVE_SIGNAL_SERVICE_VERSION",
    "FinalNarrativeSignalServiceError",
    "OUTER_PLANETS",
    "PAIR_DOMAINS",
    "SIGNAL_KIND_BY_ROLE",
    "pair_orientations",
    "resolve_relationship_signal",
    "supported_evidence_signal_values",
    "supported_relationship_signal_values",
]
