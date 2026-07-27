#!/usr/bin/env python3
"""Separate structural validity from reader-copy production readiness."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable


from readable_interpretation.final_narrative_composition import SECTION_COMPOSITION_RULES
from readable_interpretation.final_narrative_pages.action_direction_renderer import (
    action_sentence_trace,
)
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import (
    MERCURY_PARAGRAPH_FOLLOWUPS,
    MOON_PARAGRAPH_OPENINGS,
    PRESSURE_PARAGRAPH_CONTRASTS,
    ROLE_CATALOGS,
    action_for,
    chart_sentence_trace,
    caution_for,
    headline_for,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (
    core_answer_sentence_trace,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (
    PRIMARY_DYNAMIC_FORMS,
    SECONDARY_DYNAMIC_FORMS,
    UNKNOWN_SIGNAL_FORMS,
    caution_for as fit_caution_for,
    headline_for as fit_headline_for,
    paragraph_relationship_fit_value,
    relationship_fit_sentence_trace,
    signal_forms as fit_signal_forms,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (
    timing_sentence_trace,
)
from readable_interpretation.final_narrative_semantic_domains import is_unknown_signal
from readable_interpretation.final_narrative_story_arc import (
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_DIR = (
    ROOT
    / "data"
    / "reading-production-calibration"
    / "baselines"
    / "final-narrative-composer-v13"
)
DEFAULT_CORPUS_PATH = DEFAULT_BASELINE_DIR / "holdout-corpus.json"
DEFAULT_CONTRACT_PATH = ROOT / "data" / "reading-quality-cases" / "final-layer-production-contract-v1.json"
DEFAULT_JSON_OUTPUT = DEFAULT_BASELINE_DIR / "copy-readiness-audit.json"
DEFAULT_REPORT_OUTPUT = ROOT / "docs" / "research" / "30-final-layer-production-readiness-baseline.md"
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
SENTENCE_SPLIT = re.compile(r"[。！？!?\n]+")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract(path: Path) -> dict[str, Any]:
    contract = load_json(path)
    extends = str(contract.get("extends") or "")
    if not extends:
        return contract
    parent = load_contract(path.parent / extends)
    merged = {**parent, **contract}
    merged["qualityTargets"] = {
        **(parent.get("qualityTargets") or {}),
        **(contract.get("qualityTargets") or {}),
    }
    return merged


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def normalized_sentence(value: str) -> str:
    return re.sub(r"\s+", "", value or "").strip()


def visible_text(section: dict[str, Any]) -> str:
    return "\n".join(str(section.get(field) or "") for field in VISIBLE_FIELDS)


def section_field(case: dict[str, Any], section_id: str, field: str) -> str:
    section = (case.get("sections") or {}).get(section_id) or {}
    return str(section.get(field) or "")


def phrase_hits(
    cases: list[dict[str, Any]],
    definitions: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    total = len(cases)
    for definition in definitions:
        section_id = str(definition.get("sectionId") or "")
        field = str(definition.get("field") or "")
        phrase = str(definition.get("phrase") or "")
        matched = [
            str(case.get("id") or "")
            for case in cases
            if phrase and phrase in section_field(case, section_id, field)
        ]
        output.append(
            {
                **definition,
                "caseCount": len(matched),
                "coverage": round(len(matched) / total, 3) if total else 0.0,
                "sampleCaseIds": matched[:5],
            }
        )
    return output


def marker_hits(cases: list[dict[str, Any]], markers: Iterable[str]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for marker in markers:
        matches: list[dict[str, str]] = []
        for case in cases:
            for section_id, section in (case.get("sections") or {}).items():
                if not isinstance(section, dict):
                    continue
                for field in VISIBLE_FIELDS:
                    if marker and marker in str(section.get(field) or ""):
                        matches.append(
                            {
                                "caseId": str(case.get("id") or ""),
                                "sectionId": str(section_id),
                                "field": field,
                            }
                        )
        if matches:
            output.append({"phrase": marker, "hitCount": len(matches), "samples": matches[:5]})
    return output


def semantic_duplication_hits(
    cases: list[dict[str, Any]],
    definitions: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for definition in definitions:
        section_id = str(definition.get("sectionId") or "")
        field = str(definition.get("field") or "")
        markers = [str(item) for item in definition.get("containsAll") or [] if str(item)]
        matches = []
        for case in cases:
            text = section_field(case, section_id, field)
            if markers and all(marker in text for marker in markers):
                matches.append(
                    {
                        "caseId": str(case.get("id") or ""),
                        "text": text,
                    }
                )
        if matches:
            output.append(
                {
                    **definition,
                    "caseCount": len(matches),
                    "sampleCases": matches[:3],
                }
            )
    return output


def chart_semantic_trace_error(
    case: dict[str, Any],
    *,
    field: str,
    sentence: str,
) -> str | None:
    trace = chart_sentence_trace(sentence)
    if trace is None:
        return "chart sentence is not in the approved native catalog"
    section = (
        ((case.get("finalFactContract") or {}).get("sections") or {}).get(
            "chart-positioning"
        )
        or {}
    )
    role_values = section.get("roleValues") or {}
    kind = str(trace.get("kind") or "")
    role = str(trace.get("role") or "")
    value_key = str(trace.get("valueKey") or "")
    purpose = str(trace.get("purpose") or "")
    expected_fields = {
        ("fact-realization", "user-emotional-need"): "meaning",
        ("paragraph-realization", "user-emotional-need"): "meaning",
        ("fact-realization", "user-communication-style"): "meaning",
        ("paragraph-realization", "user-communication-style"): "meaning",
        ("fact-realization", "partner-pressure-response"): "body",
        ("paragraph-realization", "partner-pressure-response"): "body",
        ("composition", "headline"): "headline",
        ("composition", "partner-pressure-response"): "nextMove",
        ("composition", "precision-mode"): "caution",
    }
    if expected_fields.get((kind, role)) != field:
        return f"approved chart sentence appeared in the wrong field: {kind}:{role}:{field}"

    if kind in {"fact-realization", "paragraph-realization"}:
        if value_key not in [str(item) for item in role_values.get(role) or []]:
            return f"chart sentence value does not match its source fact: {role}:{value_key}"
        if kind == "paragraph-realization":
            paragraph_catalogs = {
                "user-emotional-need": MOON_PARAGRAPH_OPENINGS,
                "user-communication-style": MERCURY_PARAGRAPH_FOLLOWUPS,
                "partner-pressure-response": PRESSURE_PARAGRAPH_CONTRASTS,
            }
            expected = (paragraph_catalogs.get(role) or {}).get(value_key)
            if expected is None:
                return f"chart sentence has no approved paragraph entry: {role}:{value_key}"
        else:
            entry = (ROLE_CATALOGS.get(role) or {}).get(value_key)
            if entry is None:
                return f"chart sentence has no approved source entry: {role}:{value_key}"
            expected = entry.forms.for_purpose(purpose)
    elif role == "headline":
        moon_value = str(next(iter(role_values.get("user-emotional-need") or []), ""))
        pressure_value = str(
            next(iter(role_values.get("partner-pressure-response") or []), "")
        )
        expected = headline_for(moon_value, pressure_value)
    elif role == "partner-pressure-response":
        if value_key not in [str(item) for item in role_values.get(role) or []]:
            return f"chart action does not match its pressure fact: {value_key}"
        expected = action_for(value_key)
    elif role == "precision-mode":
        if value_key not in [str(item) for item in role_values.get(role) or []]:
            return f"chart boundary does not match its precision fact: {value_key}"
        expected = caution_for(value_key)
    else:
        return f"unsupported chart sentence trace: {trace}"

    if normalized_sentence(expected) != normalized_sentence(sentence):
        return "chart sentence trace does not reproduce the visible sentence"
    return None


def relationship_fit_semantic_trace_error(
    case: dict[str, Any],
    *,
    field: str,
    sentence: str,
) -> str | None:
    trace = relationship_fit_sentence_trace(sentence)
    if trace is None:
        return "relationship-fit sentence is not in the approved native catalog"
    section = (
        ((case.get("finalFactContract") or {}).get("sections") or {}).get(
            "relationship-fit"
        )
        or {}
    )
    role_values = section.get("roleValues") or {}
    kind = str(trace.get("kind") or "")
    role = str(trace.get("role") or "")
    value_key = str(trace.get("valueKey") or "")
    purpose = str(trace.get("purpose") or "")
    expected_fields = {
        ("composition", "relationship-archetype"): "headline",
        ("fact-realization", "primary-dynamic"): "meaning",
        ("paragraph-realization", "primary-dynamic"): "meaning",
        ("fact-realization", "secondary-dynamic"): "body",
        ("paragraph-realization", "secondary-dynamic"): "body",
        ("fact-realization", "attraction-signal"): "body",
        ("paragraph-realization", "attraction-signal"): "body",
        ("fact-realization", "friction-signal"): "body",
        ("paragraph-realization", "friction-signal"): "body",
        ("fact-realization", "growth-signal"): "nextMove",
        ("paragraph-realization", "growth-signal"): "nextMove",
        ("composition", "fit-boundary"): "caution",
    }
    if expected_fields.get((kind, role)) != field:
        return (
            "approved relationship-fit sentence appeared in the wrong field: "
            f"{kind}:{role}:{field}"
        )

    values = [str(item) for item in role_values.get(role) or []]
    if kind == "composition" and role == "relationship-archetype":
        if value_key not in values:
            return f"relationship-fit headline does not match its archetype: {value_key}"
        expected = fit_headline_for(value_key)
    elif kind == "composition" and role == "fit-boundary":
        expected = fit_caution_for()
    elif role in {"primary-dynamic", "secondary-dynamic"}:
        if value_key not in values:
            return f"relationship-fit dynamic does not match its fact: {role}:{value_key}"
        if kind == "paragraph-realization":
            expected = paragraph_relationship_fit_value(role, value_key)
        else:
            catalog = (
                PRIMARY_DYNAMIC_FORMS
                if role == "primary-dynamic"
                else SECONDARY_DYNAMIC_FORMS
            )
            expected = catalog[value_key].forms.for_purpose(purpose)
    elif role in {"attraction-signal", "friction-signal", "growth-signal"}:
        unknown_values = [value for value in values if is_unknown_signal(value)]
        if value_key:
            if value_key not in values:
                return f"relationship-fit signal does not match its fact: {role}:{value_key}"
            if kind == "paragraph-realization":
                expected = paragraph_relationship_fit_value(role, value_key)
            else:
                expected_kind = role.removesuffix("-signal")
                expected = fit_signal_forms(
                    value_key,
                    expected_kind=expected_kind,
                ).for_purpose(purpose)
        elif unknown_values and trace.get("certainty") == "unknown":
            if kind == "paragraph-realization":
                expected = paragraph_relationship_fit_value(role, unknown_values[0])
            else:
                expected = UNKNOWN_SIGNAL_FORMS[role].forms.for_purpose(purpose)
        else:
            return f"relationship-fit unknown signal has no matching fact: {role}"
    else:
        return f"unsupported relationship-fit sentence trace: {trace}"

    if normalized_sentence(expected) != normalized_sentence(sentence):
        return "relationship-fit sentence trace does not reproduce the visible sentence"
    return None


def native_semantic_trace_error(
    case: dict[str, Any],
    *,
    section_id: str,
    field: str,
    sentence: str,
) -> str | None:
    if section_id == "chart-positioning":
        return chart_semantic_trace_error(case, field=field, sentence=sentence)
    if section_id == "relationship-fit":
        return relationship_fit_semantic_trace_error(
            case,
            field=field,
            sentence=sentence,
        )
    trace_functions = {
        "core-answer": core_answer_sentence_trace,
        "timing-reading": timing_sentence_trace,
        "action-direction": action_sentence_trace,
    }
    trace_function = trace_functions.get(section_id)
    if trace_function is None:
        return "section has no native semantic trace"
    trace = trace_function(sentence)
    if trace is None:
        return f"{section_id} sentence is not in the approved native catalog"

    role = str(trace.get("role") or "")
    value_key = str(trace.get("valueKey") or "")
    owner = SECTION_COMPOSITION_RULES[section_id].role_owners.get(role)
    if owner is None or owner.field != field:
        return f"approved {section_id} sentence appeared in the wrong field: {role}:{field}"

    section = (
        ((case.get("finalFactContract") or {}).get("sections") or {}).get(section_id)
        or {}
    )
    role_values = section.get("roleValues") or {}
    values = [str(item) for item in role_values.get(role) or []]
    if value_key and value_key not in values:
        return f"{section_id} sentence does not match its fact: {role}:{value_key}"
    if not value_key and trace.get("certainty") != "unknown":
        return f"{section_id} sentence trace lacks a source value: {role}"

    contributor_role = str(trace.get("contributorRole") or "")
    contributor_value = str(trace.get("contributorValueKey") or "")
    if contributor_role:
        contributor_owner = SECTION_COMPOSITION_RULES[section_id].role_owners.get(
            contributor_role
        )
        contributor_presentation = str(
            (FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}).get(
                contributor_role
            )
            or ""
        )
        if contributor_owner is not None and contributor_owner.field != field:
            return (
                f"approved {section_id} sentence has a contributor in the wrong field: "
                f"{contributor_role}:{field}"
            )
        if contributor_owner is None and not contributor_presentation.startswith("hidden-"):
            return (
                f"approved {section_id} sentence has an unowned contributor: "
                f"{contributor_role}:{field}"
            )
        contributor_values = [
            str(item) for item in role_values.get(contributor_role) or []
        ]
        if contributor_value not in contributor_values:
            return (
                f"{section_id} sentence does not match its contributing fact: "
                f"{contributor_role}:{contributor_value}"
            )
    return None


def sentence_metrics(
    cases: list[dict[str, Any]],
    *,
    maximum: int,
    repeated_coverage: float,
    approved_repetitions: set[str],
) -> dict[str, Any]:
    lengths: list[int] = []
    long_sentences: list[dict[str, Any]] = []
    occurrences: dict[tuple[str, str, str], set[str]] = {}
    semantic_inputs: dict[str, set[str]] = {}
    approved_semantic_sentence_count = 0
    semantic_trace_errors: list[dict[str, str]] = []
    for case in cases:
        for section_id, section in (case.get("sections") or {}).items():
            if not isinstance(section, dict):
                continue
            fact_section = (((case.get("finalFactContract") or {}).get("sections") or {}).get(section_id) or {})
            semantic_identity = str(fact_section.get("factIdentity") or case.get("id") or "")
            semantic_inputs.setdefault(str(section_id), set()).add(semantic_identity)
            for field in VISIBLE_FIELDS:
                seen: set[str] = set()
                for sentence in SENTENCE_SPLIT.split(str(section.get(field) or "")):
                    normalized = normalized_sentence(sentence)
                    if not normalized:
                        continue
                    length = len(normalized)
                    lengths.append(length)
                    if length > maximum:
                        long_sentences.append(
                            {
                                "caseId": str(case.get("id") or ""),
                                "sectionId": str(section_id),
                                "field": field,
                                "length": length,
                                "sentence": sentence.strip(),
                            }
                        )
                    if length < 12 or normalized in seen:
                        continue
                    seen.add(normalized)
                    if section_id in SECTION_COMPOSITION_RULES:
                        trace_error = native_semantic_trace_error(
                            case,
                            section_id=str(section_id),
                            field=field,
                            sentence=sentence.strip(),
                        )
                        if trace_error is None:
                            approved_semantic_sentence_count += 1
                            continue
                        semantic_trace_errors.append(
                            {
                                "caseId": str(case.get("id") or ""),
                                "sectionId": str(section_id),
                                "field": field,
                                "sentence": sentence.strip(),
                                "error": trace_error,
                            }
                        )
                    if any(approved in normalized for approved in approved_repetitions):
                        continue
                    occurrences.setdefault((str(section_id), field, normalized), set()).add(semantic_identity)

    repeated = [
        {
            "sectionId": section_id,
            "field": field,
            "sentence": sentence,
            "caseCount": len(identities),
            "semanticInputCount": len(semantic_inputs.get(section_id) or ()),
            "coverage": round(len(identities) / len(semantic_inputs.get(section_id) or ()), 3)
            if semantic_inputs.get(section_id)
            else 0.0,
        }
        for (section_id, field, sentence), identities in sorted(
            occurrences.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        if len(identities) / max(1, len(semantic_inputs.get(section_id) or ())) > repeated_coverage
    ]
    sorted_lengths = sorted(lengths)
    percentile_index = max(0, math.ceil(len(sorted_lengths) * 0.95) - 1) if sorted_lengths else 0
    return {
        "sentenceCount": len(lengths),
        "maximumLength": max(lengths, default=0),
        "p95Length": sorted_lengths[percentile_index] if sorted_lengths else 0,
        "longSentenceCount": len(long_sentences),
        "longSentences": sorted(long_sentences, key=lambda item: -int(item["length"]))[:20],
        "repeatedExactSentenceCount": len(repeated),
        "repeatedExactSentences": repeated[:30],
        "approvedSemanticSentenceCount": approved_semantic_sentence_count,
        "semanticTraceErrorCount": len(semantic_trace_errors),
        "semanticTraceErrors": semantic_trace_errors[:30],
        "semanticInputCounts": {key: len(value) for key, value in sorted(semantic_inputs.items())},
    }


def structural_result(
    corpus: dict[str, Any],
    cases: list[dict[str, Any]],
    expected_composer: str,
    expected_matrix_count: int,
) -> dict[str, Any]:
    failures: list[str] = []
    if len(cases) != expected_matrix_count:
        failures.append(f"matrix case count is {len(cases)}, expected {expected_matrix_count}")
    if int(corpus.get("matrixCaseCount") or 0) != len(cases):
        failures.append("declared matrix case count does not match persisted cases")
    if corpus.get("composerVersion") != expected_composer:
        failures.append(
            f"composer version is {corpus.get('composerVersion')}, expected {expected_composer}"
        )
    visible = [str((case.get("fingerprints") or {}).get("visible") or "") for case in cases]
    if len(set(visible)) != len(cases):
        failures.append("full visible output fingerprints are not unique")
    invalid_contracts = [
        str(case.get("id") or "")
        for case in cases
        if str((case.get("sectionContracts") or {}).get("validationStatus") or "") != "valid"
    ]
    if invalid_contracts:
        failures.append(f"invalid section contracts: {len(invalid_contracts)}")
    return {
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "matrixCaseCount": len(cases),
        "uniqueVisibleOutputCount": len(set(visible)),
        "invalidSectionContractCount": len(invalid_contracts),
    }


def evaluate(corpus: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    cases = [item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)]
    targets = contract.get("qualityTargets") or {}
    repeated_limit = float(targets.get("maximumRepeatedOpeningCoverage") or 0.2)
    fallback_limit = float(targets.get("maximumKnownInputFallbackCoverage") or 0.0)
    forbidden = marker_hits(cases, contract.get("forbiddenExactPhrases") or [])
    abstract = marker_hits(cases, contract.get("forbiddenAbstractPhrases") or [])
    meta = marker_hits(cases, contract.get("readerMetaNarrationMarkers") or [])
    fallbacks = phrase_hits(cases, contract.get("selectorFallbacks") or [])
    frames = phrase_hits(cases, contract.get("repeatedFrames") or [])
    duplications = semantic_duplication_hits(cases, contract.get("semanticDuplicationPatterns") or [])
    sentences = sentence_metrics(
        cases,
        maximum=int(targets.get("maximumSentenceCharacters") or 70),
        repeated_coverage=float(targets.get("maximumExactSentenceCoverage") or 0.1),
        approved_repetitions={
            normalized_sentence(str(item))
            for item in contract.get("approvedRepeatedSafetyPhrases") or []
            if str(item)
        },
    )
    copy_failures: list[str] = []
    if forbidden:
        copy_failures.append(f"known bad phrases remain: {len(forbidden)}")
    if abstract:
        copy_failures.append(f"abstract reader-facing phrases remain: {len(abstract)}")
    if meta:
        copy_failures.append(f"reader-facing page narration remains: {len(meta)}")
    excessive_fallbacks = [item for item in fallbacks if float(item.get("coverage") or 0) > fallback_limit]
    if excessive_fallbacks:
        copy_failures.append(f"known selector fallbacks remain: {len(excessive_fallbacks)}")
    excessive_frames = [item for item in frames if float(item.get("coverage") or 0) > repeated_limit]
    if excessive_frames:
        copy_failures.append(f"repeated rhetorical frames exceed {repeated_limit:.0%}: {len(excessive_frames)}")
    if duplications:
        copy_failures.append(f"known semantic duplications remain: {len(duplications)}")
    if sentences["longSentenceCount"]:
        copy_failures.append(
            f"sentences exceed {int(targets.get('maximumSentenceCharacters') or 70)} characters: {sentences['longSentenceCount']}"
        )
    if sentences["repeatedExactSentenceCount"]:
        copy_failures.append(
            f"exact sentences exceed {float(targets.get('maximumExactSentenceCoverage') or 0.1):.0%} coverage: {sentences['repeatedExactSentenceCount']}"
        )
    if sentences["semanticTraceErrorCount"]:
        copy_failures.append(
            f"approved semantic sentence traces are invalid: {sentences['semanticTraceErrorCount']}"
        )

    structural = structural_result(
        corpus,
        cases,
        str(contract.get("baselineComposerVersion") or ""),
        int(contract.get("expectedMatrixCaseCount") or 125),
    )
    automated_gate_ready = structural["status"] == "PASS" and not copy_failures
    return {
        "version": contract.get("version"),
        "corpusVersion": corpus.get("version"),
        "composerVersion": corpus.get("composerVersion"),
        "structural": structural,
        "copyQuality": {
            "status": "FAIL" if copy_failures else "PASS",
            "failures": copy_failures,
            "knownBadPhraseHits": forbidden,
            "abstractPhraseHits": abstract,
            "readerMetaNarrationHits": meta,
            "selectorFallbacks": fallbacks,
            "repeatedFrames": frames,
            "semanticDuplications": duplications,
            "sentenceMetrics": sentences,
        },
        "automatedPhase2To4Ready": automated_gate_ready,
        "remainingRoadmapPhases": [
            "phase-8-human-acceptance",
        ],
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in row) + " |"
        for row in rows
    )
    return lines


def render_report(result: dict[str, Any]) -> str:
    structural = result["structural"]
    copy = result["copyQuality"]
    sentences = copy["sentenceMetrics"]
    duplication_rows = (
        markdown_table(
            ["Pattern", "Section", "Field", "Cases"],
            [
                [item["id"], item["sectionId"], item["field"], item["caseCount"]]
                for item in copy["semanticDuplications"]
            ],
        )
        if copy["semanticDuplications"]
        else ["- None."]
    )
    lines = [
        (
            "# Final-Layer Production Readiness Baseline"
            if result.get("version") == "final-layer-production-contract-v1"
            else "# Final-Layer Phase 2-4 Automated Gate"
        ),
        "",
        (
            "> Phase 0 snapshot. Structural validity and reader-copy acceptance are intentionally reported separately."
            if result.get("version") == "final-layer-production-contract-v1"
            else "> Automated architecture, reader-language realization, and semantic-coverage gate. Phases 5-7 are verified separately; Phase 8 remains."
        ),
        "",
        "## Verdict",
        "",
        f"- Structural status: **{structural['status']}**",
        f"- Copy-quality status: **{copy['status']}**",
        f"- Automated Phase 2-4 gate ready: **{'YES' if result['automatedPhase2To4Ready'] else 'NO'}**",
        "- Full production acceptance: **PENDING PHASE 8**",
        f"- Composer: `{result.get('composerVersion')}`",
        f"- Matrix cases: {structural['matrixCaseCount']}",
        f"- Unique visible outputs: {structural['uniqueVisibleOutputCount']}",
        "",
        "This automated PASS proves the Phase 2 page boundary, Phase 3 controlled realization contract, and Phase 4 semantic coverage against the current corpus. Phase 5 composition, the Phase 6 semantic test engine, and the Phase 7 calibration corpus are enforced by separate runtime gates; this report does not complete Phase 8 human acceptance.",
        "",
        "## Copy Failures",
        "",
        *([f"- {item}" for item in copy["failures"]] or ["- None."]),
        "",
        "## Plain-Language Violations",
        "",
        *(
            [f"- `{item['phrase']}`: {item['hitCount']} hit(s)" for item in copy["abstractPhraseHits"]]
            or ["- None."]
        ),
        "",
        "## Sentence Complexity",
        "",
        f"- Sentences measured: {sentences['sentenceCount']}",
        f"- Maximum sentence length: {sentences['maximumLength']}",
        f"- P95 sentence length: {sentences['p95Length']}",
        f"- Sentences above the contract limit: {sentences['longSentenceCount']}",
        "",
        "## Selector Fallbacks",
        "",
        *markdown_table(
            ["Fallback", "Section", "Cases", "Coverage", "Phrase"],
            [
                [item["id"], item["sectionId"], item["caseCount"], f"{float(item['coverage']):.1%}", item["phrase"]]
                for item in copy["selectorFallbacks"]
            ],
        ),
        "",
        "## Repeated Frames",
        "",
        *markdown_table(
            ["Frame", "Section", "Field", "Cases", "Coverage"],
            [
                [item["id"], item["sectionId"], item["field"], item["caseCount"], f"{float(item['coverage']):.1%}"]
                for item in copy["repeatedFrames"]
            ],
        ),
        "",
        "## Known Semantic Duplications",
        "",
        *duplication_rows,
        "",
        "## Longest Sentences",
        "",
        *markdown_table(
            ["Case", "Section", "Field", "Length", "Sentence"],
            [
                [item["caseId"], item["sectionId"], item["field"], item["length"], item["sentence"]]
                for item in sentences["longSentences"][:10]
            ],
        ),
        "",
        "## Renderer Boundary",
        "",
        (
            "The next implementation step introduces fact-only section contracts with stable IDs, evidence ownership, source fingerprints, and unknown-value diagnostics. Existing prose slots remain available only through an explicitly marked compatibility adapter until the five Phase 2 renderers migrate."
            if result.get("version") == "final-layer-production-contract-v1"
            else "All five visible sections render from evidence-owned stable facts through page-owned renderers. Every emitted semantic role must be explicitly consumed or classified as non-reader control data; legacy prose slots cannot alter reader copy."
        ),
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--report-output", "--out", dest="report_output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    result = evaluate(load_json(args.corpus), load_contract(args.contract))
    if not args.no_write:
        write_json(args.json_output, result)
        write_text(args.report_output, render_report(result))
    print(f"Structural status: {result['structural']['status']}")
    print(f"Copy-quality status: {result['copyQuality']['status']}")
    print(f"Automated Phase 2-4 gate ready: {result['automatedPhase2To4Ready']}")
    return 0 if result["automatedPhase2To4Ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
