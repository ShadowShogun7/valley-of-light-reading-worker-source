#!/usr/bin/env python3
"""Verify controlled, deterministic reader-language realization."""

from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FinalNarrativeComposer,
    FinalNarrativeSemanticInput,
    SectionNarrativeSpecError,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    ValidatedFinalNarrativeFactContract,
)
from readable_interpretation.final_narrative_fact_renderer import (  # noqa: E402
    ARCHETYPE_FORMS,
    DYNAMIC_FORMS,
    MERCURY_STYLE_FORMS,
    MOON_NEED_FORMS,
    OBSERVABLE_FORMS,
    PARTNER_MOON_NEED_FORMS,
    PRESSURE_RESPONSE_FORMS,
    directional_signal_forms,
    render_final_narrative_section,
)
from readable_interpretation.final_narrative_page_grammar import sentence_count  # noqa: E402
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    ACTION_MODE_FORMS,
    OBSERVABLE_RESPONSE_VARIANTS,
    STOP_VARIANTS,
    action_rationale_variants,
)
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import (  # noqa: E402
    MERCURY_NATIVE_FORMS,
    MOON_NATIVE_FORMS,
    PRESSURE_ACTIONS,
    PRESSURE_NATIVE_FORMS,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    CORE_DIRECT_ANSWER_CATALOG,
    CORE_QUESTION_FOCUS_TERMS,
    UNCERTAINTY_COPY,
    core_dynamic_variants,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    ARCHETYPE_HEADLINES,
    PRIMARY_DYNAMIC_FORMS,
    SECONDARY_DYNAMIC_FORMS,
    signal_forms as fit_signal_forms,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (  # noqa: E402
    CONTACT_STATUS_COPY,
    PRECISE_DATE_COPY,
    TIMING_ACTION_VARIANTS,
    TIMING_ACTION_FORMS,
    TIMING_BAND_COPY,
    TIMING_BAND_FORMS,
)
from readable_interpretation.final_narrative_realization import REALIZATION_PURPOSES  # noqa: E402
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
)
from readable_interpretation.final_narrative_semantic_domains import (  # noqa: E402
    ATTRACTION_PAIR_KEYS,
    CONTACT_STATUS_KEYS,
    FRICTION_PAIR_KEYS,
    GROWTH_PAIR_KEYS,
    QUESTION_KEYS,
    RELATIONSHIP_ARCHETYPE_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
    RELATIONSHIP_STAGE_KEYS,
    ZODIAC_SIGNS,
    parse_relationship_signal,
)
from visible_reading_depth import build_view_models  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def semantic_input(bundle: dict) -> FinalNarrativeSemanticInput:
    context = ((bundle.get("sections") or {}).get("core-answer") or {}).get("context") or {}
    return FinalNarrativeSemanticInput(
        question_key=str(context.get("questionKey") or ""),
        stage_key=str(context.get("stageKey") or ""),
        contact_key=str(context.get("contactKey") or ""),
        section_specs=bundle,
        fact_contract=bundle.get("finalNarrativeFacts"),
    )


def visible(composer: FinalNarrativeComposer) -> tuple[str, ...]:
    output: list[str] = []
    for section_id in (
        "chart-positioning",
        "relationship-fit",
        "core-answer",
        "timing-reading",
        "action-direction",
    ):
        draft = composer.render_section(section_id)
        output.extend((draft.headline, draft.meaning, draft.body, draft.next_move, draft.caution))
    return tuple(output)


def validate_form_catalog(identity: str, catalog: dict, expected_values: set[str]) -> int:
    require(set(catalog) == expected_values, f"{identity}: semantic value domain mismatch")
    checked = 0
    for value_key, forms in catalog.items():
        forms.validate(f"{identity}:{value_key}")
        for purpose in REALIZATION_PURPOSES:
            copy_value = forms.for_purpose(purpose)
            require(
                sentence_count(copy_value) == 1,
                f"{identity}:{value_key}:{purpose}: form contains more than one sentence",
            )
            checked += 1
    return checked


