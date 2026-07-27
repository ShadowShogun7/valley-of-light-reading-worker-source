#!/usr/bin/env python3
"""Verify the Phase 1 fact-only final-narrative boundary."""

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
    SectionNarrativeSpecError,
)
from readable_interpretation.final_narrative_fact_contract import (  # noqa: E402
    FACT_KEY_PATTERN,
    FINAL_FACT_SECTION_IDS,
    FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
    FINAL_NARRATIVE_FACT_POLICIES,
    FINAL_NARRATIVE_FACT_RENDERER_MODE,
    FORBIDDEN_PROSE_KEYS,
    validate_final_narrative_fact_contract,
)
from visible_reading_depth import READING_PATHS, build_view_models  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def semantic_input(view_model: dict[str, Any], bundle: dict[str, Any]) -> FinalNarrativeSemanticInput:
    context = view_model.get("context") or {}
    return FinalNarrativeSemanticInput(
        question_key=str(context.get("main_question") or ""),
        stage_key=str(context.get("relationship_stage") or ""),
        contact_key=str(context.get("contact_status") or ""),
        section_specs=bundle,
        fact_contract=bundle.get("finalNarrativeFacts"),
    )


def assert_contract(view_model: dict[str, Any]) -> int:
    bundle = view_model.get("sectionNarrativeSpecs") if isinstance(view_model.get("sectionNarrativeSpecs"), dict) else {}
    specs = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    contract = bundle.get("finalNarrativeFacts") if isinstance(bundle.get("finalNarrativeFacts"), dict) else {}
    require(contract.get("version") == FINAL_NARRATIVE_FACT_CONTRACT_VERSION, "fact contract version missing")
    require(contract.get("rendererMode") == FINAL_NARRATIVE_FACT_RENDERER_MODE, "fact renderer mode missing")
    require(contract.get("factsRequired") is True, "facts are not required")
    require(contract.get("visibleProseAllowedInFacts") is False, "fact contract permits visible prose")
    validation = validate_final_narrative_fact_contract(contract, specs)
    require(validation.get("status") == "valid", f"fact contract invalid: {validation}")
    sections = contract.get("sections") if isinstance(contract.get("sections"), dict) else {}
    require(set(sections) == set(FINAL_FACT_SECTION_IDS), "fact section set mismatch")
    fact_count = 0
    for section_id in FINAL_FACT_SECTION_IDS:
        section = sections.get(section_id) or {}
        facts = [item for item in section.get("facts") or [] if isinstance(item, dict)]
        roles = {str(item.get("role") or "") for item in facts}
        required_roles = set(FINAL_NARRATIVE_FACT_POLICIES[section_id]["requiredRoles"])
        require(required_roles <= roles, f"{section_id}: missing required roles {sorted(required_roles - roles)}")
        for fact in facts:
            require(not (set(fact) & FORBIDDEN_PROSE_KEYS), f"{section_id}: prose leaked into a fact")
            require(bool(FACT_KEY_PATTERN.fullmatch(str(fact.get("id") or ""))), f"{section_id}: unstable fact id")
            require(bool(FACT_KEY_PATTERN.fullmatch(str(fact.get("valueKey") or ""))), f"{section_id}: unstable value key")
        fact_count += len(facts)
    composer = FinalNarrativeComposer.from_semantic_input(semantic_input(view_model, bundle))
    require(composer.fact_values("chart-positioning", "user-emotional-need"), "composer cannot access typed facts")
    return fact_count


def expect_contract_failure(view_model: dict[str, Any], mutate: str) -> None:
    bundle = copy.deepcopy(view_model.get("sectionNarrativeSpecs") or {})
    contract = bundle["finalNarrativeFacts"]
    if mutate == "prose-key":
        contract["sections"]["core-answer"]["facts"][0]["text"] = "visible prose must not enter facts"
    elif mutate == "unowned-evidence":
        contract["sections"]["timing-reading"]["facts"][0]["evidenceIds"] = ["E-not-owned"]
    elif mutate == "stale-source":
        bundle["sections"]["chart-positioning"]["semanticSlots"]["personAEmotionalNeed"] = "changed legacy prose"
    else:
        raise AssertionError(f"unknown mutation: {mutate}")
    try:
        FinalNarrativeComposer.from_semantic_input(semantic_input(view_model, bundle))
    except SectionNarrativeSpecError:
        return
    raise AssertionError(f"invalid fact contract reached the composer: {mutate}")


def main() -> int:
    view_models = build_view_models(READING_PATHS)
    require(view_models, "representative reading fixtures are missing")
    total_facts = sum(assert_contract(view_model) for view_model in view_models)
    for mutation in ("prose-key", "unowned-evidence", "stale-source"):
        expect_contract_failure(view_models[0], mutation)
    print("Final narrative fact contract smoke passed.")
    print(f"- representative readings: {len(view_models)}")
    print(f"- typed facts checked: {total_facts}")
    print("- visible prose, unowned evidence, and stale source specs fail before rendering")
    print(f"- compatibility mode: {FINAL_NARRATIVE_FACT_RENDERER_MODE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
