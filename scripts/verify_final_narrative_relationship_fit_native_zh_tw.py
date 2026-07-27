#!/usr/bin/env python3
"""Verify the production native-Chinese relationship-fit renderer."""

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
from readable_interpretation.final_narrative_pages.relationship_fit_renderer import (  # noqa: E402
    render_relationship_fit,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    ARCHETYPE_HEADLINES,
    FIT_PARAGRAPH_THESES,
    RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS,
    ROLE_TO_KIND,
    catalog_errors,
    paragraph_relationship_fit_value,
    relationship_fit_sentence_trace,
    supported_signal_values,
    validate_relationship_fit_rendered,
)
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    SectionFactReader,
)
from readable_interpretation.final_narrative_semantic_domains import (  # noqa: E402
    RELATIONSHIP_ARCHETYPE_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
)


BASE_VALUES = {
    "relationship-archetype": "communication-repair",
    "primary-dynamic": "communication-repair",
    "secondary-dynamic": "emotional-safety",
    "attraction-signal": (
        "attraction:sun-moon:persona:sun>personb:moon:trine:soft"
    ),
    "friction-signal": (
        "friction:mercury-mars:persona:mercury>personb:mars:square:hard"
    ),
    "growth-signal": (
        "growth:moon-saturn:persona:moon>personb:saturn:trine:soft"
    ),
}


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
    identity = f"relationship-fit:{role}:{value_key}"
    return {
        "id": fact_id_override or fact_id("relationship-fit", role, value_key),
        "sectionId": "relationship-fit",
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
    values: dict[str, str] | None = None,
    *,
    replacements: dict[str, dict[str, Any]] | None = None,
    omit_roles: set[str] | None = None,
    duplicate_role: str = "",
    include_secondary: bool = True,
) -> ValidatedFinalNarrativeFactContract:
    selected = {**BASE_VALUES, **(values or {})}
    facts = {
        role: synthetic_fact(role, value)
        for role, value in selected.items()
        if (include_secondary or role != "secondary-dynamic")
        and role not in (omit_roles or set())
    }
    for role, replacement in (replacements or {}).items():
        facts[role] = replacement
    records = list(facts.values())
    if duplicate_role:
        records.append(dict(facts[duplicate_role]))
    return ValidatedFinalNarrativeFactContract(
        contract={"synthetic": True},
        sections={"relationship-fit": {"facts": records}},
    )


def render_case(
    values: dict[str, str] | None = None,
    *,
    seed: str = "r3-production-verifier",
    replacements: dict[str, dict[str, Any]] | None = None,
    omit_roles: set[str] | None = None,
    duplicate_role: str = "",
    include_secondary: bool = True,
) -> tuple[dict[str, str], dict[str, Any]]:
    reader = SectionFactReader(
        contract=synthetic_contract(
            values,
            replacements=replacements,
            omit_roles=omit_roles,
            duplicate_role=duplicate_role,
            include_secondary=include_secondary,
        ),
        section_id="relationship-fit",
    )
    rendered = render_relationship_fit(reader, seed)
    reader.assert_complete()
    validate_section_composition("relationship-fit", rendered)
    return rendered, reader.fallback_diagnostics()


def changed_fields(left: dict[str, str], right: dict[str, str]) -> set[str]:
    return {field for field in left if left[field] != right[field]}


def expect_failure(label: str, operation: Callable[[], Any]) -> None:
    try:
        operation()
    except (ValueError, AssertionError):
        return
    raise AssertionError(f"deliberate invalid case did not fail: {label}")


def verify_static_domains() -> int:
    rendered_count = 0
    for value_key in (*RELATIONSHIP_ARCHETYPE_KEYS, "unknown"):
        rendered, diagnostics = render_case({"relationship-archetype": value_key})
        require(rendered["headline"] == ARCHETYPE_HEADLINES[value_key], value_key)
        require(
            diagnostics["unknownFallbackCount"] == (1 if value_key == "unknown" else 0),
            f"archetype unknown diagnostics mismatch: {value_key}",
        )
        rendered_count += 1
    for role in ("primary-dynamic", "secondary-dynamic"):
        for value_key in (*RELATIONSHIP_DYNAMIC_KEYS, "unknown"):
            values = {role: value_key}
            if role == "secondary-dynamic" and value_key == BASE_VALUES["primary-dynamic"]:
                values["primary-dynamic"] = "emotional-safety"
            if role == "primary-dynamic" and value_key == BASE_VALUES["secondary-dynamic"]:
                values["secondary-dynamic"] = "saturn-pressure"
            rendered, diagnostics = render_case(values)
            field = "meaning" if role == "primary-dynamic" else "body"
            purpose = "direct" if role == "primary-dynamic" else "situational"
            expected = (
                FIT_PARAGRAPH_THESES[value_key]
                if role == "primary-dynamic"
                else paragraph_relationship_fit_value(role, value_key)
            )
            require(
                expected in rendered[field],
                f"{role} is not visible: {value_key}",
            )
            require(
                diagnostics["knownFallbackCount"] == 0,
                f"known dynamic used fallback: {role}:{value_key}",
            )
            rendered_count += 1
    return rendered_count


