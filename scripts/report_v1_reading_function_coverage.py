#!/usr/bin/env python3
"""Generate a V1 reading-function coverage report from method digest usage."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_digests import MethodClaim, flattened_digests, load_book_digest_files
from kb_utils import ROOT, read_text
from method_claim_usage import ClaimUsageRecord, active_artifact_types, build_method_claim_usage_records, target_patterns


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "15-western-v1-reading-function-coverage.md"
STRUCTURED_ARTIFACT_TYPES = {"atom", "rule", "question_blueprint", "guardrail"}
RUNTIME_ARTIFACT_TYPES = {"runtime_builder", "runtime_trace"}
VISIBLE_ARTIFACT_TYPES = {"frontend_result", "readable_renderer", "narrative_prompt"}
SCENARIO_TARGET_ALIASES = {
    "angleHouseFramework": ("Asc", "Desc", "house", "houses", "overlay", "location_fallback", "precision"),
    "birthDataQuality": ("birthDataQuality", "birth time", "birthplace", "location_fallback", "precision"),
    "relationshipChartLayer": ("relationshipChartLayer", "relationship chart", "composite", "Davison"),
    "compositeLayer": ("compositeLayer", "relationship chart", "composite", "Davison"),
    "timingMercuryMessage": ("timingMercuryCommunication", "Mercury", "message", "low-pressure"),
}


@dataclass(frozen=True)
class ReadingFunction:
    id: str
    title: str
    purpose: str
    required_targets: tuple[str, ...]
    visible_targets: tuple[str, ...] = ()


V1_FUNCTIONS = (
    ReadingFunction(
        id="profile-positioning",
        title="01 星盤定位",
        purpose="Separate each person's natal relationship needs before judging the relationship.",
        required_targets=(
            "relationshipProfiles",
            "personProfile",
            "identityNeeds",
            "natalRelationshipNeeds",
            "planetSignStyle",
            "moonSignEmotionalSafety",
            "mercurySignCommunicationRepair",
            "venusSignAffectionStyle",
            "marsSignPursuitConflict",
            "saturnSignDefenseDelay",
            "functionElementMatrix",
            "functionModalityMatrix",
            "birthDataQuality",
            "precisionWarnings",
        ),
        visible_targets=("relationshipProfiles", "personProfile", "readableInterpretation", "precisionWarnings"),
    ),
    ReadingFunction(
        id="relationship-fit",
        title="02 兩個人的關係契合度分析",
        purpose="Combine synastry, safety, attraction, pressure, communication, and repair without turning one aspect into a verdict.",
        required_targets=(
            "relationshipFit",
            "fitSummary",
            "elementComparison",
            "luminaryComparison",
            "aspectPriority",
            "aspectContactModifier",
            "aspectFunctionCombination",
            "aspectPairContactTemplate",
            "attraction",
            "emotionalSafety",
            "pressure",
            "communication",
            "repair",
            "safetyValidationLanguage",
            "evidenceReducer",
        ),
        visible_targets=("relationshipFit", "fitSummary", "safetyValidationLanguage"),
    ),
    ReadingFunction(
        id="core-question",
        title="03 核心問題解讀",
        purpose="Answer the user's relationship question with calculated evidence, context boundaries, and no mind-reading.",
        required_targets=(
            "answerEvidenceContract",
            "contextModifier",
            "contextReducer",
            "consultationSafety",
            "relationshipResultRules",
            "readableInterpretation",
            "narrative",
            "readingBlueprint",
            "includedReadingRows",
        ),
        visible_targets=("answerGuidance", "answerEvidenceContract", "readableInterpretation", "narrative", "includedReadingRows"),
    ),
    ReadingFunction(
        id="timing",
        title="04 時機判讀",
        purpose="Use current transits and timing reducers as climate and contact rhythm, not guaranteed outcome dates.",
        required_targets=(
            "currentTransits",
            "timingWindowBand",
            "timingContactReducer",
            "contactSituationPolicy",
            "timingMercuryCommunication",
            "timingMercuryMessage",
            "timingVenusSoftening",
            "timingMarsActivation",
            "timingSaturnPressure",
            "timingMoonWeather",
        ),
        visible_targets=("timingWindowBand", "timingContactReducer", "timingGuidance", "timeline"),
    ),
    ReadingFunction(
        id="action-direction",
        title="05 行動方向",
        purpose="Turn the chart and context into safe next steps, contact boundaries, don'ts, and pacing.",
        required_targets=(
            "actionBoundary",
            "actionDirection",
            "contactStatus",
            "contactSituationPolicy",
            "donts",
            "timeline",
            "timingContactReducer",
            "consultationSafety",
        ),
        visible_targets=("actionBoundary", "actionDirection", "donts", "timeline"),
    ),
    ReadingFunction(
        id="blocked-future-layers",
        title="Method limits",
        purpose="Make unavailable precision layers explicit so the result never pretends to calculate houses, overlays, composite, or Davison.",
        required_targets=(
            "angleHouseFramework",
            "houseOverlayLayer",
            "relationshipChartLayer",
            "compositeLayer",
            "birthDataQuality",
            "precisionWarnings",
        ),
        visible_targets=("precisionWarnings",),
    ),
)


def md_escape(value: Any) -> str:
    return str(value or "").replace("\n", "<br>").replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(md_escape(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def claim_index() -> dict[str, tuple[Any, MethodClaim]]:
    return {
        claim.id: (digest, claim)
        for digest in flattened_digests(load_book_digest_files())
        for claim in digest.method_claims
    }


def scenario_paths() -> list[Path]:
    paths = [path for path in (ROOT / "scripts").glob("smoke_western*.py") if path.is_file()]
    web_scripts_dir = ROOT / "apps" / "web" / "scripts"
    if web_scripts_dir.exists():
        paths.extend(path for path in web_scripts_dir.glob("smoke-*.mjs") if path.is_file())
    examples_dir = ROOT / "examples"
    if examples_dir.exists():
        paths.extend(path for path in examples_dir.rglob("*.json") if path.is_file())
    return sorted(paths)


def scenario_targets(targets: set[str]) -> set[str]:
    matched: set[str] = set()
    for path in scenario_paths():
        text = read_text(path)
        for target in targets:
            patterns = {*target_patterns(target), *SCENARIO_TARGET_ALIASES.get(target, ())}
            if any(pattern and pattern in text for pattern in patterns):
                matched.add(target)
    return matched


def records_for_target(records: list[ClaimUsageRecord], target: str) -> list[ClaimUsageRecord]:
    return [record for record in records if target in record.runtime_targets and active_artifact_types(record)]


def target_quality(
    target: str,
    records: list[ClaimUsageRecord],
    claims: dict[str, tuple[Any, MethodClaim]],
    scenario_hits: set[str],
    *,
    visible_required: bool,
) -> tuple[str, str]:
    if not records:
        return "missing", "No active method claim currently supports this target."

    artifact_types = set().union(*(active_artifact_types(record) for record in records))
    claim_objects = [claims[record.claim_id][1] for record in records if record.claim_id in claims]
    has_source_support = any(claim.evidence_level in {"source_backed", "source_guided"} for claim in claim_objects)
    has_line_anchor = any(claim.source_locations for claim in claim_objects)
    has_runtime = bool(artifact_types.intersection(RUNTIME_ARTIFACT_TYPES))
    has_structured = bool(artifact_types.intersection(STRUCTURED_ARTIFACT_TYPES))
    has_visible = bool(artifact_types.intersection(VISIBLE_ARTIFACT_TYPES))
    has_scenario = target in scenario_hits
    has_implemented = any(record.implementation_status == "implemented" for record in records)
    only_blocked = all(record.implementation_status == "blocked" for record in records)

    missing_bits: list[str] = []
    if only_blocked:
        return "blocked", "Explicitly blocked as a future layer or precision limit."
    if not has_source_support:
        missing_bits.append("source-guided/source-backed claim")
    if not has_line_anchor:
        missing_bits.append("line-level source anchor")
    if not has_runtime:
        missing_bits.append("runtime trace/builder")
    if not has_structured:
        missing_bits.append("structured atom/rule/blueprint/guardrail")
    if visible_required and not has_visible:
        missing_bits.append("visible renderer/frontend/narrative artifact")
    if not has_scenario:
        missing_bits.append("scenario smoke coverage")

    if not missing_bits and has_implemented:
        return "strong", "Source-supported, structured, runtime-wired, scenario-covered, and implemented."
    if not missing_bits:
        return "covered", "Source-supported, structured, runtime-wired, and scenario-covered; still marked partial."
    if len(missing_bits) <= 2:
        return "thin", "Missing " + ", ".join(missing_bits) + "."
    return "weak", "Missing " + ", ".join(missing_bits[:4]) + ("." if len(missing_bits) <= 4 else ", ...")


def build_report(records: list[ClaimUsageRecord]) -> str:
    claims = claim_index()
    all_required_targets = {target for reading_function in V1_FUNCTIONS for target in reading_function.required_targets}
    scenario_hits = scenario_targets(all_required_targets)
    lines = [
        "# Western V1 Reading Function Coverage",
        "",
        "Generated from `kb/book_digests`, method-claim runtime usage, smoke scenarios, and example fixtures.",
        "",
        "## Purpose",
        "",
        "This report checks whether each V1 result section is backed by digested book method, structured KB artifacts, runtime wiring, visible output, and scenario coverage. It is stricter than checking whether a source is merely listed in the wiki.",
        "",
        "## Reading Flow Gate",
        "",
        "A V1 section is considered strong only when its required runtime targets have source-backed or source-guided method claims, line-level anchors where applicable, structured atoms/rules/blueprints/guardrails, runtime builder or trace usage, and scenario smoke coverage. Visible sections also need renderer/frontend/narrative usage.",
        "",
    ]

    summary_rows: list[list[Any]] = []
    detail_sections: list[str] = []
    for reading_function in V1_FUNCTIONS:
        rows: list[list[Any]] = []
        statuses: list[str] = []
        visible_targets = set(reading_function.visible_targets)
        for target in reading_function.required_targets:
            target_records = records_for_target(records, target)
            quality, gap = target_quality(
                target,
                target_records,
                claims,
                scenario_hits,
                visible_required=target in visible_targets,
            )
            statuses.append(quality)
            artifact_types = sorted(set().union(*(active_artifact_types(record) for record in target_records)) if target_records else set())
            claim_ids = [record.claim_id for record in target_records[:5]]
            source_ids = sorted({record.source_id for record in target_records})
            rows.append(
                [
                    target,
                    quality,
                    ", ".join(source_ids[:4]),
                    ", ".join(claim_ids),
                    ", ".join(artifact_types),
                    "yes" if target in scenario_hits else "no",
                    gap,
                ]
            )

        missing_count = sum(1 for status in statuses if status == "missing")
        weak_count = sum(1 for status in statuses if status == "weak")
        thin_count = sum(1 for status in statuses if status == "thin")
        strong_count = sum(1 for status in statuses if status == "strong")
        covered_count = sum(1 for status in statuses if status == "covered")
        blocked_count = sum(1 for status in statuses if status == "blocked")
        if missing_count:
            overall = "incomplete"
        elif weak_count:
            overall = "weak"
        elif thin_count:
            overall = "thin"
        elif covered_count:
            overall = "covered"
        else:
            overall = "strong"
        summary_rows.append(
            [
                reading_function.title,
                overall,
                f"{strong_count} strong, {covered_count} covered, {blocked_count} blocked",
                f"{weak_count} weak, {thin_count} thin, {missing_count} missing",
            ]
        )
        detail_sections.extend(
            [
                f"## {reading_function.title}",
                "",
                reading_function.purpose,
                "",
                md_table(
                    [
                        "Runtime target",
                        "Quality",
                        "Sources",
                        "Claims",
                        "Artifacts",
                        "Scenario",
                        "Gap",
                    ],
                    rows,
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Summary",
            "",
            md_table(["V1 function", "Overall", "Coverage", "Gaps"], summary_rows),
            "",
            *detail_sections,
            "## Implementation Rule",
            "",
            "When adding or changing a reading section, update the relevant book digest claim first, wire it into atoms/rules/runtime/readable output, add or extend a smoke scenario, then regenerate this report. If a target is weak or thin, do not use it as a primary paid-result claim yet.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate V1 reading function coverage report.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(build_method_claim_usage_records()), encoding="utf-8")
    print(f"Wrote V1 reading function coverage report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
