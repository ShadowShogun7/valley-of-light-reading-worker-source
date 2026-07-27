#!/usr/bin/env python3
"""Product-level quality engine for paid relationship result readings."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_relationship_fit_semantic_similarity import jaccard_similarity  # noqa: E402
from audit_relationship_result_variation import GENERATED_SCENARIOS_PATH  # noqa: E402
from readable_interpretation.copy_contract import intra_page_overlap_hits, reader_meta_narration_hits  # noqa: E402
from readable_interpretation.final_narrative_pages.action_direction_renderer import action_sentence_trace  # noqa: E402
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import chart_sentence_trace  # noqa: E402
from readable_interpretation.final_narrative_pages.core_answer_renderer import core_answer_sentence_trace  # noqa: E402
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import relationship_fit_sentence_trace  # noqa: E402
from readable_interpretation.final_narrative_pages.timing_renderer import timing_sentence_trace  # noqa: E402
from visible_reading_depth import READING_PATHS, build_view_models  # noqa: E402


DEFAULT_CASE_DIR = ROOT / "data" / "reading-quality-cases"
DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "28-reading-quality-engine-report.md"
SECTION_IDS = ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction")
READABLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution", "stuckPattern")
SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？!?；;\n]+")
NEAR_DUPLICATE_PREVIEW_LIMIT = 8

SENTENCE_TRACERS = {
    "chart-positioning": chart_sentence_trace,
    "relationship-fit": relationship_fit_sentence_trace,
    "core-answer": core_answer_sentence_trace,
    "timing-reading": timing_sentence_trace,
    "action-direction": action_sentence_trace,
}


@dataclass(frozen=True)
class QualityCase:
    source: str
    id: str
    question: str
    stage: str
    contact: str
    primary_dynamic: str
    secondary_dynamics: tuple[str, ...]
    section_texts: dict[str, str]
    section_fields: dict[str, dict[str, str]]
    section_content_texts: dict[str, str]
    full_text: str
    fit_body: str
    semantic_identity: str
    section_semantic_identities: dict[str, str]
    section_dynamic_keys: dict[str, str]


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    category: str
    case_id: str
    source: str
    message: str


@dataclass(frozen=True)
class SimilarityIssue:
    source: str
    left_id: str
    right_id: str
    score: float
    category: str
    left_text: str
    right_text: str


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def short_hash(value: str) -> str:
    return hashlib.sha1(normalize_text(value).encode("utf-8")).hexdigest()[:10]


def semantic_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:12]


def markdown_cell(value: Any, limit: int = 96) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip()).replace("|", "\\|")
    return text[:limit]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def load_quality_contract(case_dir: Path) -> dict[str, Any]:
    paths = sorted(path for path in case_dir.glob("*.json") if path.is_file())
    if not paths:
        raise FileNotFoundError(f"No reading-quality case contract found under {case_dir}")
    merged: dict[str, Any] = {
        "datasets": {},
        "thresholds": {},
        "allowed_repeated_sentences": [],
        "technical_terms": [],
        "generic_repair_phrases": [],
        "concrete_behavior_markers": [],
        "question_expectations": {},
        "stage_expectations": {},
        "contact_expectations": {},
        "dynamic_markers": {},
    }
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            elif isinstance(value, list) and isinstance(merged.get(key), list):
                merged[key].extend(str(item) for item in value)
            else:
                merged[key] = value
    for key in ("allowed_repeated_sentences", "technical_terms", "generic_repair_phrases", "concrete_behavior_markers"):
        merged[key] = list(dict.fromkeys(as_str_list(merged.get(key))))
    return merged


def visible_section_text(section: dict[str, Any] | None) -> str:
    if not isinstance(section, dict):
        return ""
    return "\n".join(str(section.get(field) or "") for field in READABLE_FIELDS if section.get(field))


def final_sections(view_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    final = view_model.get("finalInterpretation") if isinstance(view_model.get("finalInterpretation"), dict) else {}
    sections = final.get("sections") if isinstance(final.get("sections"), dict) else {}
    return {section_id: sections.get(section_id) or {} for section_id in SECTION_IDS}


def narrative_specs(view_model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bundle = view_model.get("sectionNarrativeSpecs") if isinstance(view_model.get("sectionNarrativeSpecs"), dict) else {}
    sections = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    return {section_id: sections.get(section_id) or {} for section_id in SECTION_IDS}


def semantic_identity_for_spec(spec: dict[str, Any]) -> str:
    return semantic_hash(
        {
            "context": spec.get("context") or {},
            "semanticSlots": spec.get("semanticSlots") or {},
            "conceptKeys": spec.get("conceptKeys") or [],
        }
    )


def context_from_view_model(view_model: dict[str, Any]) -> tuple[str, str, str]:
    context = view_model.get("context") if isinstance(view_model.get("context"), dict) else {}
    return (
        str(context.get("main_question") or ""),
        str(context.get("relationship_stage") or ""),
        str(context.get("contact_status") or ""),
    )


def primary_dynamic_from_view_model(view_model: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    model = view_model.get("relationshipCaseModel") if isinstance(view_model.get("relationshipCaseModel"), dict) else {}
    primary = model.get("primaryDynamic") if isinstance(model.get("primaryDynamic"), dict) else {}
    secondaries = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    return (
        str(primary.get("key") or ""),
        tuple(str(item.get("key") or "") for item in secondaries if item.get("key")),
    )


def quality_case_from_view_model(source: str, view_model: dict[str, Any]) -> QualityCase:
    question, stage, contact = context_from_view_model(view_model)
    primary_dynamic, secondary_dynamics = primary_dynamic_from_view_model(view_model)
    sections = final_sections(view_model)
    specs = narrative_specs(view_model)
    section_texts = {section_id: visible_section_text(section) for section_id, section in sections.items()}
    section_fields = {
        section_id: {field: str(section.get(field) or "") for field in READABLE_FIELDS}
        for section_id, section in sections.items()
    }
    section_content_texts = {
        section_id: "\n".join(
            str(section.get(field) or "")
            for field in READABLE_FIELDS
            if section.get(field)
        )
        for section_id, section in sections.items()
    }
    section_semantic_identities = {
        section_id: semantic_identity_for_spec(spec)
        for section_id, spec in specs.items()
    }
    section_slots = {
        section_id: spec.get("semanticSlots") if isinstance(spec.get("semanticSlots"), dict) else {}
        for section_id, spec in specs.items()
    }
    section_dynamic_keys = {
        "relationship-fit": str(section_slots["relationship-fit"].get("primaryDynamicKey") or ""),
        "core-answer": str(section_slots["core-answer"].get("centralDynamicKey") or primary_dynamic),
        "action-direction": str(section_slots["action-direction"].get("repairLeverKey") or ""),
    }
    full_text = "\n".join(section_texts[section_id] for section_id in SECTION_IDS if section_texts.get(section_id))
    fit_body = str((sections.get("relationship-fit") or {}).get("body") or "")
    return QualityCase(
        source=source,
        id=str(view_model.get("id") or "unknown"),
        question=question,
        stage=stage,
        contact=contact,
        primary_dynamic=primary_dynamic,
        secondary_dynamics=secondary_dynamics,
        section_texts=section_texts,
        section_fields=section_fields,
        section_content_texts=section_content_texts,
        full_text=full_text,
        fit_body=fit_body,
        semantic_identity=semantic_hash(section_semantic_identities),
        section_semantic_identities=section_semantic_identities,
        section_dynamic_keys=section_dynamic_keys,
    )


def load_generated_cases(path: Path) -> list[QualityCase]:
    scenarios = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(scenarios, list):
        raise ValueError(f"{path} must contain a list of generated scenarios")
    return [quality_case_from_view_model("generated-fixture", item) for item in scenarios if isinstance(item, dict)]


def load_raw_cases() -> list[QualityCase]:
    return [quality_case_from_view_model("raw-reading", item) for item in build_view_models(READING_PATHS)]


def split_sentences(text: str) -> list[str]:
    output: list[str] = []
    for part in SENTENCE_SPLIT_PATTERN.split(text or ""):
        normalized = normalize_text(part)
        if normalized:
            output.append(normalized)
    return output


def contains_any(text: str, markers: Iterable[str]) -> int:
    return sum(1 for marker in markers if marker and marker in text)


def selected_sections_text(case: QualityCase, section_ids: Iterable[str]) -> str:
    return "\n".join(case.section_texts.get(section_id, "") for section_id in section_ids)


def strict_source(case: QualityCase, contract: dict[str, Any]) -> bool:
    dataset = (contract.get("datasets") or {}).get(case.source) or {}
    return bool(dataset.get("strict"))


def issue_for_case(
    case: QualityCase,
    contract: dict[str, Any],
    category: str,
    message: str,
    *,
    strict_only: bool = True,
) -> QualityIssue:
    severity = "failure" if (not strict_only or strict_source(case, contract)) else "warning"
    return QualityIssue(severity=severity, category=category, case_id=case.id, source=case.source, message=message)


def marker_watch_issue(case: QualityCase, category: str, message: str) -> QualityIssue:
    """Keep legacy keyword misses visible without overriding typed semantic gates."""
    return QualityIssue(
        severity="warning",
        category=category,
        case_id=case.id,
        source=case.source,
        message=message,
    )


def evaluate_case_markers(case: QualityCase, contract: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    thresholds = contract.get("thresholds") or {}
    min_question_hits = int(thresholds.get("min_question_marker_hits") or 1)
    min_stage_hits = int(thresholds.get("min_stage_marker_hits") or 1)
    min_contact_hits = int(thresholds.get("min_contact_marker_hits") or 1)

    question_expectations = contract.get("question_expectations") or {}
    question_spec = question_expectations.get(case.question) or {}
    question_sections = question_spec.get("sections") or SECTION_IDS
    question_text = selected_sections_text(case, question_sections)
    question_hits = contains_any(question_text, as_str_list(question_spec.get("required_any")))
    if question_spec and question_hits < min_question_hits:
        issues.append(
            marker_watch_issue(
                case,
                "question-fit",
                f"{case.question} has {question_hits} question marker hit(s); expected at least {min_question_hits}.",
            )
        )

    stage_markers = as_str_list((contract.get("stage_expectations") or {}).get(case.stage))
    stage_hits = contains_any(case.full_text, stage_markers)
    if stage_markers and stage_hits < min_stage_hits:
        issues.append(
            marker_watch_issue(
                case,
                "stage-fit",
                f"{case.stage} has {stage_hits} stage marker hit(s); expected at least {min_stage_hits}.",
            )
        )

    contact_markers = as_str_list((contract.get("contact_expectations") or {}).get(case.contact))
    contact_hits = contains_any(case.full_text, contact_markers)
    if contact_markers and contact_hits < min_contact_hits:
        issues.append(
            marker_watch_issue(
                case,
                "contact-fit",
                f"{case.contact} has {contact_hits} contact marker hit(s); expected at least {min_contact_hits}.",
            )
        )
    return issues


def evaluate_narrative_angle(case: QualityCase, contract: dict[str, Any]) -> list[QualityIssue]:
    dynamic_markers = contract.get("dynamic_markers") or {}
    thresholds = contract.get("thresholds") or {}
    min_hits = int(thresholds.get("min_section_dynamic_marker_hits") or 1)
    issues: list[QualityIssue] = []
    for section_id in ("relationship-fit", "core-answer", "action-direction"):
        if section_id == "action-direction" and case.contact == "blocked":
            continue
        dynamic_key = case.section_dynamic_keys.get(section_id, "")
        if not dynamic_key or dynamic_key in {"unknown", "none", "fallback", "standard-boundary"}:
            continue
        if dynamic_key not in dynamic_markers:
            issues.append(
                issue_for_case(
                    case,
                    contract,
                    "narrative-angle",
                    f"{section_id} dynamic `{dynamic_key}` has no marker contract.",
                    strict_only=False,
                )
            )
            continue
        text = case.section_texts.get(section_id, "")
        primary_hits = contains_any(text, as_str_list(dynamic_markers.get(dynamic_key)))
        if primary_hits < min_hits:
            issues.append(
                marker_watch_issue(
                    case,
                    "narrative-angle",
                    f"{section_id} dynamic `{dynamic_key}` has {primary_hits} marker hit(s); expected at least {min_hits}.",
                )
            )
    return issues


def evaluate_readability(case: QualityCase, contract: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    thresholds = contract.get("thresholds") or {}
    max_fail = int(thresholds.get("max_sentence_chars_fail") or 190)
    max_warn = int(thresholds.get("max_sentence_chars_warn") or 150)
    for term in as_str_list(contract.get("technical_terms")):
        if term and term in case.full_text:
            issues.append(issue_for_case(case, contract, "technical-copy", f"Technical term leaked: `{term}`."))
    for phrase in as_str_list(contract.get("generic_repair_phrases")):
        if phrase and phrase in case.full_text:
            issues.append(issue_for_case(case, contract, "generic-copy", f"Old generic phrase leaked: `{phrase}`."))
    meta_hits = reader_meta_narration_hits(case.full_text)
    if meta_hits:
        issues.append(
            issue_for_case(
                case,
                contract,
                "reader-meta-copy",
                f"Visible copy narrates the page instead of the relationship: {meta_hits[:4]}.",
            )
        )
    for sentence in split_sentences(case.full_text):
        if len(sentence) > max_fail:
            issues.append(
                issue_for_case(
                    case,
                    contract,
                    "readability",
                    f"Sentence too long ({len(sentence)} > {max_fail}): {sentence[:80]}",
                )
            )
        elif len(sentence) > max_warn:
            issues.append(
                QualityIssue(
                    severity="warning",
                    category="readability",
                    case_id=case.id,
                    source=case.source,
                    message=f"Long sentence ({len(sentence)} > {max_warn}): {sentence[:80]}",
                )
            )
    return issues


def evaluate_relatability(case: QualityCase, contract: dict[str, Any]) -> list[QualityIssue]:
    thresholds = contract.get("thresholds") or {}
    minimum = int(thresholds.get("min_concrete_behavior_markers") or 4)
    hits = contains_any(case.full_text, as_str_list(contract.get("concrete_behavior_markers")))
    if hits >= minimum:
        return []
    return [
        QualityIssue(
            severity="warning",
            category="relatability",
            case_id=case.id,
            source=case.source,
            message=f"Only {hits} concrete behavior marker(s); expected at least {minimum}.",
        )
    ]


def evaluate_section_ownership(case: QualityCase, contract: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for section_id, markers in (contract.get("section_forbidden_markers") or {}).items():
        text = case.section_texts.get(section_id, "")
        leaked = [marker for marker in as_str_list(markers) if marker and marker in text]
        if leaked:
            issues.append(
                issue_for_case(
                    case,
                    contract,
                    "section-ownership",
                    f"{section_id} contains out-of-scope marker(s): {leaked[:4]}.",
                )
            )
    return issues


def evaluate_section_distinctness(case: QualityCase, contract: dict[str, Any]) -> list[QualityIssue]:
    threshold = float((contract.get("thresholds") or {}).get("max_cross_section_similarity") or 0.66)
    issues: list[QualityIssue] = []
    for left_index, left_id in enumerate(SECTION_IDS):
        left_text = case.section_texts.get(left_id, "")
        for right_id in SECTION_IDS[left_index + 1 :]:
            right_text = case.section_texts.get(right_id, "")
            if not left_text or not right_text:
                continue
            score = jaccard_similarity(left_text, right_text)
            if score < threshold:
                continue
            issues.append(
                issue_for_case(
                    case,
                    contract,
                    "page-topic-overlap",
                    f"{left_id} and {right_id} similarity is {score:.3f}; maximum {threshold:.3f}.",
                )
            )
    return issues


def comparison_semantic_identity(case: QualityCase, field: str) -> str:
    if field == "fit_body":
        return case.section_semantic_identities.get("relationship-fit", "")
    return case.semantic_identity


def exact_duplicate_groups(cases: list[QualityCase], field: str) -> dict[str, list[QualityCase]]:
    groups: dict[str, list[QualityCase]] = defaultdict(list)
    for case in cases:
        value = getattr(case, field)
        if value:
            groups[short_hash(value)].append(case)
    return {
        key: group
        for key, group in groups.items()
        if len({comparison_semantic_identity(case, field) for case in group}) > 1
    }


def evaluate_dataset_size(cases_by_source: dict[str, list[QualityCase]], contract: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for source, spec in (contract.get("datasets") or {}).items():
        if source not in cases_by_source:
            continue
        minimum = int((spec or {}).get("minimum_cases") or 0)
        count = len(cases_by_source.get(source, []))
        if count >= minimum:
            continue
        severity = "failure" if (spec or {}).get("strict") else "warning"
        issues.append(
            QualityIssue(
                severity=severity,
                category="coverage",
                case_id="-",
                source=source,
                message=f"{source} has {count} case(s); expected at least {minimum}.",
            )
        )
    return issues


def evaluate_exact_repetition(cases_by_source: dict[str, list[QualityCase]], contract: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    thresholds = contract.get("thresholds") or {}
    max_visible_groups = int(thresholds.get("max_generated_visible_duplicate_groups") or 0)
    max_fit_groups = int(thresholds.get("max_generated_fit_duplicate_groups") or 0)
    for source, cases in cases_by_source.items():
        spec = (contract.get("datasets") or {}).get(source) or {}
        visible_groups = exact_duplicate_groups(cases, "full_text")
        fit_groups = exact_duplicate_groups(cases, "fit_body")
        strict = bool(spec.get("strict"))
        if strict and len(visible_groups) > max_visible_groups:
            issues.append(
                QualityIssue(
                    severity="failure",
                    category="exact-repetition",
                    case_id="-",
                    source=source,
                    message=f"{len(visible_groups)} different semantic specs collapsed to duplicate full visible output; allowed {max_visible_groups}.",
                )
            )
        elif visible_groups:
            issues.append(
                QualityIssue(
                    severity="warning",
                    category="exact-repetition",
                    case_id="-",
                    source=source,
                    message=f"{len(visible_groups)} semantic-collapse full-output group(s) found for review.",
                )
            )
        if strict and len(fit_groups) > max_fit_groups:
            issues.append(
                QualityIssue(
                    severity="failure",
                    category="exact-repetition",
                    case_id="-",
                    source=source,
                    message=f"{len(fit_groups)} different relationship-fit specs collapsed to duplicate bodies; allowed {max_fit_groups}.",
                )
            )
        elif fit_groups:
            issues.append(
                QualityIssue(
                    severity="warning",
                    category="exact-repetition",
                    case_id="-",
                    source=source,
                    message=f"{len(fit_groups)} relationship-fit semantic-collapse group(s) found for review.",
                )
            )
    return issues


def similarity_pairs(cases: list[QualityCase], field: str) -> list[SimilarityIssue]:
    pairs: list[SimilarityIssue] = []
    for left_index, left in enumerate(cases):
        left_text = getattr(left, field)
        for right in cases[left_index + 1 :]:
            right_text = getattr(right, field)
            if not left_text or not right_text:
                continue
            if comparison_semantic_identity(left, field) == comparison_semantic_identity(right, field):
                continue
            if normalize_text(left_text) == normalize_text(right_text):
                continue
            pairs.append(
                SimilarityIssue(
                    source=left.source,
                    left_id=left.id,
                    right_id=right.id,
                    score=jaccard_similarity(left_text, right_text),
                    category=field,
                    left_text=left_text,
                    right_text=right_text,
                )
            )
    return sorted(pairs, key=lambda pair: pair.score, reverse=True)


def evaluate_semantic_repetition(cases_by_source: dict[str, list[QualityCase]], contract: dict[str, Any]) -> tuple[list[QualityIssue], list[SimilarityIssue]]:
    issues: list[QualityIssue] = []
    all_pairs: list[SimilarityIssue] = []
    threshold = float((contract.get("thresholds") or {}).get("near_duplicate_similarity") or 0.72)
    for source, cases in cases_by_source.items():
        pairs = similarity_pairs(cases, "fit_body")
        all_pairs.extend(pairs[:NEAR_DUPLICATE_PREVIEW_LIMIT])
        near_pairs = [pair for pair in pairs if pair.score >= threshold]
        strict = bool(((contract.get("datasets") or {}).get(source) or {}).get("strict"))
        if strict and near_pairs:
            issues.append(
                QualityIssue(
                    severity="failure",
                    category="semantic-repetition",
                    case_id="-",
                    source=source,
                    message=f"{len(near_pairs)} relationship-fit near-duplicate pair(s) at threshold {threshold}.",
                )
            )
        elif near_pairs:
            issues.append(
                QualityIssue(
                    severity="warning",
                    category="semantic-repetition",
                    case_id="-",
                    source=source,
                    message=f"{len(near_pairs)} relationship-fit near-duplicate pair(s) found for review.",
                )
            )
    return issues, sorted(all_pairs, key=lambda pair: pair.score, reverse=True)


def evaluate_sentence_repetition(cases_by_source: dict[str, list[QualityCase]], contract: dict[str, Any]) -> tuple[list[QualityIssue], Counter[str]]:
    issues: list[QualityIssue] = []
    allowed = {normalize_text(sentence) for sentence in as_str_list(contract.get("allowed_repeated_sentences"))}
    max_repeat = int((contract.get("thresholds") or {}).get("max_exact_sentence_repeat") or 6)
    sentence_counts: Counter[str] = Counter()
    sentence_semantics: dict[str, set[str]] = defaultdict(set)
    sentence_sections: dict[str, set[str]] = defaultdict(set)
    sentence_fact_identities: dict[str, set[str]] = defaultdict(set)
    sentence_untraced_occurrences: Counter[str] = Counter()
    for case in cases_by_source.get("generated-fixture", []):
        for section_id, text in case.section_content_texts.items():
            semantic_identity = case.section_semantic_identities.get(section_id, "")
            for sentence in split_sentences(text):
                if len(sentence) < 18 or sentence in allowed:
                    continue
                sentence_counts[sentence] += 1
                sentence_semantics[sentence].add(f"{section_id}:{semantic_identity}")
                sentence_sections[sentence].add(section_id)
                tracer = SENTENCE_TRACERS.get(section_id)
                trace = tracer(sentence) if tracer is not None else None
                role = str((trace or {}).get("role") or "")
                value_key = str((trace or {}).get("valueKey") or "")
                if (trace or {}).get("kind") == "fact-realization" and role and value_key:
                    sentence_fact_identities[sentence].add(
                        f"{section_id}:{role}:{value_key}"
                    )
                else:
                    sentence_untraced_occurrences[sentence] += 1
    repeated = [
        (sentence, count)
        for sentence, count in sentence_counts.most_common()
        if len(sentence_semantics[sentence]) > max_repeat
        and not (
            sentence_untraced_occurrences[sentence] == 0
            and len(sentence_fact_identities[sentence]) == 1
        )
    ]
    if repeated:
        issues.append(
            QualityIssue(
                severity="failure",
                category="sentence-repetition",
                case_id="-",
                source="generated-fixture",
                message=(
                    f"{len(repeated)} visible sentence(s) repeat across more than "
                    f"{max_repeat} distinct semantic specs."
                ),
            )
        )
    return issues, sentence_counts


def evaluate_intra_page_repetition(cases_by_source: dict[str, list[QualityCase]], contract: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for cases in cases_by_source.values():
        for case in cases:
            for section_id, fields in case.section_fields.items():
                hits = intra_page_overlap_hits(fields)
                if not hits:
                    continue
                preview = hits[0]
                issues.append(
                    issue_for_case(
                        case,
                        contract,
                        "intra-page-repetition",
                        (
                            f"{section_id} repeats `{preview.get('phrase')}` across "
                            f"{preview.get('leftField')} and {preview.get('rightField')}."
                        ),
                    )
                )
    return issues


def evaluate_cases(cases_by_source: dict[str, list[QualityCase]], contract: dict[str, Any]) -> tuple[list[QualityIssue], list[SimilarityIssue], Counter[str]]:
    issues: list[QualityIssue] = []
    issues.extend(evaluate_dataset_size(cases_by_source, contract))
    issues.extend(evaluate_exact_repetition(cases_by_source, contract))
    semantic_issues, semantic_pairs = evaluate_semantic_repetition(cases_by_source, contract)
    issues.extend(semantic_issues)
    sentence_issues, sentence_counts = evaluate_sentence_repetition(cases_by_source, contract)
    issues.extend(sentence_issues)
    issues.extend(evaluate_intra_page_repetition(cases_by_source, contract))
    for cases in cases_by_source.values():
        for case in cases:
            issues.extend(evaluate_case_markers(case, contract))
            issues.extend(evaluate_narrative_angle(case, contract))
            issues.extend(evaluate_readability(case, contract))
            issues.extend(evaluate_relatability(case, contract))
            issues.extend(evaluate_section_ownership(case, contract))
            issues.extend(evaluate_section_distinctness(case, contract))
    return issues, semantic_pairs, sentence_counts


def issue_counts(issues: list[QualityIssue]) -> tuple[int, int]:
    return (
        sum(1 for issue in issues if issue.severity == "failure"),
        sum(1 for issue in issues if issue.severity == "warning"),
    )


def category_counts(issues: list[QualityIssue], severity: str | None = None) -> Counter[str]:
    return Counter(issue.category for issue in issues if severity is None or issue.severity == severity)


def render_case_matrix(cases: list[QualityCase], contract: dict[str, Any], issues: list[QualityIssue]) -> list[str]:
    issue_lookup: dict[tuple[str, str, str], list[QualityIssue]] = defaultdict(list)
    for issue in issues:
        issue_lookup[(issue.source, issue.case_id, issue.severity)].append(issue)
    dynamic_markers = contract.get("dynamic_markers") or {}
    lines = [
        "| Case | Source | Question | Stage | Contact | Primary dynamic | Concrete markers | Failures | Warnings |",
        "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for case in sorted(cases, key=lambda item: (item.source, item.id)):
        concrete_hits = contains_any(case.full_text, as_str_list(contract.get("concrete_behavior_markers")))
        core_dynamic = case.section_dynamic_keys.get("core-answer") or case.primary_dynamic
        marker_hits = contains_any(
            case.section_texts.get("core-answer", ""),
            as_str_list(dynamic_markers.get(core_dynamic)),
        )
        failures = len(issue_lookup.get((case.source, case.id, "failure"), []))
        warnings = len(issue_lookup.get((case.source, case.id, "warning"), []))
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{case.id}`",
                    case.source,
                    case.question,
                    case.stage,
                    case.contact,
                    f"{core_dynamic} ({marker_hits})",
                    str(concrete_hits),
                    str(failures),
                    str(warnings),
                ]
            )
            + " |"
        )
    return lines


def render_issue_section(title: str, issues: list[QualityIssue], severity: str) -> list[str]:
    selected = [issue for issue in issues if issue.severity == severity]
    lines = [f"## {title}", ""]
    if not selected:
        lines.append("- None.")
        return lines
    for issue in selected[:80]:
        lines.append(f"- `{issue.source}` `{issue.case_id}` `{issue.category}`: {issue.message}")
    if len(selected) > 80:
        lines.append(f"- ... {len(selected) - 80} more.")
    return lines


def render_similarity_section(pairs: list[SimilarityIssue]) -> list[str]:
    lines = [
        "## Top Semantic Similarity Pairs",
        "",
        "| Score | Source | Left | Right | Category | Left text | Right text |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    if not pairs:
        lines.append("| - | - | - | - | - | No pairs. | - |")
        return lines
    for pair in pairs[:NEAR_DUPLICATE_PREVIEW_LIMIT]:
        lines.append(
            f"| {pair.score:.3f} | {pair.source} | `{pair.left_id}` | `{pair.right_id}` | "
            f"{pair.category} | {markdown_cell(pair.left_text)} | {markdown_cell(pair.right_text)} |"
        )
    return lines


def render_repeated_sentence_section(sentence_counts: Counter[str], contract: dict[str, Any]) -> list[str]:
    max_repeat = int((contract.get("thresholds") or {}).get("max_exact_sentence_repeat") or 6)
    repeated = [(sentence, count) for sentence, count in sentence_counts.most_common(15) if count > 1]
    lines = [
        "## Repeated Sentence Watchlist",
        "",
        f"- Informational watchlist: repeated body/next-step copy. A warning is raised only when it crosses page ownership and more than `{max_repeat}` semantic specs.",
        "",
        "| Count | Sentence |",
        "| ---: | --- |",
    ]
    if not repeated:
        lines.append("| - | No repeated generated-fixture sentences above minimum length. |")
        return lines
    for sentence, count in repeated:
        lines.append(f"| {count} | {markdown_cell(sentence, 160)} |")
    return lines


def render_report(
    cases_by_source: dict[str, list[QualityCase]],
    contract: dict[str, Any],
    issues: list[QualityIssue],
    semantic_pairs: list[SimilarityIssue],
    sentence_counts: Counter[str],
) -> str:
    failures, warnings = issue_counts(issues)
    all_cases = [case for cases in cases_by_source.values() for case in cases]
    lines = [
        "# Reading Quality Engine Report",
        "",
        "> Generated by `scripts/test_reading_quality_engine.py`. Hard gates cover repetition, semantic collapse, readability, and page ownership. Legacy keyword misses remain compatibility warnings here; the Phase 6 engine separately enforces typed ownership, one-input metamorphic behavior, and role-and-concept collapse gates.",
        "",
        "## Summary",
        "",
        f"- Status: {'PASS' if failures == 0 else 'FAIL'}",
        f"- Cases checked: {len(all_cases)}",
        f"- Failures: {failures}",
        f"- Warnings: {warnings}",
        f"- Contract: `{contract.get('version') or 'unknown'}`",
        "",
        "## Dataset Coverage",
        "",
        "| Dataset | Cases | Strict | Minimum | Unique full outputs | Unique fit bodies |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for source, cases in sorted(cases_by_source.items()):
        spec = (contract.get("datasets") or {}).get(source) or {}
        lines.append(
            f"| `{source}` | {len(cases)} | {bool(spec.get('strict'))} | {int(spec.get('minimum_cases') or 0)} | "
            f"{len({short_hash(case.full_text) for case in cases})} | {len({short_hash(case.fit_body) for case in cases})} |"
        )
    lines.extend(
        [
            "",
            "## Issue Counts",
            "",
            "| Severity | Category | Count |",
            "| --- | --- | ---: |",
        ]
    )
    for severity in ("failure", "warning"):
        counts = category_counts(issues, severity)
        if not counts:
            lines.append(f"| {severity} | - | 0 |")
        for category, count in counts.most_common():
            lines.append(f"| {severity} | `{category}` | {count} |")
    lines.extend([""])
    lines.extend(render_issue_section("Failures", issues, "failure"))
    lines.extend([""])
    lines.extend(render_issue_section("Warnings", issues, "warning"))
    lines.extend([""])
    lines.extend(render_similarity_section(semantic_pairs))
    lines.extend([""])
    lines.extend(render_repeated_sentence_section(sentence_counts, contract))
    lines.extend(["", "## Case Matrix", ""])
    lines.extend(render_case_matrix(all_cases, contract, issues))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run product-level reading quality checks.")
    parser.add_argument("--case-dir", default=str(DEFAULT_CASE_DIR))
    parser.add_argument("--generated-scenarios", default=str(GENERATED_SCENARIOS_PATH))
    parser.add_argument("--out", "--report", dest="out", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--skip-raw", action="store_true", help="Only evaluate generated scenario fixtures.")
    args = parser.parse_args()

    contract = load_quality_contract(Path(args.case_dir))
    cases_by_source: dict[str, list[QualityCase]] = {
        "generated-fixture": load_generated_cases(Path(args.generated_scenarios)),
    }
    if not args.skip_raw:
        cases_by_source["raw-reading"] = load_raw_cases()

    issues, semantic_pairs, sentence_counts = evaluate_cases(cases_by_source, contract)
    report = render_report(cases_by_source, contract, issues, semantic_pairs, sentence_counts)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    failures, warnings = issue_counts(issues)
    print(f"Wrote {display_path(out_path)}")
    print("Reading quality engine: " + ("PASS" if failures == 0 else "FAIL"))
    print(f"Cases: {sum(len(cases) for cases in cases_by_source.values())}")
    print(f"Failures: {failures}")
    print(f"Warnings: {warnings}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
