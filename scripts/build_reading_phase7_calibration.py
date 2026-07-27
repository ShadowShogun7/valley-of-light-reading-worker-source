#!/usr/bin/env python3
"""Build the Phase 7 split, coverage-driven production calibration corpus."""

from __future__ import annotations

import argparse
import copy
import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from build_reading_phase5_calibration import (
    RUNTIME_SOURCE_PATHS as PHASE5_RUNTIME_SOURCE_PATHS,
    compact_record,
    display_path,
    write_json,
)
from build_reading_production_baseline import (
    ANALYSIS_DATE,
    CONTACTS,
    DESIRED_OUTCOMES,
    EMOTIONAL_RISKS,
    QUESTIONS,
    build_runtime_case,
    deterministic_pairs,
    file_hash,
    reading_for_pair,
    stable_hash,
)
from complete_relationship_result_runtime import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    load_articles,
    load_claims_by_article,
)
from kb_utils import ROOT
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
from readable_interpretation.section_narrative_spec import SECTION_NARRATIVE_IDS
from relationship_status_answer_policy import STAGE_ORDER
from structured_runtime import load_structured_kb


CORPUS_VERSION = "relationship-reading-phase7-calibration-v1"
REVIEW_VERSION = "relationship-reading-phase7-review-v1"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "reading-production-calibration" / "v2"
DEFAULT_WEB_REVIEW_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "phase7-review-cases.json"
DEFAULT_CONTRACT_PATH = ROOT / "data" / "reading-quality-cases" / "final-narrative-phase7-calibration-contract.json"
PRECISION_PROFILES = (
    "both-known",
    "person-a-unknown",
    "person-b-unknown",
    "both-unknown",
)
COMPARISON_AXES = ("question", "status", "contact", "risk", "chart")
RUNTIME_SOURCE_PATHS = (
    *PHASE5_RUNTIME_SOURCE_PATHS,
    ROOT / "scripts" / "build_reading_phase7_calibration.py",
    ROOT / "scripts" / "verify_reading_phase7_calibration.py",
    ROOT / "scripts" / "test_reading_phase5_calibration.py",
    ROOT / "scripts" / "audit_final_narrative_production_readiness.py",
    ROOT / "scripts" / "readable_interpretation" / "final_narrative_test_engine.py",
    DEFAULT_CONTRACT_PATH,
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_source_hashes() -> dict[str, str]:
    return {
        display_path(path): file_hash(path)
        for path in RUNTIME_SOURCE_PATHS
        if path.exists()
    }


def context_for_cell(stage: str, question: str, contact: str, risk: str) -> dict[str, Any]:
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


def apply_precision_profile(reading: dict[str, Any], profile: str) -> None:
    if profile not in PRECISION_PROFILES:
        raise ValueError(f"unknown Phase 7 precision profile: {profile}")
    if profile in {"person-a-unknown", "both-unknown"}:
        reading["person_a"]["birth_time"] = None
    if profile in {"person-b-unknown", "both-unknown"}:
        reading["person_b"]["birth_time"] = None


def input_precision_profile(reading: dict[str, Any]) -> str:
    person_a_known = bool((reading.get("person_a") or {}).get("birth_time"))
    person_b_known = bool((reading.get("person_b") or {}).get("birth_time"))
    if person_a_known and person_b_known:
        return "both-known"
    if not person_a_known and person_b_known:
        return "person-a-unknown"
    if person_a_known and not person_b_known:
        return "person-b-unknown"
    return "both-unknown"


def split_for_cell(cell_index: int, risk_index: int) -> str:
    precision_target = (cell_index // len(PRECISION_PROFILES)) % len(PRECISION_PROFILES)
    holdout_risk = (precision_target - cell_index) % len(EMOTIONAL_RISKS)
    review_risk = (precision_target + 1 - cell_index) % len(EMOTIONAL_RISKS)
    if risk_index == holdout_risk:
        return "automated-holdout"
    if risk_index == review_risk:
        return "human-review-candidate"
    return "development"


def enrich_record(
    record: dict[str, Any],
    *,
    reading: dict[str, Any],
    split: str,
    logical_axis: str = "matrix",
) -> dict[str, Any]:
    record["split"] = split
    record["calibrationAxes"] = {
        "logicalAxis": logical_axis,
        "emotionalRisk": str((reading.get("context") or {}).get("emotional_risk") or ""),
        "inputPrecision": input_precision_profile(reading),
    }
    return record


def semantic_review_tokens(case: dict[str, Any]) -> tuple[str, ...]:
    context = case.get("context") or {}
    hidden = case.get("hiddenModel") or {}
    timing_roles = (((case.get("finalFactContract") or {}).get("sections") or {}).get("timing-reading") or {}).get("roleValues") or {}
    action_roles = (((case.get("finalFactContract") or {}).get("sections") or {}).get("action-direction") or {}).get("roleValues") or {}
    tokens = {
        f"stage:{context.get('relationship_stage') or ''}",
        f"question:{context.get('main_question') or ''}",
        f"contact:{context.get('contact_status') or ''}",
        f"risk:{context.get('emotional_risk') or ''}",
        f"precision:{(case.get('calibrationAxes') or {}).get('inputPrecision') or ''}",
        f"archetype:{hidden.get('archetypeTitle') or ''}",
        f"primary:{hidden.get('primaryDynamicKey') or ''}",
        f"timing:{next(iter(timing_roles.get('recommended-action') or []), '')}",
        f"repair:{next(iter(action_roles.get('repair-lever') or []), '')}",
        f"stop:{next(iter(action_roles.get('stop-condition') or []), '')}",
    }
    tokens.update(
        f"secondary:{item.get('key') or ''}"
        for item in hidden.get("secondaryDynamics") or []
        if isinstance(item, dict) and item.get("key")
    )
    return tuple(sorted(token for token in tokens if not token.endswith(":")))


def coverage_driven_review_cases(cases: Iterable[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    remaining = [case for case in cases if case.get("split") != "automated-holdout"]
    token_frequency = Counter(token for case in remaining for token in semantic_review_tokens(case))
    selected: list[dict[str, Any]] = []
    selected_counts: Counter[str] = Counter()
    while remaining and len(selected) < count:
        def selection_key(case: dict[str, Any]) -> tuple[float, str]:
            novelty = sum(
                (1.0 / max(1, token_frequency[token])) * (1.0 / (1 + selected_counts[token]))
                for token in semantic_review_tokens(case)
            )
            return (-novelty, stable_hash({"phase7-review": case.get("id")}))

        chosen = min(remaining, key=selection_key)
        remaining.remove(chosen)
        selected.append(chosen)
        selected_counts.update(semantic_review_tokens(chosen))
    return selected


def balanced_comparison_bases(cases: list[dict[str, Any]], axis: str, count: int) -> list[dict[str, Any]]:
    remaining = sorted(
        [case for case in cases if case.get("split") == "automated-holdout"],
        key=lambda case: stable_hash({"phase7-comparison": axis, "id": case.get("id")}),
    )
    selected: list[dict[str, Any]] = []
    counts: dict[str, Counter[str]] = {
        "stage": Counter(),
        "question": Counter(),
        "contact": Counter(),
        "risk": Counter(),
        "primary": Counter(),
    }
    while remaining and len(selected) < count:
        def balance_key(case: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
            context = case.get("context") or {}
            hidden = case.get("hiddenModel") or {}
            return (
                counts["stage"][str(context.get("relationship_stage") or "")],
                counts["question"][str(context.get("main_question") or "")],
                counts["contact"][str(context.get("contact_status") or "")],
                counts["risk"][str(context.get("emotional_risk") or "")],
                counts["primary"][str(hidden.get("primaryDynamicKey") or "")],
                str(case.get("id") or ""),
            )

        chosen = min(remaining, key=balance_key)
        remaining.remove(chosen)
        selected.append(chosen)
        context = chosen.get("context") or {}
        hidden = chosen.get("hiddenModel") or {}
        counts["stage"][str(context.get("relationship_stage") or "")] += 1
        counts["question"][str(context.get("main_question") or "")] += 1
        counts["contact"][str(context.get("contact_status") or "")] += 1
        counts["risk"][str(context.get("emotional_risk") or "")] += 1
        counts["primary"][str(hidden.get("primaryDynamicKey") or "")] += 1
    return selected


def mutate_context(context: dict[str, Any], axis: str) -> dict[str, Any]:
    output = copy.deepcopy(context)
    if axis == "question":
        current = QUESTIONS.index(str(output.get("main_question") or QUESTIONS[0]))
        question = QUESTIONS[(current + 1) % len(QUESTIONS)]
        output["main_question"] = question
        output["desired_outcome"] = DESIRED_OUTCOMES[question]
    elif axis == "status":
        current = STAGE_ORDER.index(str(output.get("relationship_stage") or STAGE_ORDER[0]))
        output["relationship_stage"] = STAGE_ORDER[(current + 1) % len(STAGE_ORDER)]
    elif axis == "contact":
        current = CONTACTS.index(str(output.get("contact_status") or CONTACTS[0]))
        output["contact_status"] = CONTACTS[(current + 1) % len(CONTACTS)]
    elif axis == "risk":
        current = EMOTIONAL_RISKS.index(str(output.get("emotional_risk") or EMOTIONAL_RISKS[0]))
        output["emotional_risk"] = EMOTIONAL_RISKS[(current + 1) % len(EMOTIONAL_RISKS)]
    elif axis != "chart":
        raise ValueError(f"unknown Phase 7 comparison axis: {axis}")
    return output


def review_coverage(cases: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    output: dict[str, set[str]] = {}
    for case in cases:
        for token in semantic_review_tokens(case):
            group, value = token.split(":", 1)
            output.setdefault(group, set()).add(value)
    return {group: sorted(values) for group, values in sorted(output.items())}


def ensure_review_eligible_semantics(cases: list[dict[str, Any]]) -> int:
    swaps = 0
    while True:
        all_tokens = {token for case in cases for token in semantic_review_tokens(case)}
        eligible_counts = Counter(
            token
            for case in cases
            if case.get("split") != "automated-holdout"
            for token in semantic_review_tokens(case)
        )
        missing = sorted(all_tokens - set(eligible_counts))
        if not missing:
            return swaps
        token = missing[0]
        holder = next(
            case
            for case in cases
            if case.get("split") == "automated-holdout" and token in semantic_review_tokens(case)
        )
        holder_axes = holder.get("calibrationAxes") or {}
        holder_context = holder.get("context") or {}
        candidates = [
            case
            for case in cases
            if case.get("split") == "human-review-candidate"
            and (case.get("calibrationAxes") or {}).get("inputPrecision") == holder_axes.get("inputPrecision")
            and (case.get("context") or {}).get("emotional_risk") == holder_context.get("emotional_risk")
            and all(eligible_counts[item] > 1 for item in semantic_review_tokens(case))
        ]
        if not candidates:
            raise ValueError(f"cannot move rare semantic token into review pool: {token}")
        candidate = min(
            candidates,
            key=lambda case: stable_hash({"phase7-review-eligibility-swap": token, "id": case.get("id")}),
        )
        holder["split"] = "human-review-candidate"
        candidate["split"] = "automated-holdout"
        swaps += 1


def primary_dynamic(record: dict[str, Any]) -> str:
    return str((record.get("hiddenModel") or {}).get("primaryDynamicKey") or "")


def repair_lever(record: dict[str, Any]) -> str:
    section = (((record.get("finalFactContract") or {}).get("sections") or {}).get("action-direction") or {})
    return str(next(iter((section.get("roleValues") or {}).get("repair-lever") or []), ""))


def concentration_excess(cases: list[dict[str, Any]], coverage_contract: dict[str, Any]) -> int:
    primary_counts = Counter(primary_dynamic(case) for case in cases)
    repair_counts = Counter(repair_lever(case) for case in cases)
    primary_limit = int(len(cases) * float(coverage_contract.get("maximumPrimaryDynamicCoverage") or 0))
    repair_limit = int(len(cases) * float(coverage_contract.get("maximumRepairLeverCoverage") or 0))
    return max(0, max(primary_counts.values(), default=0) - primary_limit) + max(
        0,
        max(repair_counts.values(), default=0) - repair_limit,
    )


def rebalance_matrix_cases(
    *,
    matrix_cases: list[dict[str, Any]],
    readings_by_id: dict[str, dict[str, Any]],
    pairs_by_id: dict[str, tuple[int, int]],
    candidate_pairs: list[tuple[int, int]],
    coverage_contract: dict[str, Any],
    articles: dict[str, Any],
    claims: dict[str, Any],
    structured_kb: dict[str, Any],
) -> dict[str, int]:
    attempts = 0
    replacements = 0
    while concentration_excess(matrix_cases, coverage_contract) > 0 and attempts < len(candidate_pairs):
        primary_counts = Counter(primary_dynamic(case) for case in matrix_cases)
        repair_counts = Counter(repair_lever(case) for case in matrix_cases)
        dominant_primary = primary_counts.most_common(1)[0][0]
        dominant_repair = repair_counts.most_common(1)[0][0]
        targets = [
            index
            for index, case in enumerate(matrix_cases)
            if primary_dynamic(case) == dominant_primary or repair_lever(case) == dominant_repair
        ]
        targets.sort(key=lambda index: stable_hash({"phase7-rebalance": matrix_cases[index].get("id")}))
        target_index = targets[attempts % len(targets)]
        target = matrix_cases[target_index]
        target_id = str(target.get("id") or "")
        old_reading = readings_by_id[target_id]
        candidate_pair = candidate_pairs[attempts]
        attempts += 1
        candidate_reading = reading_for_pair(
            reading_id=target_id,
            pair=candidate_pair,
            context=copy.deepcopy(old_reading.get("context") or {}),
            mix_unknown_times=False,
            record_index=target_index,
        )
        apply_precision_profile(candidate_reading, input_precision_profile(old_reading))
        calculation_payload, view_model = build_runtime_case(
            candidate_reading,
            articles=articles,
            claims=claims,
            structured_kb=structured_kb,
        )
        candidate = compact_record(
            candidate_reading,
            calculation_payload,
            view_model,
            pair=candidate_pair,
            cohort="phase7-matrix",
        )
        enrich_record(candidate, reading=candidate_reading, split=str(target.get("split") or ""))
        before = concentration_excess(matrix_cases, coverage_contract)
        trial = list(matrix_cases)
        trial[target_index] = candidate
        if concentration_excess(trial, coverage_contract) >= before:
            continue
        matrix_cases[target_index] = candidate
        readings_by_id[target_id] = candidate_reading
        pairs_by_id[target_id] = candidate_pair
        replacements += 1
    remaining = concentration_excess(matrix_cases, coverage_contract)
    if remaining:
        raise ValueError(
            f"Phase 7 chart sampling could not satisfy concentration quotas: remaining excess={remaining}"
        )
    return {"attempts": attempts, "replacements": replacements}


def build_corpus(
    *,
    contract: dict[str, Any],
    progress_every: int = 25,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    repetitions = int((contract.get("matrix") or {}).get("repetitionsPerContextCell") or 0)
    expected_matrix_count = len(STAGE_ORDER) * len(QUESTIONS) * len(CONTACTS) * len(EMOTIONAL_RISKS)
    if repetitions != len(EMOTIONAL_RISKS) or expected_matrix_count != int((contract.get("matrix") or {}).get("expectedCaseCount") or 0):
        raise ValueError("Phase 7 calibration contract does not match the supported context domains")
    comparisons_per_axis = int((contract.get("controlledComparisons") or {}).get("casesPerAxis") or 0)
    comparison_pair_start = expected_matrix_count
    rebalance_pair_start = comparison_pair_start + comparisons_per_axis
    pair_count = rebalance_pair_start + 200
    pairs = deterministic_pairs(pair_count)
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    matrix_cases: list[dict[str, Any]] = []
    readings_by_id: dict[str, dict[str, Any]] = {}
    pairs_by_id: dict[str, tuple[int, int]] = {}
    engine_versions: dict[str, Any] = {}
    context_cells = list(itertools.product(STAGE_ORDER, QUESTIONS, CONTACTS))
    record_index = 0
    for cell_index, (stage, question, contact) in enumerate(context_cells):
        for risk_index, risk in enumerate(EMOTIONAL_RISKS):
            pair = pairs[record_index]
            split = split_for_cell(cell_index, risk_index)
            precision = PRECISION_PROFILES[(risk_index + cell_index) % len(PRECISION_PROFILES)]
            reading = reading_for_pair(
                reading_id=f"phase7-matrix-{record_index + 1:03d}-{stage}-{question}-{contact}-{risk}",
                pair=pair,
                context=context_for_cell(stage, question, contact, risk),
                mix_unknown_times=False,
                record_index=record_index,
            )
            apply_precision_profile(reading, precision)
            calculation_payload, view_model = build_runtime_case(
                reading,
                articles=articles,
                claims=claims,
                structured_kb=structured_kb,
            )
            if not engine_versions:
                engine_versions = copy.deepcopy((calculation_payload.get("debug") or {}).get("engine_versions") or {})
            record = compact_record(reading, calculation_payload, view_model, pair=pair, cohort="phase7-matrix")
            enrich_record(record, reading=reading, split=split)
            matrix_cases.append(record)
            readings_by_id[record["id"]] = reading
            pairs_by_id[record["id"]] = pair
            record_index += 1
            if progress_every and record_index % progress_every == 0:
                print(f"matrix progress: {record_index}/{expected_matrix_count}", flush=True)

    sampling_diagnostics = rebalance_matrix_cases(
        matrix_cases=matrix_cases,
        readings_by_id=readings_by_id,
        pairs_by_id=pairs_by_id,
        candidate_pairs=pairs[rebalance_pair_start:],
        coverage_contract=contract.get("coverage") or {},
        articles=articles,
        claims=claims,
        structured_kb=structured_kb,
    )
    sampling_diagnostics["reviewEligibilitySwaps"] = ensure_review_eligible_semantics(matrix_cases)

    comparison_cases: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    impact_policies = ((contract.get("controlledComparisons") or {}).get("impactPolicies") or {})
    for axis_index, axis in enumerate(COMPARISON_AXES):
        bases = balanced_comparison_bases(matrix_cases, axis, comparisons_per_axis)
        for sample_index, left_record in enumerate(bases):
            left_id = str(left_record.get("id") or "")
            left_reading = readings_by_id[left_id]
            right_pair = pairs_by_id[left_id]
            if axis == "chart":
                right_pair = pairs[comparison_pair_start + sample_index]
                right_reading = reading_for_pair(
                    reading_id=f"phase7-compare-{axis}-{sample_index + 1:02d}",
                    pair=right_pair,
                    context=copy.deepcopy(left_reading.get("context") or {}),
                    mix_unknown_times=False,
                    record_index=sample_index,
                )
                apply_precision_profile(right_reading, input_precision_profile(left_reading))
            else:
                right_reading = copy.deepcopy(left_reading)
                right_reading["reading_id"] = f"phase7-compare-{axis}-{sample_index + 1:02d}"
                right_reading["context"] = mutate_context(left_reading.get("context") or {}, axis)
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
                cohort=f"phase7-comparison-{axis}",
            )
            enrich_record(
                right_record,
                reading=right_reading,
                split="controlled-comparison",
                logical_axis=axis,
            )
            comparison_cases.append(right_record)
            policy = impact_policies.get(axis) or {}
            comparisons.append(
                {
                    "id": f"phase7-{axis}-{sample_index + 1:02d}",
                    "type": axis,
                    "leftId": left_id,
                    "rightId": right_record["id"],
                    "requiredChangedSections": list(policy.get("requiredChangedSections") or []),
                    "allowedChangedSections": list(policy.get("allowedChangedSections") or []),
                }
            )

    source_hashes = runtime_source_hashes()
    corpus_identity = {
        "matrixCaseIds": [case["id"] for case in matrix_cases],
        "comparisonCaseIds": [case["id"] for case in comparison_cases],
        "sourceHashes": source_hashes,
        "contractVersion": contract.get("version"),
        "composerVersion": FINAL_NARRATIVE_COMPOSER_VERSION,
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "semanticCoverageVersion": FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
    }
    split_counts = Counter(str(case.get("split") or "") for case in matrix_cases)
    corpus = {
        "version": CORPUS_VERSION,
        "contractVersion": contract.get("version"),
        "composerVersion": FINAL_NARRATIVE_COMPOSER_VERSION,
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "semanticCoverageVersion": FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
        "syntheticDataOnly": True,
        "purpose": "Split production calibration for semantic coverage and reader review; not real-user validation.",
        "matrixCaseCount": len(matrix_cases),
        "comparisonCaseCount": len(comparison_cases),
        "splitCounts": dict(sorted(split_counts.items())),
        "samplingDiagnostics": sampling_diagnostics,
        "supportedStages": list(STAGE_ORDER),
        "supportedQuestions": list(QUESTIONS),
        "supportedContacts": list(CONTACTS),
        "supportedEmotionalRisks": list(EMOTIONAL_RISKS),
        "supportedPrecisionProfiles": list(PRECISION_PROFILES),
        "sectionIds": list(SECTION_NARRATIVE_IDS),
        "engineVersions": engine_versions,
        "runtimeSourceHashes": source_hashes,
        "corpusFingerprint": stable_hash(corpus_identity),
        "matrixCases": matrix_cases,
        "comparisonCases": comparison_cases,
        "controlledComparisons": comparisons,
    }

    review_contract = contract.get("humanReview") or {}
    review_count = int(review_contract.get("selectedCaseCount") or 0)
    selected = coverage_driven_review_cases(matrix_cases, review_count)
    coverage = review_coverage(selected)
    review_manifest = {
        "version": REVIEW_VERSION,
        "corpusVersion": CORPUS_VERSION,
        "corpusFingerprint": corpus["corpusFingerprint"],
        "compositionVersion": FINAL_NARRATIVE_COMPOSITION_VERSION,
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "hardQualityVersion": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
        "hardQualityContractFingerprint": hard_quality_contract_fingerprint(),
        "requiredAcceptedCount": int(review_contract.get("requiredAcceptedCount") or 0),
        "selectedCaseCount": len(selected),
        "dimensions": list(review_contract.get("dimensions") or []),
        "minimumDimensionScore": int(review_contract.get("minimumDimensionScore") or 0),
        "coverage": coverage,
        "cases": [
            {
                "id": case["id"],
                "split": case["split"],
                "context": case["context"],
                "inputPrecision": (case.get("calibrationAxes") or {}).get("inputPrecision"),
                "primaryDynamicKey": (case.get("hiddenModel") or {}).get("primaryDynamicKey"),
                "archetypeTitle": (case.get("hiddenModel") or {}).get("archetypeTitle"),
                "status": "pending",
                "scores": {dimension: None for dimension in review_contract.get("dimensions") or []},
                "notes": "",
            }
            for case in selected
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
        "dimensions": list(review_contract.get("dimensions") or []),
        "requiredAcceptedCount": review_manifest["requiredAcceptedCount"],
        "coverage": coverage,
        "cases": selected,
    }
    return corpus, review_manifest, web_review_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--web-review-output", type=Path, default=DEFAULT_WEB_REVIEW_PATH)
    parser.add_argument("--progress-every", type=int, default=25)
    args = parser.parse_args()
    contract = read_json(args.contract)
    corpus, review_manifest, web_review_payload = build_corpus(
        contract=contract,
        progress_every=max(0, args.progress_every),
    )
    write_json(args.output_dir / "holdout-corpus.json", corpus)
    write_json(args.output_dir / "review-manifest.json", review_manifest)
    write_json(args.web_review_output, web_review_payload)
    print(f"Wrote {len(corpus['matrixCases'])} Phase 7 matrix cases -> {display_path(args.output_dir)}")
    print(f"Wrote {len(corpus['comparisonCases'])} controlled comparison variants")
    print(f"Wrote {len(web_review_payload['cases'])} review cases -> {display_path(args.web_review_output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
