#!/usr/bin/env python3
"""Verify Phase 4 case-model provenance and pair-grammar completeness."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.section_narrative_spec import (  # noqa: E402
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
)


SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
CONTEXT_FREE_SECTIONS = {"chart-positioning", "relationship-fit"}
CASE_TRACE_SECTIONS = {"core-answer", "timing-reading", "action-direction"}
TRACE_FIELDS = {
    "version",
    "caseModelVersion",
    "sectionId",
    "primaryDynamicKey",
    "secondaryDynamicKey",
    "secondaryRole",
    "grammarId",
    "grammarMode",
    "caseEvidenceIds",
}
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution", "confidenceNote")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def visible_text(final: dict[str, Any]) -> str:
    return "\n".join(
        str(section.get(field) or "")
        for section in (final.get("sections") or {}).values()
        if isinstance(section, dict)
        for field in VISIBLE_FIELDS
    )


def expected_trace(model: dict[str, Any], section_id: str) -> dict[str, Any]:
    primary = model.get("primaryDynamic") or {}
    secondaries = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    secondary = secondaries[0] if secondaries else {}
    interaction = model.get("dynamicInteractionPlan") or {}
    return {
        "version": "relationship-case-model-trace-v1",
        "caseModelVersion": model.get("version"),
        "sectionId": section_id,
        "primaryDynamicKey": interaction.get("primaryKey") or primary.get("key"),
        "secondaryDynamicKey": interaction.get("secondaryKey") or secondary.get("key"),
        "secondaryRole": interaction.get("secondaryRole") or secondary.get("role"),
        "grammarId": interaction.get("grammarId"),
        "grammarMode": interaction.get("grammarMode"),
        "caseEvidenceIds": interaction.get("evidenceIds") or [],
    }


def verify_scenario(view_model: dict[str, Any]) -> str:
    label = str(view_model.get("id") or "unknown")
    model = view_model.get("relationshipCaseModel") or {}
    interaction = model.get("dynamicInteractionPlan") or {}
    final = view_model.get("finalInterpretation") or {}
    bundle = view_model.get("sectionNarrativeSpecs") or final.get("sectionSpecs") or {}
    specs = bundle.get("sections") or {}
    sections = final.get("sections") or {}

    require(bundle.get("version") == SECTION_NARRATIVE_SPEC_VERSION, f"{label}: wrong Phase 4 spec version")
    require(
        bundle.get("rendererVersion") == SECTION_NARRATIVE_RENDERER_VERSION,
        f"{label}: wrong Phase 4 renderer version",
    )
    require((bundle.get("validation") or {}).get("status") == "valid", f"{label}: invalid section spec bundle")
    require(interaction.get("matchedGrammar") is True, f"{label}: unmatched pair grammar")
    require(interaction.get("grammarMode") in {"explicit", "composed"}, f"{label}: invalid grammar mode")
    require("fallback" not in str(interaction.get("grammarId") or ""), f"{label}: fallback grammar remains")
    require("relationshipCaseModel" not in (final.get("evidenceClusterKeys") or []), f"{label}: global case model owns evidence")

    for section_id in CONTEXT_FREE_SECTIONS:
        require(not ((specs.get(section_id) or {}).get("caseModelTrace") or {}), f"{label}:{section_id}: spec trace leak")
        require(not ((sections.get(section_id) or {}).get("caseModelTrace") or {}), f"{label}:{section_id}: final trace leak")

    for section_id in CASE_TRACE_SECTIONS:
        trace = (specs.get(section_id) or {}).get("caseModelTrace") or {}
        rendered_trace = (sections.get(section_id) or {}).get("caseModelTrace") or {}
        expected = expected_trace(model, section_id)
        require(set(trace) == TRACE_FIELDS, f"{label}:{section_id}: trace schema mismatch")
        require(trace == expected, f"{label}:{section_id}: trace does not match selected model")
        require(rendered_trace == trace, f"{label}:{section_id}: renderer changed trace")

    expected_final = expected_trace(model, "final-reading")
    require(final.get("caseModelTrace") == expected_final, f"{label}: top-level final trace mismatch")
    public_copy = visible_text(final)
    hidden_tokens = {
        str(expected_final.get("caseModelVersion") or ""),
        str(expected_final.get("primaryDynamicKey") or ""),
        str(expected_final.get("secondaryDynamicKey") or ""),
        str(expected_final.get("grammarId") or ""),
        *[str(item) for item in expected_final.get("caseEvidenceIds") or []],
    }
    leaked = sorted(token for token in hidden_tokens if token and token in public_copy)
    require(not leaked, f"{label}: hidden trace leaked into visible copy: {leaked}")
    return str(interaction.get("grammarMode") or "")


def main() -> int:
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    require(isinstance(scenarios, list) and len(scenarios) >= 45, "Phase 4 requires at least 45 generated scenarios")
    failures: list[str] = []
    modes: Counter[str] = Counter()
    for scenario in scenarios:
        try:
            modes[verify_scenario(scenario)] += 1
        except AssertionError as exc:
            failures.append(str(exc))
    if modes["explicit"] == 0:
        failures.append("no explicit pair grammar coverage")
    if modes["composed"] == 0:
        failures.append("no compositional pair grammar coverage")
    if failures:
        print("Phase 4 provenance smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Phase 4 provenance smoke passed")
    print(f"- scenarios: {len(scenarios)}")
    print(f"- explicit grammars: {modes['explicit']}")
    print(f"- composed grammars: {modes['composed']}")
    print("- fallback grammars: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
