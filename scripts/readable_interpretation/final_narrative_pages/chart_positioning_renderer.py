"""Reader-language realization for the chart-positioning page."""

from __future__ import annotations

from typing import Any

from ..final_narrative_chinese_plan import frame_from_fact
from ..final_narrative_paragraph_plan import paragraph_plan, validate_paragraph_output
from ..final_narrative_semantic_coverage import (
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    require_supported_value,
)
from ..final_narrative_semantic_domains import ZODIAC_SIGNS
from .chart_positioning_zh_tw_catalog import (
    PRECISION_CAUTIONS,
    action_for,
    caution_for,
    finish_sentence,
    headline_for,
    paragraph_chart_frame,
    validate_chart_positioning_rendered,
)


ROLE_PREFIXES = {
    "user-emotional-need": "moon",
    "user-communication-style": "mercury",
    "partner-pressure-response": "mars",
}


def single_fact(facts: SectionFactReader, role: str) -> dict[str, Any]:
    records = facts.records(role)
    if len(records) != 1:
        raise FinalNarrativeSemanticCoverageError(
            f"{facts.section_id}:{role}: expected exactly one fact, got {len(records)}"
        )
    return records[0]


def controlled_planet_value(value_key: str, *, section_id: str, role: str) -> str:
    prefix = ROLE_PREFIXES[role]
    supported = {f"{prefix}.{sign}" for sign in (*ZODIAC_SIGNS, "unknown")}
    require_supported_value(
        section_id=section_id,
        role=role,
        value=value_key,
        supported=supported,
    )
    return value_key


def render_chart_positioning(facts: SectionFactReader, seed: str) -> dict[str, str]:
    del seed
    moon_fact = single_fact(facts, "user-emotional-need")
    mercury_fact = single_fact(facts, "user-communication-style")
    pressure_fact = single_fact(facts, "partner-pressure-response")
    precision_fact = single_fact(facts, "precision-mode")

    moon_value = controlled_planet_value(
        str(moon_fact.get("valueKey") or ""),
        section_id=facts.section_id,
        role="user-emotional-need",
    )
    mercury_value = controlled_planet_value(
        str(mercury_fact.get("valueKey") or ""),
        section_id=facts.section_id,
        role="user-communication-style",
    )
    pressure_value = controlled_planet_value(
        str(pressure_fact.get("valueKey") or ""),
        section_id=facts.section_id,
        role="partner-pressure-response",
    )
    for role, value in (
        ("user-emotional-need", moon_value),
        ("user-communication-style", mercury_value),
        ("partner-pressure-response", pressure_value),
    ):
        if value.endswith(".unknown"):
            facts.record_unknown_fallback(role, value, f"{role}-approved-unknown")
    precision_value = str(precision_fact.get("valueKey") or "")
    require_supported_value(
        section_id=facts.section_id,
        role="precision-mode",
        value=precision_value,
        supported=set(PRECISION_CAUTIONS),
    )
    if precision_value == "unknown":
        facts.record_unknown_fallback(
            "precision-mode",
            precision_value,
            "precision-mode-approved-unknown",
        )

    moon_frame = frame_from_fact(
        moon_fact,
        scene_key="emotional-need",
        purpose="direct",
        certainty="bounded",
    )
    mercury_frame = frame_from_fact(
        mercury_fact,
        scene_key="communication-under-disagreement",
        purpose="situational",
        certainty="bounded",
    )
    pressure_frame = frame_from_fact(
        pressure_fact,
        scene_key="partner-response-under-pressure",
        purpose="situational",
        certainty="bounded",
    )
    precision_frame = frame_from_fact(
        precision_fact,
        scene_key="chart-data-boundary",
        purpose="direct",
        certainty="bounded" if precision_value != "unknown" else "unknown",
    )

    plan = paragraph_plan(
        section_id=facts.section_id,
        paragraph_kind="individual-style-contrast",
        conclusion_key=f"{moon_value}-{pressure_value}",
        steps=(
            ("opening", moon_frame),
            ("elaboration", mercury_frame),
            ("contrast", pressure_frame),
            ("boundary", precision_frame),
        ),
    )

    rendered = {
        "headline": headline_for(moon_value, pressure_value),
        "meaning": finish_sentence(paragraph_chart_frame(moon_frame))
        + finish_sentence(paragraph_chart_frame(mercury_frame)),
        "body": finish_sentence(paragraph_chart_frame(pressure_frame)),
        "nextMove": finish_sentence(action_for(pressure_value)),
        "caution": finish_sentence(caution_for(precision_value)),
    }
    validate_chart_positioning_rendered(
        rendered,
        moon_frame=moon_frame,
        mercury_frame=mercury_frame,
        pressure_frame=pressure_frame,
        precision_frame=precision_frame,
    )
    validate_paragraph_output(plan, rendered)
    return rendered
