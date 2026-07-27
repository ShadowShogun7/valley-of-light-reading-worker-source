"""Independent page renderers for the five paid result sections."""

from __future__ import annotations

from typing import Callable

from ..final_narrative_semantic_coverage import SectionFactReader
from .action_direction_renderer import render_action_direction
from .chart_positioning_renderer import render_chart_positioning
from .core_answer_renderer import render_core_answer
from .relationship_fit_renderer import render_relationship_fit
from .timing_renderer import render_timing_reading


PageRenderer = Callable[[SectionFactReader, str], dict[str, str]]


PAGE_RENDERERS: dict[str, PageRenderer] = {
    "chart-positioning": render_chart_positioning,
    "relationship-fit": render_relationship_fit,
    "core-answer": render_core_answer,
    "timing-reading": render_timing_reading,
    "action-direction": render_action_direction,
}


__all__ = ["PAGE_RENDERERS", "PageRenderer"]
