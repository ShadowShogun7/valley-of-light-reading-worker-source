#!/usr/bin/env python3
"""Verify paragraph and cross-page composition constraints for Phase 5."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_reading_phase5_calibration import CORPUS_VERSION  # noqa: E402
from readable_interpretation.final_narrative_composer import (  # noqa: E402
    FINAL_NARRATIVE_COMPOSER_VERSION,
)
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    FINAL_NARRATIVE_COMPOSITION_VERSION,
    MAXIMUM_CROSS_PAGE_BIGRAM_SIMILARITY,
    MAXIMUM_SENTENCE_CHARACTERS,
    SECTION_COMPOSITION_RULES,
    FinalNarrativeCompositionError,
    composition_contract_errors,
    composition_metrics,
    normalize_copy,
    validate_composition_contract,
    validate_reading_composition,
)
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    ACTION_COMMAND_VARIANTS,
    BLOCKED_ACTION_INFINITIVES,
    action_page_rationale_variants,
)
from readable_interpretation.final_narrative_fact_renderer import BLOCKED_ACTION_COPY  # noqa: E402
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    core_page_dynamic_variants,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    PRIMARY_DYNAMIC_FORMS,
)
from readable_interpretation.final_narrative_realization import REALIZATION_PURPOSES  # noqa: E402
from readable_interpretation.final_narrative_semantic_coverage import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
)
from readable_interpretation.final_narrative_semantic_domains import (  # noqa: E402
    RELATIONSHIP_DYNAMIC_KEYS,
)
from readable_interpretation.section_narrative_spec import SECTION_NARRATIVE_IDS  # noqa: E402


DEFAULT_CORPUS_PATH = (
    ROOT / "data" / "reading-production-calibration" / "v1" / "holdout-corpus.json"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_rejected(identity: str, operation: Callable[[], Any]) -> None:
    try:
        operation()
    except FinalNarrativeCompositionError:
        return
    raise AssertionError(f"composition mutation was accepted: {identity}")


def page_catalog_check() -> int:
    checked = 0
    require(
        set(BLOCKED_ACTION_INFINITIVES) == set(BLOCKED_ACTION_COPY),
        "blocked-action reader phrases do not cover the semantic domain",
    )
    for dynamic in (*RELATIONSHIP_DYNAMIC_KEYS, "unknown"):
        catalogs = {
            "relationship-fit": tuple(
                PRIMARY_DYNAMIC_FORMS[dynamic].forms.for_purpose(purpose)
                for purpose in REALIZATION_PURPOSES
            ),
            "core-answer": core_page_dynamic_variants(dynamic),
            "action-direction": action_page_rationale_variants(dynamic),
        }
        normalized = {
            section_id: {normalize_copy(value) for value in values}
            for section_id, values in catalogs.items()
        }
        for section_id, values in catalogs.items():
            require(
                len(values) >= 3 and len(normalized[section_id]) == len(values),
                f"{section_id}:{dynamic}: fewer than three distinct page-owned forms",
            )
            checked += len(values)
        section_ids = tuple(catalogs)
        for left_index, left_id in enumerate(section_ids):
            for right_id in section_ids[left_index + 1 :]:
                overlap = normalized[left_id] & normalized[right_id]
                require(
                    not overlap,
                    f"{dynamic}: page-owned wording shared by {left_id} and {right_id}",
                )

    for mode, values in ACTION_COMMAND_VARIANTS.items():
        require(len(values) >= 5, f"{mode}: action command coverage is too thin")
        require(
            len({normalize_copy(value) for value in values}) == len(values),
            f"{mode}: duplicate action command forms",
        )
        checked += len(values)
    return checked


def runtime_route_check() -> None:
    source_path = ROOT / "scripts" / "readable_interpretation" / "zh_tw.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    render_all_calls = 0
    render_section_calls = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "render_all":
            render_all_calls += 1
        elif node.func.attr == "render_section":
            render_section_calls += 1
    require(render_all_calls == 1, f"expected one render_all call, found {render_all_calls}")
    require(
        render_section_calls == 0,
        f"runtime bypasses cross-page composition with {render_section_calls} render_section call(s)",
    )


def deliberate_mutation_check(sample: dict[str, dict[str, str]]) -> int:
    intra_page = copy.deepcopy(sample)
    intra_page["action-direction"]["caution"] = intra_page["action-direction"]["body"]
    expect_rejected("intra-page repeated sentence", lambda: validate_reading_composition(intra_page))

    cross_page = copy.deepcopy(sample)
    cross_page["core-answer"]["caution"] = cross_page["relationship-fit"]["caution"]
    expect_rejected("cross-page repeated sentence", lambda: validate_reading_composition(cross_page))

    overlong = copy.deepcopy(sample)
    overlong["action-direction"]["meaning"] = "這" * (MAXIMUM_SENTENCE_CHARACTERS + 1) + "。"
    expect_rejected("overlong sentence", lambda: validate_reading_composition(overlong))

    rules = dict(SECTION_COMPOSITION_RULES)
    action_rule = rules["action-direction"]
    missing_role_owners = dict(action_rule.role_owners)
    missing_role_owners.pop("completion-boundary")
    rules["action-direction"] = replace(action_rule, role_owners=missing_role_owners)
    errors = composition_contract_errors(rules, FINAL_NARRATIVE_ROLE_DISPOSITIONS)
    require(
        any("completion-boundary" in error for error in errors),
        "missing semantic role ownership was accepted",
    )
    return 4


def evaluate(corpus: dict[str, Any]) -> dict[str, Any]:
    require(corpus.get("version") == CORPUS_VERSION, "Phase 5 corpus version is stale")
    require(
        corpus.get("composerVersion") == FINAL_NARRATIVE_COMPOSER_VERSION,
        "Phase 5 corpus composer version is stale",
    )
    require(
        corpus.get("compositionVersion") == FINAL_NARRATIVE_COMPOSITION_VERSION,
        "Phase 5 corpus composition version is stale",
    )
    validate_composition_contract()
    runtime_route_check()
    controlled_form_count = page_catalog_check()

    cases = [
        item
        for item in [*(corpus.get("matrixCases") or []), *(corpus.get("comparisonCases") or [])]
        if isinstance(item, dict)
    ]
    require(cases, "Phase 5 corpus has no cases")
    maximum_similarity = 0.0
    maximum_sentence = 0
    for case in cases:
        sections = case.get("sections") if isinstance(case.get("sections"), dict) else {}
        require(set(sections) == set(SECTION_NARRATIVE_IDS), f"{case.get('id')}: section set mismatch")
        validate_reading_composition(sections)
        metrics = composition_metrics(sections)
        maximum_similarity = max(
            maximum_similarity,
            float(metrics["maximumCrossPageBigramSimilarity"]),
        )
        maximum_sentence = max(maximum_sentence, int(metrics["maximumSentenceCharacters"]))

    mutation_count = deliberate_mutation_check(copy.deepcopy(cases[0]["sections"]))
    role_count = sum(len(roles) for roles in FINAL_NARRATIVE_ROLE_DISPOSITIONS.values())
    return {
        "passed": True,
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "composerVersion": FINAL_NARRATIVE_COMPOSER_VERSION,
        "caseCount": len(cases),
        "sectionCount": len(cases) * len(SECTION_NARRATIVE_IDS),
        "ownedRoleCount": role_count,
        "controlledPageFormCount": controlled_form_count,
        "maximumSentenceCharacters": maximum_sentence,
        "maximumCrossPageBigramSimilarity": round(maximum_similarity, 3),
        "crossPageSimilarityLimit": MAXIMUM_CROSS_PAGE_BIGRAM_SIMILARITY,
        "deliberateMutationCount": mutation_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(json.loads(args.corpus.read_text(encoding="utf-8")))
    except (AssertionError, FinalNarrativeCompositionError) as exc:
        if args.json:
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"Final narrative Phase 5 composition verification failed: {exc}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print("Final narrative Phase 5 composition verification passed")
        print(f"- cases: {result['caseCount']}")
        print(f"- sections: {result['sectionCount']}")
        print(f"- typed role owners: {result['ownedRoleCount']}")
        print(f"- page-owned controlled forms: {result['controlledPageFormCount']}")
        print(f"- maximum sentence characters: {result['maximumSentenceCharacters']}")
        print(
            "- maximum cross-page bigram similarity: "
            f"{result['maximumCrossPageBigramSimilarity']}"
        )
        print(f"- deliberate invalid compositions rejected: {result['deliberateMutationCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
