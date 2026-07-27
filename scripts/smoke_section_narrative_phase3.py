#!/usr/bin/env python3
"""Verify Phase 3 evidence-to-language depth and semantic ownership."""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composer import FINAL_NARRATIVE_COMPOSER_VERSION  # noqa: E402
from readable_interpretation.section_narrative_spec import (  # noqa: E402
    DYNAMIC_PAIR_PRIORITY,
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
)


SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
PAIR_KEY_PATTERN = re.compile(
    r"(?:Sun|Moon|Mercury|Venus|Mars|Saturn)-(?:Sun|Moon|Mercury|Venus|Mars|Saturn)|Outer-planet"
)
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def visible_section(scenario: dict[str, Any], section_id: str) -> dict[str, Any]:
    return (((scenario.get("finalInterpretation") or {}).get("sections") or {}).get(section_id) or {})


def visible_text(scenario: dict[str, Any], section_id: str) -> str:
    section = visible_section(scenario, section_id)
    return "\n".join(str(section.get(field) or "") for field in VISIBLE_FIELDS if section.get(field))


def semantic_slots(scenario: dict[str, Any], section_id: str) -> dict[str, Any]:
    return (
        (((scenario.get("sectionNarrativeSpecs") or {}).get("sections") or {}).get(section_id) or {}).get(
            "semanticSlots"
        )
        or {}
    )


def resolved_signals(value: Any) -> list[dict[str, Any]]:
    return [
        item
        for item in value or []
        if isinstance(item, dict) and not str(item.get("key") or "").endswith(":unresolved")
    ]


def assert_bundle_versions(scenario: dict[str, Any]) -> None:
    bundle = scenario.get("sectionNarrativeSpecs") or {}
    require(bundle.get("version") == SECTION_NARRATIVE_SPEC_VERSION, "section spec version mismatch")
    require(bundle.get("rendererVersion") == SECTION_NARRATIVE_RENDERER_VERSION, "renderer version mismatch")
    require((bundle.get("validation") or {}).get("status") == "valid", "section bundle is invalid")


def assert_signal_trace(scenario: dict[str, Any], section_id: str, signal: dict[str, Any]) -> None:
    spec = (((scenario.get("sectionNarrativeSpecs") or {}).get("sections") or {}).get(section_id) or {})
    owned_ids = {str(item.get("id") or "") for item in spec.get("evidence") or [] if isinstance(item, dict)}
    signal_ids = {str(item) for item in signal.get("evidenceIds") or [] if item}
    require(signal_ids and signal_ids <= owned_ids, f"{scenario.get('id')}:{section_id}: signal escaped evidence ownership")


def main() -> int:
    scenarios = [item for item in read_json(SCENARIOS_PATH) if isinstance(item, dict)]
    require(len(scenarios) >= 40, "Phase 3 scenario corpus is incomplete")
    fit_bodies_by_signature: dict[str, set[str]] = defaultdict(set)
    fit_signatures_by_body: dict[str, set[str]] = defaultdict(set)
    resolved_fit_cases = 0
    resolved_core_cases = 0
    central_pairs: set[str] = set()

    for scenario in scenarios:
        scenario_id = str(scenario.get("id") or "unknown")
        assert_bundle_versions(scenario)
        fit_slots = semantic_slots(scenario, "relationship-fit")
        core_slots = semantic_slots(scenario, "core-answer")
        fit_signature = str(fit_slots.get("fitSignature") or "")
        require(fit_signature, f"{scenario_id}: fit signature missing")
        fit_body = str(visible_section(scenario, "relationship-fit").get("body") or "")
        core_body = str(visible_section(scenario, "core-answer").get("body") or "")
        fit_bodies_by_signature[fit_signature].add(fit_body)
        fit_signatures_by_body[fit_body].add(fit_signature)

        fit_signals = [
            *resolved_signals(fit_slots.get("attractionSignals")),
            *resolved_signals(fit_slots.get("frictionSignals")),
            *resolved_signals(fit_slots.get("growthSignals")),
        ]
        if fit_signals:
            resolved_fit_cases += 1
        for signal in fit_signals:
            assert_signal_trace(scenario, "relationship-fit", signal)

        central_signal = core_slots.get("centralEvidenceSignal") if isinstance(core_slots.get("centralEvidenceSignal"), dict) else {}
        answer_signals = [item for item in core_slots.get("answerEvidenceSignals") or [] if isinstance(item, dict)]
        require(central_signal, f"{scenario_id}: central evidence signal missing")
        require(
            str(central_signal.get("key") or "") in {str(item.get("key") or "") for item in answer_signals},
            f"{scenario_id}: central signal not present in answer evidence",
        )
        assert_signal_trace(scenario, "core-answer", central_signal)
        if not str(central_signal.get("key") or "").endswith(":unresolved"):
            resolved_core_cases += 1
            pair_key = str(central_signal.get("pairKey") or "")
            central_pairs.add(pair_key)
            dynamic_key = str(core_slots.get("centralDynamicKey") or "")
            expected_pairs = DYNAMIC_PAIR_PRIORITY.get(dynamic_key) or ()
            if expected_pairs:
                require(pair_key in expected_pairs, f"{scenario_id}: {pair_key} does not explain {dynamic_key}")

        visible = "\n".join(
            visible_text(scenario, section_id)
            for section_id in ("relationship-fit", "core-answer")
        )
        require(not PAIR_KEY_PATTERN.search(visible), f"{scenario_id}: technical pair key leaked into visible copy")
        require(len(fit_body) <= 320, f"{scenario_id}: relationship-fit body is too long")
        require(len(core_body) <= 320, f"{scenario_id}: core-answer body is too long")

    collapsed = {body: signatures for body, signatures in fit_signatures_by_body.items() if len(signatures) > 1}
    require(not collapsed, f"different fit specs collapsed to identical bodies: {len(collapsed)}")
    require(resolved_fit_cases >= 35, f"resolved fit evidence coverage too low: {resolved_fit_cases}")
    require(resolved_core_cases >= 35, f"resolved core evidence coverage too low: {resolved_core_cases}")
    require(len(central_pairs) >= 8, f"central evidence pair coverage too narrow: {sorted(central_pairs)}")
    require(
        len({next(iter(bodies)) for bodies in fit_bodies_by_signature.values()}) == len(fit_bodies_by_signature),
        "fit signatures are not one-to-one with rendered bodies",
    )

    print("Section narrative Phase 3 smoke passed.")
    print(f"- composer: {FINAL_NARRATIVE_COMPOSER_VERSION}")
    print(f"- scenarios: {len(scenarios)}")
    print(f"- resolved fit/core evidence: {resolved_fit_cases}/{resolved_core_cases}")
    print(f"- central pair families: {len(central_pairs)}")
    print("- different semantic specs do not collapse to identical relationship-fit bodies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
