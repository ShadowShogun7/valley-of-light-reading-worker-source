#!/usr/bin/env python3
"""Verify the Phase 2 independent page-renderer architecture."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_fact_renderer import (  # noqa: E402
    render_final_narrative_section,
)
from readable_interpretation.final_narrative_pages import PAGE_RENDERERS  # noqa: E402
from readable_interpretation.final_narrative_page_grammar import PAGE_GRAMMARS  # noqa: E402
from visible_reading_depth import build_view_models  # noqa: E402


EXPECTED_MODULES = {
    "chart-positioning": "readable_interpretation.final_narrative_pages.chart_positioning_renderer",
    "relationship-fit": "readable_interpretation.final_narrative_pages.relationship_fit_renderer",
    "core-answer": "readable_interpretation.final_narrative_pages.core_answer_renderer",
    "timing-reading": "readable_interpretation.final_narrative_pages.timing_renderer",
    "action-direction": "readable_interpretation.final_narrative_pages.action_direction_renderer",
}

EXPECTED_REQUIRED_CONTENT = {
    "chart-positioning": (
        "your emotional need",
        "your communication habit",
        "his pressure response",
    ),
    "relationship-fit": (
        "attraction mechanism",
        "friction mechanism",
        "repair potential",
    ),
    "core-answer": (
        "direct answer",
        "strongest evidence",
        "change condition",
    ),
    "timing-reading": (
        "contact permission",
        "suitable window",
        "uncertainty",
    ),
    "action-direction": (
        "action purpose",
        "one action",
        "completion boundary",
        "one stopping condition",
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(set(PAGE_RENDERERS) == set(EXPECTED_MODULES), "page renderer set mismatch")
    require(set(PAGE_GRAMMARS) == set(EXPECTED_MODULES), "page grammar set mismatch")
    for section_id, module_name in EXPECTED_MODULES.items():
        renderer = PAGE_RENDERERS[section_id]
        require(renderer.__module__ == module_name, f"{section_id}: renderer is not page-owned")
        require(
            PAGE_GRAMMARS[section_id].required_content == EXPECTED_REQUIRED_CONTENT[section_id],
            f"{section_id}: page content grammar drifted",
        )

    facade_path = ROOT / "scripts" / "readable_interpretation" / "final_narrative_fact_renderer.py"
    facade_source = facade_path.read_text(encoding="utf-8")
    for obsolete in (
        "def render_chart(",
        "def render_relationship_fit(",
        "def render_core(",
        "def render_timing(",
        "def render_action(",
    ):
        require(obsolete not in facade_source, f"obsolete monolithic renderer remains: {obsolete}")

    signature = inspect.signature(render_final_narrative_section)
    require(
        set(signature.parameters) == {"section_id", "facts", "seed"},
        "final renderer still accepts routing side channels",
    )

    composer_path = ROOT / "scripts" / "readable_interpretation" / "final_narrative_composer.py"
    composer_source = composer_path.read_text(encoding="utf-8")
    require(
        len(composer_source.splitlines()) <= 250,
        "FinalNarrativeComposer is no longer orchestration-only",
    )
    for obsolete_method in (
        "def chart_positioning(",
        "def relationship_fit(",
        "def core_answer(",
        "def timing_reading(",
        "def action_direction(",
    ):
        require(
            obsolete_method not in composer_source,
            f"legacy page implementation remains in composer: {obsolete_method}",
        )

    view_models = build_view_models()
    rendered_count = 0
    for view_model in view_models:
        bundle = view_model.get("sectionNarrativeSpecs") or {}
        from readable_interpretation.final_narrative_composer import (  # noqa: PLC0415
            FinalNarrativeComposer,
            FinalNarrativeSemanticInput,
        )

        context = ((bundle.get("sections") or {}).get("core-answer") or {}).get("context") or {}
        composer = FinalNarrativeComposer.from_semantic_input(
            FinalNarrativeSemanticInput(
                question_key=str(context.get("questionKey") or ""),
                stage_key=str(context.get("stageKey") or ""),
                contact_key=str(context.get("contactKey") or ""),
                section_specs=bundle,
                fact_contract=bundle.get("finalNarrativeFacts"),
            )
        )
        for section_id in EXPECTED_MODULES:
            composer.render_section(section_id)
            rendered_count += 1

    print("Final narrative Phase 2 page-module verification passed")
    print(f"- independent page modules: {len(PAGE_RENDERERS)}")
    print(f"- composer lines: {len(composer_source.splitlines())}")
    print(f"- representative sections rendered: {rendered_count}")
    print("- routing side channels accepted by final renderer: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
