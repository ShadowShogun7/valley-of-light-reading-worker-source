#!/usr/bin/env python3
"""Build the compact Phase 5 production-calibration holdout corpus."""

from __future__ import annotations

import argparse
import copy
import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any

from build_reading_production_baseline import (
    ANALYSIS_DATE,
    CONTACTS,
    DESIRED_OUTCOMES,
    EMOTIONAL_RISKS,
    QUESTIONS,
    build_runtime_case,
    chart_fingerprint,
    deterministic_pairs,
    file_hash,
    reading_for_pair,
    stable_hash,
    visible_sections,
)
from complete_relationship_result_runtime import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    load_articles,
    load_claims_by_article,
)
from kb_utils import ROOT
from readable_interpretation.final_narrative_fact_contract import (
    FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
    FINAL_NARRATIVE_FACT_RENDERER_MODE,
)
from readable_interpretation.final_narrative_composer import FINAL_NARRATIVE_COMPOSER_VERSION
from readable_interpretation.final_narrative_chinese_quality import (
    FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
    hard_quality_contract_fingerprint,
)
from readable_interpretation.final_narrative_composition import (
    FINAL_NARRATIVE_COMPOSITION_VERSION,
)
from readable_interpretation.final_narrative_paragraph_plan import (
    FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
)
from readable_interpretation.final_narrative_semantic_coverage import (
    FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
)
from readable_interpretation.section_narrative_spec import (
    SECTION_NARRATIVE_IDS,
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
)
from relationship_status_answer_policy import STAGE_ORDER
from structured_runtime import (
    DEFAULT_ATOMS_PATH,
    DEFAULT_GUARDRAILS_PATH,
    DEFAULT_QUESTION_BLUEPRINTS_PATH,
    DEFAULT_RULES_PATH,
    load_structured_kb,
)


