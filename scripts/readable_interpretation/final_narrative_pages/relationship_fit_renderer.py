"""Reader-language realization for the relationship-fit page."""

from __future__ import annotations

from typing import Any

from ..final_narrative_chinese_plan import ReaderMeaningFrame, frame_from_fact
from ..final_narrative_paragraph_plan import paragraph_plan, validate_paragraph_output
from ..final_narrative_semantic_coverage import (
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    require_supported_value,
)
from ..final_narrative_semantic_domains import (
    RELATIONSHIP_ARCHETYPE_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
    is_unknown_signal,
)
from .relationship_fit_zh_tw_catalog import (
    ROLE_TO_KIND,
    caution_for,
    finish_sentence,
    headline_for,
    paragraph_relationship_fit_frame,
    supported_signal_values,
    validate_relationship_fit_rendered,
)


def single_fact(facts: SectionFactReader, role: str) -> dict[str, Any]:
    records = facts.records(role)
    if len(records) != 1:
        raise FinalNarrativeSemanticCoverageError(
            f"{facts.section_id}:{role}: expected exactly one fact, got {len(records)}"
        )
    return records[0]


def optional_single_fact(
    facts: SectionFactReader,
    role: str,
) -> dict[str, Any] | None:
    records = facts.records(role)
    if len(records) > 1:
        raise FinalNarrativeSemanticCoverageError(
            f"{facts.section_id}:{role}: expected at most one fact, got {len(records)}"
        )
    return records[0] if records else None


def controlled_static_value(
    fact: dict[str, Any],
    *,
    section_id: str,
    role: str,
    supported: set[str],
) -> str:
    value_key = str(fact.get("valueKey") or "")
    return require_supported_value(
        section_id=section_id,
        role=role,
        value=value_key,
        supported=supported,
    )


def controlled_signal_value(
    facts: SectionFactReader,
    fact: dict[str, Any],
    *,
    role: str,
) -> str:
    value_key = str(fact.get("valueKey") or "")
    kind = ROLE_TO_KIND[role]
    if is_unknown_signal(value_key):
        facts.record_unknown_fallback(role, value_key, f"{role}-approved-unknown")
        return value_key
    require_supported_value(
        section_id=facts.section_id,
        role=role,
        value=value_key,
        supported=set(supported_signal_values(kind)),
    )
    return value_key


def meaning_frame(
    fact: dict[str, Any],
    *,
    scene_key: str,
    purpose: str,
    unknown: bool = False,
) -> ReaderMeaningFrame:
    return frame_from_fact(
        fact,
        scene_key=scene_key,
        purpose=purpose,  # type: ignore[arg-type]
        certainty="unknown" if unknown else "bounded",
    )


def render_relationship_fit(facts: SectionFactReader, seed: str) -> dict[str, str]:
    del seed
    archetype_fact = single_fact(facts, "relationship-archetype")
    primary_fact = single_fact(facts, "primary-dynamic")
    secondary_fact = optional_single_fact(facts, "secondary-dynamic")
    attraction_fact = single_fact(facts, "attraction-signal")
    friction_fact = single_fact(facts, "friction-signal")
    growth_fact = single_fact(facts, "growth-signal")

    archetype_value = controlled_static_value(
        archetype_fact,
        section_id=facts.section_id,
        role="relationship-archetype",
        supported={*RELATIONSHIP_ARCHETYPE_KEYS, "unknown"},
    )
    primary_value = controlled_static_value(
        primary_fact,
        section_id=facts.section_id,
        role="primary-dynamic",
        supported={*RELATIONSHIP_DYNAMIC_KEYS, "unknown"},
    )
    secondary_value = ""
    if secondary_fact is not None:
        secondary_value = controlled_static_value(
            secondary_fact,
            section_id=facts.section_id,
            role="secondary-dynamic",
            supported={*RELATIONSHIP_DYNAMIC_KEYS, "unknown"},
        )
        if secondary_value == primary_value and primary_value != "unknown":
            raise FinalNarrativeSemanticCoverageError(
                "relationship-fit: primary and secondary dynamics must be distinct"
            )

    for role, value in (
        ("relationship-archetype", archetype_value),
        ("primary-dynamic", primary_value),
        ("secondary-dynamic", secondary_value),
    ):
        if value == "unknown":
            facts.record_unknown_fallback(role, value, f"{role}-approved-unknown")

    attraction_value = controlled_signal_value(
        facts,
        attraction_fact,
        role="attraction-signal",
    )
    friction_value = controlled_signal_value(
        facts,
        friction_fact,
        role="friction-signal",
    )
    growth_value = controlled_signal_value(
        facts,
        growth_fact,
        role="growth-signal",
    )

    archetype_frame = meaning_frame(
        archetype_fact,
        scene_key="relationship-archetype",
        purpose="direct",
        unknown=archetype_value == "unknown",
    )
    primary_frame = meaning_frame(
        primary_fact,
        scene_key="primary-relationship-dynamic",
        purpose="direct",
        unknown=primary_value == "unknown",
    )
    secondary_frame = (
        meaning_frame(
            secondary_fact,
            scene_key="secondary-relationship-dynamic",
            purpose="situational",
            unknown=secondary_value == "unknown",
        )
        if secondary_fact is not None
        else None
    )
    attraction_frame = meaning_frame(
        attraction_fact,
        scene_key="attraction-mechanism",
        purpose="relational",
        unknown=is_unknown_signal(attraction_value),
    )
    friction_frame = meaning_frame(
        friction_fact,
        scene_key="friction-under-pressure",
        purpose="situational",
        unknown=is_unknown_signal(friction_value),
    )
    growth_frame = meaning_frame(
        growth_fact,
        scene_key="repair-potential",
        purpose="relational",
        unknown=is_unknown_signal(growth_value),
    )

    secondary_text = (
        paragraph_relationship_fit_frame(secondary_frame)
        if secondary_frame is not None
        else ""
    )
    plan_steps = [
        ("headline", archetype_frame),
        ("opening", primary_frame),
        ("elaboration", attraction_frame),
        ("contrast", friction_frame),
    ]
    if secondary_frame is not None:
        plan_steps.append(("consequence", secondary_frame))
    plan_steps.append(("condition", growth_frame))
    plan = paragraph_plan(
        section_id=facts.section_id,
        paragraph_kind="attraction-friction-cycle",
        conclusion_key=primary_value,
        steps=plan_steps,
    )
    rendered = {
        "headline": headline_for(archetype_value),
        "meaning": finish_sentence(paragraph_relationship_fit_frame(primary_frame)),
        "body": "".join(
            finish_sentence(value)
            for value in (
                paragraph_relationship_fit_frame(attraction_frame),
                paragraph_relationship_fit_frame(friction_frame),
                secondary_text,
            )
            if value
        ),
        "nextMove": finish_sentence(paragraph_relationship_fit_frame(growth_frame)),
        "caution": finish_sentence(caution_for()),
    }
    validate_relationship_fit_rendered(
        rendered,
        archetype_frame=archetype_frame,
        primary_frame=primary_frame,
        secondary_frame=secondary_frame,
        attraction_frame=attraction_frame,
        friction_frame=friction_frame,
        growth_frame=growth_frame,
    )
    validate_paragraph_output(plan, rendered)
    return rendered
