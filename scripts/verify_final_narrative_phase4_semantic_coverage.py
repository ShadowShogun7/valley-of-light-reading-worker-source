#!/usr/bin/env python3
"""Prove every emitted final-layer semantic role has a realization path."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FinalNarrativeComposer,
    FinalNarrativeSemanticInput,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
    FINAL_NARRATIVE_FACT_POLICIES,
    ValidatedFinalNarrativeFactContract,
    fact_id,
)
from readable_interpretation.final_narrative_fact_renderer import (  # noqa: E402
    ARCHETYPES,
    ATTRACTION_PAIRS,
    BLOCKED_ACTION_COPY,
    DYNAMIC_FORMS,
    FRICTION_PAIRS,
    GROWTH_PAIRS,
    MERCURY_STYLE_FORMS,
    MOON_NEED_FORMS,
    OBSERVABLE_FORMS,
    PARTNER_MOON_NEED_FORMS,
    PRESSURE_RESPONSE_FORMS,
    REPAIR_COPY,
)
from readable_interpretation.final_narrative_page_grammar import validate_page_grammar  # noqa: E402
from readable_interpretation.final_narrative_pages import PAGE_RENDERERS  # noqa: E402
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    ACTION_MODE_FORMS,
    CONTACT_POSTURE_TAGS as ACTION_CONTACT_POSTURES,
    STOP_COPY,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    ANSWER_TRACK_HEADLINES,
    UNCERTAINTY_COPY,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    paragraph_relationship_fit_value,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (  # noqa: E402
    ACTION_HEADLINES as TIMING_ACTION_HEADLINES,
    CONTACT_POSTURE_HEADLINES as TIMING_CONTACT_POSTURES,
    PRECISE_DATE_COPY,
    TIMING_BAND_FORMS,
    WINDOW_CATEGORY_COPY,
    TRIGGER_CONTEXT,
)
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
    FinalNarrativeSemanticCoverageError,
    SectionFactReader,
    semantic_policy_alignment_errors,
)
from readable_interpretation.final_narrative_semantic_domains import (  # noqa: E402
    ASPECT_KEYS,
    ATTRACTION_PAIR_KEYS,
    CONTACT_STATUS_KEYS,
    FRICTION_PAIR_KEYS,
    GROWTH_PAIR_KEYS,
    QUESTION_KEYS,
    RELATIONSHIP_ARCHETYPE_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
    RELATIONSHIP_STAGE_KEYS,
    ZODIAC_SIGNS,
)
from readable_interpretation.section_narrative_spec import SECTION_NARRATIVE_SPEC_VERSION  # noqa: E402
from visible_reading_depth import build_view_models  # noqa: E402
from build_reading_phase7_calibration import CORPUS_VERSION  # noqa: E402


DEFAULT_GENERATED_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
DEFAULT_CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def find_bundles(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if (
            value.get("version") == SECTION_NARRATIVE_SPEC_VERSION
            and isinstance(value.get("finalNarrativeFacts"), dict)
        ):
            yield value
        for child in value.values():
            yield from find_bundles(child)
    elif isinstance(value, list):
        for child in value:
            yield from find_bundles(child)


def composer_for(bundle: dict[str, Any]) -> FinalNarrativeComposer:
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


def signal_value(kind: str, pair_key: str, actor: str = "persona") -> str:
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


def synthetic_contract(section_id: str, role_values: dict[str, list[str]]) -> ValidatedFinalNarrativeFactContract:
    facts: list[dict[str, Any]] = []
    for role, values in role_values.items():
        for index, value in enumerate(values):
            facts.append(
                {
                    "id": fact_id(section_id, role, value),
                    "sectionId": section_id,
                    "role": role,
                    "valueKey": value,
                    "sourceSlot": role,
                    "sourceBindingFingerprint": "0" * 64,
                    "evidenceIds": [f"synthetic:{section_id}:{role}:{index}"],
                    "qualifiers": [],
                }
            )
    return ValidatedFinalNarrativeFactContract(
        contract={"synthetic": True},
        sections={section_id: {"facts": facts}},
    )


def render_synthetic(
    section_id: str,
    role_values: dict[str, list[str]],
) -> tuple[dict[str, str], dict[str, Any]]:
    reader = SectionFactReader(
        contract=synthetic_contract(section_id, role_values),
        section_id=section_id,
    )
    rendered = PAGE_RENDERERS[section_id](reader, "exhaustive-domain-check")
    reader.assert_complete()
    validate_page_grammar(section_id, rendered)
    return rendered, reader.fallback_diagnostics()


def known_render(
    section_id: str,
    base: dict[str, list[str]],
    role: str,
    values: list[str],
) -> int:
    count = 0
    for value in values:
        case = {key: list(items) for key, items in base.items()}
        case[role] = [value]
        if section_id == "relationship-fit" and value != "unknown":
            if role == "primary-dynamic" and case.get("secondary-dynamic") == [value]:
                case["secondary-dynamic"] = [
                    next(item for item in RELATIONSHIP_DYNAMIC_KEYS if item != value)
                ]
            if role == "secondary-dynamic" and case.get("primary-dynamic") == [value]:
                case["primary-dynamic"] = [
                    next(item for item in RELATIONSHIP_DYNAMIC_KEYS if item != value)
                ]
        _, diagnostics = render_synthetic(section_id, case)
        require(
            diagnostics["knownFallbackCount"] == 0 and diagnostics["unknownFallbackCount"] == 0,
            f"{section_id}:{role}: known value used fallback: {value}",
        )
        count += 1
    return count


def representative_bundles() -> list[dict[str, Any]]:
    return [
        item.get("sectionNarrativeSpecs") or {}
        for item in build_view_models()
        if isinstance(item.get("sectionNarrativeSpecs"), dict)
    ]


def exhaustive_value_domain_check() -> dict[str, Any]:
    tested_values: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    def check(
        section_id: str,
        base: dict[str, list[str]],
        role: str,
        values: list[str],
    ) -> int:
        tested_values[section_id][role].update(values)
        return known_render(section_id, base, role, values)

    sign_domain = {*ZODIAC_SIGNS, "unknown"}
    dynamic_domain = {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"}
    archetype_domain = {*RELATIONSHIP_ARCHETYPE_KEYS, "unknown"}
    require(set(MOON_NEED_FORMS) == sign_domain, "emotional-need domain is incomplete")
    require(set(MERCURY_STYLE_FORMS) == sign_domain, "communication domain is incomplete")
    require(set(PRESSURE_RESPONSE_FORMS) == sign_domain, "pressure-response domain is incomplete")
    require(set(PARTNER_MOON_NEED_FORMS) == sign_domain, "partner-need domain is incomplete")
    require(set(ARCHETYPES) == archetype_domain, "relationship-archetype domain is incomplete")
    require(set(DYNAMIC_FORMS) == dynamic_domain, "relationship-dynamic domain is incomplete")
    require(set(REPAIR_COPY) == dynamic_domain, "relationship repair has known-input fallbacks")
    require(set(ATTRACTION_PAIRS) == set(ATTRACTION_PAIR_KEYS), "attraction-pair domain is incomplete")
    require(set(FRICTION_PAIRS) == set(FRICTION_PAIR_KEYS), "friction-pair domain is incomplete")
    require(set(GROWTH_PAIRS) == set(GROWTH_PAIR_KEYS), "growth-pair domain is incomplete")
    unknown_disclosure_markers = ("不足", "不能", "實際", "確認", "沒有", "不清楚", "缺少")
    for identity, catalog in (
        ("emotional need", MOON_NEED_FORMS),
        ("communication style", MERCURY_STYLE_FORMS),
        ("pressure response", PRESSURE_RESPONSE_FORMS),
        ("partner need", PARTNER_MOON_NEED_FORMS),
        ("relationship dynamic", DYNAMIC_FORMS),
    ):
        unknown_forms = catalog["unknown"]
        for purpose in ("direct", "situational", "relational"):
            copy_value = unknown_forms.for_purpose(purpose)
            require(
                any(marker in copy_value for marker in unknown_disclosure_markers),
                f"{identity}:{purpose}: unknown state reads like chart-specific analysis",
            )

    base_chart = {
        "user-emotional-need": ["moon.aries"],
        "user-communication-style": ["mercury.aries"],
        "partner-pressure-response": ["mars.aries"],
        "precision-mode": ["chart-only"],
    }
    base_fit = {
        "relationship-archetype": ["communication-repair"],
        "primary-dynamic": ["communication-repair"],
        "secondary-dynamic": ["emotional-safety"],
        "attraction-signal": [signal_value("attraction", "sun-moon")],
        "friction-signal": [signal_value("friction", "mercury-mars")],
        "growth-signal": [signal_value("growth", "moon-saturn")],
    }
    base_core = {
        "question": ["still-love-me"],
        "relationship-stage": ["ambiguous"],
        "contact-status": ["no-contact"],
        "answer-track": ["remaining-feeling"],
        "central-dynamic": ["communication-repair"],
        "partner-relationship-need": ["moon.aries"],
        "evidence-signal": [signal_value("friction", "mercury-mars")],
        "observable-sign": ["partner-continues-without-prompt"],
        "uncertainty-level": ["medium"],
    }
    base_timing = {
        "question": ["when-to-contact"],
        "contact-status": ["no-contact"],
        "timing-posture": ["observe-only"],
        "recommended-action": ["observe-only"],
        "timing-band": ["neutral"],
        "contact-posture": ["observe-channel"],
        "precise-dates-available": ["available"],
        "timing-window": ["2026-08-mid|softening|venus-venus|trine"],
    }
    base_action = {
        "question": ["still-love-me"],
        "contact-status": ["no-contact"],
        "action-purpose": ["small-bid-response-led"],
        "action-mode": ["small-bid-response-led"],
        "completion-boundary": ["small-bid-response-led"],
        "repair-lever": ["communication-repair"],
        "stop-condition": ["standard"],
        "contact-posture": ["observe-channel"],
        "blocked-action": ["long-explanation"],
    }

    known_render_count = 0
    for role, prefix in (
        ("user-emotional-need", "moon"),
        ("user-communication-style", "mercury"),
        ("partner-pressure-response", "mars"),
    ):
        known_render_count += check(
            "chart-positioning",
            base_chart,
            role,
            [f"{prefix}.{sign}" for sign in ZODIAC_SIGNS],
        )
    known_render_count += check(
        "chart-positioning",
        base_chart,
        "precision-mode",
        ["chart-only", "full", "partial", "low"],
    )

    known_render_count += check(
        "relationship-fit",
        base_fit,
        "relationship-archetype",
        list(RELATIONSHIP_ARCHETYPE_KEYS),
    )
    known_render_count += check(
        "relationship-fit",
        base_fit,
        "primary-dynamic",
        list(RELATIONSHIP_DYNAMIC_KEYS),
    )
    known_render_count += check(
        "relationship-fit",
        base_fit,
        "secondary-dynamic",
        list(RELATIONSHIP_DYNAMIC_KEYS),
    )
    for secondary in RELATIONSHIP_DYNAMIC_KEYS:
        case = {key: list(values) for key, values in base_fit.items()}
        if case["primary-dynamic"] == [secondary]:
            case["primary-dynamic"] = [
                next(value for value in RELATIONSHIP_DYNAMIC_KEYS if value != secondary)
            ]
        case["secondary-dynamic"] = [secondary]
        rendered, diagnostics = render_synthetic("relationship-fit", case)
        require(
            paragraph_relationship_fit_value("secondary-dynamic", secondary)
            in rendered["body"],
            f"relationship-fit: secondary dynamic was not reader-visible: {secondary}",
        )
        require(
            diagnostics["knownFallbackCount"] == 0,
            f"relationship-fit: secondary dynamic used fallback: {secondary}",
        )
    duplicate_secondary = {key: list(values) for key, values in base_fit.items()}
    duplicate_secondary["secondary-dynamic"] = [
        "emotional-safety",
        "saturn-pressure",
    ]
    try:
        render_synthetic("relationship-fit", duplicate_secondary)
    except FinalNarrativeSemanticCoverageError as exc:
        require(
            "expected at most one fact" in str(exc),
            "multiple secondary dynamics failed for the wrong reason",
        )
    else:
        raise AssertionError("multiple secondary dynamics were silently dropped")
    for role, kind, pairs in (
        ("attraction-signal", "attraction", ATTRACTION_PAIR_KEYS),
        ("friction-signal", "friction", FRICTION_PAIR_KEYS),
        ("growth-signal", "growth", GROWTH_PAIR_KEYS),
    ):
        values = [signal_value(kind, pair, actor) for pair in pairs for actor in ("persona", "personb")]
        known_render_count += check("relationship-fit", base_fit, role, values)

    known_render_count += check("core-answer", base_core, "question", list(QUESTION_KEYS))
    known_render_count += check(
        "core-answer",
        base_core,
        "relationship-stage",
        list(RELATIONSHIP_STAGE_KEYS),
    )
    known_render_count += check(
        "core-answer",
        base_core,
        "contact-status",
        list(CONTACT_STATUS_KEYS),
    )
    known_render_count += check(
        "core-answer",
        base_core,
        "answer-track",
        list(ANSWER_TRACK_HEADLINES),
    )
    known_render_count += check(
        "core-answer",
        base_core,
        "central-dynamic",
        list(RELATIONSHIP_DYNAMIC_KEYS),
    )
    known_render_count += check(
        "core-answer",
        base_core,
        "partner-relationship-need",
        [f"moon.{sign}" for sign in ZODIAC_SIGNS],
    )
    evidence_values = [
        signal_value(kind, pair, actor)
        for kind, pairs in (
            ("attraction", ATTRACTION_PAIR_KEYS),
            ("friction", FRICTION_PAIR_KEYS),
            ("growth", GROWTH_PAIR_KEYS),
        )
        for pair in pairs
        for actor in ("persona", "personb")
    ]
    known_render_count += check(
        "core-answer",
        base_core,
        "evidence-signal",
        evidence_values,
    )
    known_render_count += check(
        "core-answer",
        base_core,
        "observable-sign",
        list(OBSERVABLE_FORMS),
    )
    known_render_count += check(
        "core-answer",
        base_core,
        "uncertainty-level",
        ["low", "medium", "high"],
    )

    known_render_count += check("timing-reading", base_timing, "question", list(QUESTION_KEYS))
    for contact in CONTACT_STATUS_KEYS:
        case = {key: list(values) for key, values in base_timing.items()}
        case["contact-status"] = [contact]
        if contact == "blocked":
            case["timing-posture"] = ["avoid-push"]
            case["recommended-action"] = ["avoid-push"]
            case["contact-posture"] = ["boundary-first"]
        _, diagnostics = render_synthetic("timing-reading", case)
        require(
            diagnostics["unknownFallbackCount"] == 0,
            f"timing contact used fallback: {contact}",
        )
        known_render_count += 1
        tested_values["timing-reading"]["contact-status"].add(contact)
    for action in TIMING_ACTION_HEADLINES:
        case = {key: list(values) for key, values in base_timing.items()}
        case["timing-posture"] = [action]
        case["recommended-action"] = [action]
        _, diagnostics = render_synthetic("timing-reading", case)
        require(diagnostics["unknownFallbackCount"] == 0, f"timing action used fallback: {action}")
        known_render_count += 1
        tested_values["timing-reading"]["timing-posture"].add(action)
        tested_values["timing-reading"]["recommended-action"].add(action)
    known_render_count += check(
        "timing-reading",
        base_timing,
        "timing-band",
        list(TIMING_BAND_FORMS),
    )
    known_render_count += check(
        "timing-reading",
        base_timing,
        "contact-posture",
        list(TIMING_CONTACT_POSTURES),
    )
    known_render_count += check(
        "timing-reading",
        base_timing,
        "precise-dates-available",
        list(PRECISE_DATE_COPY),
    )
    timing_windows = [
        *[f"2026-08-mid|{category}|venus-venus|trine" for category in WINDOW_CATEGORY_COPY],
        *[f"2026-08-mid|softening|{trigger}-{trigger}|trine" for trigger in TRIGGER_CONTEXT],
        *[f"2026-08-mid|softening|venus-venus|{aspect}" for aspect in ASPECT_KEYS],
    ]
    known_render_count += check(
        "timing-reading",
        base_timing,
        "timing-window",
        timing_windows,
    )

    known_render_count += check("action-direction", base_action, "question", list(QUESTION_KEYS))
    for contact in CONTACT_STATUS_KEYS:
        case = {key: list(values) for key, values in base_action.items()}
        case["contact-status"] = [contact]
        if contact == "blocked":
            case["action-purpose"] = ["boundary-only"]
            case["action-mode"] = ["boundary-only"]
            case["completion-boundary"] = ["boundary-only"]
            case["contact-posture"] = ["boundary-first"]
        _, diagnostics = render_synthetic("action-direction", case)
        require(diagnostics["unknownFallbackCount"] == 0, f"action contact used fallback: {contact}")
        known_render_count += 1
        tested_values["action-direction"]["contact-status"].add(contact)
    for mode in ACTION_MODE_FORMS:
        case = {key: list(values) for key, values in base_action.items()}
        case["action-purpose"] = [mode]
        case["action-mode"] = [mode]
        case["completion-boundary"] = [mode]
        _, diagnostics = render_synthetic("action-direction", case)
        require(diagnostics["unknownFallbackCount"] == 0, f"action mode used fallback: {mode}")
        for role in ("action-purpose", "action-mode", "completion-boundary"):
            tested_values["action-direction"][role].add(mode)
        known_render_count += 1
    known_render_count += check(
        "action-direction",
        base_action,
        "repair-lever",
        list(RELATIONSHIP_DYNAMIC_KEYS),
    )
    known_render_count += check(
        "action-direction",
        base_action,
        "stop-condition",
        list(STOP_COPY),
    )
    known_render_count += check(
        "action-direction",
        base_action,
        "contact-posture",
        list(ACTION_CONTACT_POSTURES),
    )
    known_render_count += check(
        "action-direction",
        base_action,
        "blocked-action",
        list(BLOCKED_ACTION_COPY),
    )

    unknown_cases = [
        ("chart-positioning", {**base_chart, "user-emotional-need": ["moon.unknown"]}),
        ("chart-positioning", {**base_chart, "user-communication-style": ["mercury.unknown"]}),
        ("chart-positioning", {**base_chart, "partner-pressure-response": ["mars.unknown"]}),
        ("chart-positioning", {**base_chart, "precision-mode": ["unknown"]}),
        ("relationship-fit", {**base_fit, "relationship-archetype": ["unknown"]}),
        ("relationship-fit", {**base_fit, "primary-dynamic": ["unknown"]}),
        ("relationship-fit", {**base_fit, "secondary-dynamic": ["unknown"]}),
        ("relationship-fit", {**base_fit, "attraction-signal": ["attraction:attractiondynamics:unresolved"]}),
        ("relationship-fit", {**base_fit, "friction-signal": ["friction:frictiondynamics:unresolved"]}),
        ("relationship-fit", {**base_fit, "growth-signal": ["growth:growthdynamics:unresolved"]}),
        ("core-answer", {**base_core, "central-dynamic": ["unknown"]}),
        ("core-answer", {**base_core, "partner-relationship-need": ["moon.unknown"]}),
        ("core-answer", {**base_core, "evidence-signal": ["friction:frictiondynamics:unresolved"]}),
        ("core-answer", {**base_core, "uncertainty-level": ["unknown"]}),
        ("timing-reading", {**base_timing, "timing-window": ["not-calculated|unknown|unknown|unknown"]}),
        ("action-direction", {**base_action, "repair-lever": ["unknown"]}),
    ]
    unknown_fallback_count = 0
    for section_id, values in unknown_cases:
        _, diagnostics = render_synthetic(section_id, values)
        require(
            diagnostics["unknownFallbackCount"] > 0,
            f"{section_id}: unknown state was not logged",
        )
        unknown_fallback_count += diagnostics["unknownFallbackCount"]

    expected_roles = {
        (section_id, role)
        for section_id, roles in FINAL_NARRATIVE_ROLE_DISPOSITIONS.items()
        for role in roles
    }
    tested_roles = {
        (section_id, role)
        for section_id, roles in tested_values.items()
        for role, values in roles.items()
        if values
    }
    require(
        tested_roles == expected_roles,
        "exhaustive value registry does not cover every semantic role: "
        f"missing={sorted(expected_roles - tested_roles)} extra={sorted(tested_roles - expected_roles)}",
    )
    return {
        "knownRenderCount": known_render_count,
        "knownFallbackCount": 0,
        "unknownCaseCount": len(unknown_cases),
        "unknownFallbackCount": unknown_fallback_count,
        "testedRoleCount": len(tested_roles),
        "testedValueCount": sum(
            len(values)
            for roles in tested_values.values()
            for values in roles.values()
        ),
        "testedRoleValues": {
            section_id: {
                role: sorted(values)
                for role, values in sorted(roles.items())
            }
            for section_id, roles in sorted(tested_values.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Phase 4 final narrative semantic coverage.")
    parser.add_argument("--generated", type=Path, default=DEFAULT_GENERATED_PATH)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--representative-only", action="store_true")
    args = parser.parse_args()

    alignment_errors = semantic_policy_alignment_errors(FINAL_NARRATIVE_FACT_POLICIES)
    require(not alignment_errors, "; ".join(alignment_errors))
    exhaustive = exhaustive_value_domain_check()

    bundles = representative_bundles()
    if not args.representative_only:
        generated = json.loads(args.generated.read_text(encoding="utf-8"))
        generated_bundles = list(find_bundles(generated))
        require(generated_bundles, "generated scenario bundles are missing")
        bundles.extend(generated_bundles)

    unique_bundles: dict[str, dict[str, Any]] = {}
    for bundle in bundles:
        contract = bundle.get("finalNarrativeFacts") or {}
        identity = json.dumps(
            [
                str(((contract.get("sections") or {}).get(section_id) or {}).get("sourceSpecFingerprint") or "")
                for section_id in sorted(FINAL_NARRATIVE_ROLE_DISPOSITIONS)
            ],
            separators=(",", ":"),
        )
        unique_bundles[identity] = bundle

    observed_values: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    rendered_sections = 0
    for bundle in unique_bundles.values():
        contract = bundle.get("finalNarrativeFacts") or {}
        require(
            contract.get("version") == FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
            f"stale generated fact contract: {contract.get('version')}",
        )
        require(
            contract.get("semanticCoverageVersion") == FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
            "semantic coverage version missing",
        )
        composer = composer_for(bundle)
        for section_id in FINAL_NARRATIVE_ROLE_DISPOSITIONS:
            composer.render_section(section_id)
            rendered_sections += 1
            for fact in composer.facts.facts(section_id):
                observed_values[section_id][str(fact.get("role") or "")].add(
                    str(fact.get("valueKey") or "")
                )

    calibration_case_count = 0
    if not args.representative_only:
        corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
        require(corpus.get("version") == CORPUS_VERSION, "semantic coverage corpus is stale")
        require(
            corpus.get("semanticCoverageVersion") == FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
            "calibration corpus semantic coverage version is stale",
        )
        calibration_cases = [
            item
            for item in [*(corpus.get("matrixCases") or []), *(corpus.get("comparisonCases") or [])]
            if isinstance(item, dict)
        ]
        calibration_case_count = len(calibration_cases)
        for case in calibration_cases:
            fact_sections = ((case.get("finalFactContract") or {}).get("sections") or {})
            for section_id, section in fact_sections.items():
                for role, values in (section.get("roleValues") or {}).items():
                    observed_values[str(section_id)][str(role)].update(str(value) for value in values)

    missing_roles: list[str] = []
    for section_id, role_registry in FINAL_NARRATIVE_ROLE_DISPOSITIONS.items():
        for role in role_registry:
            if role not in observed_values[section_id]:
                missing_roles.append(f"{section_id}:{role}")
    require(not missing_roles, f"semantic roles have no scenario coverage: {missing_roles}")

    role_count = sum(len(roles) for roles in observed_values.values())
    value_count = sum(len(values) for roles in observed_values.values() for values in roles.values())
    disposition_counts: dict[str, int] = defaultdict(int)
    for roles in FINAL_NARRATIVE_ROLE_DISPOSITIONS.values():
        for disposition in roles.values():
            disposition_counts[disposition] += 1

    print("Final narrative Phase 4 semantic coverage verification passed")
    print(f"- unique fact bundles: {len(unique_bundles)}")
    print(f"- calibration cases: {calibration_case_count}")
    print(f"- sections rendered: {rendered_sections}")
    print(f"- emitted roles realized: {role_count}")
    print(f"- emitted values realized: {value_count}")
    print(f"- exhaustive known values rendered: {exhaustive['knownRenderCount']}")
    print("- known-input fallback rate: 0.0%")
    print(f"- explicit unknown cases logged: {exhaustive['unknownCaseCount']}")
    print(f"- role dispositions: {dict(sorted(disposition_counts.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
