#!/usr/bin/env python3
"""Verify production R5 native-Chinese page-realizer unification."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_chinese_contract import (  # noqa: E402
    audit_native_zh_tw_text,
)
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    normalize_copy,
    validate_section_composition,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    ValidatedFinalNarrativeFactContract,
    fact_id,
)
from readable_interpretation.final_narrative_fact_renderer import (  # noqa: E402
    OBSERVABLE_FORMS,
)
from readable_interpretation.final_narrative_pages import PAGE_RENDERERS  # noqa: E402
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    ACTION_COMMAND_VARIANTS,
    ACTION_PURPOSE_VARIANTS,
    ACTION_RATIONALE_EXTRA,
    BLOCKED_ACTION_INFINITIVES,
    COMPLETION_BOUNDARY_VARIANTS,
    OBSERVABLE_RESPONSE_VARIANTS,
    STOP_COPY,
    action_catalog_errors,
    action_sentence_trace,
    action_sentence_traces,
)
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import (  # noqa: E402
    catalog_errors as chart_catalog_errors,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    ANSWER_TRACK_HEADLINES,
    UNCERTAINTY_COPY,
    core_answer_catalog_errors,
    core_answer_sentence_trace,
    core_signal_forms,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    ROLE_TO_KIND,
    catalog_errors as relationship_fit_catalog_errors,
    signal_forms as relationship_fit_signal_forms,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (  # noqa: E402
    ACTION_HEADLINES,
    ASPECT_DOMAIN,
    CONTACT_POSTURE_HEADLINES,
    PRECISE_DATE_COPY,
    TIMING_BAND_COPY,
    WINDOW_CATEGORY_COPY,
    WINDOW_TRIGGER_KEYS,
    timing_catalog_errors,
    timing_sentence_trace,
    timing_window_sentence,
)
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    SectionFactReader,
)
from readable_interpretation.final_narrative_semantic_domains import (  # noqa: E402
    CONTACT_STATUS_KEYS,
    QUESTION_KEYS,
    RELATIONSHIP_DYNAMIC_KEYS,
)
from readable_interpretation.final_narrative_signal_service import (  # noqa: E402
    FINAL_NARRATIVE_SIGNAL_SERVICE_VERSION,
    resolve_relationship_signal,
    supported_evidence_signal_values,
    supported_relationship_signal_values,
)


CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"

CORE_BASE = {
    "question": ["any-chance"],
    "relationship-stage": ["broke-up-recent"],
    "contact-status": ["occasional-contact"],
    "answer-track": ["reconciliation-potential"],
    "central-dynamic": ["communication-repair"],
    "partner-relationship-need": ["moon.libra"],
    "evidence-signal": [
        "attraction:sun-moon:persona:sun>personb:moon:trine:soft"
    ],
    "observable-sign": ["partner-continues-without-prompt"],
    "uncertainty-level": ["medium"],
}

TIMING_BASE = {
    "question": ["when-to-contact"],
    "contact-status": ["occasional-contact"],
    "timing-posture": ["low-pressure-message"],
    "recommended-action": ["low-pressure-message"],
    "timing-band": ["better"],
    "contact-posture": ["test-low-pressure"],
    "precise-dates-available": ["available"],
    "timing-window": [
        "2026-07-mid|communication-opening|mercury-venus|sextile"
    ],
}

ACTION_BASE = {
    "question": ["when-to-contact"],
    "contact-status": ["occasional-contact"],
    "action-purpose": ["small-bid-response-led"],
    "action-mode": ["small-bid-response-led"],
    "completion-boundary": ["small-bid-response-led"],
    "repair-lever": ["communication-repair"],
    "stop-condition": ["standard"],
    "contact-posture": ["test-low-pressure"],
    "blocked-action": ["repeated-messages", "long-explanation"],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fingerprint(identity: str) -> str:
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def synthetic_fact(
    section_id: str,
    role: str,
    value_key: str,
    *,
    id_override: str = "",
    fingerprint_override: str = "",
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    identity = f"{section_id}:{role}:{value_key}"
    return {
        "id": id_override or fact_id(section_id, role, value_key),
        "sectionId": section_id,
        "role": role,
        "valueKey": value_key,
        "sourceSlot": role,
        "sourceBindingFingerprint": fingerprint_override or fingerprint(identity),
        "evidenceIds": evidence_ids if evidence_ids is not None else [f"synthetic:{identity}"],
        "qualifiers": [],
    }


def synthetic_contract(
    section_id: str,
    base: dict[str, list[str]],
    *,
    overrides: dict[str, list[str]] | None = None,
    omit_roles: set[str] | None = None,
    replacements: dict[str, list[dict[str, Any]]] | None = None,
    extras: list[dict[str, Any]] | None = None,
) -> ValidatedFinalNarrativeFactContract:
    selected = {
        role: list(values)
        for role, values in {**base, **(overrides or {})}.items()
        if role not in (omit_roles or set())
    }
    records = [
        synthetic_fact(section_id, role, value)
        for role, values in selected.items()
        for value in values
    ]
    for role, values in (replacements or {}).items():
        records = [record for record in records if record.get("role") != role]
        records.extend(values)
    records.extend(extras or [])
    return ValidatedFinalNarrativeFactContract(
        contract={"synthetic": True},
        sections={section_id: {"facts": records}},
    )


def render_section(
    section_id: str,
    base: dict[str, list[str]],
    *,
    overrides: dict[str, list[str]] | None = None,
    omit_roles: set[str] | None = None,
    replacements: dict[str, list[dict[str, Any]]] | None = None,
    extras: list[dict[str, Any]] | None = None,
    seed: str = "r5-page-realizer-verifier",
) -> dict[str, str]:
    reader = SectionFactReader(
        contract=synthetic_contract(
            section_id,
            base,
            overrides=overrides,
            omit_roles=omit_roles,
            replacements=replacements,
            extras=extras,
        ),
        section_id=section_id,
    )
    rendered = PAGE_RENDERERS[section_id](reader, seed)
    reader.assert_complete()
    validate_section_composition(section_id, rendered)
    return rendered


def changed_fields(left: dict[str, str], right: dict[str, str]) -> set[str]:
    return {field for field in left if left[field] != right[field]}


def expect_failure(label: str, operation: Callable[[], Any]) -> None:
    try:
        operation()
    except (AssertionError, ValueError):
        return
    raise AssertionError(f"deliberate invalid case did not fail: {label}")


def verify_catalogs() -> dict[str, int]:
    checks = {
        "chart-positioning": chart_catalog_errors(),
        "relationship-fit": relationship_fit_catalog_errors(),
        "core-answer": core_answer_catalog_errors(),
        "timing-reading": timing_catalog_errors(),
        "action-direction": action_catalog_errors(),
    }
    for section_id, errors in checks.items():
        require(not errors, f"{section_id} native catalog failed: {errors[:3]}")
    return {section_id: len(errors) for section_id, errors in checks.items()}


def verify_shared_signal_service() -> int:
    require(
        FINAL_NARRATIVE_SIGNAL_SERVICE_VERSION == "final-narrative-signal-service-v1",
        "shared relationship signal service version is stale",
    )
    expected = sum(
        len(supported_relationship_signal_values(kind)) for kind in ROLE_TO_KIND.values()
    )
    values = supported_evidence_signal_values()
    require(len(values) == expected, "core evidence signal domain diverged from fit domains")
    checked = 0
    for kind in ROLE_TO_KIND.values():
        for value_key in supported_relationship_signal_values(kind):
            signal = resolve_relationship_signal(value_key, expected_kind=kind)
            require(signal.raw == value_key, f"shared signal changed identity: {value_key}")
            fit_forms = relationship_fit_signal_forms(value_key, expected_kind=kind)
            core_forms = core_signal_forms(value_key)
            for purpose in ("direct", "situational", "relational"):
                fit_text = fit_forms.for_purpose(purpose)
                core_text = core_forms.for_purpose(purpose)
                require(
                    normalize_copy(fit_text) != normalize_copy(core_text),
                    f"fit and core reused visible wording: {value_key}:{purpose}",
                )
                shared_prefix = 0
                for fit_character, core_character in zip(fit_text, core_text):
                    if fit_character != core_character:
                        break
                    shared_prefix += 1
                require(
                    shared_prefix <= 18,
                    f"fit and core reused the same sentence opening: "
                    f"{value_key}:{purpose}:{shared_prefix}",
                )
                trace = core_answer_sentence_trace(core_text)
                require(
                    trace
                    == {
                        "kind": "fact-realization",
                        "role": "evidence-signal",
                        "valueKey": value_key,
                        "purpose": purpose,
                    },
                    f"core signal trace is stale: {value_key}:{purpose}",
                )
                checked += 1
    return checked


def verify_timing_windows() -> int:
    checked = 0
    seen: set[str] = set()
    forbidden_phrases = (
        "反應會來得集中",
        "會更明顯",
        "會影響",
        "對話比較容易放鬆，雙方容易互相頂住",
    )
    for category in WINDOW_CATEGORY_COPY:
        for trigger in WINDOW_TRIGGER_KEYS:
            for aspect in ASPECT_DOMAIN:
                value_key = f"2026-07-mid|{category}|{trigger}|{aspect}"
                sentence = timing_window_sentence(value_key, 0)
                require(not audit_native_zh_tw_text(sentence), value_key)
                require("你們" in sentence, f"timing window lacks an explicit pair subject: {value_key}")
                require(
                    not any(phrase in sentence for phrase in forbidden_phrases),
                    f"timing window uses vague or contradictory wording: {value_key}",
                )
                require(sentence.count("和") <= 2, f"timing window repeats 和: {value_key}")
                trace = timing_sentence_trace(sentence)
                require(
                    trace
                    == {
                        "kind": "fact-realization",
                        "role": "timing-window",
                        "valueKey": value_key,
                        "purpose": "situational",
                    },
                    f"timing window trace is stale: {value_key}",
                )
                normalized = normalize_copy(sentence)
                require(normalized not in seen, f"timing windows collapsed: {value_key}")
                seen.add(normalized)
                checked += 1
    return checked


def verify_action_traces() -> int:
    traces = action_sentence_traces()
    require(traces, "action sentence trace registry is empty")
    for sentence, trace in traces.items():
        require(action_sentence_trace(sentence) == trace, f"stale action trace: {sentence}")
        require(not audit_native_zh_tw_text(sentence), f"action trace violates Chinese gate: {sentence}")
    expected_roles = {
        "question": set(QUESTION_KEYS),
        "action-purpose": set(ACTION_PURPOSE_VARIANTS),
        "repair-lever": {*RELATIONSHIP_DYNAMIC_KEYS, "unknown"},
        "contact-posture": set(OBSERVABLE_RESPONSE_VARIANTS),
        "action-mode": set(ACTION_COMMAND_VARIANTS),
        "completion-boundary": set(COMPLETION_BOUNDARY_VARIANTS),
        "stop-condition": set(STOP_COPY),
    }
    observed = {
        role: {trace.get("valueKey") for trace in traces.values() if trace.get("role") == role}
        for role in expected_roles
    }
    for role, expected in expected_roles.items():
        require(observed[role] == expected, f"action trace role domain is incomplete: {role}")
    contributor_values = {
        trace.get("contributorValueKey")
        for trace in traces.values()
        if trace.get("contributorRole") == "blocked-action"
    }
    require(
        contributor_values == set(BLOCKED_ACTION_INFINITIVES),
        "action blocked-action trace domain is incomplete",
    )
    return len(traces)


def verify_page_jobs_and_field_ownership() -> int:
    core = render_section("core-answer", CORE_BASE)
    timing = render_section("timing-reading", TIMING_BASE)
    action = render_section("action-direction", ACTION_BASE)

    require("2026 年" in timing["body"], "timing page does not identify the workable window")
    require("完成" in action["body"], "action page lacks a completion boundary")
    require(
        any(marker in action["nextMove"] for marker in ("只", "先", "不要", "停止")),
        "action page lacks one concrete move",
    )
    require(
        any(marker in action["caution"] for marker in ("如果", "只要", "當", "若")),
        "action page lacks a stopping condition",
    )

    mutations: list[tuple[str, dict[str, str], dict[str, str], set[str]]] = []

    core_mutations = (
        ({"answer-track": ["repairability"]}, {"headline"}),
        ({"central-dynamic": ["emotional-safety"]}, set()),
        (
            {
                "evidence-signal": [
                    "friction:mercury-mars:persona:mercury>personb:mars:square:hard"
                ]
            },
            {"body"},
        ),
        ({"partner-relationship-need": ["moon.aries"]}, set()),
        ({"partner-relationship-need": ["moon.unknown"]}, set()),
        ({"observable-sign": ["spontaneous-next-interaction"]}, {"nextMove"}),
        ({"uncertainty-level": ["high"]}, {"caution"}),
    )
    for overrides, expected in core_mutations:
        changed = render_section("core-answer", CORE_BASE, overrides=overrides)
        require(changed_fields(core, changed) == expected, f"core ownership crossed: {overrides}")

    timing_mutations = (
        ({"question": ["still-love-me"]}, {"headline"}),
        ({"contact-status": ["no-contact"]}, {"meaning"}),
        (
            {
                "timing-posture": ["observe-only"],
                "recommended-action": ["observe-only"],
            },
            {"headline", "nextMove"},
        ),
        ({"timing-band": ["avoid"]}, {"body"}),
        ({"contact-posture": ["watch-initiation"]}, {"meaning"}),
        ({"precise-dates-available": ["unavailable"]}, {"caution"}),
        (
            {
                "timing-window": [
                    "2026-08-early|conflict-risk|moon-saturn|square"
                ]
            },
            {"body"},
        ),
    )
    for overrides, expected in timing_mutations:
        changed = render_section("timing-reading", TIMING_BASE, overrides=overrides)
        require(changed_fields(timing, changed) == expected, f"timing ownership crossed: {overrides}")

    action_mutations = (
        ({"question": ["stay-or-let-go"]}, {"headline"}),
        ({"contact-status": ["no-contact"]}, set()),
        (
            {
                "action-purpose": ["tone-repair-in-existing-channel"],
                "action-mode": ["tone-repair-in-existing-channel"],
                "completion-boundary": ["tone-repair-in-existing-channel"],
            },
            {"meaning", "body", "nextMove"},
        ),
        ({"repair-lever": ["emotional-safety"]}, set()),
        ({"stop-condition": ["anxiety-guard"]}, {"caution"}),
        ({"contact-posture": ["watch-initiation"]}, set()),
        (
            {"blocked-action": ["long-pressure-message", "testing-loyalty"]},
            {"caution"},
        ),
    )
    for overrides, expected in action_mutations:
        changed = render_section("action-direction", ACTION_BASE, overrides=overrides)
        require(changed_fields(action, changed) == expected, f"action ownership crossed: {overrides}")

    for section_id, base in (
        ("core-answer", CORE_BASE),
        ("timing-reading", TIMING_BASE),
        ("action-direction", ACTION_BASE),
    ):
        changed = render_section(section_id, base, seed="seed-must-not-select-copy")
        baseline = {"core-answer": core, "timing-reading": timing, "action-direction": action}[section_id]
        require(changed == baseline, f"seed still changes {section_id} wording")
    return len(core_mutations) + len(timing_mutations) + len(action_mutations)


def verify_deliberate_invalid_cases() -> int:
    invalid: list[tuple[str, Callable[[], Any]]] = [
        (
            "blocked-timing-allows-message",
            lambda: render_section(
                "timing-reading",
                TIMING_BASE,
                overrides={"contact-status": ["blocked"]},
            ),
        ),
        (
            "timing-posture-disagrees-with-action",
            lambda: render_section(
                "timing-reading",
                TIMING_BASE,
                overrides={"timing-posture": ["observe-only"]},
            ),
        ),
        (
            "blocked-contact-has-active-action",
            lambda: render_section(
                "action-direction",
                ACTION_BASE,
                overrides={"contact-status": ["blocked"]},
            ),
        ),
        (
            "action-missing-blocked-condition",
            lambda: render_section(
                "action-direction",
                ACTION_BASE,
                omit_roles={"blocked-action"},
            ),
        ),
        (
            "unsupported-core-signal",
            lambda: render_section(
                "core-answer",
                CORE_BASE,
                overrides={
                    "evidence-signal": [
                        "attraction:mercury-mars:persona:mercury>personb:mars:trine:soft"
                    ]
                },
            ),
        ),
        (
            "action-purpose-disagrees-with-mode",
            lambda: render_section(
                "action-direction",
                ACTION_BASE,
                overrides={"action-purpose": ["tone-repair-in-existing-channel"]},
            ),
        ),
        (
            "stale-source-fingerprint",
            lambda: render_section(
                "core-answer",
                CORE_BASE,
                replacements={
                    "evidence-signal": [
                        synthetic_fact(
                            "core-answer",
                            "evidence-signal",
                            CORE_BASE["evidence-signal"][0],
                            fingerprint_override="stale",
                        )
                    ]
                },
            ),
        ),
        (
            "wrong-source-fact-id",
            lambda: render_section(
                "action-direction",
                ACTION_BASE,
                replacements={
                    "action-mode": [
                        synthetic_fact(
                            "action-direction",
                            "action-mode",
                            "small-bid-response-led",
                            id_override="action-direction.action-mode.boundary-only",
                        )
                    ]
                },
            ),
        ),
        (
            "unowned-action-fact",
            lambda: render_section(
                "action-direction",
                ACTION_BASE,
                extras=[
                    synthetic_fact(
                        "action-direction",
                        "primary-dynamic",
                        "communication-repair",
                    )
                ],
            ),
        ),
        (
            "duplicate-action-mode",
            lambda: render_section(
                "action-direction",
                ACTION_BASE,
                extras=[
                    synthetic_fact(
                        "action-direction",
                        "action-mode",
                        "boundary-only",
                    )
                ],
            ),
        ),
    ]
    for label, operation in invalid:
        expect_failure(label, operation)
    return len(invalid)


def verify_generated_blocked_boundaries() -> int:
    require(CORPUS_PATH.exists(), "R5 holdout corpus is missing")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    checked = 0
    for case in corpus.get("matrixCases") or []:
        context = case.get("context") if isinstance(case.get("context"), dict) else {}
        if context.get("contact_status") != "blocked":
            continue
        sections = ((case.get("finalFactContract") or {}).get("sections") or {})
        timing_values = (sections.get("timing-reading") or {}).get("roleValues") or {}
        action_values = (sections.get("action-direction") or {}).get("roleValues") or {}
        require(
            timing_values.get("timing-posture") == ["avoid-push"]
            and timing_values.get("recommended-action") == ["avoid-push"],
            f"{case.get('id')}: blocked timing boundary is stale",
        )
        require(
            action_values.get("action-mode") == ["boundary-only"],
            f"{case.get('id')}: blocked action boundary is stale",
        )
        checked += 1
    require(checked > 0, "R5 corpus contains no blocked-contact fixtures")
    return checked


def main() -> int:
    try:
        verify_catalogs()
        signal_forms_checked = verify_shared_signal_service()
        timing_windows_checked = verify_timing_windows()
        action_traces_checked = verify_action_traces()
        ownership_mutations = verify_page_jobs_and_field_ownership()
        invalid_cases = verify_deliberate_invalid_cases()
        blocked_cases = verify_generated_blocked_boundaries()
    except (AssertionError, KeyError, ValueError) as exc:
        print(f"Final narrative R5 page-realizer verification failed: {exc}")
        return 1

    print("Final narrative R5 page-realizer verification passed")
    print(f"- shared signal forms checked: {signal_forms_checked}")
    print(f"- timing-window combinations checked: {timing_windows_checked}")
    print(f"- action sentence traces checked: {action_traces_checked}")
    print(f"- field-ownership mutations checked: {ownership_mutations}")
    print(f"- deliberate invalid cases rejected: {invalid_cases}")
    print(f"- blocked-contact corpus cases checked: {blocked_cases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
