#!/usr/bin/env python3
"""Report which reducer evidence powers each paid V1 result surface."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
)


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "18-paid-v1-result-surface-evidence.md"
READING_PATHS = (
    ROOT / "examples" / "readings" / "cold-war-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-long-any-chance.json",
    ROOT / "examples" / "readings" / "cold-war-when-to-contact.json",
    ROOT / "examples" / "readings" / "broke-up-recent-what-did-i-do-wrong.json",
    ROOT / "examples" / "readings" / "crisis-stay-or-let-go.json",
    ROOT / "examples" / "readings" / "broke-up-recent-still-love-me.json",
    ROOT / "examples" / "readings" / "blocked-anxious-still-love-me.json",
    ROOT / "examples" / "readings" / "no-contact-desperate-when-to-contact.json",
    ROOT / "examples" / "readings" / "still-in-contact-self-blaming-what-did-i-do-wrong.json",
    ROOT / "examples" / "readings" / "ambiguous-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-long-release-stay-or-let-go.json",
)
TIMING_SELECTOR_KEYS = (
    "timingMercuryCommunication",
    "timingVenusSoftening",
    "timingMarsActivation",
    "timingSaturnPressure",
    "timingMoonWeather",
)
REQUIRED_TIMING_ACTIONS = {
    "avoid_push",
    "low_pressure_message",
    "observe_only",
}


@dataclass(frozen=True)
class SurfaceSpec:
    id: str
    section: str
    role: str
    value_path: str
    evidence_paths: tuple[str, ...]
    theme_required: bool = False


SURFACES = (
    SurfaceSpec(
        id="relationshipProfiles.personA",
        section="01 星盤定位",
        role="Reader-facing profile cards for the user's Moon/Mercury/Venus/Mars/Saturn relationship functions.",
        value_path="viewModel.relationshipProfiles.personA",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.birthDataQuality",
            "westernRelationshipCaseFile.evidenceClusters.identityNeeds",
            "westernRelationshipCaseFile.evidenceClusters.planetSignStyle",
            "westernRelationshipCaseFile.evidenceClusters.moonSignEmotionalSafety",
            "westernRelationshipCaseFile.evidenceClusters.mercurySignCommunicationRepair",
            "westernRelationshipCaseFile.evidenceClusters.venusSignAffectionStyle",
            "westernRelationshipCaseFile.evidenceClusters.marsSignPursuitConflict",
            "westernRelationshipCaseFile.evidenceClusters.saturnSignDefenseDelay",
        ),
    ),
    SurfaceSpec(
        id="relationshipProfiles.personB",
        section="01 星盤定位",
        role="Reader-facing profile cards for the partner's Moon/Mercury/Venus/Mars/Saturn relationship functions.",
        value_path="viewModel.relationshipProfiles.personB",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.birthDataQuality",
            "westernRelationshipCaseFile.evidenceClusters.identityNeeds",
            "westernRelationshipCaseFile.evidenceClusters.planetSignStyle",
            "westernRelationshipCaseFile.evidenceClusters.moonSignEmotionalSafety",
            "westernRelationshipCaseFile.evidenceClusters.mercurySignCommunicationRepair",
            "westernRelationshipCaseFile.evidenceClusters.venusSignAffectionStyle",
            "westernRelationshipCaseFile.evidenceClusters.marsSignPursuitConflict",
            "westernRelationshipCaseFile.evidenceClusters.saturnSignDefenseDelay",
        ),
    ),
    SurfaceSpec(
        id="relationshipProfiles.fitSummary",
        section="02 兩個人的關係契合度分析",
        role="Natural fit, effort, and friction buckets before the core question answer.",
        value_path="viewModel.relationshipProfiles.fitSummary",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.elementComparison",
            "westernRelationshipCaseFile.evidenceClusters.luminaryComparison",
            "westernRelationshipCaseFile.evidenceClusters.safetyValidationLanguage",
            "westernRelationshipCaseFile.evidenceClusters.aspectPriority",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
    ),
    SurfaceSpec(
        id="relationshipProfiles.fitSummary.pivotalAspect",
        section="02 兩個人的關係契合度分析",
        role="Pivotal synastry aspect card with pair-template meaning and single-aspect guardrail.",
        value_path="viewModel.relationshipProfiles.fitSummary.pivotalAspect",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.selectedCombinations",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
            "viewModel.relationshipProfiles.fitSummary.pivotalAspect.pairContactTemplate",
            "viewModel.relationshipProfiles.fitSummary.pivotalAspect.pairContactTemplateMeaning",
            "viewModel.relationshipProfiles.fitSummary.pivotalAspect.pairContactTemplateGuardrail",
        ),
    ),
    SurfaceSpec(
        id="relationshipArchetype",
        section="01 星盤定位",
        role="Dynamic relationship title such as high-attraction/high-friction, conflict-growth, or emotional-safety archetype.",
        value_path="viewModel.relationshipArchetype",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.relationshipArchetype",
            "westernRelationshipCaseFile.evidenceClusters.relationshipArchetype",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
        ),
    ),
    SurfaceSpec(
        id="attractionDynamics",
        section="02 兩個人的關係契合度分析",
        role="Core attraction aspects, including Venus-Mars, Sun-Moon, Moon-Moon, Moon-Venus, or Sun-Venus when present.",
        value_path="viewModel.attractionDynamics",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.attractionDynamics",
            "westernRelationshipCaseFile.evidenceClusters.attractionDynamics",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
        ),
    ),
    SurfaceSpec(
        id="conflictDynamics",
        section="02 兩個人的關係契合度分析",
        role="Conflict and pressure aspects, including Saturn, Mars, Mercury-Mars, or hard contact patterns.",
        value_path="viewModel.conflictDynamics",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.conflictDynamics",
            "westernRelationshipCaseFile.evidenceClusters.conflictDynamics",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
        ),
    ),
    SurfaceSpec(
        id="growthDynamics",
        section="02 兩個人的關係契合度分析",
        role="Growth/support aspects and explicit gaps for Chiron/Node when unsupported.",
        value_path="viewModel.growthDynamics",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.growthDynamics",
            "westernRelationshipCaseFile.evidenceClusters.growthDynamics",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
        ),
    ),
    SurfaceSpec(
        id="partnerNeeds",
        section="03 核心問題解讀",
        role="Partner-needs block framed as chart-based stability conditions, not mind-reading.",
        value_path="viewModel.partnerNeeds",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.partnerNeeds",
            "westernRelationshipCaseFile.evidenceClusters.partnerNeeds",
            "westernRelationshipCaseFile.evidenceClusters.identityNeeds",
        ),
    ),
    SurfaceSpec(
        id="relationshipTurningWindows",
        section="04 時機判讀",
        role="Relationship timing climate windows with precise-date promises blocked.",
        value_path="viewModel.relationshipTurningWindows",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.relationshipTurningWindows",
            "westernRelationshipCaseFile.evidenceClusters.relationshipTurningWindows",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
        ),
    ),
    SurfaceSpec(
        id="fightLandmines",
        section="05 行動方向",
        role="Three concrete fight landmines selected from conflict/communication evidence.",
        value_path="viewModel.fightLandmines",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.fightLandmines",
            "westernRelationshipCaseFile.evidenceClusters.fightLandmines",
            "westernRelationshipCaseFile.evidenceClusters.conflictDynamics",
        ),
    ),
    SurfaceSpec(
        id="survivalGuide",
        section="05 行動方向",
        role="Five concrete survival-guide suggestions derived from attraction, conflict, needs, growth, and timing evidence.",
        value_path="viewModel.survivalGuide",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipInsightLayer.survivalGuide",
            "westernRelationshipCaseFile.evidenceClusters.survivalGuide",
            "westernRelationshipCaseFile.evidenceClusters.attractionDynamics",
            "westernRelationshipCaseFile.evidenceClusters.conflictDynamics",
            "westernRelationshipCaseFile.evidenceClusters.partnerNeeds",
        ),
    ),
    SurfaceSpec(
        id="relationshipThesis",
        section="Hidden synthesis layer",
        role="Evidence-linked relationship thesis used by finalInterpretation to convert chart/context signals into a case-specific interaction mechanism.",
        value_path="viewModel.relationshipThesis",
        evidence_paths=(
            "westernRelationshipCaseFile.relationshipThesis",
            "westernRelationshipCaseFile.evidenceClusters.relationshipThesis",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
        ),
    ),
    SurfaceSpec(
        id="reading.answer",
        section="03 核心問題解讀",
        role="Top-level answer shown as the user's direct relationship answer.",
        value_path="viewModel.reading.answer",
        evidence_paths=(
            "westernRelationshipCaseFile.answerLayer",
            "westernRelationshipCaseFile.answerLayer.evidenceContract",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
    ),
    SurfaceSpec(
        id="metrics",
        section="03 核心問題解讀",
        role="Compact summary chips; now expected to use the dominant repeated relationship theme.",
        value_path="viewModel.metrics",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="includedReadingRows",
        section="03 核心問題解讀",
        role="Rows that explain what the complete paid reading includes.",
        value_path="viewModel.includedReadingRows",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
            "westernRelationshipCaseFile.answerLayer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="answerGuidance",
        section="03 核心問題解讀",
        role="Structured answer block with short answer, evidence highlights, next move, and readable interpretation.",
        value_path="viewModel.answerGuidance",
        evidence_paths=(
            "westernRelationshipCaseFile.answerLayer",
            "westernRelationshipCaseFile.answerLayer.evidenceContract",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="reasons",
        section="03 核心問題解讀",
        role="Reason cards that explain why the answer leans the way it does.",
        value_path="viewModel.reasons",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="chance",
        section="03 核心問題解讀",
        role="Chance notes framed as conditional opportunity, not guaranteed outcome.",
        value_path="viewModel.chance",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
            "westernRelationshipCaseFile.answerLayer.evidenceContract",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="readableQuestionAnswer.sections.answer",
        section="03 核心問題解讀",
        role="Mirrored readable answer section used by result-page renderers.",
        value_path="viewModel.readableQuestionAnswer.sections.answer",
        evidence_paths=(
            "westernRelationshipCaseFile.answerLayer",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="timingGuidance",
        section="04 時機判讀",
        role="Timing guidance based on public trend windows and contact reducer output.",
        value_path="viewModel.timingGuidance",
        evidence_paths=(
            "westernRelationshipCaseFile.timingLayer.windowScan",
            "westernRelationshipCaseFile.evidenceClusters.timingWindowBand",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.timingMercuryCommunication",
            "westernRelationshipCaseFile.evidenceClusters.timingVenusSoftening",
            "westernRelationshipCaseFile.evidenceClusters.timingMarsActivation",
            "westernRelationshipCaseFile.evidenceClusters.timingSaturnPressure",
            "westernRelationshipCaseFile.evidenceClusters.timingMoonWeather",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="timeline",
        section="04 時機判讀",
        role="Near-term pacing steps; treated as an action sequence, not exact prediction dates.",
        value_path="viewModel.timeline",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.timingWindowBand",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="readableQuestionAnswer.sections.timing",
        section="04 時機判讀",
        role="Mirrored readable timing section used by result-page renderers.",
        value_path="viewModel.readableQuestionAnswer.sections.timing",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.timingWindowBand",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="readableQuestionAnswer.sections.timeline",
        section="04 時機判讀",
        role="Mirrored readable timeline section used by result-page renderers.",
        value_path="viewModel.readableQuestionAnswer.sections.timeline",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.timingWindowBand",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="actionGuidance",
        section="05 行動方向",
        role="Concrete next-move guidance after contact policy and timing reducer boundaries.",
        value_path="viewModel.actionGuidance",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="readableQuestionAnswer.sections.action",
        section="05 行動方向",
        role="Mirrored readable action section used by result-page renderers.",
        value_path="viewModel.readableQuestionAnswer.sections.action",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="readableQuestionAnswer.sections.donts",
        section="05 行動方向",
        role="Boundary and don't cards; these must follow the repeated relationship theme when present.",
        value_path="viewModel.readableQuestionAnswer.sections.donts",
        evidence_paths=(
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination.repeatedThemeReducer",
        ),
        theme_required=True,
    ),
    SurfaceSpec(
        id="readingBlueprint",
        section="Why this judgment",
        role="Evidence blueprint used by narrative/prompt/runtime to prove the answer is Western-only.",
        value_path="viewModel.readingBlueprint",
        evidence_paths=(
            "westernRelationshipCaseFile.methodTrace",
            "westernRelationshipCaseFile.evidenceClusters.aspectFunctionCombination",
            "westernRelationshipCaseFile.evidenceClusters.timingContactReducer",
            "westernRelationshipCaseFile.evidenceClusters.contactSituationPolicy",
        ),
    ),
)


@dataclass
class SurfaceAudit:
    example_id: str
    surface: SurfaceSpec
    present: bool
    evidence_ok: bool
    theme_ok: bool
    theme_keys: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    claim_ids: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.present and self.evidence_ok and self.theme_ok


@dataclass
class ExampleAudit:
    path: Path
    view_model: dict[str, Any]
    audits: list[SurfaceAudit]
    errors: list[str]


def md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(md_escape(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def unique(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def compact(values: Iterable[Any], *, limit: int = 8) -> str:
    items = unique(values)
    if len(items) > limit:
        return ", ".join(items[:limit]) + f", +{len(items) - limit} more"
    return ", ".join(items)


def path_value(view_model: dict[str, Any], path: str) -> Any:
    roots = {
        "viewModel": view_model,
        "westernRelationshipCaseFile": view_model.get("westernRelationshipCaseFile") or {},
    }
    parts = path.split(".")
    current: Any = roots.get(parts[0])
    for part in parts[1:]:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (dict, list, str, tuple, set)):
        return bool(value)
    return True


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def direct_theme_key(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    relationship_theme = value.get("relationshipTheme")
    if isinstance(relationship_theme, dict) and relationship_theme.get("themeKey"):
        return str(relationship_theme.get("themeKey") or "")
    return str(value.get("themeKey") or "")


def surface_theme_keys(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(unique(direct_theme_key(item) for item in value if isinstance(item, dict)))
    return tuple(unique([direct_theme_key(value)]))


def collect_claim_ids(value: Any) -> list[str]:
    claim_ids: list[str] = []
    for item in walk(value):
        if not isinstance(item, dict):
            continue
        for key in ("methodClaimIds", "sourceClaimIds", "claimIds", "questionClaimIds", "runtimeClaimIds"):
            raw = item.get(key)
            if isinstance(raw, list):
                claim_ids.extend(str(claim_id) for claim_id in raw if claim_id)
            elif raw:
                claim_ids.append(str(raw))
    return unique(claim_ids)


def evidence_alias(path: str) -> str:
    prefixes = (
        "westernRelationshipCaseFile.evidenceClusters.",
        "westernRelationshipCaseFile.",
        "viewModel.",
    )
    for prefix in prefixes:
        if path.startswith(prefix):
            return path[len(prefix) :]
    return path


def dominant_theme(view_model: dict[str, Any]) -> dict[str, str]:
    reducer = (
        ((view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {})
        .get("aspectFunctionCombination", {})
        .get("repeatedThemeReducer", {})
    )
    return {
        "key": str(reducer.get("dominantRepeatedThemeKey") or ""),
        "label": str(reducer.get("dominantRepeatedThemeLabel") or ""),
    }


def audit_surface(view_model: dict[str, Any], example_id: str, surface: SurfaceSpec) -> SurfaceAudit:
    value = path_value(view_model, surface.value_path)
    theme = dominant_theme(view_model)
    theme_keys = surface_theme_keys(value)
    missing_evidence = tuple(path for path in surface.evidence_paths if not is_present(path_value(view_model, path)))
    if surface.theme_required:
        expected_key = theme["key"]
        if isinstance(value, list):
            item_count = len([item for item in value if isinstance(item, dict)])
            theme_ok = bool(expected_key) and item_count > 0 and len(theme_keys) == 1 and theme_keys[0] == expected_key
        else:
            theme_ok = bool(expected_key) and len(theme_keys) == 1 and theme_keys[0] == expected_key
    else:
        theme_ok = True
    claim_ids = collect_claim_ids(value)
    for evidence_path in surface.evidence_paths:
        claim_ids.extend(collect_claim_ids(path_value(view_model, evidence_path)))
    return SurfaceAudit(
        example_id=example_id,
        surface=surface,
        present=is_present(value),
        evidence_ok=not missing_evidence,
        theme_ok=theme_ok,
        theme_keys=theme_keys,
        missing_evidence=missing_evidence,
        claim_ids=tuple(unique(claim_ids)),
    )


def exact_timing_public_only(view_model: dict[str, Any]) -> bool:
    case = view_model.get("westernRelationshipCaseFile") or {}
    timing_layer = case.get("timingLayer") or {}
    window_scan = timing_layer.get("windowScan") or {}
    clusters = case.get("evidenceClusters") or {}
    contact_reducer = clusters.get("timingContactReducer") or {}
    timing_guidance = view_model.get("timingGuidance") or {}
    return (
        window_scan.get("preciseDatesAvailable") is False
        and contact_reducer.get("preciseDatesAvailable") is False
        and timing_guidance.get("preciseDatesAvailable") is False
    )


def audit_example(path: Path, articles: dict[str, dict[str, Any]], claims_by_article: dict[str, list[dict[str, Any]]]) -> ExampleAudit:
    reading = read_json(path)
    payload = build_payload(reading, include_drafts=True, select=True)
    view_model = build_view_model(payload, articles, claims_by_article)
    example_id = str(view_model.get("id") or reading.get("reading_id") or path.stem)
    audits = [audit_surface(view_model, example_id, surface) for surface in SURFACES]
    errors: list[str] = []
    for audit in audits:
        if not audit.present:
            errors.append(f"{example_id}: {audit.surface.id} missing")
        if audit.missing_evidence:
            errors.append(
                f"{example_id}: {audit.surface.id} missing evidence "
                + ", ".join(evidence_alias(item) for item in audit.missing_evidence)
            )
        if not audit.theme_ok:
            theme = dominant_theme(view_model)
            errors.append(
                f"{example_id}: {audit.surface.id} theme mismatch, expected {theme['key']}, got {', '.join(audit.theme_keys) or 'none'}"
            )

    case = view_model.get("westernRelationshipCaseFile") or {}
    clusters = case.get("evidenceClusters") or {}
    if not ((clusters.get("aspectFunctionCombination") or {}).get("repeatedThemeReducer") or {}).get("dominantRepeatedThemeKey"):
        errors.append(f"{example_id}: repeated theme reducer has no dominant theme")
    if not exact_timing_public_only(view_model):
        errors.append(f"{example_id}: timing surfaces leaked precise date availability")
    return ExampleAudit(path=path, view_model=view_model, audits=audits, errors=errors)


def timing_summary(view_model: dict[str, Any]) -> dict[str, Any]:
    clusters = (view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {}
    contact_reducer = clusters.get("timingContactReducer") or {}
    window_band = clusters.get("timingWindowBand") or {}
    selectors = [
        f"{key}:{(clusters.get(key) or {}).get('dominantContactType') or 'none'}"
        for key in TIMING_SELECTOR_KEYS
    ]
    return {
        "action": contact_reducer.get("recommendedAction") or "",
        "mode": contact_reducer.get("contactMode") or "",
        "band": window_band.get("topBand") or "",
        "selectors": selectors,
    }


def contact_summary(view_model: dict[str, Any]) -> dict[str, Any]:
    policy = ((view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {}).get("contactSituationPolicy") or {}
    return {
        "status": policy.get("statusKey") or "",
        "actionMode": policy.get("actionMode") or "",
        "canSuggestDirectContact": policy.get("canSuggestDirectContact"),
    }


def surface_summary_rows(example_audits: list[ExampleAudit]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    total_examples = len(example_audits)
    for surface in SURFACES:
        audits = [audit for example in example_audits for audit in example.audits if audit.surface.id == surface.id]
        ok_count = sum(1 for audit in audits if audit.ok)
        present_count = sum(1 for audit in audits if audit.present)
        theme_keys = sorted({key for audit in audits for key in audit.theme_keys})
        claim_ids = unique(claim_id for audit in audits for claim_id in audit.claim_ids)
        missing = sorted({evidence_alias(path) for audit in audits for path in audit.missing_evidence})
        if ok_count == total_examples:
            status = "ok"
        elif present_count == total_examples and not missing:
            status = "theme drift"
        elif present_count:
            status = "partial"
        else:
            status = "missing"
        rows.append(
            [
                surface.section,
                surface.id,
                status,
                f"{ok_count}/{total_examples}",
                "required" if surface.theme_required else "not required",
                compact(theme_keys, limit=5),
                compact(evidence_alias(path) for path in surface.evidence_paths),
                compact(claim_ids, limit=6),
                compact(missing, limit=5),
            ]
        )
    return rows


def example_summary_rows(example_audits: list[ExampleAudit]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for example in example_audits:
        view_model = example.view_model
        context = view_model.get("context") or {}
        theme = dominant_theme(view_model)
        timing = timing_summary(view_model)
        contact = contact_summary(view_model)
        theme_required = [audit for audit in example.audits if audit.surface.theme_required]
        theme_ok_count = sum(1 for audit in theme_required if audit.theme_ok)
        rows.append(
            [
                view_model.get("id") or example.path.stem,
                f"{context.get('relationship_stage')} / {context.get('main_question')} / {context.get('contact_status')}",
                f"{theme['key']} / {theme['label']}",
                f"{theme_ok_count}/{len(theme_required)}",
                f"{timing['action']} / {timing['band']} / {timing['mode']}",
                f"{contact['status']} / {contact['actionMode']} / direct={contact['canSuggestDirectContact']}",
                compact(timing["selectors"], limit=5),
                "ok" if not example.errors else f"{len(example.errors)} errors",
            ]
        )
    return rows


def timing_observation(example_audits: list[ExampleAudit]) -> str:
    actions = timing_actions(example_audits)
    bands = [str(timing_summary(example.view_model).get("band") or "") for example in example_audits]
    unique_actions = unique(actions)
    unique_bands = unique(bands)
    if len(unique_actions) == 1 and len(unique_bands) == 1:
        return (
            f"These {len(example_audits)} paid-example readings currently all resolve to `{unique_actions[0]}` / `{unique_bands[0]}`. "
            "That is acceptable for this surface audit because it checks paid-result wiring, but timing-branch behavior "
            "still needs the dedicated timing reducer fixture matrix for Mercury, Venus, Mars, Saturn, neutral, and missing-scan branches."
        )
    return (
        f"These {len(example_audits)} paid-example readings cover timing actions `{', '.join(unique_actions)}` "
        f"and timing bands `{', '.join(unique_bands)}`. "
        "The dedicated timing reducer matrix still proves the full Mercury, Venus, Mars, Saturn, neutral, and missing-scan branch set."
    )


def timing_actions(example_audits: list[ExampleAudit]) -> list[str]:
    return [str(timing_summary(example.view_model).get("action") or "") for example in example_audits]


def timing_action_count_rows(example_audits: list[ExampleAudit]) -> list[list[Any]]:
    counts = Counter(timing_actions(example_audits))
    rows: list[list[Any]] = []
    for action in sorted(set(counts) | REQUIRED_TIMING_ACTIONS):
        rows.append(
            [
                action,
                counts.get(action, 0),
                "yes" if action in REQUIRED_TIMING_ACTIONS else "no",
            ]
        )
    return rows


def timing_action_errors(example_audits: list[ExampleAudit]) -> list[str]:
    observed = set(timing_actions(example_audits))
    missing = sorted(REQUIRED_TIMING_ACTIONS - observed)
    if not missing:
        return []
    return [
        "paid example timing action coverage missing required actions: "
        + ", ".join(missing)
    ]


def section_rollup_rows(example_audits: list[ExampleAudit]) -> list[list[Any]]:
    sections = unique(surface.section for surface in SURFACES)
    rows: list[list[Any]] = []
    for section in sections:
        audits = [
            audit
            for example in example_audits
            for audit in example.audits
            if audit.surface.section == section
        ]
        rows.append(
            [
                section,
                len({audit.surface.id for audit in audits}),
                f"{sum(1 for audit in audits if audit.ok)}/{len(audits)}",
                compact(sorted({evidence_alias(path) for audit in audits for path in audit.surface.evidence_paths}), limit=10),
            ]
        )
    return rows


def build_report(example_audits: list[ExampleAudit]) -> str:
    errors = [error for example in example_audits for error in example.errors]
    errors.extend(timing_action_errors(example_audits))
    lines = [
        "# Paid V1 Result Surface Evidence",
        "",
        f"Generated from {len(example_audits)} paid V1 example readings and the live `complete_relationship_result_runtime` view-model builder.",
        "",
        "## Purpose",
        "",
        "This report maps each visible paid-result surface to the reducer or evidence layer that powers it. It is meant to keep the new result-page design honest: every card should be traceable to Western calculation, context boundary, repeated-theme reduction, timing reduction, or the reading blueprint.",
        "",
        "## Gate Result",
        "",
        "Status: " + ("PASS" if not errors else "FAIL"),
        "",
        md_table(
            ["Section", "Surface count", "Passing surface checks", "Primary evidence/reducers"],
            section_rollup_rows(example_audits),
        ),
        "",
        "## Example Matrix",
        "",
        md_table(
            [
                "Example",
                "Context",
                "Dominant repeated theme",
                "Theme surfaces",
                "Timing reducer",
                "Contact policy",
                "Timing selector states",
                "Status",
            ],
            example_summary_rows(example_audits),
        ),
        "",
        "Timing note: " + timing_observation(example_audits),
        "",
        "## Timing Action Coverage",
        "",
        "These paid examples must keep at least one visible-result fixture for each required action branch. The dedicated timing reducer matrix remains responsible for lower-level Mercury, Venus, Mars, Saturn, neutral, and missing-scan branch coverage.",
        "",
        md_table(
            ["Timing action", "Example count", "Required in paid examples"],
            timing_action_count_rows(example_audits),
        ),
        "",
        "## Surface Matrix",
        "",
        md_table(
            [
                "Section",
                "Surface",
                "Status",
                "Examples",
                "Theme metadata",
                "Observed theme keys",
                "Evidence paths",
                "Claim ids",
                "Missing evidence",
            ],
            surface_summary_rows(example_audits),
        ),
        "",
        "## Surface Roles",
        "",
    ]
    for surface in SURFACES:
        lines.extend(
            [
                f"### {surface.id}",
                "",
                f"- Section: {surface.section}",
                f"- Role: {surface.role}",
                f"- Value path: `{surface.value_path}`",
                f"- Evidence: {', '.join(f'`{evidence_alias(path)}`' for path in surface.evidence_paths)}",
                f"- Theme metadata required: {'yes' if surface.theme_required else 'no'}",
                "",
            ]
        )
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    lines.extend(
        [
            "## Reading Rule",
            "",
            "When a result-page component renders one of these surfaces, it should not invent an interpretation from display copy alone. The component should render the surface payload and, when useful, expose the related `relationshipTheme`, `relationshipThesis`, `sourceClaimIds`, `methodClaimIds`, timing reducer state, and contact-policy boundary for audit/debug views.",
            "",
            "If a new paid result card is added, add it to this report first, define the evidence paths that justify it, then wire the renderer. That keeps the frontend flow aligned with the calculation and KB method instead of drifting into generic comfort copy.",
            "",
        ]
    )
    return "\n".join(lines)


def load_example_audits() -> list[ExampleAudit]:
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims_by_article = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    return [audit_example(path, articles, claims_by_article) for path in READING_PATHS]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate paid V1 result surface evidence report.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    parser.add_argument("--check", action="store_true", help="Validate without writing and fail if the report is stale.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    report = build_report(load_example_audits())
    errors_present = "Status: FAIL" in report
    if args.check:
        if errors_present:
            print(report)
            return 1
        if not out_path.exists():
            print(f"Missing paid V1 surface evidence report: {out_path.relative_to(ROOT)}")
            return 1
        if out_path.read_text(encoding="utf-8") != report:
            print(f"Paid V1 surface evidence report is stale: {out_path.relative_to(ROOT)}")
            return 1
        print("Paid V1 result surface evidence report passed")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    if errors_present:
        print(f"Wrote failing paid V1 surface evidence report -> {out_path.relative_to(ROOT)}")
        return 1
    print(f"Wrote paid V1 surface evidence report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
