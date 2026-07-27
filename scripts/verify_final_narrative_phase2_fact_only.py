#!/usr/bin/env python3
"""Verify that final visible copy is controlled only by typed facts."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FinalNarrativeComposer,
    FinalNarrativeSemanticInput,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    FINAL_NARRATIVE_FACT_RENDERER_MODE,
    refresh_final_narrative_fact_contract,
)
from visible_reading_depth import build_view_models  # noqa: E402


SECTION_IDS = (
    "chart-positioning",
    "relationship-fit",
    "core-answer",
    "timing-reading",
    "action-direction",
)
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def composer_for(view_model: dict[str, Any], bundle: dict[str, Any]) -> FinalNarrativeComposer:
    context = ((bundle.get("sections") or {}).get("core-answer") or {}).get("context") or {}
    return FinalNarrativeComposer.from_semantic_input(
        FinalNarrativeSemanticInput(
            question_key=str(context.get("questionKey") or ""),
            stage_key=str(context.get("stageKey") or ""),
            contact_key=str(context.get("contactKey") or ""),
            section_specs=bundle,
            fact_contract=bundle.get("finalNarrativeFacts"),
        )
    )


def rendered(composer: FinalNarrativeComposer) -> dict[str, tuple[str, ...]]:
    output: dict[str, tuple[str, ...]] = {}
    for section_id in SECTION_IDS:
        draft = composer.render_section(section_id)
        output[section_id] = (
            draft.headline,
            draft.meaning,
            draft.body,
            draft.next_move,
            draft.caution,
        )
    return output


def mutate_legacy_prose(bundle: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(bundle)
    sections = mutated.get("sections") or {}
    chart_slots = (sections.get("chart-positioning") or {}).get("semanticSlots") or {}
    for key in ("personAEmotionalNeed", "personACommunicationStyle", "personBPressureResponse"):
        chart_slots[key] = f"LEGACY-PROSE-MUTATED:{key}"

    fit_slots = (sections.get("relationship-fit") or {}).get("semanticSlots") or {}
    fit_slots["archetypeTitle"] = "LEGACY-PROSE-MUTATED:archetype"
    for key in ("attractionSignals", "frictionSignals", "growthSignals"):
        for item in fit_slots.get(key) or []:
            if not isinstance(item, dict):
                continue
            for prose_key in ("everydaySignal", "meaning", "advice"):
                item[prose_key] = f"LEGACY-PROSE-MUTATED:{key}:{prose_key}"

    core_slots = (sections.get("core-answer") or {}).get("semanticSlots") or {}
    for item in core_slots.get("observableSigns") or []:
        if isinstance(item, dict):
            item["behavior"] = "LEGACY-PROSE-MUTATED:observable"
    for key in ("centralEvidenceSignal", "answerEvidenceSignals"):
        values = core_slots.get(key)
        records = values if isinstance(values, list) else [values]
        for item in records:
            if not isinstance(item, dict):
                continue
            for prose_key in ("everydaySignal", "meaning", "advice"):
                item[prose_key] = f"LEGACY-PROSE-MUTATED:{key}:{prose_key}"

    contract = mutated.get("finalNarrativeFacts") or {}
    refresh_final_narrative_fact_contract(contract, sections)
    return mutated


def main() -> int:
    view_models = build_view_models()
    require(len(view_models) >= 11, "Phase 2 needs representative readings")
    checked_sections = 0
    for view_model in view_models:
        label = str(view_model.get("id") or "unknown")
        bundle = view_model.get("sectionNarrativeSpecs") or {}
        contract = bundle.get("finalNarrativeFacts") or {}
        require(contract.get("rendererMode") == FINAL_NARRATIVE_FACT_RENDERER_MODE == "fact-only", f"{label}: renderer is not fact-only")
        require((contract.get("validation") or {}).get("status") == "valid", f"{label}: invalid fact contract")
        for section_id in SECTION_IDS:
            diagnostics = (((contract.get("sections") or {}).get(section_id) or {}).get("diagnostics") or {})
            require(not diagnostics.get("compatibilityProseSlots"), f"{label}:{section_id}: compatibility prose remains")

        baseline = rendered(composer_for(view_model, bundle))
        mutated_bundle = mutate_legacy_prose(bundle)
        mutated = rendered(composer_for(view_model, mutated_bundle))
        require(mutated == baseline, f"{label}: legacy prose changed visible output")
        checked_sections += len(SECTION_IDS)

    zh_tw_source = (ROOT / "scripts" / "readable_interpretation" / "zh_tw.py").read_text(encoding="utf-8")
    for legacy_call in (
        "final_composer.chart_positioning(",
        "final_composer.relationship_fit(",
        "final_composer.core_answer(",
        "final_composer.timing_reading(",
        "final_composer.action_direction(",
    ):
        require(legacy_call not in zh_tw_source, f"runtime still calls legacy renderer: {legacy_call}")

    print("Final narrative Phase 2 fact-only verification passed")
    print(f"- representative readings: {len(view_models)}")
    print(f"- fact-only sections checked: {checked_sections}")
    print("- legacy prose mutations cannot change visible copy")
    print("- compatibility prose slots: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
