#!/usr/bin/env python3
"""Verify page-level discourse plans and paragraph-output invariants."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_pages import (  # noqa: E402
    action_direction_renderer,
    chart_positioning_renderer,
    core_answer_renderer,
    relationship_fit_renderer,
    timing_renderer,
)
from readable_interpretation.final_narrative_paragraph_plan import (  # noqa: E402
    FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
    PAGE_BLUEPRINTS,
    ParagraphStep,
    ReaderParagraphPlan,
    validate_paragraph_output,
)
from verify_final_narrative_r5_page_realizers import (  # noqa: E402
    ACTION_BASE,
    CORE_BASE,
    TIMING_BASE,
    render_section,
)


CHART_BASE = {
    "user-emotional-need": ["moon.sagittarius"],
    "user-communication-style": ["mercury.capricorn"],
    "partner-pressure-response": ["mars.aquarius"],
    "precision-mode": ["chart-only"],
}

FIT_BASE = {
    "relationship-archetype": ["fast-spark-conflict"],
    "primary-dynamic": ["action-conflict"],
    "secondary-dynamic": ["saturn-pressure"],
    "attraction-signal": [
        "attraction:venus-mars:persona:mars>personb:venus:conjunction:conjunction"
    ],
    "friction-signal": [
        "friction:mars-saturn:persona:mars>personb:saturn:conjunction:conjunction"
    ],
    "growth-signal": [
        "growth:sun-saturn:persona:saturn>personb:sun:sextile:soft"
    ],
}

SECTION_CASES = {
    "chart-positioning": (chart_positioning_renderer, CHART_BASE),
    "relationship-fit": (relationship_fit_renderer, FIT_BASE),
    "core-answer": (core_answer_renderer, CORE_BASE),
    "timing-reading": (timing_renderer, TIMING_BASE),
    "action-direction": (action_direction_renderer, ACTION_BASE),
}

EXPECTED_RELATIONS = {
    "chart-positioning": ("opening", "elaboration", "contrast", "boundary"),
    "relationship-fit": (
        "headline",
        "opening",
        "elaboration",
        "contrast",
        "consequence",
        "condition",
    ),
    "core-answer": (
        "headline",
        "opening",
        "evidence",
        "condition",
        "boundary",
    ),
    "timing-reading": (
        "headline",
        "opening",
        "elaboration",
        "condition",
        "action",
        "boundary",
    ),
    "action-direction": (
        "headline",
        "opening",
        "condition",
        "action",
        "boundary",
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_failure(label: str, operation: Callable[[], Any]) -> None:
    try:
        operation()
    except (AssertionError, ValueError):
        return
    raise AssertionError(f"deliberate invalid paragraph case did not fail: {label}")


def capture_page_plan(section_id: str) -> tuple[ReaderParagraphPlan, dict[str, str]]:
    module, base = SECTION_CASES[section_id]
    captured: list[ReaderParagraphPlan] = []
    original = module.paragraph_plan

    def capturing_paragraph_plan(**kwargs: Any) -> ReaderParagraphPlan:
        plan = original(**kwargs)
        captured.append(plan)
        return plan

    module.paragraph_plan = capturing_paragraph_plan
    try:
        rendered = render_section(section_id, base)
    finally:
        module.paragraph_plan = original
    require(len(captured) == 1, f"{section_id}: renderer did not create exactly one paragraph plan")
    return captured[0], rendered


def verify_runtime_plans() -> tuple[dict[str, ReaderParagraphPlan], dict[str, dict[str, str]]]:
    plans: dict[str, ReaderParagraphPlan] = {}
    rendered: dict[str, dict[str, str]] = {}
    for section_id in SECTION_CASES:
        plan, output = capture_page_plan(section_id)
        require(plan.version == FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION, section_id)
        require(plan.section_id == section_id, section_id)
        require(set(PAGE_BLUEPRINTS[section_id]).issubset(plan.roles), section_id)
        require(len(plan.source_fact_ids) == len(set(plan.source_fact_ids)), section_id)
        require(
            tuple(step.relation for step in plan.steps) == EXPECTED_RELATIONS[section_id],
            f"{section_id}: discourse order changed",
        )
        validate_paragraph_output(plan, output)
        plans[section_id] = plan
        rendered[section_id] = output
    return plans, rendered


def verify_invalid_plans(plans: dict[str, ReaderParagraphPlan]) -> int:
    chart = plans["chart-positioning"]
    core = plans["core-answer"]
    fit = plans["relationship-fit"]
    invalid: list[tuple[str, Callable[[], Any]]] = [
        (
            "stale-version",
            lambda: replace(chart, version="stale").validate(),
        ),
        (
            "invalid-conclusion-key",
            lambda: replace(chart, conclusion_key="讀者文案").validate(),
        ),
        (
            "missing-required-role",
            lambda: replace(
                core,
                supports=tuple(
                    support
                    for support in core.supports
                    if support.role != "relationship-stage"
                ),
            ).validate(),
        ),
        (
            "cross-page-frame",
            lambda: replace(
                chart,
                steps=(replace(chart.steps[0], frame=fit.steps[1].frame), *chart.steps[1:]),
            ).validate(),
        ),
        (
            "unsupported-relation",
            lambda: replace(
                chart,
                steps=(replace(chart.steps[0], relation="cause"), *chart.steps[1:]),
            ).validate(),
        ),
        (
            "duplicate-fact",
            lambda: replace(
                chart,
                steps=(*chart.steps, ParagraphStep("context", chart.steps[0].frame)),
            ).validate(),
        ),
        (
            "missing-opening",
            lambda: replace(
                chart,
                steps=(replace(chart.steps[0], relation="evidence"), *chart.steps[1:]),
            ).validate(),
        ),
    ]
    for label, operation in invalid:
        expect_failure(label, operation)
    return len(invalid)


def verify_invalid_outputs(
    plans: dict[str, ReaderParagraphPlan],
    rendered: dict[str, dict[str, str]],
) -> int:
    invalid_outputs: list[tuple[str, str, dict[str, str]]] = []

    fit = dict(rendered["relationship-fit"])
    fit["body"] = fit["body"].replace("。但", "。", 1)
    invalid_outputs.append(("fit-unmarked-friction", "relationship-fit", fit))

    timing = dict(rendered["timing-reading"])
    timing_sentences = timing["body"].split("。")
    timing["body"] = f"{timing_sentences[0]}。目前仍要保守。"
    invalid_outputs.append(("timing-disconnected-band", "timing-reading", timing))

    action = dict(rendered["action-direction"])
    action["caution"] = f"不要接著在{action['caution']}"
    invalid_outputs.append(("action-fragment-assembly", "action-direction", action))

    core = dict(rendered["core-answer"])
    core["body"] = ""
    invalid_outputs.append(("core-missing-evidence", "core-answer", core))

    chart = dict(rendered["chart-positioning"])
    chart["meaning"] = chart["meaning"].split("。")[0] + "。"
    invalid_outputs.append(("chart-missing-communication", "chart-positioning", chart))

    for label, section_id, output in invalid_outputs:
        expect_failure(
            label,
            lambda section_id=section_id, output=output: validate_paragraph_output(
                plans[section_id], output
            ),
        )
    return len(invalid_outputs)


def main() -> int:
    plans, rendered = verify_runtime_plans()
    invalid_plan_count = verify_invalid_plans(plans)
    invalid_output_count = verify_invalid_outputs(plans, rendered)
    print("Final narrative paragraph-plan verification passed")
    print(f"- page renderers using one discourse plan: {len(plans)}/5")
    print(f"- required semantic roles covered: {sum(len(plan.roles) for plan in plans.values())}")
    print(f"- deliberate invalid plans rejected: {invalid_plan_count}")
    print(f"- deliberate incoherent outputs rejected: {invalid_output_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
