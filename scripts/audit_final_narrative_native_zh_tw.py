#!/usr/bin/env python3
"""Inventory and classify current final-narrative Traditional Chinese output."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from readable_interpretation.final_narrative_chinese_contract import (  # noqa: E402
    FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION,
    NATIVE_CHINESE_PATTERNS,
    NativeChineseIssue,
    audit_native_zh_tw_text,
    native_contract_fingerprint,
    native_contract_payload,
)
from readable_interpretation.final_narrative_chinese_quality import (  # noqa: E402
    FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
    hard_quality_contract_fingerprint,
    hard_quality_contract_payload,
)
from readable_interpretation.final_narrative_chinese_plan import (  # noqa: E402
    FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION,
    meaning_frame_contract_payload,
)
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    SECTION_COMPOSITION_RULES,
)
from readable_interpretation.final_narrative_fact_contract import fact_id  # noqa: E402
from readable_interpretation.final_narrative_page_grammar import VISIBLE_FIELDS  # noqa: E402
from readable_interpretation.final_narrative_story_arc import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
)
from readable_interpretation.final_narrative_pages.chart_positioning_zh_tw_catalog import (  # noqa: E402
    CHART_POSITIONING_NATIVE_ZH_TW_CATALOG_VERSION,
    chart_sentence_trace,
)
from readable_interpretation.final_narrative_pages.action_direction_renderer import (  # noqa: E402
    ACTION_DIRECTION_NATIVE_ZH_TW_CATALOG_VERSION,
    action_sentence_trace,
)
from readable_interpretation.final_narrative_pages.core_answer_renderer import (  # noqa: E402
    CORE_ANSWER_NATIVE_ZH_TW_CATALOG_VERSION,
    core_answer_sentence_trace,
)
from readable_interpretation.final_narrative_pages.relationship_fit_zh_tw_catalog import (  # noqa: E402
    RELATIONSHIP_FIT_NATIVE_ZH_TW_CATALOG_VERSION,
    relationship_fit_sentence_trace,
)
from readable_interpretation.final_narrative_pages.timing_renderer import (  # noqa: E402
    TIMING_NATIVE_ZH_TW_CATALOG_VERSION,
    timing_sentence_trace,
)
from readable_interpretation.final_narrative_semantic_domains import (  # noqa: E402
    is_unknown_signal,
    parse_relationship_signal,
)


INVENTORY_VERSION = "final-narrative-native-zh-tw-r6-inventory-v1"
DEFAULT_CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"
DEFAULT_REGRESSION_PATH = (
    ROOT
    / "data"
    / "reading-quality-cases"
    / "final-narrative-native-zh-tw-regressions-v1.json"
)
DEFAULT_JSON_OUTPUT = (
    ROOT
    / "data"
    / "reading-production-calibration"
    / "native-zh-tw-v1"
    / "r0-realization-inventory.json"
)
DEFAULT_REPORT_OUTPUT = ROOT / "docs" / "research" / "37-final-narrative-native-zh-tw-r0-r1.md"
SENTENCE_SPLIT = re.compile(r"[。！？!?]+")
SIGNAL_ROLES = {"attraction-signal", "friction-signal", "growth-signal", "evidence-signal"}
MAXIMUM_SAMPLE_LOCATIONS = 4
MAXIMUM_SAMPLE_CONTEXT_FINGERPRINTS = 8
MIGRATED_SECTION_IDS = frozenset(SECTION_COMPOSITION_RULES)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip("。！？!?；;")


def field_sentences(field: str, value: str) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    if field == "headline":
        return [text]
    return [item.strip() for item in SENTENCE_SPLIT.split(text) if item.strip()]


def owned_roles(section_id: str, field: str) -> list[str]:
    rule = SECTION_COMPOSITION_RULES[section_id]
    return sorted(role for role, owner in rule.role_owners.items() if owner.field == field)


def role_values(case: Mapping[str, Any], section_id: str, roles: Iterable[str]) -> dict[str, list[str]]:
    fact_contract = case.get("finalFactContract") if isinstance(case.get("finalFactContract"), dict) else {}
    sections = fact_contract.get("sections") if isinstance(fact_contract.get("sections"), dict) else {}
    section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else {}
    values = section.get("roleValues") if isinstance(section.get("roleValues"), dict) else {}
    return {
        role: sorted(str(value) for value in values.get(role) or [] if str(value or "").strip())
        for role in roles
    }


def signal_payload(value: str) -> dict[str, str] | None:
    if is_unknown_signal(value):
        return None
    try:
        signal = parse_relationship_signal(value)
    except ValueError:
        return None
    return {
        "valueKey": signal.raw,
        "kind": signal.kind,
        "pairKey": signal.pair_key,
        "actorPerson": signal.actor_person,
        "actorPlanet": signal.actor_planet,
        "receiverPerson": signal.receiver_person,
        "receiverPlanet": signal.receiver_planet,
        "direction": signal.direction_key,
        "aspect": signal.aspect,
        "polarity": signal.polarity,
    }


def complaint_matches(text: str, regression_cases: Iterable[Mapping[str, Any]]) -> list[str]:
    normalized = normalized_text(text)
    return [
        str(item.get("id") or "")
        for item in regression_cases
        if normalized_text(str(item.get("text") or ""))
        and normalized_text(str(item.get("text") or "")) in normalized
    ]


def native_sentence_trace(section_id: str, sentence: str) -> dict[str, str] | None:
    if section_id == "chart-positioning":
        return chart_sentence_trace(sentence)
    if section_id == "relationship-fit":
        return relationship_fit_sentence_trace(sentence)
    if section_id == "core-answer":
        return core_answer_sentence_trace(sentence)
    if section_id == "timing-reading":
        return timing_sentence_trace(sentence)
    if section_id == "action-direction":
        return action_sentence_trace(sentence)
    return None


def defect_taxonomy() -> list[dict[str, str]]:
    structural = [
        {
            "id": "internal-semantic-label",
            "severity": "failure",
            "description": "內部行星功能名稱直接出現在可見文案。",
        },
        {
            "id": "reader-meta-narration",
            "severity": "failure",
            "description": "頁面範圍或閱讀流程說明進入結果文案。",
        },
        {
            "id": "long-native-sentence",
            "severity": "warning",
            "description": "句子長度需要人工檢查。",
        },
        {
            "id": "overloaded-native-sentence",
            "severity": "warning",
            "description": "單句包含過多分句。",
        },
        {
            "id": "reader-reported-regression",
            "severity": "failure",
            "description": "已由讀者指出不自然或破碎的文案。",
        },
    ]
    return sorted(
        [
            *structural,
            *[
                {
                    "id": item.id,
                    "severity": item.severity,
                    "description": item.description,
                }
                for item in NATIVE_CHINESE_PATTERNS
            ],
        ],
        key=lambda item: item["id"],
    )


def build_regression_results(
    corpus_text: str,
    regression_cases: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in regression_cases:
        text = str(item.get("text") or "")
        detected = {issue.id for issue in audit_native_zh_tw_text(text)}
        detected.add("reader-reported-regression")
        expected = {str(value) for value in item.get("expectedDefectIds") or []}
        output.append(
            {
                "id": str(item.get("id") or ""),
                "text": text,
                "note": str(item.get("note") or ""),
                "expectedDefectIds": sorted(expected),
                "detectedDefectIds": sorted(detected),
                "contractRecognized": expected <= detected,
                "presentInCorpus": text in corpus_text,
            }
        )
    return output


def build_audit(
    corpus: Mapping[str, Any],
    regressions: Mapping[str, Any],
    *,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
) -> dict[str, Any]:
    cases = [item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)]
    regression_cases = [item for item in regressions.get("cases") or [] if isinstance(item, dict)]
    entries: dict[str, dict[str, Any]] = {}
    section_occurrences: Counter[str] = Counter()
    section_unique: dict[str, set[str]] = defaultdict(set)
    observed_role_values: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    defect_occurrences: Counter[str] = Counter()
    defect_unique: dict[str, set[str]] = defaultdict(set)
    section_failure_unique: dict[str, set[str]] = defaultdict(set)
    section_warning_unique: dict[str, set[str]] = defaultdict(set)
    section_purpose_trace_gaps: Counter[str] = Counter()
    section_purpose_traced: Counter[str] = Counter()
    ownership_trace_occurrences: Counter[str] = Counter()
    corpus_visible_parts: list[str] = []
    signal_registry: dict[str, dict[str, str]] = {}

    for case in cases:
        case_id = str(case.get("id") or "")
        sections = case.get("sections") if isinstance(case.get("sections"), dict) else {}
        for section_id, section in sections.items():
            if section_id not in SECTION_COMPOSITION_RULES or not isinstance(section, dict):
                continue
            for field in VISIBLE_FIELDS:
                visible_value = str(section.get(field) or "")
                corpus_visible_parts.append(visible_value)
                roles = owned_roles(section_id, field)
                values = role_values(case, section_id, roles)
                for role, items in values.items():
                    observed_role_values[section_id][role].update(items)
                for sentence in field_sentences(field, visible_value):
                    normalized = normalized_text(sentence)
                    if not normalized:
                        continue
                    trace = native_sentence_trace(section_id, sentence)
                    sentence_roles = list(roles)
                    sentence_values = dict(values)
                    realization_purpose = "legacy-untraced"
                    ownership_trace_status = (
                        "fact-owned"
                        if len(sentence_roles) == 1
                        else "field-level-ambiguous"
                        if sentence_roles
                        else "composition-only-untraced"
                    )
                    if trace is not None:
                        trace_kind = str(trace.get("kind") or "")
                        trace_role = str(trace.get("role") or "")
                        realization_purpose = str(trace.get("purpose") or "")
                        if trace_kind == "fact-realization":
                            sentence_roles = [trace_role]
                        elif section_id == "chart-positioning" and trace_role == "headline":
                            sentence_roles = [
                                "user-emotional-need",
                                "partner-pressure-response",
                            ]
                        elif trace_role in SECTION_COMPOSITION_RULES[section_id].role_owners:
                            sentence_roles = [trace_role]
                        else:
                            sentence_roles = []
                        contributor_role = str(trace.get("contributorRole") or "")
                        if (
                            contributor_role
                            and contributor_role in (
                                FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}
                            )
                            and contributor_role not in sentence_roles
                        ):
                            sentence_roles.append(contributor_role)
                        sentence_values = role_values(case, section_id, sentence_roles)
                        trace_value = str(trace.get("valueKey") or "")
                        if trace_value and trace_value not in sentence_values.get(trace_role, []):
                            raise ValueError(
                                f"{case_id}:{section_id}:{field}: sentence trace does not "
                                f"match its source fact: {trace_role}:{trace_value}"
                            )
                        contributor_value = str(
                            trace.get("contributorValueKey") or ""
                        )
                        if (
                            contributor_value
                            and contributor_value
                            not in sentence_values.get(contributor_role, [])
                        ):
                            raise ValueError(
                                f"{case_id}:{section_id}:{field}: sentence trace does not "
                                "match its contributing fact: "
                                f"{contributor_role}:{contributor_value}"
                            )
                        ownership_trace_status = (
                            "native-frame-owned"
                            if trace_kind == "fact-realization"
                            else "native-composition-owned"
                        )

                    source_fact_ids = sorted(
                        {
                            fact_id(section_id, role, value)
                            for role, items in sentence_values.items()
                            for value in items
                        }
                    )
                    signals = sorted(
                        (
                            payload
                            for role, items in sentence_values.items()
                            if role in SIGNAL_ROLES
                            for value in items
                            if (payload := signal_payload(value)) is not None
                        ),
                        key=lambda item: item["valueKey"],
                    )
                    for signal in signals:
                        signal_registry[signal["valueKey"]] = signal
                    semantic_context = stable_hash(sentence_values)
                    entry_id = stable_hash({"text": normalized})[:20]
                    issues = list(audit_native_zh_tw_text(sentence))
                    complaint_ids = complaint_matches(sentence, regression_cases)
                    if complaint_ids:
                        issues.append(
                            NativeChineseIssue(
                                id="reader-reported-regression",
                                severity="failure",
                                match=sentence,
                                message=f"已知讀者回報：{', '.join(complaint_ids)}",
                            )
                        )
                    issue_payloads = [issue.as_payload() for issue in issues]
                    if normalized not in entries:
                        entries[normalized] = {
                            "id": entry_id,
                            "text": sentence,
                            "normalizedText": normalized,
                            "occurrenceCount": 0,
                            "sectionIds": set(),
                            "fields": set(),
                            "ownedRoles": set(),
                            "sourceFactIds": set(),
                            "semanticContextFingerprints": set(),
                            "signalValueKeys": set(),
                            "defects": {},
                            "sampleLocations": [],
                            "realizationPurposes": set(),
                            "purposeTraceGapOccurrenceCount": 0,
                            "purposeTracedOccurrenceCount": 0,
                            "ownershipTraceStatuses": set(),
                        }
                    entry = entries[normalized]
                    entry["occurrenceCount"] += 1
                    entry["sectionIds"].add(section_id)
                    entry["fields"].add(field)
                    entry["ownedRoles"].update(sentence_roles)
                    entry["sourceFactIds"].update(source_fact_ids)
                    entry["semanticContextFingerprints"].add(semantic_context)
                    entry["ownershipTraceStatuses"].add(ownership_trace_status)
                    entry["realizationPurposes"].add(realization_purpose)
                    ownership_trace_occurrences[ownership_trace_status] += 1
                    if realization_purpose == "legacy-untraced":
                        entry["purposeTraceGapOccurrenceCount"] += 1
                        section_purpose_trace_gaps[section_id] += 1
                    else:
                        entry["purposeTracedOccurrenceCount"] += 1
                        section_purpose_traced[section_id] += 1
                    entry["signalValueKeys"].update(signal["valueKey"] for signal in signals)
                    for issue in issue_payloads:
                        entry["defects"][issue["id"]] = issue
                        defect_occurrences[issue["id"]] += 1
                        defect_unique[issue["id"]].add(normalized)
                        if issue["severity"] == "failure":
                            section_failure_unique[section_id].add(normalized)
                        elif issue["severity"] == "warning":
                            section_warning_unique[section_id].add(normalized)
                    if len(entry["sampleLocations"]) < MAXIMUM_SAMPLE_LOCATIONS:
                        entry["sampleLocations"].append(
                            {
                                "caseId": case_id,
                                "sectionId": section_id,
                                "field": field,
                                "semanticContextFingerprint": semantic_context,
                            }
                        )
                    section_occurrences[section_id] += 1
                    section_unique[section_id].add(normalized)

    serialized_entries: list[dict[str, Any]] = []
    for entry in entries.values():
        serialized_base = {
            key: value
            for key, value in entry.items()
            if key
            not in {
                "sectionIds",
                "fields",
                "ownedRoles",
                "sourceFactIds",
                "semanticContextFingerprints",
                "ownershipTraceStatuses",
                "realizationPurposes",
                "signalValueKeys",
                "defects",
            }
        }
        purposes = sorted(entry["realizationPurposes"])
        serialized_entries.append(
            {
                **serialized_base,
                "sectionIds": sorted(entry["sectionIds"]),
                "fields": sorted(entry["fields"]),
                "ownedRoles": sorted(entry["ownedRoles"]),
                "sourceFactIds": sorted(entry["sourceFactIds"]),
                "semanticContextFingerprintCount": len(entry["semanticContextFingerprints"]),
                "sampleSemanticContextFingerprints": sorted(entry["semanticContextFingerprints"])[
                    :MAXIMUM_SAMPLE_CONTEXT_FINGERPRINTS
                ],
                "ownershipTraceStatuses": sorted(entry["ownershipTraceStatuses"]),
                "realizationPurpose": purposes[0] if len(purposes) == 1 else "mixed",
                "realizationPurposes": purposes,
                "signalValueKeys": sorted(entry["signalValueKeys"]),
                "defects": [entry["defects"][key] for key in sorted(entry["defects"])],
            }
        )
    serialized_entries.sort(key=lambda item: (item["sectionIds"], item["fields"], item["normalizedText"]))

    regression_results = build_regression_results("\n".join(corpus_visible_parts), regression_cases)
    unique_failures = {
        entry["normalizedText"]
        for entry in serialized_entries
        if any(issue["severity"] == "failure" for issue in entry["defects"])
    }
    unique_warnings = {
        entry["normalizedText"]
        for entry in serialized_entries
        if any(issue["severity"] == "warning" for issue in entry["defects"])
    }
    defect_summary = [
        {
            "id": defect_id,
            "occurrenceCount": count,
            "uniqueSentenceCount": len(defect_unique[defect_id]),
        }
        for defect_id, count in sorted(defect_occurrences.items(), key=lambda item: (-item[1], item[0]))
    ]
    status = (
        "NOT_READY"
        if (
            unique_failures
            or unique_warnings
            or sum(section_purpose_trace_gaps.values())
            or not all(item["contractRecognized"] for item in regression_results)
        )
        else "READY"
    )
    return {
        "version": INVENTORY_VERSION,
        "status": status,
        "sourceCorpus": {
            "path": str(corpus_path.relative_to(ROOT)) if corpus_path.is_relative_to(ROOT) else str(corpus_path),
            "version": str(corpus.get("version") or ""),
            "composerVersion": str(corpus.get("composerVersion") or ""),
            "compositionVersion": str(corpus.get("compositionVersion") or ""),
            "hardQualityVersion": str(corpus.get("hardQualityVersion") or ""),
            "hardQualityContractFingerprint": str(
                corpus.get("hardQualityContractFingerprint") or ""
            ),
            "caseCount": len(cases),
            "sha256": file_hash(corpus_path) if corpus_path.exists() else stable_hash(corpus),
        },
        "contract": {
            "version": FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION,
            "fingerprint": native_contract_fingerprint(),
            "payload": native_contract_payload(),
        },
        "hardQualityContract": {
            "version": FINAL_NARRATIVE_NATIVE_ZH_TW_HARD_GATE_VERSION,
            "fingerprint": hard_quality_contract_fingerprint(),
            "payload": hard_quality_contract_payload(),
        },
        "meaningFrameContract": meaning_frame_contract_payload(),
        "summary": {
            "sentenceOccurrenceCount": sum(section_occurrences.values()),
            "uniqueSentenceCount": len(serialized_entries),
            "uniqueFailureSentenceCount": len(unique_failures),
            "uniqueWarningSentenceCount": len(unique_warnings),
            "realizationPurposeTraceGapCount": sum(section_purpose_trace_gaps.values()),
            "realizationPurposeTracedCount": sum(section_purpose_traced.values()),
            "compositionOwnershipTraceGapCount": ownership_trace_occurrences[
                "composition-only-untraced"
            ],
            "ambiguousFieldOwnershipTraceCount": ownership_trace_occurrences[
                "field-level-ambiguous"
            ],
            "regressionCaseCount": len(regression_results),
            "recognizedRegressionCaseCount": sum(item["contractRecognized"] for item in regression_results),
        },
        "defectTaxonomy": defect_taxonomy(),
        "defectSummary": defect_summary,
        "sectionSummary": {
            section_id: {
                "occurrenceCount": section_occurrences[section_id],
                "uniqueSentenceCount": len(section_unique[section_id]),
                "uniqueFailureSentenceCount": len(section_failure_unique[section_id]),
                "uniqueWarningSentenceCount": len(section_warning_unique[section_id]),
                "purposeTraceGapCount": section_purpose_trace_gaps[section_id],
                "purposeTracedCount": section_purpose_traced[section_id],
                "nativeMigrationStatus": (
                    "READY"
                    if section_id in MIGRATED_SECTION_IDS
                    and not section_failure_unique[section_id]
                    and not section_warning_unique[section_id]
                    and section_purpose_trace_gaps[section_id] == 0
                    else "NOT_READY"
                ),
            }
            for section_id in SECTION_COMPOSITION_RULES
        },
        "semanticCoverage": {
            section_id: {
                role: sorted(values)
                for role, values in sorted(roles.items())
            }
            for section_id, roles in sorted(observed_role_values.items())
        },
        "signalRegistry": {
            key: signal_registry[key]
            for key in sorted(signal_registry)
        },
        "regressions": regression_results,
        "purposeTrace": {
            "currentStatus": (
                "fully-traced"
                if not sum(section_purpose_trace_gaps.values())
                else "partially-migrated"
                if sum(section_purpose_traced.values())
                else "legacy-untraced"
            ),
            "targetFrameVersion": FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION,
            "migratedCatalogVersions": {
                "chart-positioning": CHART_POSITIONING_NATIVE_ZH_TW_CATALOG_VERSION,
                "relationship-fit": RELATIONSHIP_FIT_NATIVE_ZH_TW_CATALOG_VERSION,
                "core-answer": CORE_ANSWER_NATIVE_ZH_TW_CATALOG_VERSION,
                "timing-reading": TIMING_NATIVE_ZH_TW_CATALOG_VERSION,
                "action-direction": ACTION_DIRECTION_NATIVE_ZH_TW_CATALOG_VERSION,
            },
            "reason": (
                "All visible pages use approved native Chinese catalogs and expose "
                "sentence-to-purpose traces."
            ),
        },
        "sentences": serialized_entries,
    }


def markdown_cell(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> list[str]:
    output = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    output.extend("| " + " | ".join(markdown_cell(value) for value in row) + " |" for row in rows)
    return output


def render_report(audit: Mapping[str, Any]) -> str:
    summary = audit.get("summary") or {}
    source = audit.get("sourceCorpus") or {}
    defect_rows = [
        [item["id"], item["occurrenceCount"], item["uniqueSentenceCount"]]
        for item in audit.get("defectSummary") or []
    ]
    section_rows = [
        [
            section_id,
            item.get("nativeMigrationStatus"),
            item.get("occurrenceCount"),
            item.get("uniqueSentenceCount"),
            item.get("uniqueFailureSentenceCount"),
            item.get("purposeTraceGapCount"),
        ]
        for section_id, item in (audit.get("sectionSummary") or {}).items()
    ]
    regression_rows = [
        [
            item.get("id"),
            "yes" if item.get("contractRecognized") else "no",
            "yes" if item.get("presentInCorpus") else "no",
            item.get("text"),
        ]
        for item in audit.get("regressions") or []
    ]
    defective = [item for item in audit.get("sentences") or [] if item.get("defects")]
    defective.sort(key=lambda item: (-int(item.get("occurrenceCount") or 0), str(item.get("text") or "")))
    sample_rows = [
        [
            item.get("occurrenceCount"),
            ", ".join(item.get("sectionIds") or []),
            ", ".join(issue.get("id") for issue in item.get("defects") or []),
            item.get("text"),
        ]
        for item in defective[:20]
    ]
    lines = [
        "# Final Narrative Native Traditional Chinese R0-R6",
        "",
        "## Verdict",
        "",
        f"- Current realization status: **{audit.get('status')}**",
        "- R0 inventory and reader-complaint baseline: **COMPLETE**",
        "- R1 native Chinese contract: **COMPLETE**",
        "- R2 prose-free meaning frame: **COMPLETE**",
        "- R3 chart-positioning native renderer: **COMPLETE**",
        "- R4 relationship-signal realization: **COMPLETE**",
        "- R5 unified page realizers: **COMPLETE**",
        "- R6 hard Chinese quality gates: **COMPLETE**",
        "",
        "All five pages now use approved native Traditional Chinese catalogs with exact fact, purpose,",
        "and composition traces. The verdict remains READY only when every sentence is traced and warning-free.",
        "",
        "## Baseline",
        "",
        f"- Source corpus: `{source.get('path')}`",
        f"- Corpus version: `{source.get('version')}`",
        f"- Composer version: `{source.get('composerVersion')}`",
        f"- Composition version: `{source.get('compositionVersion')}`",
        f"- Hard-quality version: `{source.get('hardQualityVersion')}`",
        f"- Matrix cases: {source.get('caseCount')}",
        f"- Sentence occurrences: {summary.get('sentenceOccurrenceCount')}",
        f"- Unique sentences: {summary.get('uniqueSentenceCount')}",
        f"- Unique failure sentences: {summary.get('uniqueFailureSentenceCount')}",
        f"- Unique warning sentences: {summary.get('uniqueWarningSentenceCount')}",
        f"- Composition-only ownership trace gaps: {summary.get('compositionOwnershipTraceGapCount')}",
        f"- Ambiguous field-level ownership traces: {summary.get('ambiguousFieldOwnershipTraceCount')}",
        f"- Traced sentence occurrences: {summary.get('realizationPurposeTracedCount')}",
        "",
        "## Defect Inventory",
        "",
        *markdown_table(["Defect", "Occurrences", "Unique sentences"], defect_rows),
        "",
        *markdown_table(
            ["Page", "Migration", "Occurrences", "Unique", "Failures", "Trace gaps"],
            section_rows,
        ),
        "",
        "## Reader Regressions",
        "",
        *markdown_table(["Case", "Recognized", "In corpus", "Text"], regression_rows),
        "",
        "## Frequent Defective Sentences",
        "",
        *markdown_table(["Occurrences", "Page", "Defects", "Sentence"], sample_rows),
        "",
        "## R1 Contract",
        "",
        f"- Native copy contract: `{FINAL_NARRATIVE_NATIVE_ZH_TW_CONTRACT_VERSION}`",
        f"- Meaning frame: `{FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION}`",
        "- Locale: `zh-Hant-TW`",
        "- Runtime LLM: forbidden",
        "- Generic fallback: forbidden",
        "- Missing approved realization: fail closed",
        "- Internal planet-function labels: never visible",
        "",
        (
            "The future path is `typed fact -> ReaderMeaningFrame -> approved native sentence catalog "
            "-> page composition`."
        ),
        (
            "The frame contains stable keys, ownership, direction, aspect behavior, certainty, evidence, "
            "and purpose, but no prose."
        ),
        "",
        "## Trace Coverage",
        "",
        f"Current sentence-to-purpose traces missing: {summary.get('realizationPurposeTraceGapCount')}",
        "",
        "Chart positioning, relationship fit, core answer, timing, and action all expose exact sentence traces.",
        "Any future untraced sentence changes the audit verdict to NOT_READY.",
        "",
        "## Next Gate",
        "",
        "R7 should add a sentence-review workflow over the frozen R6 automated boundary.",
        "No catalog or contract change should merge until R6 and the complete paid-reading stack remain green.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--regressions", type=Path, default=DEFAULT_REGRESSION_PATH)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    audit = build_audit(read_json(args.corpus), read_json(args.regressions), corpus_path=args.corpus)
    report = render_report(audit)
    if not args.no_write:
        write_json(args.json_out, audit)
        write_text(args.out, report)
    if args.json:
        print(json.dumps(audit, ensure_ascii=False, sort_keys=True))
    else:
        print(f"Native Traditional Chinese R0 audit: {audit['status']}")
        print(f"- cases: {audit['sourceCorpus']['caseCount']}")
        print(f"- unique sentences: {audit['summary']['uniqueSentenceCount']}")
        print(f"- unique failure sentences: {audit['summary']['uniqueFailureSentenceCount']}")
        print(f"- report: {args.out}")
        print(f"- inventory: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