def validate_variant_catalog(
    identity: str,
    catalog: dict[str, tuple[str, ...]],
    expected_values: set[str],
    *,
    minimum: int,
) -> int:
    require(set(catalog) == expected_values, f"{identity}: semantic value domain mismatch")
    checked = 0
    for value_key, variants in catalog.items():
        require(len(variants) >= minimum, f"{identity}:{value_key}: too few controlled variants")
        normalized = {"".join(value.split()).rstrip("。！？") for value in variants}
        require(
            len(normalized) == len(variants),
            f"{identity}:{value_key}: controlled variants are not distinct",
        )
        for index, copy_value in enumerate(variants):
            require(
                sentence_count(copy_value) == 1,
                f"{identity}:{value_key}:{index}: variant contains more than one sentence",
            )
            checked += 1
    return checked


def signal_value(kind: str, pair_key: str, actor: str) -> str:
    receiver = "personb" if actor == "persona" else "persona"
    if pair_key == "outer-planet-intensity":
        actor_planet, receiver_planet = "pluto", "neptune"
    else:
        actor_planet, receiver_planet = pair_key.split("-", 1)
    aspect, polarity = ("square", "hard") if kind == "friction" else ("trine", "soft")
    return (
        f"{kind}:{pair_key}:{actor}:{actor_planet}>"
        f"{receiver}:{receiver_planet}:{aspect}:{polarity}"
    )


