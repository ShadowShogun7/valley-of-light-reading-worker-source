#!/usr/bin/env python3
"""Verify five-page story progression and hidden-support ownership."""

from __future__ import annotations

import copy
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_composition import normalize_copy  # noqa: E402
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    FINAL_NARRATIVE_FACT_POLICIES,
)
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    ACTION_RATIONALE_EXTRA,
    OBSERVABLE_RESPONSE_VARIANTS,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    CORE_PARAGRAPH_DYNAMIC_THESES,
)
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
)
from readable_interpretation.final_narrative_story_arc import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    STORY_CHAPTERS,
    story_arc_contract_errors,
    story_arc_fact_errors,
    visible_roles,
)
from readable_interpretation.section_narrative_spec import SECTION_NARRATIVE_IDS  # noqa: E402
from visible_reading_depth import build_view_models  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_failure(label: str, operation: Callable[[], Any]) -> None:
    try:
        result = operation()
    except (AssertionError, ValueError):
        return
    if isinstance(result, list) and result:
        return
    raise AssertionError(f"deliberate invalid story case did not fail: {label}")


def normalized_catalog(values: Any) -> set[str]:
    output: set[str] = set()
    if isinstance(values, dict):
        for value in values.values():
            output.update(normalized_catalog(value))
    elif isinstance(values, (list, tuple, set)):
        for value in values:
            output.update(normalized_catalog(value))
    elif isinstance(values, str):
        output.add(normalize_copy(values))
    return output


def runtime_story_checks() -> tuple[int, int]:
    view_models = build_view_models()
    require(len(view_models) >= 10, "story audit needs at least ten representative readings")
    hidden_core_copy = normalized_catalog(CORE_PARAGRAPH_DYNAMIC_THESES)
    hidden_action_copy = normalized_catalog(ACTION_RATIONALE_EXTRA) | normalized_catalog(
        OBSERVABLE_RESPONSE_VARIANTS
    )
    checked_visible_claims = 0

    for view_model in view_models:
        reading_id = str(view_model.get("id") or "unknown")
        bundle = view_model.get("sectionNarrativeSpecs") or {}
        fact_contract = bundle.get("finalNarrativeFacts") or {}
        fact_sections = fact_contract.get("sections") or {}
        errors = story_arc_fact_errors(fact_sections)
        require(not errors, f"{reading_id}: invalid story handoff: {errors}")

        final = view_model.get("finalInterpretation") or {}
        outputs = final.get("sections") or {}
        require(set(outputs) == set(SECTION_NARRATIVE_IDS), f"{reading_id}: final chapters missing")

        core = outputs["core-answer"]
        action = outputs["action-direction"]
        require(
            len([item for item in str(core.get("body") or "").split("。") if item.strip()]) == 1,
            f"{reading_id}: core answer repeated supporting explanations",
        )
        require("完成" in str(action.get("body") or ""), f"{reading_id}: action has no completion boundary")
        require(
            normalize_copy(str(core.get("body") or "")) not in hidden_core_copy,
            f"{reading_id}: relationship thesis leaked back into core body",
        )
        require(
            normalize_copy(str(action.get("meaning") or "")) not in hidden_action_copy,
            f"{reading_id}: repair theory leaked back into action meaning",
        )
        require(
            normalize_copy(str(action.get("body") or "")) not in hidden_action_copy,
            f"{reading_id}: core observable condition leaked into action body",
        )

        for section_id in SECTION_NARRATIVE_IDS:
            section = fact_sections.get(section_id) or {}
            emitted_roles = {
                str(item.get("role") or "")
                for item in section.get("facts") or []
                if isinstance(item, dict)
            }
            checked_visible_claims += len(emitted_roles & visible_roles(section_id))
    return len(view_models), checked_visible_claims


def deliberate_invalid_checks() -> int:
    visible_control = copy.deepcopy(FINAL_NARRATIVE_ROLE_PRESENTATIONS)
    visible_control["core-answer"]["central-dynamic"] = "visible-claim"

    duplicate_chapter = dict(STORY_CHAPTERS)
    duplicate_chapter["action-direction"] = replace(
        duplicate_chapter["action-direction"],
        proposition_key=duplicate_chapter["timing-reading"].proposition_key,
    )

    missing_completion_policy = copy.deepcopy(FINAL_NARRATIVE_FACT_POLICIES)
    action_policy = missing_completion_policy["action-direction"]
    action_policy["allowedRoles"] = tuple(
        role for role in action_policy["allowedRoles"] if role != "completion-boundary"
    )

    view_model = build_view_models()[0]
    fact_sections = copy.deepcopy(
        (((view_model.get("sectionNarrativeSpecs") or {}).get("finalNarrativeFacts") or {}).get("sections") or {})
    )
    action_facts = fact_sections["action-direction"]["facts"]
    for fact in action_facts:
        if fact.get("role") == "action-purpose":
            fact["valueKey"] = "tone-repair-in-existing-channel"
            break

    invalid = (
        (
            "shared-control-made-visible",
            lambda: story_arc_contract_errors(
                FINAL_NARRATIVE_FACT_POLICIES,
                FINAL_NARRATIVE_ROLE_DISPOSITIONS,
                role_presentations=visible_control,
            ),
        ),
        (
            "duplicate-chapter-proposition",
            lambda: story_arc_contract_errors(
                FINAL_NARRATIVE_FACT_POLICIES,
                FINAL_NARRATIVE_ROLE_DISPOSITIONS,
                chapters=duplicate_chapter,
            ),
        ),
        (
            "chapter-lost-completion-role",
            lambda: story_arc_contract_errors(
                missing_completion_policy,
                FINAL_NARRATIVE_ROLE_DISPOSITIONS,
            ),
        ),
        (
            "action-purpose-disconnected",
            lambda: story_arc_fact_errors(fact_sections),
        ),
    )
    for label, operation in invalid:
        expect_failure(label, operation)
    return len(invalid)


def main() -> int:
    contract_errors = story_arc_contract_errors(
        FINAL_NARRATIVE_FACT_POLICIES,
        FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    )
    require(not contract_errors, f"story arc contract is invalid: {contract_errors}")
    reading_count, visible_claim_count = runtime_story_checks()
    invalid_count = deliberate_invalid_checks()
    print("Final narrative story-arc verification passed")
    print(f"- representative five-page readings checked: {reading_count}")
    print(f"- visible chapter facts checked: {visible_claim_count}")
    print(f"- deliberate ownership regressions rejected: {invalid_count}")
    print("- shared thesis and repair facts remain hidden controls outside relationship fit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
