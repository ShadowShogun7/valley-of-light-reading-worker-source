#!/usr/bin/env python3
"""Score and gate the Phase 5 production-calibration holdout corpus."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from audit_relationship_fit_semantic_similarity import jaccard_similarity
from audit_final_narrative_production_readiness import native_semantic_trace_error
from build_reading_phase5_calibration import (
    CORPUS_VERSION,
    MATRIX_CASE_COUNT,
    REVIEW_DIMENSIONS,
    REVIEW_VERSION,
    RUNTIME_SOURCE_PATHS,
    runtime_source_hashes,
)
from build_reading_production_baseline import CONTACTS, QUESTIONS
from kb_utils import ROOT
from readable_interpretation.copy_contract import intra_page_overlap_hits, reader_meta_narration_hits
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
from readable_interpretation.final_narrative_pages.core_answer_renderer import (
    core_answer_sentence_trace,
)
from readable_interpretation.final_narrative_semantic_coverage import (
    FINAL_NARRATIVE_ROLE_DISPOSITIONS,
    FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION,
)
from readable_interpretation.final_narrative_story_arc import (
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
)
from readable_interpretation.section_narrative_spec import (
    SECTION_NARRATIVE_IDS,
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
)
from relationship_status_answer_policy import STAGE_ORDER
from test_reading_quality_engine import load_quality_contract


DEFAULT_CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "holdout-corpus.json"
DEFAULT_REVIEW_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "review-manifest.json"
DEFAULT_CONTRACT_DIR = ROOT / "data" / "reading-quality-cases"
DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "29-phase5-production-calibration.md"
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
SENTENCE_SPLIT = re.compile(r"[。！？!?\n]+")
ABSOLUTE_PATTERNS = (
    re.compile(r"(?<!不)一定會"),
    re.compile(r"(?<!不)肯定會"),
    re.compile(r"百分之百|命中註定|保證復合"),
)
SPECIFICITY_MARKERS = {
    "chart-positioning": ("安全感", "安心", "表達", "壓力", "需要", "回應", "反應", "親密關係"),
    "relationship-fit": (
        "吸引",
        "好感",
        "摩擦",
        "火花",
        "節奏",
        "互動",
        "相處",
        "調整",
        "情緒",
        "回應",
        "責任",
        "速度",
        "行動",
        "靠近",
        "信任",
    ),
    "core-answer": ("回覆", "互動", "行動", "反應", "對話", "關係", "訊息", "主動"),
    "timing-reading": ("目前", "現在", "時間", "時機", "聯絡", "日期", "時段", "氣氛", "界線", "回應"),
    "action-direction": ("訊息", "開口", "一步", "停", "不要", "做法", "下一步", "界線", "回覆", "互動", "對話"),
}
PAGE_RELEVANCE_MARKERS = {
    "chart-positioning": (
        "你需要",
        "你會",
        "你重視",
        "你希望",
        "你一旦",
        "你習慣",
        "你先",
        "你表達",
        "你傾向",
        "你說話",
        "你越",
        "對方",
        "他需要",
        "他有壓力",
        "他一",
        "他覺得",
        "他容易",
        "他可能",
        "他感到",
        "他會",
        "很多感受",
        "重要話題",
        "爭執",
        "事情碰到",
        "情緒",
        "安全感",
        "安心方式",
        "親密關係",
        "情感習慣",
    ),
    "relationship-fit": ("型", "吸引", "好感", "火花", "相處", "磨合"),
    "timing-reading": ("目前", "現在", "時間", "時機", "聯絡狀態"),
    "action-direction": ("下一步", "做法", "只做一件", "最容易踩到", "停"),
}
CORE_RELEVANCE_MARKERS = {
    "still-love-me": ("心意", "在意", "主動", "行動"),
    "any-chance": ("修復", "機會", "重新", "改變"),
    "when-to-contact": ("聯絡", "開口", "靠近", "界線"),
    "what-did-i-do-wrong": ("錯", "責任", "自責", "調整"),
    "stay-or-let-go": ("等待", "繼續", "放下", "投入"),
}
TOPIC_FORBIDDEN = {
    "chart-positioning": ("冷戰", "分手", "復合", "封鎖", "什麼時候聯絡"),
    "relationship-fit": ("冷戰", "分手", "復合", "封鎖", "現在適合聯絡", "指定日期"),
    "core-answer": ("2026 年", "2026年", "第 1 天", "第1天"),
    "timing-reading": ("你們比較像", "吸引的地方在於", "最容易吵架"),
    "action-direction": ("2026 年", "2026年", "關係氣氛比較柔和"),
}
MINIMUM_SCORE_AVERAGES = {
    "readability": 4.5,
    "specificity": 4.5,
    "relevance": 4.5,
    "emotionalSafety": 5.0,
    "topicOwnership": 5.0,
}
MINIMUM_DIFFERENTIATION_AVERAGES = {
    "chart-positioning": 4.0,
    "relationship-fit": 4.5,
    "core-answer": 4.5,
    "timing-reading": 4.0,
    "action-direction": 4.0,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def text_for_section(section: dict[str, Any]) -> str:
    return "\n".join(str(section.get(field) or "") for field in VISIBLE_FIELDS if section.get(field))


def body_for_section(section: dict[str, Any]) -> str:
    return str(section.get("body") or "")


def section_semantic_signature(case: dict[str, Any], section_id: str) -> str:
    fact_contract = case.get("finalFactContract") if isinstance(case.get("finalFactContract"), dict) else {}
    fact_sections = fact_contract.get("sections") if isinstance(fact_contract.get("sections"), dict) else {}
    fact_section = fact_sections.get(section_id) if isinstance(fact_sections.get(section_id), dict) else {}
    role_values = fact_section.get("roleValues") if isinstance(fact_section.get("roleValues"), dict) else {}
    if not role_values:
        return ""
    presentations = FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}
    output_owned_values = {
        role: values
        for role, values in role_values.items()
        if presentations.get(role) != "hidden-support"
    }
    return json.dumps(
        output_owned_values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def marker_hits(text: str, markers: tuple[str, ...] | list[str]) -> int:
    return sum(1 for marker in markers if marker and marker in text)


def core_answer_has_owned_answer(
    section: dict[str, Any],
    *,
    question: str,
    contact: str,
) -> bool:
    trace = core_answer_sentence_trace(str(section.get("meaning") or ""))
    return bool(
        trace
        and trace.get("kind") == "paragraph-composition"
        and trace.get("role") == "question"
        and trace.get("valueKey") == question
        and trace.get("contributorRole") == "contact-status"
        and trace.get("contributorValueKey") == contact
    )


def maximum_sentence_length(text: str) -> int:
    return max((len(item.strip()) for item in SENTENCE_SPLIT.split(text) if item.strip()), default=0)


def normalized_sentence(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def sentence_slot_repetition(cases: list[dict[str, Any]], contract: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {
        normalized_sentence(str(item))
        for item in contract.get("allowed_repeated_sentences") or []
        if str(item or "").strip()
    }
    counts: Counter[tuple[str, str, str]] = Counter()
    for case in cases:
        for section_id, section in (case.get("sections") or {}).items():
            if not isinstance(section, dict):
                continue
            for field in VISIBLE_FIELDS:
                seen: set[str] = set()
                for sentence in SENTENCE_SPLIT.split(str(section.get(field) or "")):
                    normalized = normalized_sentence(sentence)
                    if len(normalized) < 12 or normalized in allowed or normalized in seen:
                        continue
                    trace_error = native_semantic_trace_error(
                        case,
                        section_id=str(section_id),
                        field=field,
                        sentence=sentence.strip(),
                    )
                    if trace_error is None:
                        continue
                    seen.add(normalized)
                    counts[(str(section_id), field, normalized)] += 1
    threshold = max(15, int(len(cases) * 0.40))
    return [
        {
            "sectionId": section_id,
            "field": field,
            "sentence": sentence,
            "count": count,
            "coverage": round(count / len(cases), 3) if cases else 0.0,
        }
        for (section_id, field, sentence), count in counts.most_common()
        if count > threshold
    ]


def intra_page_repetition(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for case in cases:
        for section_id, section in (case.get("sections") or {}).items():
            if not isinstance(section, dict):
                continue
            for hit in intra_page_overlap_hits(section):
                failures.append({"caseId": case.get("id"), "sectionId": section_id, **hit})
    return failures


def score_band(value: int, *, high: int, medium: int) -> int:
    if value >= high:
        return 5
    if value >= medium:
        return 4
    if value > 0:
        return 3
    return 2


def score_pages(cases: list[dict[str, Any]], contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    body_counts: dict[str, Counter[str]] = {section_id: Counter() for section_id in SECTION_NARRATIVE_IDS}
    bodies: dict[str, list[tuple[str, str]]] = {section_id: [] for section_id in SECTION_NARRATIVE_IDS}
    case_signatures: dict[tuple[str, str], str] = {}
    output_signatures: dict[str, dict[str, set[str]]] = {
        section_id: defaultdict(set) for section_id in SECTION_NARRATIVE_IDS
    }
    signature_outputs: dict[str, dict[str, set[str]]] = {
        section_id: defaultdict(set) for section_id in SECTION_NARRATIVE_IDS
    }
    for case in cases:
        case_id = str(case.get("id") or "")
        for section_id in SECTION_NARRATIVE_IDS:
            section = (case.get("sections") or {}).get(section_id) or {}
            visible = text_for_section(section)
            signature = section_semantic_signature(case, section_id)
            body_counts[section_id][visible] += 1
            bodies[section_id].append((case_id, visible))
            case_signatures[(section_id, case_id)] = signature
            output_signatures[section_id][visible].add(signature)
            signature_outputs[section_id][signature].add(visible)

    closest_similarity: dict[tuple[str, str], float] = {}
    for section_id, items in bodies.items():
        for left_index, (left_id, left_text) in enumerate(items):
            closest = 0.0
            for right_id, right_text in items[left_index + 1 :]:
                similarity = jaccard_similarity(left_text, right_text)
                closest_similarity[(section_id, left_id)] = max(closest_similarity.get((section_id, left_id), 0.0), similarity)
                closest_similarity[(section_id, right_id)] = max(closest_similarity.get((section_id, right_id), 0.0), similarity)
                closest = max(closest, similarity)

    technical_terms = [str(item) for item in contract.get("technical_terms") or [] if item]
    results: list[dict[str, Any]] = []
    dimension_totals: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for case in cases:
        context = case.get("context") or {}
        question = str(context.get("main_question") or "")
        contact = str(context.get("contact_status") or "")
        for section_id in SECTION_NARRATIVE_IDS:
            section = (case.get("sections") or {}).get(section_id) or {}
            text = text_for_section(section)
            body = body_for_section(section)
            technical_hits = [term for term in technical_terms if term and term in text]
            meta_hits = reader_meta_narration_hits(text)
            readability = 5 if maximum_sentence_length(text) <= 150 and not technical_hits else 4 if maximum_sentence_length(text) <= 190 and not technical_hits else 2
            specificity = score_band(marker_hits(text, SPECIFICITY_MARKERS[section_id]), high=3, medium=2)
            if section_id == "core-answer":
                relevance_markers = list(((contract.get("question_expectations") or {}).get(question) or {}).get("required_any") or [])
                relevance_markers.extend(CORE_RELEVANCE_MARKERS.get(question) or ())
            else:
                relevance_markers = list(PAGE_RELEVANCE_MARKERS.get(section_id) or ())
            if section_id in {"timing-reading", "action-direction"}:
                relevance_markers.extend(((contract.get("contact_expectations") or {}).get(contact) or []))
            if section_id == "core-answer" and core_answer_has_owned_answer(
                section,
                question=question,
                contact=contact,
            ):
                relevance = 5
            else:
                relevance = score_band(
                    marker_hits(text, relevance_markers),
                    high=2,
                    medium=1,
                )
            unsafe = [pattern.pattern for pattern in ABSOLUTE_PATTERNS if pattern.search(text)]
            if contact == "blocked" and section_id in {"timing-reading", "action-direction"}:
                has_boundary = marker_hits(
                    text,
                    ("界線", "先不要", "不突破", "封鎖", "聯絡方式", "不要主動聯絡", "不要換"),
                ) > 0
            else:
                has_boundary = True
            safety = 5 if not unsafe and has_boundary else 1
            topic_hits = [term for term in TOPIC_FORBIDDEN[section_id] if term in body]
            ownership = 5 if not topic_hits else 2
            repeat_count = body_counts[section_id][text]
            closest = closest_similarity.get((section_id, str(case.get("id") or "")), 0.0)
            signature = case_signatures.get((section_id, str(case.get("id") or "")), "")
            semantic_collapse_width = len(output_signatures[section_id].get(text) or ())
            semantic_output_variants = len(signature_outputs[section_id].get(signature) or ())
            # Page catalogs intentionally share grammar. Differentiation is a
            # one-to-one semantic contract; lexical similarity stays diagnostic.
            if signature and semantic_collapse_width == 1 and semantic_output_variants == 1:
                differentiation = 5
            elif signature and semantic_collapse_width <= 2 and semantic_output_variants <= 2:
                differentiation = 4
            elif signature:
                differentiation = 3
            else:
                differentiation = 2
            scores = {
                "readability": readability,
                "specificity": specificity,
                "relevance": relevance,
                "emotionalSafety": safety,
                "topicOwnership": ownership,
                "differentiation": differentiation,
            }
            for dimension, score in scores.items():
                dimension_totals[section_id][dimension].append(score)
            results.append(
                {
                    "caseId": case.get("id"),
                    "sectionId": section_id,
                    "scores": scores,
                    "average": round(sum(scores.values()) / len(scores), 2),
                    "technicalHits": technical_hits,
                    "readerMetaHits": meta_hits,
                    "unsafeHits": unsafe,
                    "topicHits": topic_hits,
                    "maxSentenceLength": maximum_sentence_length(text),
                    "exactBodyRepeat": repeat_count,
                    "closestBodySimilarity": round(closest, 3),
                    "semanticSignature": signature,
                    "semanticCollapseWidth": semantic_collapse_width,
                    "semanticOutputVariants": semantic_output_variants,
                }
            )
    averages = {
        section_id: {
            dimension: round(sum(values) / len(values), 2) if values else 0.0
            for dimension, values in dimensions.items()
        }
        for section_id, dimensions in dimension_totals.items()
    }
    return results, averages


def evaluate(corpus: dict[str, Any], review_manifest: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    matrix_cases = [item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)]
    comparison_cases = [item for item in corpus.get("comparisonCases") or [] if isinstance(item, dict)]
    all_cases = {str(item.get("id") or ""): item for item in [*matrix_cases, *comparison_cases]}
    if corpus.get("version") != CORPUS_VERSION:
        failures.append("corpus version mismatch")
    if corpus.get("sectionSpecVersion") != SECTION_NARRATIVE_SPEC_VERSION:
        failures.append("section spec version is stale")
    if corpus.get("rendererVersion") != SECTION_NARRATIVE_RENDERER_VERSION:
        failures.append("renderer version is stale")
    if corpus.get("factContractVersion") != FINAL_NARRATIVE_FACT_CONTRACT_VERSION:
        failures.append("final narrative fact contract version is stale")
    if corpus.get("factRendererMode") != FINAL_NARRATIVE_FACT_RENDERER_MODE:
        failures.append("final narrative fact renderer mode is stale")
    if corpus.get("semanticCoverageVersion") != FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION:
        failures.append("final narrative semantic coverage version is stale")
    if corpus.get("compositionVersion") != FINAL_NARRATIVE_COMPOSITION_VERSION:
        failures.append("final narrative composition version is stale")
    if corpus.get("paragraphPlanVersion") != FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION:
        failures.append("final narrative paragraph-plan version is stale")
    if corpus.get("composerVersion") != FINAL_NARRATIVE_COMPOSER_VERSION:
        failures.append("composer version is stale")
    if corpus.get("hardQualityVersion") != FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION:
        failures.append("final narrative R6 hard-quality version is stale")
    if corpus.get("hardQualityContractFingerprint") != hard_quality_contract_fingerprint():
        failures.append("final narrative R6 hard-quality fingerprint is stale")
    if corpus.get("runtimeSourceHashes") != runtime_source_hashes():
        failures.append("runtime source hashes are stale; rebuild the Phase 5 corpus")
    if len(matrix_cases) != MATRIX_CASE_COUNT:
        failures.append(f"matrix case count is {len(matrix_cases)}, expected {MATRIX_CASE_COUNT}")
    expected_combos = set(itertools.product(STAGE_ORDER, QUESTIONS, CONTACTS))
    actual_combos = {
        (
            str((item.get("context") or {}).get("relationship_stage") or ""),
            str((item.get("context") or {}).get("main_question") or ""),
            str((item.get("context") or {}).get("contact_status") or ""),
        )
        for item in matrix_cases
    }
    if actual_combos != expected_combos:
        failures.append(f"context matrix mismatch: missing={len(expected_combos - actual_combos)} extra={len(actual_combos - expected_combos)}")
    chart_count = len({str((item.get("fingerprints") or {}).get("chart") or "") for item in matrix_cases})
    pair_count = len({str((item.get("fingerprints") or {}).get("pair") or "") for item in matrix_cases})
    if chart_count != MATRIX_CASE_COUNT or pair_count != MATRIX_CASE_COUNT:
        failures.append(f"holdout charts are not unique: pairs={pair_count}, charts={chart_count}")
    if len({str((item.get("fingerprints") or {}).get("visible") or "") for item in matrix_cases}) != MATRIX_CASE_COUNT:
        failures.append("different holdout inputs collapsed to identical full visible outputs")

    for case in [*matrix_cases, *comparison_cases]:
        case_id = str(case.get("id") or "unknown")
        contracts = case.get("sectionContracts") or {}
        if contracts.get("version") != SECTION_NARRATIVE_SPEC_VERSION or contracts.get("validationStatus") != "valid":
            failures.append(f"{case_id}: invalid section contract")
        for section_id in SECTION_NARRATIVE_IDS:
            section = (case.get("sections") or {}).get(section_id) or {}
            if not section.get("headline") or not section.get("body"):
                failures.append(f"{case_id}:{section_id}: visible copy missing")
        fact_contract = case.get("finalFactContract") if isinstance(case.get("finalFactContract"), dict) else {}
        if fact_contract.get("version") != FINAL_NARRATIVE_FACT_CONTRACT_VERSION:
            failures.append(f"{case_id}: final fact contract version missing")
        if fact_contract.get("rendererMode") != FINAL_NARRATIVE_FACT_RENDERER_MODE:
            failures.append(f"{case_id}: final fact renderer mode missing")
        if fact_contract.get("semanticCoverageVersion") != FINAL_NARRATIVE_SEMANTIC_COVERAGE_VERSION:
            failures.append(f"{case_id}: final semantic coverage version missing")
        if fact_contract.get("validationStatus") != "valid":
            failures.append(f"{case_id}: final fact contract invalid")
        fact_sections = fact_contract.get("sections") if isinstance(fact_contract.get("sections"), dict) else {}
        for section_id in SECTION_NARRATIVE_IDS:
            fact_section = fact_sections.get(section_id) if isinstance(fact_sections.get(section_id), dict) else {}
            if int(fact_section.get("factCount") or 0) <= 0:
                failures.append(f"{case_id}:{section_id}: final facts missing")
            if not fact_section.get("sourceSpecFingerprint"):
                failures.append(f"{case_id}:{section_id}: final fact source fingerprint missing")
            role_values = fact_section.get("roleValues") if isinstance(fact_section.get("roleValues"), dict) else {}
            unknown_roles = set(role_values) - set(FINAL_NARRATIVE_ROLE_DISPOSITIONS[section_id])
            if unknown_roles:
                failures.append(f"{case_id}:{section_id}: unregistered semantic roles: {sorted(unknown_roles)}")

    comparison_results: list[dict[str, Any]] = []
    for comparison in corpus.get("controlledComparisons") or []:
        left = all_cases.get(str(comparison.get("leftId") or "")) or {}
        right = all_cases.get(str(comparison.get("rightId") or "")) or {}
        errors: list[str] = []
        if not left or not right:
            errors.append("case missing")
        for section_id in comparison.get("stableSections") or []:
            if (left.get("sections") or {}).get(section_id) != (right.get("sections") or {}).get(section_id):
                errors.append(f"{section_id} changed but must remain stable")
        for section_id in comparison.get("expectedChangedSections") or []:
            if (left.get("sections") or {}).get(section_id) == (right.get("sections") or {}).get(section_id):
                errors.append(f"{section_id} did not change")
        comparison_type = str(comparison.get("type") or "")
        same_chart = (left.get("fingerprints") or {}).get("chart") == (right.get("fingerprints") or {}).get("chart")
        if comparison_type == "chart-change" and same_chart:
            errors.append("chart-change pair reused the same chart")
        if comparison_type != "chart-change" and not same_chart:
            errors.append("context-only pair changed chart")
        if errors:
            failures.append(f"{comparison.get('id')}: {', '.join(errors)}")
        comparison_results.append({"id": comparison.get("id"), "type": comparison_type, "passed": not errors, "errors": errors})

    scores, score_averages = score_pages(matrix_cases, contract)
    repeated_sentence_slots = sentence_slot_repetition(matrix_cases, contract)
    intra_page_repetitions = intra_page_repetition(matrix_cases)
    technical_leaks = [item for item in scores if item.get("technicalHits")]
    reader_meta_leaks = [item for item in scores if item.get("readerMetaHits")]
    safety_failures = [item for item in scores if item.get("scores", {}).get("emotionalSafety", 0) < 5]
    ownership_failures = [item for item in scores if item.get("scores", {}).get("topicOwnership", 0) < 5]
    semantic_collapses = [item for item in scores if int(item.get("semanticCollapseWidth") or 0) > 1]
    semantic_splits = [item for item in scores if int(item.get("semanticOutputVariants") or 0) > 1]
    if technical_leaks:
        failures.append(f"technical copy leaked in {len(technical_leaks)} page(s)")
    if reader_meta_leaks:
        failures.append(f"reader-facing page narration leaked in {len(reader_meta_leaks)} page(s)")
    if safety_failures:
        failures.append(f"emotional safety failed in {len(safety_failures)} page(s)")
    if ownership_failures:
        failures.append(f"page-topic ownership failed in {len(ownership_failures)} page(s)")
    if semantic_collapses:
        failures.append(f"different semantic fact bundles collapsed in {len(semantic_collapses)} page case(s)")
    if semantic_splits:
        failures.append(f"identical semantic fact bundles produced multiple outputs in {len(semantic_splits)} page case(s)")
    if repeated_sentence_slots:
        failures.append(f"sentence-slot repetition exceeded 40% coverage in {len(repeated_sentence_slots)} slot(s)")
    if intra_page_repetitions:
        failures.append(f"intra-page copy repetition found in {len(intra_page_repetitions)} field pair(s)")
    low_automated_scores = [item for item in scores if float(item.get("average") or 0) < 3.5]
    if low_automated_scores:
        failures.append(f"automated page score below 3.5 in {len(low_automated_scores)} page(s)")
    for section_id, averages in score_averages.items():
        for dimension, minimum in MINIMUM_SCORE_AVERAGES.items():
            if float(averages.get(dimension) or 0) < minimum:
                failures.append(f"{section_id} {dimension} average below {minimum}")
        differentiation_minimum = MINIMUM_DIFFERENTIATION_AVERAGES[section_id]
        if float(averages.get("differentiation") or 0) < differentiation_minimum:
            failures.append(f"{section_id} differentiation average below {differentiation_minimum}")

    archetype_counts = Counter(str((item.get("hiddenModel") or {}).get("archetypeTitle") or "") for item in matrix_cases)
    primary_counts = Counter(str((item.get("hiddenModel") or {}).get("primaryDynamicKey") or "") for item in matrix_cases)
    if len(archetype_counts) < 6:
        failures.append(f"archetype coverage too thin: {len(archetype_counts)}")
    if archetype_counts and archetype_counts.most_common(1)[0][1] / len(matrix_cases) > 0.40:
        failures.append("one archetype exceeds 40% of holdout cases")
    if len(primary_counts) < 5:
        failures.append(f"primary dynamic coverage too thin: {len(primary_counts)}")
    if primary_counts and primary_counts.most_common(1)[0][1] / len(matrix_cases) > 0.60:
        failures.append("one primary dynamic exceeds 60% of holdout cases")

    review_cases = [item for item in review_manifest.get("cases") or [] if isinstance(item, dict)]
    if review_manifest.get("version") != REVIEW_VERSION or len(review_cases) != 40:
        failures.append("human review manifest is missing or incomplete")
    if review_manifest.get("corpusVersion") != CORPUS_VERSION:
        failures.append("human review corpus version is stale")
    if review_manifest.get("corpusFingerprint") != corpus.get("corpusFingerprint"):
        failures.append("human review manifest is stale")
    if review_manifest.get("compositionVersion") != FINAL_NARRATIVE_COMPOSITION_VERSION:
        failures.append("human review composition version is stale")
    if review_manifest.get("paragraphPlanVersion") != FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION:
        failures.append("human review paragraph-plan version is stale")
    if review_manifest.get("hardQualityVersion") != FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION:
        failures.append("human review R6 hard-quality version is stale")
    if review_manifest.get("hardQualityContractFingerprint") != hard_quality_contract_fingerprint():
        failures.append("human review R6 hard-quality fingerprint is stale")
    if tuple(review_manifest.get("dimensions") or ()) != REVIEW_DIMENSIONS:
        failures.append("human review dimensions do not match the current review contract")
    selected_contexts = [item.get("context") or {} for item in review_cases]
    for key, expected in (
        ("relationship_stage", STAGE_ORDER),
        ("main_question", QUESTIONS),
        ("contact_status", CONTACTS),
    ):
        actual = {str(item.get(key) or "") for item in selected_contexts}
        if actual != set(expected):
            failures.append(f"human review selection misses {key} coverage")

    return {
        "passed": not failures,
        "gateScope": "structural-only",
        "failures": failures,
        "matrixCaseCount": len(matrix_cases),
        "comparisonCaseCount": len(comparison_cases),
        "uniqueChartCount": chart_count,
        "uniqueVisibleCount": len({str((item.get("fingerprints") or {}).get("visible") or "") for item in matrix_cases}),
        "archetypeCounts": dict(archetype_counts),
        "primaryDynamicCounts": dict(primary_counts),
        "comparisonResults": comparison_results,
        "scoreAverages": score_averages,
        "lowAutomatedScores": sorted(scores, key=lambda item: float(item.get("average") or 0))[:20],
        "technicalLeakCount": len(technical_leaks),
        "readerMetaLeakCount": len(reader_meta_leaks),
        "safetyFailureCount": len(safety_failures),
        "ownershipFailureCount": len(ownership_failures),
        "semanticCollapseCount": len(semantic_collapses),
        "semanticSplitCount": len(semantic_splits),
        "unknownFactCount": sum(
            len(((item.get("finalFactContract") or {}).get("sections") or {}).get(section_id, {}).get("unknownFactIds") or [])
            for item in matrix_cases
            for section_id in SECTION_NARRATIVE_IDS
        ),
        "compatibilityProseSlotCount": sum(
            len(((item.get("finalFactContract") or {}).get("sections") or {}).get(section_id, {}).get("compatibilityProseSlots") or [])
            for item in matrix_cases
            for section_id in SECTION_NARRATIVE_IDS
        ),
        "repeatedSentenceSlots": repeated_sentence_slots,
        "intraPageRepetitions": intra_page_repetitions,
        "humanReview": {
            "selected": len(review_cases),
            "requiredAccepted": int(review_manifest.get("requiredAcceptedCount") or 0),
            "completed": sum(1 for item in review_cases if item.get("status") != "pending"),
            "status": "PENDING" if any(item.get("status") == "pending" for item in review_cases) else "COMPLETE",
        },
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows)
    return lines


def render_report(result: dict[str, Any], corpus: dict[str, Any]) -> str:
    score_rows = []
    for section_id in SECTION_NARRATIVE_IDS:
        dimensions = result.get("scoreAverages", {}).get(section_id) or {}
        score_rows.append([section_id, *[f"{float(dimensions.get(key) or 0):.2f}" for key in ("readability", "specificity", "relevance", "emotionalSafety", "topicOwnership", "differentiation")]])
    comparison_counts = Counter(str(item.get("type") or "") for item in result.get("comparisonResults") or [] if item.get("passed"))
    lines = [
        "# Phase 5 Structural Calibration Report",
        "",
        "> Generated by `scripts/test_reading_phase5_calibration.py`. This structural gate checks corpus integrity, section ownership, controlled input changes, and basic copy constraints. It does not establish reader-copy production acceptance.",
        "",
        "## Summary",
        "",
        f"- Automated structural status: {'PASS' if result.get('passed') else 'FAIL'}",
        "- Reader-copy production acceptance: NOT EVALUATED BY THIS GATE",
        f"- Human acceptance status: {result.get('humanReview', {}).get('status')}",
        f"- Matrix cases: {result.get('matrixCaseCount')} / {MATRIX_CASE_COUNT}",
        f"- Unique charts: {result.get('uniqueChartCount')}",
        f"- Unique full visible outputs: {result.get('uniqueVisibleCount')}",
        f"- Controlled comparison variants: {result.get('comparisonCaseCount')}",
        f"- Technical leaks: {result.get('technicalLeakCount')}",
        f"- Reader-facing page narration leaks: {result.get('readerMetaLeakCount')}",
        f"- Safety failures: {result.get('safetyFailureCount')}",
        f"- Page ownership failures: {result.get('ownershipFailureCount')}",
        f"- Semantic output collapses: {result.get('semanticCollapseCount')}",
        f"- Semantic output splits: {result.get('semanticSplitCount')}",
        f"- Unknown typed facts: {result.get('unknownFactCount')}",
        f"- Legacy prose compatibility slots: {result.get('compatibilityProseSlotCount')}",
        f"- Sentence-slot repetition failures: {len(result.get('repeatedSentenceSlots') or [])}",
        f"- Intra-page repetition failures: {len(result.get('intraPageRepetitions') or [])}",
        "",
        "## Automated Page Scores",
        "",
        *markdown_table(
            ["Section", "Readability", "Specificity", "Relevance", "Safety", "Ownership", "Differentiation"],
            score_rows,
        ),
        "",
        "## Controlled Comparisons",
        "",
        *markdown_table(["Change type", "Passing pairs"], [[key, value] for key, value in sorted(comparison_counts.items())]),
        "",
        "## Distribution",
        "",
        "### Relationship Types",
        "",
        *markdown_table(["Type", "Cases"], [[key, value] for key, value in sorted((result.get("archetypeCounts") or {}).items())]),
        "",
        "### Primary Dynamics",
        "",
        *markdown_table(["Dynamic", "Cases"], [[key, value] for key, value in sorted((result.get("primaryDynamicCounts") or {}).items())]),
        "",
        "## Human Acceptance",
        "",
        f"- Review queue: {result.get('humanReview', {}).get('selected')} cases",
        f"- Required accepted cases: {result.get('humanReview', {}).get('requiredAccepted')}",
        f"- Completed reviews: {result.get('humanReview', {}).get('completed')}",
        "- Review scores must be supplied by a person; automated checks never fabricate acceptance ratings.",
        "- Timing cases use a real 56-day scan sampled every 7 days, so timing differentiation is held to the same production standard as the other pages.",
        "",
        "## Failures",
        "",
    ]
    failures = result.get("failures") or []
    lines.extend([f"- {item}" for item in failures] or ["- None."])
    lines.extend(["", "## Repeated Sentence Slots", ""])
    lines.extend(
        markdown_table(
            ["Section", "Field", "Cases", "Coverage", "Sentence"],
            [
                [item.get("sectionId"), item.get("field"), item.get("count"), item.get("coverage"), item.get("sentence")]
                for item in result.get("repeatedSentenceSlots") or []
            ],
        )
        if result.get("repeatedSentenceSlots")
        else ["- None."]
    )
    lines.extend(["", "## Intra-Page Repetition", ""])
    lines.extend(
        markdown_table(
            ["Case", "Section", "Fields", "Coverage", "Repeated phrase"],
            [
                [
                    item.get("caseId"),
                    item.get("sectionId"),
                    f"{item.get('leftField')} / {item.get('rightField')}",
                    item.get("shorterFieldCoverage"),
                    item.get("phrase"),
                ]
                for item in result.get("intraPageRepetitions") or []
            ],
        )
        if result.get("intraPageRepetitions")
        else ["- None."]
    )
    lines.extend(["", "## Lowest Automated Page Scores", ""])
    lines.extend(
        markdown_table(
            ["Case", "Section", "Average", "Exact repeat", "Closest similarity"],
            [
                [item.get("caseId"), item.get("sectionId"), item.get("average"), item.get("exactBodyRepeat"), item.get("closestBodySimilarity")]
                for item in result.get("lowAutomatedScores") or []
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Contract",
            "",
            f"- Corpus: `{corpus.get('version')}`",
            f"- Section spec: `{corpus.get('sectionSpecVersion')}`",
            f"- Renderer: `{corpus.get('rendererVersion')}`",
            f"- Final fact contract: `{corpus.get('factContractVersion')}`",
            f"- Fact renderer mode: `{corpus.get('factRendererMode')}`",
            f"- Composition: `{corpus.get('compositionVersion')}`",
            f"- Composer: `{corpus.get('composerVersion')}`",
            "- This structural gate can pass while copy-quality and human acceptance remain incomplete. Production release requires all three gates.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 5 production calibration.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_PATH)
    parser.add_argument("--contract-dir", type=Path, default=DEFAULT_CONTRACT_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    corpus = load_json(args.corpus)
    review_manifest = load_json(args.review_manifest)
    contract = load_quality_contract(args.contract_dir)
    result = evaluate(corpus, review_manifest, contract)
    if not args.no_write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_report(result, corpus), encoding="utf-8")
        print(f"Wrote {display_path(args.out)}")
    print(f"Phase 5 structural calibration: {'PASS' if result['passed'] else 'FAIL'}")
    print(f"Matrix cases: {result['matrixCaseCount']}")
    print(f"Controlled comparisons: {result['comparisonCaseCount']}")
    print(f"Human acceptance: {result['humanReview']['status']}")
    for failure in result.get("failures") or []:
        print(f"- {failure}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