def main() -> int:
    form_count = 0
    sign_domain = {*ZODIAC_SIGNS, "unknown"}
    form_count += validate_form_catalog("moon needs", MOON_NEED_FORMS, sign_domain)
    form_count += validate_form_catalog("mercury styles", MERCURY_STYLE_FORMS, sign_domain)
    form_count += validate_form_catalog("pressure responses", PRESSURE_RESPONSE_FORMS, sign_domain)
    form_count += validate_form_catalog("partner moon needs", PARTNER_MOON_NEED_FORMS, sign_domain)
    form_count += validate_form_catalog(
        "native chart Moon needs",
        {key: entry.forms for key, entry in MOON_NATIVE_FORMS.items()},
        {f"moon.{sign}" for sign in sign_domain},
    )
    form_count += validate_form_catalog(
        "native chart Mercury styles",
        {key: entry.forms for key, entry in MERCURY_NATIVE_FORMS.items()},
        {f"mercury.{sign}" for sign in sign_domain},
    )
    form_count += validate_form_catalog(
        "native chart pressure responses",
        {key: entry.forms for key, entry in PRESSURE_NATIVE_FORMS.items()},
        {f"mars.{sign}" for sign in sign_domain},
    )
    form_count += validate_form_catalog(
        "relationship archetypes",
        ARCHETYPE_FORMS,
        {*RELATIONSHIP_ARCHETYPE_KEYS, "unknown"},
    )
    form_count += validate_form_catalog(
        "relationship dynamics",
        DYNAMIC_FORMS,
        {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"},
    )
    form_count += validate_form_catalog("observable signs", OBSERVABLE_FORMS, set(OBSERVABLE_FORMS))
    form_count += validate_form_catalog("timing actions", TIMING_ACTION_FORMS, set(TIMING_ACTION_FORMS))
    form_count += validate_form_catalog("timing bands", TIMING_BAND_FORMS, set(TIMING_BAND_FORMS))
    form_count += validate_form_catalog("action modes", ACTION_MODE_FORMS, set(ACTION_MODE_FORMS))
    direct_answer_domain = {
        (stage, question, contact)
        for stage in RELATIONSHIP_STAGE_KEYS
        for question in QUESTION_KEYS
        for contact in CONTACT_STATUS_KEYS
    }
    require(
        set(CORE_DIRECT_ANSWER_CATALOG) == direct_answer_domain,
        "core direct answers: semantic value domain mismatch",
    )
    focus_domain = {
        (stage, question)
        for stage in RELATIONSHIP_STAGE_KEYS
        for question in QUESTION_KEYS
    }
    require(
        set(CORE_QUESTION_FOCUS_TERMS) == focus_domain,
        "core direct answer focus: semantic value domain mismatch",
    )
    require(
        len(set(CORE_DIRECT_ANSWER_CATALOG.values())) == len(CORE_DIRECT_ANSWER_CATALOG),
        "core direct answers collapse across status-question-contact contexts",
    )
    for identity, copy_value in CORE_DIRECT_ANSWER_CATALOG.items():
        stage, question, _contact = identity
        require(
            sentence_count(copy_value) == 1,
            f"core direct answer contains more than one sentence: {identity}",
        )
        require(
            "；" not in copy_value,
            f"core direct answer concatenates independent clauses: {identity}",
        )
        require(
            any(term in copy_value for term in CORE_QUESTION_FOCUS_TERMS[(stage, question)]),
            f"core direct answer lost status-question focus: {identity}",
        )
        form_count += 1

    dynamic_domain = {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"}
    archetype_domain = {*RELATIONSHIP_ARCHETYPE_KEYS, "unknown"}
    expanded_catalogs = (
        (
            "chart pressure actions",
            {key: (value,) for key, value in PRESSURE_ACTIONS.items()},
            {f"mars.{sign}" for sign in sign_domain},
            1,
        ),
        (
            "fit dynamic variants",
            {
                key: tuple(
                    entry.forms.for_purpose(purpose)
                    for entry in (
                        PRIMARY_DYNAMIC_FORMS[key],
                        SECONDARY_DYNAMIC_FORMS[key],
                    )
                    for purpose in REALIZATION_PURPOSES
                )
                for key in dynamic_domain
            },
            dynamic_domain,
            6,
        ),
        (
            "fit archetype headlines",
            {key: (ARCHETYPE_HEADLINES[key],) for key in archetype_domain},
            archetype_domain,
            1,
        ),
        (
            "core dynamic variants",
            {key: core_dynamic_variants(key) for key in dynamic_domain},
            dynamic_domain,
            5,
        ),
        ("core uncertainty variants", UNCERTAINTY_COPY, set(UNCERTAINTY_COPY), 10),
        ("timing contact variants", CONTACT_STATUS_COPY, set(CONTACT_STATUS_COPY), 5),
        ("timing action variants", TIMING_ACTION_VARIANTS, set(TIMING_ACTION_VARIANTS), 5),
        ("timing band variants", TIMING_BAND_COPY, set(TIMING_BAND_COPY), 5),
        ("timing precision variants", PRECISE_DATE_COPY, set(PRECISE_DATE_COPY), 15),
        (
            "action rationale variants",
            {key: action_rationale_variants(key) for key in dynamic_domain},
            dynamic_domain,
            3,
        ),
        ("action observable variants", OBSERVABLE_RESPONSE_VARIANTS, set(OBSERVABLE_RESPONSE_VARIANTS), 3),
        ("action stop variants", STOP_VARIANTS, set(STOP_VARIANTS), 4),
    )
    for identity, catalog, expected, minimum in expanded_catalogs:
        form_count += validate_variant_catalog(
            identity,
            catalog,
            expected,
            minimum=minimum,
        )

    directional_signal_count = 0
    for kind, pair_keys in (
        ("attraction", ATTRACTION_PAIR_KEYS),
        ("friction", FRICTION_PAIR_KEYS),
        ("growth", GROWTH_PAIR_KEYS),
    ):
        for pair_key in pair_keys:
            a_to_b = directional_signal_forms(
                parse_relationship_signal(signal_value(kind, pair_key, "persona"))
            )
            b_to_a = directional_signal_forms(
                parse_relationship_signal(signal_value(kind, pair_key, "personb"))
            )
            a_to_b.validate(f"{kind}:{pair_key}:persona>personb")
            b_to_a.validate(f"{kind}:{pair_key}:personb>persona")
            for purpose in REALIZATION_PURPOSES:
                require(
                    a_to_b.for_purpose(purpose) != b_to_a.for_purpose(purpose),
                    f"{kind}:{pair_key}:{purpose}: A/B direction collapsed",
                )
                directional_signal_count += 2

    for pair_key in GROWTH_PAIR_KEYS:
        a_to_b_forms = fit_signal_forms(
            signal_value("growth", pair_key, "persona"),
            expected_kind="growth",
        )
        b_to_a_forms = fit_signal_forms(
            signal_value("growth", pair_key, "personb"),
            expected_kind="growth",
        )
        for index, purpose in enumerate(REALIZATION_PURPOSES):
            left = a_to_b_forms.for_purpose(purpose)
            right = b_to_a_forms.for_purpose(purpose)
            require(sentence_count(left) == 1, f"growth:{pair_key}:{index}: A repair has multiple sentences")
            require(sentence_count(right) == 1, f"growth:{pair_key}:{index}: B repair has multiple sentences")
            require(left != right, f"growth:{pair_key}:{index}: repair direction collapsed")
            directional_signal_count += 2

    view_models = build_view_models()
    require(view_models, "representative view models are missing")
    deterministic_sections = 0
    for view_model in view_models:
        bundle = view_model.get("sectionNarrativeSpecs") or {}
        composer = FinalNarrativeComposer.from_semantic_input(semantic_input(bundle))
        require(visible(composer) == visible(composer), "same facts produced nondeterministic copy")
        final_sections = (view_model.get("finalInterpretation") or {}).get("sections") or {}
        for section_id in (
            "chart-positioning",
            "relationship-fit",
            "core-answer",
            "timing-reading",
            "action-direction",
        ):
            draft = composer.render_section(section_id)
            rendered = final_sections.get(section_id) or {}
            require(
                (
                    draft.headline,
                    draft.meaning,
                    draft.body,
                    draft.next_move,
                    draft.caution,
                )
                == (
                    rendered.get("headline"),
                    rendered.get("meaning"),
                    rendered.get("body"),
                    rendered.get("nextMove"),
                    rendered.get("caution"),
                ),
                f"{section_id}: downstream sanitizer changed controlled reader copy",
            )
        deterministic_sections += 5

    bundle = copy.deepcopy(view_models[0].get("sectionNarrativeSpecs") or {})
    fact = bundle["finalNarrativeFacts"]["sections"]["core-answer"]["facts"][0]
    fact["valueKey"] = "unsupported-question"
    try:
        FinalNarrativeComposer.from_semantic_input(semantic_input(bundle))
    except SectionNarrativeSpecError as exc:
        require("source binding fingerprint is stale" in str(exc), "fact mutation failed for the wrong reason")
    else:
        raise AssertionError("mutated fact value bypassed source binding")

    valid_bundle = view_models[0].get("sectionNarrativeSpecs") or {}
    source_contract = valid_bundle.get("finalNarrativeFacts") or {}
    loose_sections = copy.deepcopy(source_contract.get("sections") or {})
    moon_fact = next(
        item
        for item in loose_sections["chart-positioning"]["facts"]
        if item.get("role") == "user-emotional-need"
    )
    moon_fact["valueKey"] = "moon.unsupported"
    loose_contract = ValidatedFinalNarrativeFactContract(contract={}, sections=loose_sections)
    try:
        render_final_narrative_section(
            section_id="chart-positioning",
            facts=loose_contract,
            seed="unsupported-value-test",
        )
    except FinalNarrativeSemanticCoverageError:
        pass
    else:
        raise AssertionError("unsupported semantic value reached reader copy")

    realization_paths = [
        ROOT / "scripts" / "readable_interpretation" / "final_narrative_fact_renderer.py",
        ROOT
        / "scripts"
        / "readable_interpretation"
        / "final_narrative_pages"
        / "chart_positioning_zh_tw_catalog.py",
        *(ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages").glob(
            "*_renderer.py"
        ),
    ]
    for path in realization_paths:
        source = path.read_text(encoding="utf-8")
        require("import random" not in source, f"random realization in {path.name}")
        require("import hashlib" not in source, f"hash realization in {path.name}")
        require("stable_pick" not in source, f"hash-selected copy remains in {path.name}")
        require("qualify_statement" not in source, f"independent clause assembly remains in {path.name}")

    contract = FinalNarrativeComposer.from_semantic_input(
        semantic_input(view_models[0].get("sectionNarrativeSpecs") or {})
    ).facts
    reader = SectionFactReader(contract=contract, section_id="chart-positioning")
    reader.first("user-emotional-need", required=True)
    try:
        reader.first("user-emotional-need", required=True)
    except FinalNarrativeSemanticCoverageError:
        pass
    else:
        raise AssertionError("same semantic role could be consumed twice")

    print("Final narrative Phase 3 realization verification passed")
    print(f"- deterministic sections checked: {deterministic_sections}")
    print(f"- controlled realization forms checked: {form_count}")
    print(f"- directional signal forms checked: {directional_signal_count}")
    print("- repeated semantic fact consumption rejected")
    print("- source-bound fact mutation rejected")
    print("- unsupported realization value rejected")
    print("- downstream visible-copy rewrites: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
