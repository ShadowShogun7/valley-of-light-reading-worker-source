#!/usr/bin/env python3
"""Generate a source-to-runtime execution matrix for Western book digestion."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from book_coverage import SourceCoverage, flattened_coverages, load_book_coverage_files, source_manifest_map
from book_digests import BookDigest, MethodClaim, flattened_digests, load_book_digest_files
from kb_utils import ROOT, read_text
from method_claim_usage import ClaimUsageRecord, active_artifact_types, build_method_claim_usage_records, target_patterns
from complete_relationship_result_runtime import WESTERN_METHOD_TRACE_SECTIONS


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "17-western-book-digestion-execution-matrix.md"
SOURCE_GUIDED_POLICY_TYPES = {
    "product_rule",
    "question_selector",
    "advanced_layer_guardrail",
}
VISIBLE_ARTIFACTS = {"frontend_result", "readable_renderer", "narrative_prompt"}
STRUCTURED_ARTIFACTS = {"atom", "rule", "question_blueprint", "guardrail"}
RUNTIME_ARTIFACTS = {"runtime_builder", "runtime_trace"}
SCENARIO_TARGET_ALIASES = {
    "angleHouseFramework": ("Asc", "Desc", "house", "houses", "overlay", "location_fallback", "precision"),
    "birthDataQuality": ("birthDataQuality", "birth time", "birthplace", "location_fallback", "precision"),
    "contactStatus": ("contact_status", "blocked", "no-contact", "limited-contact", "cold-chat", "still-in-contact"),
    "desiredOutcome": ("desired_outcome", "reconnect", "clarity", "move-on"),
    "emotionalRisk": ("emotional_risk", "self-blaming", "desperate", "unsafe-or-overwhelmed", "calm"),
    "relationshipStage": ("relationship_stage", "cold-war", "broke-up-recent", "broke-up-long", "crisis"),
    "relationshipChartLayer": ("relationshipChartLayer", "relationship chart", "composite", "Davison"),
    "compositeLayer": ("compositeLayer", "relationship chart", "composite", "Davison"),
    "timingMercuryMessage": ("timingMercuryCommunication", "Mercury", "message", "low-pressure"),
}


def md_escape(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\n", "<br>").replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(md_escape(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def source_label(source_id: str, sources: dict[str, dict[str, Any]]) -> str:
    source = sources.get(source_id) or {}
    title = source.get("title") or source_id
    author = source.get("author")
    return f"{title} ({author})" if author else str(title)


def short_list(values: list[str] | set[str], limit: int = 5) -> str:
    output = [str(value) for value in values if value]
    if not output:
        return ""
    output = sorted(dict.fromkeys(output))
    suffix = "" if len(output) <= limit else f", +{len(output) - limit} more"
    return ", ".join(output[:limit]) + suffix


def digest_by_source(digests: list[BookDigest]) -> dict[str, list[BookDigest]]:
    output: dict[str, list[BookDigest]] = defaultdict(list)
    for digest in digests:
        output[digest.source_id].append(digest)
    return output


def claims_by_source(digests: list[BookDigest]) -> dict[str, list[MethodClaim]]:
    output: dict[str, list[MethodClaim]] = defaultdict(list)
    for digest in digests:
        output[digest.source_id].extend(digest.method_claims)
    return output


def records_by_claim(records: list[ClaimUsageRecord]) -> dict[str, ClaimUsageRecord]:
    return {record.claim_id: record for record in records}


def records_by_source(records: list[ClaimUsageRecord]) -> dict[str, list[ClaimUsageRecord]]:
    output: dict[str, list[ClaimUsageRecord]] = defaultdict(list)
    for record in records:
        output[record.source_id].append(record)
    return output


def coverage_by_source(coverages: list[SourceCoverage]) -> dict[str, SourceCoverage]:
    return {coverage.source_id: coverage for coverage in coverages}


def v1_section_target_map() -> dict[str, dict[str, Any]]:
    return {
        str(section.get("sectionId")): {
            "title": str(section.get("title") or section.get("sectionId")),
            "targets": {
                str(target)
                for target in [
                    *(section.get("requiredRuntimeTargets") or []),
                    *(section.get("evidenceClusterKeys") or []),
                ]
                if target
            },
            "method_claim_ids": {str(claim_id) for claim_id in section.get("methodClaimIds") or [] if claim_id},
        }
        for section in WESTERN_METHOD_TRACE_SECTIONS
    }


def direct_claim_section_ids(claim: MethodClaim, section_targets: dict[str, dict[str, Any]]) -> set[str]:
    return {
        section_id
        for section_id, section in section_targets.items()
        if claim.id in section["method_claim_ids"]
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


def scenario_hits_for_targets(targets: set[str]) -> set[str]:
    matched: set[str] = set()
    texts = [read_text(path) for path in scenario_paths()]
    for target in targets:
        patterns = {*target_patterns(target), *SCENARIO_TARGET_ALIASES.get(target, ())}
        if any(pattern and pattern in text for text in texts for pattern in patterns):
            matched.add(target)
    return matched


def status_counts(values: list[str]) -> str:
    if not values:
        return ""
    return str(dict(sorted(Counter(values).items())))


def source_runtime_targets(claims: list[MethodClaim]) -> set[str]:
    return {str(target) for claim in claims for target in claim.runtime_targets if target}


def source_artifact_types(records: list[ClaimUsageRecord]) -> set[str]:
    return {artifact for record in records for artifact in active_artifact_types(record)}


def implementation_state(claims: list[MethodClaim], coverage: SourceCoverage | None) -> str:
    claim_statuses = Counter(claim.implementation_status for claim in claims)
    coverage_statuses = Counter(section.status for section in (coverage.sections if coverage else []))
    if coverage_statuses.get("blocked") and sum(coverage_statuses.values()) == coverage_statuses["blocked"]:
        return "blocked"
    if claim_statuses.get("blocked") and sum(claim_statuses.values()) == claim_statuses["blocked"]:
        return "blocked"
    if claim_statuses.get("partial") or claim_statuses.get("not_started"):
        return "needs implementation"
    if (
        claims
        and claim_statuses.get("implemented")
        and claim_statuses.get("implemented") + claim_statuses.get("blocked", 0) == sum(claim_statuses.values())
        and (claim_statuses.get("blocked") or coverage_statuses.get("blocked"))
    ):
        return "runtime implemented + blocked future layer"
    if coverage_statuses.get("reviewed"):
        return "reviewed sections remain to deepen"
    if claims and all(claim.implementation_status == "implemented" for claim in claims):
        return "runtime implemented"
    return "mapped"


def source_guided_policy_complete(claims: list[MethodClaim]) -> bool:
    guided_claims = [
        claim
        for claim in claims
        if claim.evidence_level == "source_guided" and claim.implementation_status != "blocked"
    ]
    if not guided_claims:
        return False
    return all(
        claim.claim_type in SOURCE_GUIDED_POLICY_TYPES
        and bool(claim.source_locations)
        and bool(claim.review_notes)
        and bool(claim.must_not_claim)
        for claim in guided_claims
    )


def next_source_action(source_id: str, claims: list[MethodClaim], coverage: SourceCoverage | None, missing_scenarios: set[str]) -> str:
    claim_statuses = Counter(claim.implementation_status for claim in claims)
    evidence_counts = Counter(claim.evidence_level for claim in claims)
    reviewed_sections = [section for section in (coverage.sections if coverage else []) if section.status == "reviewed"]
    blocked_sections = [section for section in (coverage.sections if coverage else []) if section.status == "blocked"]
    if blocked_sections and len(blocked_sections) == len(coverage.sections if coverage else []):
        return "Keep blocked material as method limits until calculation support exists."
    if claim_statuses.get("blocked") and sum(claim_statuses.values()) == claim_statuses["blocked"]:
        return "Keep blocked material as method limits until calculation support exists."
    if claim_statuses.get("partial") or claim_statuses.get("not_started"):
        return "Finish partial claims into atoms/rules/runtime traces before using them as paid-result claims."
    if evidence_counts.get("source_guided") and source_guided_policy_complete(claims):
        return "Maintain as explicit source-guided product policy; deepen only with new scenario evidence or stronger source anchors."
    if evidence_counts.get("source_guided"):
        return "Convert source-guided product policy into source-backed or explicitly product-policy claims with stronger scenario fixtures."
    if missing_scenarios:
        return "Add scenario coverage for " + short_list(missing_scenarios, 4) + "."
    if reviewed_sections:
        return "Choose the highest-value reviewed section and deepen it into reducer-specific atoms/rules or visible copy."
    if source_id == "western-hand-transits":
        return "Extend timing selectors only after preserving the no-precise-date contract."
    if source_id == "western-burk-relationship-handbook":
        return "Deepen pair-family phrase templates and repeated-theme reducers."
    if source_id == "western-forrest-skymates":
        if blocked_sections:
            return "Maintain implemented readable and pivotal-interaspect work; keep house overlays blocked until reliable birth-time calculation support exists."
        return "Deepen readable relationship voice and pivotal interaspect explanation."
    if source_id == "western-suskin-synastry" and blocked_sections:
        return "Maintain implemented natal-before-synastry and aspect-ordering work; keep relationship-chart layers blocked until calculated."
    if source_id == "western-greene-saturn" and blocked_sections:
        return "Maintain implemented Saturn boundary and timing claims; keep detailed Saturn body extraction blocked until usable chapter text exists."
    if blocked_sections:
        return "Keep blocked material as method limits until calculation support exists."
    return "Maintain as implemented; deepen only when a new V1 section needs this source."


def build_source_rows(
    coverages: list[SourceCoverage],
    digests: list[BookDigest],
    records: list[ClaimUsageRecord],
    scenario_hits: set[str],
) -> list[list[Any]]:
    sources = source_manifest_map()
    digests_by_source = digest_by_source(digests)
    claims_index = claims_by_source(digests)
    records_index = records_by_source(records)
    coverage_index = coverage_by_source(coverages)
    section_targets = v1_section_target_map()
    rows: list[list[Any]] = []

    for coverage in sorted(coverages, key=lambda item: (item.priority, item.source_id)):
        source_id = coverage.source_id
        claims = claims_index.get(source_id, [])
        targets = source_runtime_targets(claims)
        sections = sorted(
            {
                section_targets[section_id]["title"]
                for claim in claims
                for section_id in direct_claim_section_ids(claim, section_targets)
                if section_id in section_targets
            }
        )
        missing_scenarios = targets - scenario_hits
        artifact_types = source_artifact_types(records_index.get(source_id, []))
        source_backed = sum(1 for claim in claims if claim.evidence_level == "source_backed")
        source_guided = sum(1 for claim in claims if claim.evidence_level == "source_guided")
        source_locations = sum(len(claim.source_locations) for claim in claims)
        rows.append(
            [
                coverage.priority,
                source_label(source_id, sources),
                ", ".join(sorted({digest.lane for digest in digests_by_source.get(source_id, [])})) or "coverage-only",
                implementation_state(claims, coverage),
                f"{len(coverage.sections)} sections / {len(claims)} claims / {source_locations} source ranges",
                f"{source_backed} backed / {source_guided} guided",
                short_list(sections, 5),
                short_list(artifact_types, 7),
                "none" if not missing_scenarios else short_list(missing_scenarios, 6),
                next_source_action(source_id, claims, coverage, missing_scenarios),
            ]
        )
    return rows


def build_section_rows(digests: list[BookDigest], records: list[ClaimUsageRecord], scenario_hits: set[str]) -> list[list[Any]]:
    sources = source_manifest_map()
    records_index = records_by_claim(records)
    section_targets = v1_section_target_map()
    rows: list[list[Any]] = []
    for section_id, section in section_targets.items():
        section_claims: list[tuple[BookDigest, MethodClaim]] = []
        for digest in digests:
            for claim in digest.method_claims:
                if section_id in direct_claim_section_ids(claim, section_targets):
                    section_claims.append((digest, claim))
        targets = set(section["targets"])
        artifact_types = {
            artifact
            for _digest, claim in section_claims
            for artifact in active_artifact_types(records_index[claim.id])
            if claim.id in records_index
        }
        source_ids = sorted({digest.source_id for digest, _claim in section_claims})
        missing_scenarios = targets - scenario_hits
        rows.append(
            [
                section_id,
                section["title"],
                len(section_claims),
                short_list([source_label(source_id, sources) for source_id in source_ids], 5),
                short_list(targets, 8),
                short_list(artifact_types, 8),
                "none" if not missing_scenarios else short_list(missing_scenarios, 6),
            ]
        )
    return rows


def build_unused_rows(coverages: list[SourceCoverage], digests: list[BookDigest], scenario_hits: set[str]) -> list[list[Any]]:
    claims_index = {claim.id: claim for digest in digests for claim in digest.method_claims}
    rows: list[list[Any]] = []
    for coverage in sorted(coverages, key=lambda item: (item.priority, item.source_id)):
        for section in coverage.sections:
            if section.status == "implemented":
                continue
            claims = [claims_index[claim_id] for claim_id in section.digest_claim_ids if claim_id in claims_index]
            targets = {target for claim in claims for target in claim.runtime_targets}
            missing = targets - scenario_hits
            if section.status == "blocked":
                action = f"Keep blocked: {section.blocked_reason}"
            elif any(claim.implementation_status in {"partial", "not_started"} for claim in claims):
                action = "Implement linked partial claim before exposing this in paid output."
            elif missing:
                action = "Add scenario coverage for " + short_list(missing, 4) + "."
            else:
                action = "Deepen into more specific atoms, reducers, or Chinese visible copy when this section is next expanded."
            rows.append(
                [
                    coverage.priority,
                    coverage.source_id,
                    section.section_id,
                    section.status,
                    section.title,
                    short_list(targets, 6),
                    short_list([claim.id for claim in claims], 4),
                    action,
                ]
            )
    return rows


def build_function_checklist_rows() -> list[list[Any]]:
    return [
        [
            "星盤定位",
            "Moon/Mercury/Venus/Mars/Saturn function-sign templates, element/modality modifiers, precision warnings",
            "Hand + George/Bloch + Forrest",
            "Add one source-backed variation at a time, then verify profile cards and chart variation matrix.",
        ],
        [
            "兩個人的關係契合度分析",
            "Pair-family templates, contact modifiers, repeated-theme reducer, safety-validation language",
            "Burk + Suskin + Forrest + Hand",
            "Deepen aspect families by relationship function, not by generic aspect keywords.",
        ],
        [
            "核心問題解讀",
            "Question-specific rule paths, context evidence boundary, nonfatal answer language",
            "OPA + Forrest + Burk",
            "Each question needs scenario tests proving context changes action framing but not chart conclusion.",
        ],
        [
            "時機判讀",
            "Mercury, Venus, Mars, Saturn, Moon timing selectors and contact reducer branches",
            "Hand Planets in Transit + OPA/Gottman",
            "Keep exact-date output blocked; add branches only through reducer fixtures.",
        ],
        [
            "行動方向",
            "Contact-status action scale, do-not-do boundaries, low-pressure repair tone, self-protection",
            "OPA + Gottman + Hand transits",
            "Every action branch must prove timing cannot override blocked or unsafe contact boundaries.",
        ],
    ]


def build_report(coverages: list[SourceCoverage], digests: list[BookDigest], records: list[ClaimUsageRecord]) -> str:
    section_targets = {
        target
        for section in v1_section_target_map().values()
        for target in section["targets"]
    }
    all_targets = source_runtime_targets([claim for digest in digests for claim in digest.method_claims]) | section_targets
    scenario_hits = scenario_hits_for_targets(all_targets)
    source_rows = build_source_rows(coverages, digests, records, scenario_hits)
    section_rows = build_section_rows(digests, records, scenario_hits)
    unused_rows = build_unused_rows(coverages, digests, scenario_hits)
    claims = [claim for digest in digests for claim in digest.method_claims]
    implementation_counts = Counter(claim.implementation_status for claim in claims)
    evidence_counts = Counter(claim.evidence_level for claim in claims)
    coverage_status_counts = Counter(section.status for coverage in coverages for section in coverage.sections)
    missing_scenario_targets = sorted(all_targets - scenario_hits)

    lines = [
        "# Western Book Digestion Execution Matrix",
        "",
        "Generated from `kb/book_digests`, `kb/book_coverage`, method-claim runtime usage, smoke scenarios, and example fixtures.",
        "",
        "## Purpose",
        "",
        "This matrix is the operating plan for fully digesting the current Western relationship sources into the paid V1 reading. It answers four questions for every source:",
        "",
        "1. What has been extracted from the source?",
        "2. Which paid V1 section uses it?",
        "3. Is it structured into atoms/rules/runtime/readable output?",
        "4. What should be deepened next before adding more frontend surface?",
        "",
        "## Current Judgment",
        "",
        "The current source set is enough to keep building V1. The bottleneck is not a missing book; it is deeper extraction from the books already present, especially reviewed-but-not-fully-productized sections, pair-family language, timing/action nuance, and Saturn body depth. Source-guided Valley product policy is allowed only when it is explicitly classified, source-anchored, review-noted, bounded by `must_not_claim`, runtime-wired, and scenario-covered.",
        "",
        "Do not buy or add new sources before the matrix backlog below is smaller, unless the new source fills a clearly blocked V1 requirement that none of the current books can cover.",
        "",
        "## Summary",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Tracked sources", len(coverages)],
                ["Coverage sections", sum(len(coverage.sections) for coverage in coverages)],
                ["Coverage statuses", dict(sorted(coverage_status_counts.items()))],
                ["Book digests", len(digests)],
                ["Method claims", len(claims)],
                ["Claim implementation", dict(sorted(implementation_counts.items()))],
                ["Claim evidence", dict(sorted(evidence_counts.items()))],
                ["Runtime targets", len(all_targets)],
                ["Scenario-covered targets", len(scenario_hits)],
                ["Missing scenario targets", "none" if not missing_scenario_targets else short_list(missing_scenario_targets, 12)],
            ],
        ),
        "",
        "## Source Execution Matrix",
        "",
        md_table(
            [
                "Priority",
                "Source",
                "Lane",
                "State",
                "Extraction depth",
                "Evidence level",
                "Paid V1 sections",
                "Runtime artifacts",
                "Scenario gaps",
                "Next action",
            ],
            source_rows,
        ),
        "",
        "## Paid V1 Section Crosswalk",
        "",
        md_table(
            [
                "Section id",
                "Visible section",
                "Claim count",
                "Source support",
                "Runtime targets",
                "Artifact types",
                "Scenario gaps",
            ],
            section_rows,
        ),
        "",
        "## Reviewed, Blocked, Or Underused Source Material",
        "",
        "Rows here are not necessarily wrong. They are the backlog for deeper digestion before expanding the result surface.",
        "",
        md_table(
            ["Priority", "Source id", "Section id", "Status", "Source section", "Runtime targets", "Claims", "Execution action"],
            unused_rows,
        ),
        "",
        "## Function Extraction Checklist",
        "",
        md_table(["Paid V1 function", "What must be extracted", "Primary sources", "How to deepen correctly"], build_function_checklist_rows()),
        "",
        "## Execution Rules",
        "",
        "- Digest book sections into method claims first; do not start from UI copy.",
        "- A claim can power the paid result only when it has structured artifacts, runtime trace/builder usage, and scenario coverage or an explicit blocked-future-layer status.",
        "- Context sources can set action boundaries and tone, but they cannot create astrology conclusions.",
        "- Timing sources can select climate and pacing, but they cannot create precise-date promises.",
        "- Blocked sources should remain visible as method limits, not hidden as missing work.",
        "- When a frontend section feels generic, deepen the relevant atom/rule/reducer before rewriting the UI.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western book digestion execution matrix.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    coverages = flattened_coverages(load_book_coverage_files())
    digests = flattened_digests(load_book_digest_files())
    records = build_method_claim_usage_records()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(coverages, digests, records), encoding="utf-8")
    print(f"Wrote book digestion execution matrix -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
