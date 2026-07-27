#!/usr/bin/env python3
"""Verify the production native-Chinese chart-positioning renderer."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_chinese_plan import frame_from_fact  # noqa: E402
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    validate_section_composition,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    ValidatedFinalNarrativeFactContract,
    fact_id,
)
from readable_interpretation.final_narrative_pages.chart_positioning_renderer import (  # noqa: E402
    render_chart_positioning,
)
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import (  # noqa: E402
    CHART_POSITIONING_EXPECTED_APPROVED_FORM_COUNT,
    CHART_POSITIONING_FORBIDDEN_REGRESSIONS,
    MERCURY_NATIVE_FORMS,
    MOON_NATIVE_FORMS,
    PRECISION_CAUTIONS,
    PRESSURE_NATIVE_FORMS,
    ROLE_CATALOGS,
    catalog_errors,
    validate_chart_positioning_rendered,
)
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    SectionFactReader,
)
from readable_interpretation.final_narrative_semantic_domains import ZODIAC_SIGNS  # noqa: E402
from readable_interpretation.section_narrative_spec import planet_role_fact_key  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def binding_fingerprint(identity: str) -> str:
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def synthetic_fact(
    role: str,
    value_key: str,
    *,
    fact_id_override: str = "",
    fingerprint_override: str | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    identity = f"chart-positioning:{role}:{value_key}"
    return {
        "id": fact_id_override or fact_id("chart-positioning", role, value_key),
        "sectionId": "chart-positioning",
        "role": role,
        "valueKey": value_key,
        "sourceSlot": role,
        "sourceBindingFingerprint": (
            binding_fingerprint(identity)
            if fingerprint_override is None
            else fingerprint_override
        ),
        "evidenceIds": (
            [f"synthetic:{identity}"] if evidence_ids is None else evidence_ids
        ),
        "qualifiers": [],
    }


def synthetic_contract(
    moon_value: str,
    mercury_value: str,
    pressure_value: str,
    precision_value: str,
    *,
    replacements: dict[str, dict[str, Any]] | None = None,
    duplicate_role: str = "",
) -> ValidatedFinalNarrativeFactContract:
    facts = {
        "user-emotional-need": synthetic_fact("user-emotional-need", moon_value),
        "user-communication-style": synthetic_fact(
            "user-communication-style", mercury_value
        ),
        "partner-pressure-response": synthetic_fact(
            "partner-pressure-response", pressure_value
        ),
        "precision-mode": synthetic_fact("precision-mode", precision_value),
    }
    for role, replacement in (replacements or {}).items():
        facts[role] = replacement
    records = list(facts.values())
    if duplicate_role:
        records.append(dict(facts[duplicate_role]))
    return ValidatedFinalNarrativeFactContract(
        contract={"synthetic": True},
        sections={"chart-positioning": {"facts": records}},
    )


def render_case(
    moon_value: str,
    mercury_value: str,
    pressure_value: str,
    precision_value: str,
    *,
    seed: str = "r2-production-verifier",
    replacements: dict[str, dict[str, Any]] | None = None,
    duplicate_role: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    reader = SectionFactReader(
        contract=synthetic_contract(
            moon_value,
            mercury_value,
            pressure_value,
            precision_value,
            replacements=replacements,
            duplicate_role=duplicate_role,
        ),
        section_id="chart-positioning",
    )
    rendered = render_chart_positioning(reader, seed)
    reader.assert_complete()
    validate_section_composition("chart-positioning", rendered)
    return rendered, reader.fallback_diagnostics()


def changed_fields(left: dict[str, str], right: dict[str, str]) -> set[str]:
    return {field for field in left if left[field] != right[field]}


def expect_failure(label: str, operation: Callable[[], Any]) -> None:
    try:
        operation()
    except (ValueError, AssertionError):
        return
    raise AssertionError(f"deliberate invalid case did not fail: {label}")


def verify_exhaustive_matrix() -> dict[str, int]:
    signs = (*ZODIAC_SIGNS, "unknown")
    moon_values = tuple(f"moon.{sign}" for sign in signs)
    mercury_values = tuple(f"mercury.{sign}" for sign in signs)
    pressure_values = tuple(f"mars.{sign}" for sign in signs)
    precision_values = tuple(PRECISION_CAUTIONS)
    output_fingerprints: set[str] = set()
    known_case_count = 0
    unknown_case_count = 0

    for moon_value in moon_values:
        for mercury_value in mercury_values:
            for pressure_value in pressure_values:
                for precision_value in precision_values:
                    rendered, diagnostics = render_case(
                        moon_value,
                        mercury_value,
                        pressure_value,
                        precision_value,
                    )
                    fingerprint = hashlib.sha256(
                        json.dumps(
                            rendered,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                    output_fingerprints.add(fingerprint)
                    expected_unknowns = sum(
                        (
                            moon_value.endswith(".unknown"),
                            mercury_value.endswith(".unknown"),
                            pressure_value.endswith(".unknown"),
                            precision_value == "unknown",
                        )
                    )
                    require(
                        diagnostics["knownFallbackCount"] == 0,
                        "known chart input used a fallback",
                    )
                    require(
                        diagnostics["unknownFallbackCount"] == expected_unknowns,
                        "chart unknown diagnostics do not match unknown inputs",
                    )
                    if expected_unknowns:
                        unknown_case_count += 1
                    else:
                        known_case_count += 1

    total_case_count = (
        len(moon_values)
        * len(mercury_values)
        * len(pressure_values)
        * len(precision_values)
    )
    require(
        len(output_fingerprints) == total_case_count,
        "different chart fact combinations collapsed into identical readings",
    )
    return {
        "matrixCaseCount": total_case_count,
        "knownCaseCount": known_case_count,
        "unknownCaseCount": unknown_case_count,
        "uniqueOutputCount": len(output_fingerprints),
    }


def verify_field_ownership() -> None:
    baseline, baseline_diagnostics = render_case(
        "moon.aries",
        "mercury.aries",
        "mars.aries",
        "chart-only",
    )
    require(
        baseline_diagnostics["knownFallbackCount"] == 0
        and baseline_diagnostics["unknownFallbackCount"] == 0,
        "baseline chart render used a fallback",
    )
    moon_changed, _ = render_case(
        "moon.taurus", "mercury.aries", "mars.aries", "chart-only"
    )
    mercury_changed, _ = render_case(
        "moon.aries", "mercury.taurus", "mars.aries", "chart-only"
    )
    pressure_changed, _ = render_case(
        "moon.aries", "mercury.aries", "mars.taurus", "chart-only"
    )
    precision_changed, _ = render_case(
        "moon.aries", "mercury.aries", "mars.aries", "partial"
    )
    seed_changed, _ = render_case(
        "moon.aries",
        "mercury.aries",
        "mars.aries",
        "chart-only",
        seed="a-different-seed-must-not-select-copy",
    )
    require(
        changed_fields(baseline, moon_changed) == {"headline", "meaning"},
        "Moon fact crossed its chart field ownership",
    )
    require(
        changed_fields(baseline, mercury_changed) == {"meaning"},
        "Mercury fact crossed its chart field ownership",
    )
    require(
        changed_fields(baseline, pressure_changed)
        == {"headline", "body", "nextMove"},
        "pressure fact crossed its chart field ownership",
    )
    require(
        changed_fields(baseline, precision_changed) == {"caution"},
        "precision fact crossed its chart field ownership",
    )
    require(seed_changed == baseline, "seed still changes chart wording")


def verify_deliberate_invalid_cases() -> int:
    invalid_cases: list[tuple[str, Callable[[], Any]]] = [
        (
            "unsupported-known-value",
            lambda: render_case(
                "moon.ophiuchus", "mercury.aries", "mars.aries", "chart-only"
            ),
        ),
        (
            "stale-source-binding-fingerprint",
            lambda: render_case(
                "moon.aries",
                "mercury.aries",
                "mars.aries",
                "chart-only",
                replacements={
                    "user-emotional-need": synthetic_fact(
                        "user-emotional-need",
                        "moon.aries",
                        fingerprint_override="stale",
                    )
                },
            ),
        ),
        (
            "wrong-source-fact-id",
            lambda: render_case(
                "moon.aries",
                "mercury.aries",
                "mars.aries",
                "chart-only",
                replacements={
                    "user-emotional-need": synthetic_fact(
                        "user-emotional-need",
                        "moon.aries",
                        fact_id_override="chart-positioning.user-emotional-need.moon.taurus",
                    )
                },
            ),
        ),
        (
            "missing-evidence",
            lambda: render_case(
                "moon.aries",
                "mercury.aries",
                "mars.aries",
                "chart-only",
                replacements={
                    "user-emotional-need": synthetic_fact(
                        "user-emotional-need", "moon.aries", evidence_ids=[]
                    )
                },
            ),
        ),
        (
            "duplicate-owned-fact",
            lambda: render_case(
                "moon.aries",
                "mercury.aries",
                "mars.aries",
                "chart-only",
                duplicate_role="user-emotional-need",
            ),
        ),
    ]
    for label, operation in invalid_cases:
        expect_failure(label, operation)

    contract = synthetic_contract(
        "moon.aries", "mercury.aries", "mars.aries", "chart-only"
    )
    facts = {
        role: contract.facts("chart-positioning", role)[0]
        for role in (
            "user-emotional-need",
            "user-communication-style",
            "partner-pressure-response",
            "precision-mode",
        )
    }
    frames = {
        "moon_frame": frame_from_fact(
            facts["user-emotional-need"],
            scene_key="emotional-need",
            purpose="direct",
        ),
        "mercury_frame": frame_from_fact(
            facts["user-communication-style"],
            scene_key="communication-under-disagreement",
            purpose="situational",
        ),
        "pressure_frame": frame_from_fact(
            facts["partner-pressure-response"],
            scene_key="partner-response-under-pressure",
            purpose="situational",
        ),
        "precision_frame": frame_from_fact(
            facts["precision-mode"],
            scene_key="chart-data-boundary",
            purpose="direct",
        ),
    }
    valid_rendered, _ = render_case(
        "moon.aries", "mercury.aries", "mars.aries", "chart-only"
    )
    for index, regression in enumerate(CHART_POSITIONING_FORBIDDEN_REGRESSIONS):
        broken = dict(valid_rendered)
        broken["headline" if index == 0 else "meaning"] = regression
        expect_failure(
            f"reader-regression-{index + 1}",
            lambda broken=broken: validate_chart_positioning_rendered(
                broken,
                **frames,
            ),
        )
    return len(invalid_cases) + len(CHART_POSITIONING_FORBIDDEN_REGRESSIONS)


def main() -> int:
    errors = catalog_errors()
    require(not errors, "; ".join(errors))
    approved_form_count = sum(
        3 for catalog in ROLE_CATALOGS.values() for _entry in catalog.values()
    )
    require(
        approved_form_count == CHART_POSITIONING_EXPECTED_APPROVED_FORM_COUNT,
        "approved chart realization count is stale",
    )
    require(len(MOON_NATIVE_FORMS) == 13, "Moon catalog coverage is stale")
    require(len(MERCURY_NATIVE_FORMS) == 13, "Mercury catalog coverage is stale")
    require(len(PRESSURE_NATIVE_FORMS) == 13, "pressure catalog coverage is stale")
    require(
        planet_role_fact_key("unknown", "moon") == "moon.unknown"
        and planet_role_fact_key("", "mercury") == "mercury.unknown"
        and planet_role_fact_key(None, "mars") == "mars.unknown"
        and planet_role_fact_key("moon.aries", "moon") == "moon.aries",
        "chart fact creation does not enforce role-scoped unknown values",
    )
    verify_field_ownership()
    invalid_case_count = verify_deliberate_invalid_cases()
    matrix = verify_exhaustive_matrix()

    print("Final narrative R2 native chart-positioning verification passed")
    print(f"- approved full-sentence forms: {approved_form_count}")
    print(f"- exhaustive fact combinations: {matrix['matrixCaseCount']}")
    print(f"- unique finished readings: {matrix['uniqueOutputCount']}")
    print(f"- known-input combinations: {matrix['knownCaseCount']}")
    print(f"- explicit-unknown combinations: {matrix['unknownCaseCount']}")
    print("- field ownership mutations: 4/4")
    print(f"- deliberate invalid cases rejected: {invalid_case_count}")
    print("- known-input fallback rate: 0.0%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
