"""Canonical semantic value domains for the final narrative layer."""

from __future__ import annotations

from dataclasses import dataclass


ZODIAC_SIGNS = (
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

QUESTION_KEYS = (
    "still-love-me",
    "any-chance",
    "when-to-contact",
    "what-did-i-do-wrong",
    "stay-or-let-go",
)
RELATIONSHIP_STAGE_KEYS = (
    "ambiguous",
    "broke-up-recent",
    "broke-up-long",
    "cold-war",
    "crisis",
)
CONTACT_STATUS_KEYS = (
    "blocked",
    "no-contact",
    "occasional-contact",
    "still-in-contact",
    "living-or-working-together",
)

RELATIONSHIP_ARCHETYPE_KEYS = (
    "past-life-intensity",
    "growth-support",
    "communication-repair",
    "mutual-activation",
    "emotional-familiarity",
    "growth-through-friction",
    "fast-spark-conflict",
    "high-attraction-high-friction",
    "natural-attraction",
    "slow-safety",
)
RELATIONSHIP_DYNAMIC_KEYS = (
    "communication-repair",
    "outer-intensity",
    "identity-rhythm",
    "emotional-safety",
    "saturn-pressure",
    "action-conflict",
    "attraction-pursuit",
    "jupiter-support",
    "slow-safety",
)

ATTRACTION_PAIR_KEYS = (
    "sun-moon",
    "sun-venus",
    "sun-mars",
    "venus-mars",
    "moon-venus",
    "moon-moon",
    "venus-venus",
)
FRICTION_PAIR_KEYS = (
    "mercury-mars",
    "mercury-moon",
    "mercury-sun",
    "mercury-venus",
    "mercury-saturn",
    "mercury-mercury",
    "mars-mars",
    "mars-saturn",
    "moon-mars",
    "moon-moon",
    "moon-venus",
    "moon-saturn",
    "venus-mars",
    "venus-venus",
    "venus-saturn",
    "sun-saturn",
    "sun-moon",
    "sun-venus",
    "sun-mars",
    "outer-planet-intensity",
)
GROWTH_PAIR_KEYS = (
    "mars-saturn",
    "moon-saturn",
    "sun-saturn",
    "venus-saturn",
    "mercury-saturn",
)

PERSON_KEYS = ("persona", "personb")
PLANET_KEYS = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "outer",
)
ASPECT_KEYS = ("conjunction", "sextile", "square", "trine", "opposition", "quincunx")
POLARITY_KEYS = ("soft", "hard", "conjunction", "mixed", "neutral")

PLANET_FUNCTIONS = {
    "sun": "被看見和做自己的需要",
    "moon": "情緒與安全感",
    "mercury": "說話和理解方式",
    "venus": "表達好感的方式",
    "mars": "靠近和處理衝突的速度",
    "jupiter": "鼓勵與期待",
    "saturn": "責任、界線和承諾",
    "uranus": "需要自由和改變的部分",
    "neptune": "想像與理想化",
    "pluto": "強烈在意與控制感",
    "outer": "強烈感受與想像",
}


class FinalNarrativeSemanticDomainError(ValueError):
    """Raised when a value is outside the published final-layer domain."""


@dataclass(frozen=True)
class RelationshipSignal:
    raw: str
    kind: str
    pair_key: str
    actor_person: str
    actor_planet: str
    receiver_person: str
    receiver_planet: str
    aspect: str
    polarity: str

    @property
    def direction_key(self) -> str:
        return f"{self.actor_person}>{self.receiver_person}"


def supported_pairs(kind: str) -> tuple[str, ...]:
    if kind == "attraction":
        return ATTRACTION_PAIR_KEYS
    if kind == "friction":
        return FRICTION_PAIR_KEYS
    if kind == "growth":
        return GROWTH_PAIR_KEYS
    raise FinalNarrativeSemanticDomainError(f"unsupported relationship signal kind: {kind}")


def is_unknown_signal(value_key: str) -> bool:
    return value_key in {"unknown", "none"} or "unresolved" in value_key


def parse_relationship_signal(value_key: str, *, expected_kind: str | None = None) -> RelationshipSignal:
    if is_unknown_signal(value_key):
        raise FinalNarrativeSemanticDomainError(f"unknown relationship signal has no direction: {value_key}")
    parts = value_key.split(":")
    if len(parts) != 7 or ">" not in parts[3]:
        raise FinalNarrativeSemanticDomainError(f"invalid relationship signal: {value_key}")
    kind, pair_key, actor_person, direction, receiver_planet, aspect, polarity = parts
    actor_planet, receiver_person = direction.split(">", 1)
    # Runtime keys encode actor planet after the direction separator:
    # persona:saturn>personb:mars -> persona Saturn acts on personb Mars.
    if expected_kind and kind != expected_kind:
        raise FinalNarrativeSemanticDomainError(
            f"relationship signal kind mismatch: expected {expected_kind}, got {kind}"
        )
    if pair_key not in supported_pairs(kind):
        raise FinalNarrativeSemanticDomainError(f"unsupported {kind} pair: {pair_key}")
    if actor_person not in PERSON_KEYS or receiver_person not in PERSON_KEYS or actor_person == receiver_person:
        raise FinalNarrativeSemanticDomainError(f"invalid relationship direction: {value_key}")
    if actor_planet not in PLANET_KEYS or receiver_planet not in PLANET_KEYS:
        raise FinalNarrativeSemanticDomainError(f"unsupported relationship planet: {value_key}")
    if aspect not in ASPECT_KEYS:
        raise FinalNarrativeSemanticDomainError(f"unsupported relationship aspect: {aspect}")
    if polarity not in POLARITY_KEYS:
        raise FinalNarrativeSemanticDomainError(f"unsupported relationship polarity: {polarity}")
    return RelationshipSignal(
        raw=value_key,
        kind=kind,
        pair_key=pair_key,
        actor_person=actor_person,
        actor_planet=actor_planet,
        receiver_person=receiver_person,
        receiver_planet=receiver_planet,
        aspect=aspect,
        polarity=polarity,
    )


__all__ = [
    "ASPECT_KEYS",
    "ATTRACTION_PAIR_KEYS",
    "CONTACT_STATUS_KEYS",
    "FRICTION_PAIR_KEYS",
    "FinalNarrativeSemanticDomainError",
    "GROWTH_PAIR_KEYS",
    "PLANET_FUNCTIONS",
    "QUESTION_KEYS",
    "RELATIONSHIP_ARCHETYPE_KEYS",
    "RELATIONSHIP_DYNAMIC_KEYS",
    "RELATIONSHIP_STAGE_KEYS",
    "RelationshipSignal",
    "ZODIAC_SIGNS",
    "is_unknown_signal",
    "parse_relationship_signal",
    "supported_pairs",
]