def verify_signal_domains() -> dict[str, int]:
    counts: dict[str, int] = {}
    for role, kind in ROLE_TO_KIND.items():
        values = supported_signal_values(kind)
        seen_sentences: set[str] = set()
        target_field = "nextMove" if role == "growth-signal" else "body"
        purpose = "relational" if role != "friction-signal" else "situational"
        for value_key in values:
            rendered, diagnostics = render_case({role: value_key})
            sentence = paragraph_relationship_fit_value(role, value_key)
            require(
                sentence in rendered[target_field],
                f"signal is not visible in its owned field: {value_key}",
            )
            require(
                diagnostics["knownFallbackCount"] == 0
                and diagnostics["unknownFallbackCount"] == 0,
                f"known signal used fallback: {value_key}",
            )
            trace = relationship_fit_sentence_trace(sentence)
            require(
                trace
                == {
                    "kind": "paragraph-realization",
                    "role": role,
                    "valueKey": value_key,
                    "purpose": purpose,
                },
                f"signal trace is stale: {value_key}",
            )
            require(
                sentence not in seen_sentences,
                f"different {role} values collapsed into one sentence: {value_key}",
            )
            seen_sentences.add(sentence)
        counts[role] = len(values)
    return counts


def verify_unknowns_and_optional_secondary() -> None:
    unknown_values = {
        "relationship-archetype": "unknown",
        "primary-dynamic": "unknown",
        "secondary-dynamic": "unknown",
        "attraction-signal": "attraction:attractiondynamics:unresolved",
        "friction-signal": "friction:frictiondynamics:unresolved",
        "growth-signal": "growth:growthdynamics:unresolved",
    }
    rendered, diagnostics = render_case(unknown_values)
    require(
        diagnostics["knownFallbackCount"] == 0
        and diagnostics["unknownFallbackCount"] == 6,
        "relationship-fit unknown diagnostics are incomplete",
    )
    disclosure_markers = ("不足", "看不出", "無法確認")
    require(
        any(marker in rendered["body"] for marker in disclosure_markers)
        and any(marker in rendered["nextMove"] for marker in disclosure_markers),
        "unknown copy is not disclosed",
    )
    without_secondary, without_diagnostics = render_case(include_secondary=False)
    require(
        len([item for item in without_secondary["body"].split("。") if item]) == 2,
        "optional secondary dynamic did not leave a two-sentence body",
    )
    require(
        without_diagnostics["knownFallbackCount"] == 0
        and without_diagnostics["unknownFallbackCount"] == 0,
        "omitted optional secondary used a fallback",
    )


def verify_field_ownership() -> None:
    baseline, _ = render_case()
    mutations = {
        "relationship-archetype": (
            {"relationship-archetype": "natural-attraction"},
            {"headline"},
        ),
        "primary-dynamic": (
            {"primary-dynamic": "saturn-pressure"},
            {"meaning"},
        ),
        "secondary-dynamic": (
            {"secondary-dynamic": "action-conflict"},
            {"body"},
        ),
        "attraction-signal": (
            {
                "attraction-signal": (
                    "attraction:venus-mars:persona:venus>personb:mars:sextile:soft"
                )
            },
            {"body"},
        ),
        "friction-signal": (
            {
                "friction-signal": (
                    "friction:moon-saturn:persona:moon>personb:saturn:opposition:hard"
                )
            },
            {"body"},
        ),
        "growth-signal": (
            {
                "growth-signal": (
                    "growth:venus-saturn:persona:venus>personb:saturn:sextile:soft"
                )
            },
            {"nextMove"},
        ),
    }
    for role, (values, expected_fields) in mutations.items():
        changed, _ = render_case(values)
        require(
            changed_fields(baseline, changed) == expected_fields,
            f"{role} crossed relationship-fit field ownership",
        )
    seed_changed, _ = render_case(seed="a-different-seed-must-not-select-copy")
    require(seed_changed == baseline, "seed still changes relationship-fit wording")