CORPUS_VERSION = "relationship-reading-phase5-calibration-v5"
REVIEW_VERSION = "relationship-reading-phase5-review-v5"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reading-production-calibration" / "v1"
DEFAULT_WEB_REVIEW_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "phase5-review-cases.json"
MATRIX_CASE_COUNT = len(STAGE_ORDER) * len(QUESTIONS) * len(CONTACTS)
REVIEW_CASE_COUNT = 40
REVIEW_DIMENSIONS = (
    "readability",
    "chartSpecificity",
    "pageTopicOwnership",
)
RUNTIME_SOURCE_PATHS = (
    ROOT / "scripts" / "build_reading_phase5_calibration.py",
    ROOT / "scripts" / "complete_relationship_result_runtime.py",
    ROOT / "scripts" / "relationship_status_answer_policy.py",
    ROOT / "scripts" / "readable_interpretation" / "schema.py",
    ROOT / "scripts" / "readable_interpretation" / "copy_contract.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_fact_contract.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_fact_renderer.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_composition.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_page_grammar.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_realization.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_chinese_contract.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_chinese_quality.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_chinese_plan.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_paragraph_plan.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_story_arc.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_semantic_coverage.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_semantic_domains.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_signal_service.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "chart_positioning_renderer.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "chart_positioning_zh_tw_catalog.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "relationship_fit_renderer.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "relationship_fit_zh_tw_catalog.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "core_answer_renderer.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "timing_renderer.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_pages" / "action_direction_renderer.py",
    ROOT / "scripts" / "readable_interpretation" / "section_narrative_spec.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_composer.py",
    ROOT / "scripts" / "readable_interpretation" / "zh_tw.py",
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    DEFAULT_ATOMS_PATH,
    DEFAULT_RULES_PATH,
    DEFAULT_QUESTION_BLUEPRINTS_PATH,
    DEFAULT_GUARDRAILS_PATH,
    ROOT
    / "data"
    / "reading-quality-cases"
    / "final-narrative-native-zh-tw-quality-contract-v1.json",
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def runtime_source_hashes() -> dict[str, str]:
    return {
        display_path(path): file_hash(path)
        for path in RUNTIME_SOURCE_PATHS
        if path.exists()
    }


def context_for_combo(index: int, stage: str, question: str, contact: str) -> dict[str, Any]:
    risk = "self-blaming" if question == "what-did-i-do-wrong" else EMOTIONAL_RISKS[index % len(EMOTIONAL_RISKS)]
    if stage == "crisis" and risk == "calm":
        risk = "anxious"
    return {
        "relationship_stage": stage,
        "main_question": question,
        "contact_status": contact,
        "desired_outcome": DESIRED_OUTCOMES[question],
        "emotional_risk": risk,
        "analysis_date": ANALYSIS_DATE,
        "timing_scan_days": 56,
        "timing_scan_step_days": 7,
    }


def semantic_identity(spec: dict[str, Any]) -> str:
    return stable_hash(
        {
            "context": spec.get("context") or {},
            "semanticSlots": spec.get("semanticSlots") or {},
            "conceptKeys": spec.get("conceptKeys") or [],
        }
    )


def compact_hidden_model(view_model: dict[str, Any]) -> dict[str, Any]:
    model = view_model.get("relationshipCaseModel") if isinstance(view_model.get("relationshipCaseModel"), dict) else {}
    primary = model.get("primaryDynamic") if isinstance(model.get("primaryDynamic"), dict) else {}
    secondaries = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    interaction = model.get("dynamicInteractionPlan") if isinstance(model.get("dynamicInteractionPlan"), dict) else {}
    return {
        "version": str(model.get("version") or ""),
        "archetypeTitle": str((view_model.get("relationshipArchetype") or {}).get("title") or ""),
        "primaryDynamicKey": str(primary.get("key") or ""),
        "secondaryDynamics": [
            {"key": str(item.get("key") or ""), "role": str(item.get("role") or "")}
            for item in secondaries
        ],
        "grammarId": str(interaction.get("grammarId") or ""),
        "grammarMode": str(interaction.get("grammarMode") or ""),
        "timingPostureKey": str((model.get("timingPosture") or {}).get("key") or ""),
        "contactPostureKey": str((model.get("contactPosture") or {}).get("key") or ""),
        "riskPostureKey": str((model.get("riskPosture") or {}).get("key") or ""),
    }


def compact_record(
    reading: dict[str, Any],
    calculation_payload: dict[str, Any],
    view_model: dict[str, Any],
    *,
    pair: tuple[int, int],
    cohort: str,
) -> dict[str, Any]:
    sections = visible_sections(view_model)
    bundle = view_model.get("sectionNarrativeSpecs") if isinstance(view_model.get("sectionNarrativeSpecs"), dict) else {}
    specs = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    fact_contract = bundle.get("finalNarrativeFacts") if isinstance(bundle.get("finalNarrativeFacts"), dict) else {}
    fact_sections = fact_contract.get("sections") if isinstance(fact_contract.get("sections"), dict) else {}
    hidden = compact_hidden_model(view_model)
    pair_input = {"personA": reading.get("person_a") or {}, "personB": reading.get("person_b") or {}}
    context = copy.deepcopy(reading.get("context") or {})
    return {
        "id": str(reading.get("reading_id") or ""),
        "cohort": cohort,
        "pair": {"personAProfile": pair[0], "personBProfile": pair[1]},
        "context": context,
        "fingerprints": {
            "pair": stable_hash(pair_input),
            "chart": chart_fingerprint(calculation_payload),
            "hiddenModel": stable_hash(hidden),
            "visible": stable_hash(sections),
            "sectionBodies": {
                section_id: stable_hash((sections.get(section_id) or {}).get("body") or "")
                for section_id in SECTION_NARRATIVE_IDS
            },
        },
        "hiddenModel": hidden,
        "sectionContracts": {
            "version": str(bundle.get("version") or ""),
            "rendererVersion": str(bundle.get("rendererVersion") or ""),
            "validationStatus": str((bundle.get("validation") or {}).get("status") or ""),
            "sections": {
                section_id: {
                    "semanticIdentity": semantic_identity(specs.get(section_id) or {}),
                    "conceptKeys": sorted(
                        str(value)
                        for value in (specs.get(section_id) or {}).get("conceptKeys") or []
                        if str(value or "").strip()
                    ),
                    "evidenceConceptKeys": sorted(
                        {
                            str(item.get("conceptKey") or "")
                            for item in (specs.get(section_id) or {}).get("evidence") or []
                            if isinstance(item, dict) and item.get("conceptKey")
                        }
                    ),
                    "caseModelTrace": copy.deepcopy((specs.get(section_id) or {}).get("caseModelTrace") or {}),
                }
                for section_id in SECTION_NARRATIVE_IDS
            },
        },
        "finalFactContract": {
            "version": str(fact_contract.get("version") or ""),
            "rendererMode": str(fact_contract.get("rendererMode") or ""),
            "semanticCoverageVersion": str(fact_contract.get("semanticCoverageVersion") or ""),
            "validationStatus": str((fact_contract.get("validation") or {}).get("status") or ""),
            "sections": {
                section_id: {
                    "factIdentity": stable_hash((fact_sections.get(section_id) or {}).get("facts") or []),
                    "factCount": len((fact_sections.get(section_id) or {}).get("facts") or []),
                    "roleValues": {
                        role: sorted(
                            {
                                str(item.get("valueKey") or "")
                                for item in (fact_sections.get(section_id) or {}).get("facts") or []
                                if isinstance(item, dict)
                                and str(item.get("role") or "") == role
                                and item.get("valueKey")
                            }
                        )
                        for role in sorted(
                            {
                                str(item.get("role") or "")
                                for item in (fact_sections.get(section_id) or {}).get("facts") or []
                                if isinstance(item, dict) and item.get("role")
                            }
                        )
                    },
                    "sourceSpecFingerprint": str(
                        (fact_sections.get(section_id) or {}).get("sourceSpecFingerprint") or ""
                    ),
                    "unknownFactIds": copy.deepcopy(
                        ((fact_sections.get(section_id) or {}).get("diagnostics") or {}).get("unknownFactIds") or []
                    ),
                    "compatibilityProseSlots": copy.deepcopy(
                        ((fact_sections.get(section_id) or {}).get("diagnostics") or {}).get("compatibilityProseSlots") or []
                    ),
                }
                for section_id in SECTION_NARRATIVE_IDS
            },
        },
        "sections": sections,
    }


def review_cases(cases: list[dict[str, Any]], count: int = REVIEW_CASE_COUNT) -> list[dict[str, Any]]:
    remaining = sorted(cases, key=lambda item: stable_hash({"phase5-review": item.get("id")}))
    selected: list[dict[str, Any]] = []
    counts: dict[str, Counter[str]] = {
        "stage": Counter(),
        "question": Counter(),
        "contact": Counter(),
        "primary": Counter(),
    }
    while remaining and len(selected) < count:
        def balance_key(item: dict[str, Any]) -> tuple[int, int, int, int, str]:
            context = item.get("context") or {}
            primary = str((item.get("hiddenModel") or {}).get("primaryDynamicKey") or "")
            return (
                counts["stage"][str(context.get("relationship_stage") or "")],
                counts["question"][str(context.get("main_question") or "")],
                counts["contact"][str(context.get("contact_status") or "")],
                counts["primary"][primary],
                str(item.get("id") or ""),
            )

        chosen = min(remaining, key=balance_key)
        remaining.remove(chosen)
        selected.append(chosen)
        context = chosen.get("context") or {}
        counts["stage"][str(context.get("relationship_stage") or "")] += 1
        counts["question"][str(context.get("main_question") or "")] += 1
        counts["contact"][str(context.get("contact_status") or "")] += 1
        counts["primary"][str((chosen.get("hiddenModel") or {}).get("primaryDynamicKey") or "")] += 1
    return selected


def build_corpus(progress_every: int = 10) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    combinations = list(itertools.product(STAGE_ORDER, QUESTIONS, CONTACTS))
    pairs = deterministic_pairs(len(combinations))
    matrix_cases: list[dict[str, Any]] = []
    matrix_readings: list[dict[str, Any]] = []
    engine_versions: dict[str, Any] = {}

    for index, ((stage, question, contact), pair) in enumerate(zip(combinations, pairs, strict=True)):
        reading = reading_for_pair(
            reading_id=f"phase5-matrix-{index + 1:03d}-{stage}-{question}-{contact}",
            pair=pair,
            context=context_for_combo(index, stage, question, contact),
            mix_unknown_times=True,
            record_index=index,
        )
        calculation_payload, view_model = build_runtime_case(
            reading,
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        )
        if not engine_versions:
            engine_versions = copy.deepcopy((calculation_payload.get("debug") or {}).get("engine_versions") or {})
        matrix_readings.append(reading)
        matrix_cases.append(compact_record(reading, calculation_payload, view_model, pair=pair, cohort="matrix"))
        if progress_every and (index + 1) % progress_every == 0:
            print(f"matrix progress: {index + 1}/{len(combinations)}", flush=True)

    comparison_specs = (
        ("question-change", 0, "core-answer"),
        ("stage-change", 5, "core-answer"),
        ("contact-change", 10, "timing-reading"),
        ("chart-change", 15, "relationship-fit"),
    )
    comparison_cases: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    for comparison_type, offset, expected_change in comparison_specs:
        for sample_index in range(5):
            left_index = offset + sample_index * len(QUESTIONS) * len(CONTACTS)
            left_reading = matrix_readings[left_index]
            left_record = matrix_cases[left_index]
            left_pair = pairs[left_index]
            right_pair = left_pair
            context = copy.deepcopy(left_reading.get("context") or {})
            if comparison_type == "question-change":
                question_index = QUESTIONS.index(str(context.get("main_question") or QUESTIONS[0]))
                next_question = QUESTIONS[(question_index + 1) % len(QUESTIONS)]
                context["main_question"] = next_question
                context["desired_outcome"] = DESIRED_OUTCOMES[next_question]
            elif comparison_type == "stage-change":
                stage_index = STAGE_ORDER.index(str(context.get("relationship_stage") or STAGE_ORDER[0]))
                context["relationship_stage"] = STAGE_ORDER[(stage_index + 1) % len(STAGE_ORDER)]
            elif comparison_type == "contact-change":
                contact_index = CONTACTS.index(str(context.get("contact_status") or CONTACTS[0]))
                context["contact_status"] = CONTACTS[(contact_index + 2) % len(CONTACTS)]
            else:
                right_pair = pairs[(left_index + 37) % len(pairs)]
            right_reading = reading_for_pair(
                reading_id=f"phase5-compare-{comparison_type}-{sample_index + 1:02d}",
                pair=right_pair,
                context=context,
                mix_unknown_times=True,
                record_index=left_index,
            )
            calculation_payload, view_model = build_runtime_case(
                right_reading,
                articles=articles,
                claims=claims,
                structured_kb=structured_kb,
            )
            right_record = compact_record(
                right_reading,
                calculation_payload,
                view_model,
                pair=right_pair,
                cohort="comparison",
            )
            comparison_cases.append(right_record)
            comparisons.append(
                {
                    "id": f"phase5-{comparison_type}-{sample_index + 1:02d}",
                    "type": comparison_type,
                    "leftId": left_record["id"],
                    "rightId": right_record["id"],
                    "stableSections": ["chart-positioning", "relationship-fit"] if comparison_type != "chart-change" else [],
                    "expectedChangedSections": [expected_change],
                }
            )

    corpus_identity = {
        "matrixCaseIds": [item["id"] for item in matrix_cases],
        "comparisonCaseIds": [item["id"] for item in comparison_cases],
        "sourceHashes": runtime_source_hashes(),
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
    }
    corpus = {
        "version": CORPUS_VERSION,
        "syntheticDataOnly": True,
        "purpose": "Unseen deterministic production calibration; not real-user validation.",
        "matrixCaseCount": len(matrix_cases),
        "comparisonCaseCount": len(comparison_cases),
        "supportedStages": list(STAGE_ORDER),
        "supportedQuestions": list(QUESTIONS),
        "supportedContacts": list(CONTACTS),
        "sectionIds": list(SECTION_NARRATIVE_IDS),
        "sectionSpecVersion": SECTION_NARRATIVE_SPEC_VERSION,
        "rendererVersion": SECTION_NARRATIVE_RENDERER_VERSION,
        "factContractVersion": FINAL_NARRATIVE_FACT_CONTRACT_VERSION,
        "factRendererMode": FINAL_NARRATIVE_FACT_RENDERER_MODE,
        "semanticCoverageVersion": FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "composerVersion": FINAL_NARRATIVE_COMPOSER_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
        "engineVersions": engine_versions,
        "runtimeSourceHashes": corpus_identity["sourceHashes"],
        "corpusFingerprint": stable_hash(corpus_identity),
        "matrixCases": matrix_cases,
        "comparisonCases": comparison_cases,
        "controlledComparisons": comparisons,
    }
    selected = review_cases(matrix_cases)
    review_manifest = {
        "version": REVIEW_VERSION,
        "corpusVersion": CORPUS_VERSION,
        "corpusFingerprint": corpus["corpusFingerprint"],
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
        "requiredAcceptedCount": 30,
        "selectedCaseCount": len(selected),
        "dimensions": list(REVIEW_DIMENSIONS),
        "minimumDimensionScore": 4,
        "cases": [
            {
                "id": item["id"],
                "context": item["context"],
                "primaryDynamicKey": (item.get("hiddenModel") or {}).get("primaryDynamicKey"),
                "archetypeTitle": (item.get("hiddenModel") or {}).get("archetypeTitle"),
                "status": "pending",
                "scores": {dimension: None for dimension in REVIEW_DIMENSIONS},
                "notes": "",
            }
            for item in selected
        ],
    }
    web_review_payload = {
        "version": REVIEW_VERSION,
        "corpusVersion": CORPUS_VERSION,
        "corpusFingerprint": corpus["corpusFingerprint"],
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
        "dimensions": list(REVIEW_DIMENSIONS),
        "requiredAcceptedCount": review_manifest["requiredAcceptedCount"],
        "cases": selected,
    }
    return corpus, review_manifest, web_review_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 5 production-calibration corpus.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--web-review-output", type=Path, default=DEFAULT_WEB_REVIEW_PATH)
    parser.add_argument("--progress-every", type=int, default=10)
    args = parser.parse_args()
    corpus, review_manifest, web_review_payload = build_corpus(progress_every=max(0, args.progress_every))
    write_json(args.output_dir / "holdout-corpus.json", corpus)
    write_json(args.output_dir / "review-manifest.json", review_manifest)
    write_json(args.web_review_output, web_review_payload)
    print(f"Wrote {len(corpus['matrixCases'])} Phase 5 matrix cases -> {display_path(args.output_dir)}")
    print(f"Wrote {len(corpus['comparisonCases'])} controlled comparison variants")
    print(f"Wrote {len(web_review_payload['cases'])} frontend review cases -> {display_path(args.web_review_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
