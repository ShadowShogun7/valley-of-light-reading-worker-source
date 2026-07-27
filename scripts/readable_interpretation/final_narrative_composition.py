"""Runtime composition constraints for the five reader-facing result pages.

Page renderers own wording. This module owns the final assembly boundary: one
semantic job per field, bounded paragraphs, no repeated sentence inside a page,
and no page borrowing another page's finished explanation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Mapping

from .copy_contract import intra_page_overlap_hits, reader_meta_narration_hits
from .final_narrative_chinese_quality import (
    NativeChineseHardGateError,
    validate_hard_native_zh_tw_section,
)
from .final_narrative_page_grammar import (
    VISIBLE_FIELDS,
    FinalNarrativePageGrammarError,
    validate_page_grammar,
)
from .final_narrative_semantic_coverage import FINAL_NARRATIVE_ROLE_DISPOSITIONS
from .final_narrative_story_arc import (
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    visible_roles,
)


FINAL_NARRATIVE_COMPOSITION_VERSION = "final-narrative-composition-v4"
MAXIMUM_SENTENCE_CHARACTERS = 70
MAXIMUM_CROSS_PAGE_BIGRAM_SIMILARITY = 0.34

SENTENCE_SPLIT = re.compile(r"[。！？!?；;\n]+")
NORMALIZE_COPY = re.compile(r"[\s，。；：！？!?「」『』（）()、\-]+")


class FinalNarrativeCompositionError(ValueError):
    """Raised when finished reader copy violates the composition contract."""


@dataclass(frozen=True)
class RoleOwner:
    field: str
    job: str


@dataclass(frozen=True)
class FieldCompositionRule:
    jobs: tuple[str, ...]
    maximum_characters: int


@dataclass(frozen=True)
class SectionCompositionRule:
    page_job: str
    fields: Mapping[str, FieldCompositionRule]
    role_owners: Mapping[str, RoleOwner]
    maximum_total_characters: int


SECTION_COMPOSITION_RULES: dict[str, SectionCompositionRule] = {
    "chart-positioning": SectionCompositionRule(
        page_job="individual relationship style",
        fields={
            "headline": FieldCompositionRule(("relationship-style orientation",), 26),
            "meaning": FieldCompositionRule(("your emotional need", "your communication habit"), 90),
            "body": FieldCompositionRule(("his pressure response",), 60),
            "nextMove": FieldCompositionRule(("pressure handling",), 45),
            "caution": FieldCompositionRule(("chart-data boundary",), 55),
        },
        role_owners={
            "user-emotional-need": RoleOwner("meaning", "your emotional need"),
            "user-communication-style": RoleOwner("meaning", "your communication habit"),
            "partner-pressure-response": RoleOwner("body", "his pressure response"),
            "precision-mode": RoleOwner("caution", "chart-data boundary"),
        },
        maximum_total_characters=190,
    ),
    "relationship-fit": SectionCompositionRule(
        page_job="relationship fit",
        fields={
            "headline": FieldCompositionRule(("relationship archetype",), 32),
            "meaning": FieldCompositionRule(("archetype meaning", "primary dynamic"), 90),
            "body": FieldCompositionRule(("attraction", "friction", "secondary dynamic"), 160),
            "nextMove": FieldCompositionRule(("repair potential",), 60),
            "caution": FieldCompositionRule(("fit boundary",), 55),
        },
        role_owners={
            "relationship-archetype": RoleOwner("headline", "relationship archetype"),
            "primary-dynamic": RoleOwner("meaning", "primary dynamic"),
            "secondary-dynamic": RoleOwner("body", "secondary dynamic"),
            "attraction-signal": RoleOwner("body", "attraction"),
            "friction-signal": RoleOwner("body", "friction"),
            "growth-signal": RoleOwner("nextMove", "repair potential"),
        },
        maximum_total_characters=320,
    ),
    "core-answer": SectionCompositionRule(
        page_job="direct answer to the selected question",
        fields={
            "headline": FieldCompositionRule(("answer track",), 35),
            "meaning": FieldCompositionRule(("direct answer",), 65),
            "body": FieldCompositionRule(("question-specific evidence",), 90),
            "nextMove": FieldCompositionRule(("condition that changes the answer",), 55),
            "caution": FieldCompositionRule(("answer uncertainty",), 55),
        },
        role_owners={
            "question": RoleOwner("meaning", "direct answer"),
            "answer-track": RoleOwner("headline", "answer track"),
            "evidence-signal": RoleOwner("body", "question-specific evidence"),
            "observable-sign": RoleOwner("nextMove", "condition that changes the answer"),
            "uncertainty-level": RoleOwner("caution", "answer uncertainty"),
        },
        maximum_total_characters=220,
    ),
    "timing-reading": SectionCompositionRule(
        page_job="current contact permission and timing window",
        fields={
            "headline": FieldCompositionRule(("timing posture", "question timing focus"), 50),
            "meaning": FieldCompositionRule(("current contact permission",), 45),
            "body": FieldCompositionRule(("suitable window", "overall timing band"), 120),
            "nextMove": FieldCompositionRule(("timing action",), 55),
            "caution": FieldCompositionRule(("timing uncertainty",), 95),
        },
        role_owners={
            "contact-status": RoleOwner("meaning", "current contact permission"),
            "timing-posture": RoleOwner("headline", "timing posture"),
            "recommended-action": RoleOwner("nextMove", "timing action"),
            "timing-band": RoleOwner("body", "overall timing band"),
            "precise-dates-available": RoleOwner("caution", "timing uncertainty"),
            "timing-window": RoleOwner("body", "suitable window"),
        },
        maximum_total_characters=250,
    ),
    "action-direction": SectionCompositionRule(
        page_job="one action, one completion boundary, and one stopping condition",
        fields={
            "headline": FieldCompositionRule(("action focus",), 40),
            "meaning": FieldCompositionRule(("action purpose",), 65),
            "body": FieldCompositionRule(("completion boundary",), 65),
            "nextMove": FieldCompositionRule(("one action",), 55),
            "caution": FieldCompositionRule(("one stopping condition",), 70),
        },
        role_owners={
            "question": RoleOwner("headline", "action focus"),
            "action-purpose": RoleOwner("meaning", "action purpose"),
            "action-mode": RoleOwner("nextMove", "one action"),
            "completion-boundary": RoleOwner("body", "completion boundary"),
            "stop-condition": RoleOwner("caution", "one stopping condition"),
        },
        maximum_total_characters=200,
    ),
}


def normalize_copy(value: str) -> str:
    return NORMALIZE_COPY.sub("", str(value or ""))


def split_sentences(value: str) -> list[str]:
    return [item.strip() for item in SENTENCE_SPLIT.split(str(value or "")) if item.strip()]


def character_bigram_similarity(left: str, right: str) -> float:
    def bigrams(value: str) -> set[str]:
        normalized = normalize_copy(value)
        return {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}

    left_bigrams = bigrams(left)
    right_bigrams = bigrams(right)
    if not left_bigrams or not right_bigrams:
        return 0.0
    return len(left_bigrams & right_bigrams) / len(left_bigrams | right_bigrams)


def composition_contract_errors(
    rules: Mapping[str, SectionCompositionRule],
    role_dispositions: Mapping[str, Mapping[str, str]],
) -> list[str]:
    errors: list[str] = []
    if set(rules) != set(role_dispositions):
        errors.append("composition section registry is incomplete")
    for section_id, rule in rules.items():
        if set(rule.fields) != set(VISIBLE_FIELDS):
            errors.append(f"{section_id}: composition field registry is incomplete")
        registered_roles = set(role_dispositions.get(section_id) or {})
        presentation_roles = set(
            FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}
        )
        if registered_roles != presentation_roles:
            errors.append(
                f"{section_id}: composition/story role registry mismatch"
            )
        owned_roles = set(rule.role_owners)
        expected_visible_roles = visible_roles(section_id)
        if owned_roles != expected_visible_roles:
            errors.append(
                f"{section_id}: role ownership mismatch: "
                f"missing={sorted(expected_visible_roles - owned_roles)} "
                f"extra={sorted(owned_roles - expected_visible_roles)}"
            )
        for role, owner in rule.role_owners.items():
            if owner.field not in rule.fields:
                errors.append(
                    f"{section_id}:{role}: owned by unknown field {owner.field}"
                )
                continue
            if owner.job not in rule.fields[owner.field].jobs:
                errors.append(
                    f"{section_id}:{role}: undeclared semantic job {owner.job}"
                )
    return errors


def validate_composition_contract() -> None:
    errors = composition_contract_errors(
        SECTION_COMPOSITION_RULES,
        FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    )
    if errors:
        raise FinalNarrativeCompositionError("; ".join(errors))


def validate_section_composition(section_id: str, rendered: Mapping[str, str]) -> None:
    validate_composition_contract()
    rule = SECTION_COMPOSITION_RULES.get(section_id)
    if rule is None:
        raise FinalNarrativeCompositionError(f"unknown composition section: {section_id}")
    try:
        validate_page_grammar(section_id, rendered)
        validate_hard_native_zh_tw_section(section_id, rendered)
    except (FinalNarrativePageGrammarError, NativeChineseHardGateError) as exc:
        raise FinalNarrativeCompositionError(str(exc)) from exc

    total_characters = sum(len(str(rendered.get(field) or "")) for field in VISIBLE_FIELDS)
    if total_characters > rule.maximum_total_characters:
        raise FinalNarrativeCompositionError(
            f"{section_id}: page length {total_characters} exceeds {rule.maximum_total_characters}"
        )

    sentence_owners: dict[str, str] = {}
    for field in VISIBLE_FIELDS:
        value = str(rendered.get(field) or "")
        field_rule = rule.fields[field]
        if len(value) > field_rule.maximum_characters:
            raise FinalNarrativeCompositionError(
                f"{section_id}:{field}: length {len(value)} exceeds {field_rule.maximum_characters}"
            )
        for sentence in split_sentences(value):
            if len(sentence) > MAXIMUM_SENTENCE_CHARACTERS:
                raise FinalNarrativeCompositionError(
                    f"{section_id}:{field}: sentence exceeds {MAXIMUM_SENTENCE_CHARACTERS} characters"
                )
            normalized = normalize_copy(sentence)
            if len(normalized) < 12:
                continue
            previous_field = sentence_owners.get(normalized)
            if previous_field is not None:
                raise FinalNarrativeCompositionError(
                    f"{section_id}: repeated sentence in {previous_field} and {field}: {sentence}"
                )
            sentence_owners[normalized] = field

    overlap_hits = intra_page_overlap_hits(dict(rendered))
    if overlap_hits:
        first = overlap_hits[0]
        raise FinalNarrativeCompositionError(
            f"{section_id}: repeated thought across {first['leftField']} and "
            f"{first['rightField']}: {first['phrase']}"
        )
    meta_hits = reader_meta_narration_hits("".join(str(rendered[field]) for field in VISIBLE_FIELDS))
    if meta_hits:
        raise FinalNarrativeCompositionError(
            f"{section_id}: reader-facing page narration leaked: {meta_hits}"
        )


def validate_reading_composition(sections: Mapping[str, Mapping[str, str]]) -> None:
    validate_composition_contract()
    if set(sections) != set(SECTION_COMPOSITION_RULES):
        raise FinalNarrativeCompositionError(
            f"reading section set mismatch: {sorted(sections)}"
        )
    for section_id, rendered in sections.items():
        validate_section_composition(section_id, rendered)

    sentence_owners: dict[str, tuple[str, str]] = {}
    page_texts: dict[str, str] = {}
    for section_id, rendered in sections.items():
        page_texts[section_id] = "".join(str(rendered[field]) for field in VISIBLE_FIELDS)
        for field in VISIBLE_FIELDS:
            for sentence in split_sentences(str(rendered[field])):
                normalized = normalize_copy(sentence)
                if len(normalized) < 14:
                    continue
                previous = sentence_owners.get(normalized)
                if previous is not None and previous[0] != section_id:
                    raise FinalNarrativeCompositionError(
                        f"cross-page sentence repeated in {previous[0]}:{previous[1]} and "
                        f"{section_id}:{field}: {sentence}"
                    )
                sentence_owners[normalized] = (section_id, field)

    for left_id, right_id in combinations(page_texts, 2):
        similarity = character_bigram_similarity(page_texts[left_id], page_texts[right_id])
        if similarity > MAXIMUM_CROSS_PAGE_BIGRAM_SIMILARITY:
            raise FinalNarrativeCompositionError(
                f"cross-page similarity {similarity:.3f} exceeds "
                f"{MAXIMUM_CROSS_PAGE_BIGRAM_SIMILARITY:.2f}: {left_id} / {right_id}"
            )


def composition_metrics(sections: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    similarities = {
        f"{left_id}|{right_id}": round(character_bigram_similarity(
            "".join(str(sections[left_id][field]) for field in VISIBLE_FIELDS),
            "".join(str(sections[right_id][field]) for field in VISIBLE_FIELDS),
        ), 3)
        for left_id, right_id in combinations(sections, 2)
    }
    sentence_lengths = [
        len(sentence)
        for rendered in sections.values()
        for field in VISIBLE_FIELDS
        for sentence in split_sentences(str(rendered[field]))
    ]
    return {
        "maximumCrossPageBigramSimilarity": max(similarities.values(), default=0.0),
        "crossPageSimilarities": similarities,
        "maximumSentenceCharacters": max(sentence_lengths, default=0),
    }


__all__ = [
    "FINAL_NARRATIVE_COMPOSITION_VERSION",
    "MAXIMUM_CROSS_PAGE_BIGRAM_SIMILARITY",
    "MAXIMUM_SENTENCE_CHARACTERS",
    "FinalNarrativeCompositionError",
    "RoleOwner",
    "SECTION_COMPOSITION_RULES",
    "SectionCompositionRule",
    "character_bigram_similarity",
    "composition_contract_errors",
    "composition_metrics",
    "normalize_copy",
    "split_sentences",
    "validate_composition_contract",
    "validate_reading_composition",
    "validate_section_composition",
]