def verify_deliberate_invalid_cases() -> int:
    invalid_cases: list[tuple[str, Callable[[], Any]]] = [
        (
            "unsupported-archetype",
            lambda: render_case({"relationship-archetype": "generic-soulmate"}),
        ),
        (
            "unsupported-signal-pair",
            lambda: render_case(
                {
                    "attraction-signal": (
                        "attraction:mercury-mars:persona:mercury>personb:mars:trine:soft"
                    )
                }
            ),
        ),
        (
            "non-canonical-polarity",
            lambda: render_case(
                {
                    "friction-signal": (
                        "friction:mercury-mars:persona:mercury>personb:mars:square:soft"
                    )
                }
            ),
        ),
        (
            "mismatched-pair-direction",
            lambda: render_case(
                {
                    "attraction-signal": (
                        "attraction:sun-moon:persona:venus>personb:moon:trine:soft"
                    )
                }
            ),
        ),
        (
            "stale-source-binding-fingerprint",
            lambda: render_case(
                replacements={
                    "primary-dynamic": synthetic_fact(
                        "primary-dynamic",
                        BASE_VALUES["primary-dynamic"],
                        fingerprint_override="stale",
                    )
                }
            ),
        ),
        (
            "wrong-source-fact-id",
            lambda: render_case(
                replacements={
                    "primary-dynamic": synthetic_fact(
                        "primary-dynamic",
                        BASE_VALUES["primary-dynamic"],
                        fact_id_override=(
                            "relationship-fit.primary-dynamic.emotional-safety"
                        ),
                    )
                }
            ),
        ),
        (
            "missing-evidence",
            lambda: render_case(
                replacements={
                    "primary-dynamic": synthetic_fact(
                        "primary-dynamic",
                        BASE_VALUES["primary-dynamic"],
                        evidence_ids=[],
                    )
                }
            ),
        ),
        (
            "duplicate-owned-fact",
            lambda: render_case(duplicate_role="attraction-signal"),
        ),
        (
            "duplicate-primary-secondary-meaning",
            lambda: render_case({"secondary-dynamic": "communication-repair"}),
        ),
        (
            "missing-required-growth-signal",
            lambda: render_case(omit_roles={"growth-signal"}),
        ),
    ]
    for label, operation in invalid_cases:
        expect_failure(label, operation)

    contract = synthetic_contract()
    facts = {
        role: contract.facts("relationship-fit", role)[0]
        for role in BASE_VALUES
    }
    frames = {
        "archetype_frame": frame_from_fact(
            facts["relationship-archetype"],
            scene_key="relationship-archetype",
            purpose="direct",
        ),
        "primary_frame": frame_from_fact(
            facts["primary-dynamic"],
            scene_key="primary-relationship-dynamic",
            purpose="direct",
        ),
        "secondary_frame": frame_from_fact(
            facts["secondary-dynamic"],
            scene_key="secondary-relationship-dynamic",
            purpose="situational",
        ),
        "attraction_frame": frame_from_fact(
            facts["attraction-signal"],
            scene_key="attraction-mechanism",
            purpose="relational",
        ),
        "friction_frame": frame_from_fact(
            facts["friction-signal"],
            scene_key="friction-under-pressure",
            purpose="situational",
        ),
        "growth_frame": frame_from_fact(
            facts["growth-signal"],
            scene_key="repair-potential",
            purpose="relational",
        ),
    }
    valid_rendered, _ = render_case()
    for index, regression in enumerate(RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS):
        broken = dict(valid_rendered)
        broken["body"] = f"{regression}。{valid_rendered['body']}"
        expect_failure(
            f"reader-regression-{index + 1}",
            lambda broken=broken: validate_relationship_fit_rendered(
                broken,
                **frames,
            ),
        )
    return len(invalid_cases) + len(RELATIONSHIP_FIT_FORBIDDEN_REGRESSIONS)


def main() -> int:
    errors = catalog_errors()
    require(not errors, "; ".join(errors))
    static_render_count = verify_static_domains()
    signal_counts = verify_signal_domains()
    verify_unknowns_and_optional_secondary()
    verify_field_ownership()
    invalid_case_count = verify_deliberate_invalid_cases()

    baseline, _ = render_case()
    fingerprint = hashlib.sha256(
        json.dumps(
            baseline,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    print("Final narrative R3 native relationship-fit verification passed")
    print(f"- static domain renders: {static_render_count}")
    print(f"- attraction signals: {signal_counts['attraction-signal']}")
    print(f"- friction signals: {signal_counts['friction-signal']}")
    print(f"- growth signals: {signal_counts['growth-signal']}")
    print(f"- total concrete signal values: {sum(signal_counts.values())}")
    print("- signal output collapse: 0")
    print("- field ownership mutations: 6/6")
    print(f"- deliberate invalid cases rejected: {invalid_case_count}")
    print("- known-input fallback rate: 0.0%")
    print(f"- baseline output fingerprint: {fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
