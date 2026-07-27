#!/usr/bin/env python3
"""Rank method claims that need deeper source extraction."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from book_coverage import SourceCoverage, flattened_coverages, load_book_coverage_files
from book_digests import MethodClaim, flattened_digests, load_book_digest_files
from kb_utils import ROOT
from method_claim_usage import ClaimUsageRecord, active_artifact_types, build_method_claim_usage_records


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "14-western-method-deepening-backlog.md"
IGNORED_ARTIFACT_TYPES = {"book_coverage", "blocked_future_layer"}
SOURCE_PRIORITY_SCORE = {"P0": 12, "P1": 8, "P2": 4, "reserve": 0}
EVIDENCE_SCORE = {"source_backed": 8, "source_guided": 4, "product_hypothesis": 1}


def md_escape(value: Any) -> str:
    return "" if value is None else str(value).replace("\n", "<br>").replace("|", "\\|")


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


def coverage_statuses_by_claim() -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    coverages: list[SourceCoverage] = flattened_coverages(load_book_coverage_files())
    for coverage in coverages:
        for section in coverage.sections:
            for claim_id in section.digest_claim_ids:
                output[str(claim_id)].append(section.status)
    return output


def active_usages(record: ClaimUsageRecord) -> list[Any]:
    return [usage for usage in record.usages if usage.artifact_type not in IGNORED_ARTIFACT_TYPES]


def extraction_depth(claim: MethodClaim) -> str:
    count = len(claim.source_locations)
    if claim.evidence_level == "product_hypothesis":
        return "product hypothesis"
    if count == 0:
        return "no source line range"
    if count == 1:
        return "thin: 1 source range"
    if count == 2:
        return "medium: 2 source ranges"
    return f"broad: {count} source ranges"


def next_action(record: ClaimUsageRecord, claim: MethodClaim) -> str:
    targets = set(claim.runtime_targets)
    if record.claim_id == "valley-blocked-contact-hard-boundary":
        return "Context matrix fixtures now lock blocked-contact action scale, blocked actions, and no-boundary-bypass copy; deepen source extraction only if this policy expands."
    if record.claim_id == "valley-contact-status-action-scale":
        return "State-specific contact-status claims now lock all five contact states; revisit only if the product adds new relationship-context states."
    if record.claim_id == "valley-no-contact-lowers-action-speed":
        return "Context matrix fixtures now lock no-contact as a single low-stimulation test with easy exit; next source work is adding deeper repair-pacing anchors if needed."
    if record.claim_id == "valley-context-modifies-action-not-conclusion":
        return "Context matrix fixtures now prove context changes action boundaries, not chart conclusions; next source work is only needed for broader policy changes."
    if record.claim_id == "burk-safety-validation-needs-before-compatibility":
        return "Use the safety-validation matrix smoke as the regression guard while deepening visible Moon/Venus answer copy."
    if record.claim_id == "burk-personal-planet-connections-attraction-and-sparks":
        return "Deepen pair-family phrase templates so attraction, pressure, and communication contacts produce distinct result cards."
    if record.claim_id == "burk-repeated-themes-outweigh-single-contacts":
        return "Add reducer evidence for reinforced themes, double aspects, and repeated function families."
    if record.claim_id == "burk-synastry-as-persistent-trigger":
        return "Chart variation fixtures now lock eligible aspect selection, pair templates, and contact modifiers; deepen Burk extraction around synastry as persistent natal-trigger evidence."
    if record.claim_id == "skymates-pivotal-interaspects-over-aspect-dump":
        return "Chart variation fixtures now lock top-4 pivotal interaspect selection over aspect dumps; next work is deeper Skymates extraction and visible result-card phrasing."
    if record.claim_id == "skymates-no-generic-love-needs":
        return "Add scenario-specific language rules so love/need claims are always tied to calculated points and user context."
    if record.claim_id == "skymates-keep-planet-functions-distinct":
        return "Audit profile renderer so every card separates planet function, sign style, and relationship expression."
    if record.claim_id == "greene-saturn-defense-not-permanent-rejection":
        return "Keep as broad Saturn guardrail until a complete Saturn body extraction is available."
    if "timingContactReducer" in targets or "timingWindowBand" in targets:
        return "Add timing selector scenarios and 90-day window reducer checks."
    if "aspectFunctionCombination" in targets or "aspectPairContactTemplate" in targets:
        return "Deepen aspect-function reducers with source-backed pair templates and hard/soft/conjunction modifiers."
    if "relationshipProfiles" in targets or "personProfile" in targets:
        return "Deepen relationship-profile atoms and readable renderer from the source method."
    if "consultationSafety" in targets or "actionBoundary" in targets:
        return "Turn the safety boundary into explicit reducer fixtures and visible action constraints."
    return "Add a source-backed atom/rule/runtime trace for the weakest runtime target in this claim."


def needs_deepening(record: ClaimUsageRecord, claim: MethodClaim, digest: Any) -> bool:
    if record.implementation_status == "blocked":
        return False
    return (
        record.implementation_status == "partial"
        or claim.evidence_level != "source_backed"
        or digest.status == "seed"
        or len(claim.source_locations) <= 1
    )


def score_record(record: ClaimUsageRecord, claim: MethodClaim, digest: Any) -> tuple[int, str]:
    active = active_usages(record)
    artifact_types = active_artifact_types(record)
    source_count = len(claim.source_locations)
    source_penalty = min(source_count, 4) * 2
    broad_runtime_bonus = len(record.runtime_targets) * 3 + len(artifact_types) * 2 + min(len(active) // 20, 10)
    source_bonus = SOURCE_PRIORITY_SCORE.get(str(digest.priority), 0) + EVIDENCE_SCORE.get(claim.evidence_level, 0)
    visible_bonus = 4 if artifact_types.intersection({"frontend_result", "readable_renderer", "narrative_prompt"}) else 0
    thin_runtime_bonus = 8 if len(artifact_types) >= 6 and source_count <= 2 else 0
    status_bonus = 20 if record.implementation_status == "partial" else 0
    guided_bonus = 14 if claim.evidence_level != "source_backed" else 0
    seed_bonus = 8 if digest.status == "seed" else 0
    thin_source_bonus = 8 if source_count <= 1 and claim.evidence_level != "product_hypothesis" else 0
    score = (
        source_bonus
        + broad_runtime_bonus
        + visible_bonus
        + thin_runtime_bonus
        + status_bonus
        + guided_bonus
        + seed_bonus
        + thin_source_bonus
        - source_penalty
    )
    reason_bits = []
    if record.implementation_status == "partial":
        reason_bits.append("not fully productized")
    if claim.evidence_level != "source_backed":
        reason_bits.append(f"{claim.evidence_level} evidence")
    if digest.status == "seed":
        reason_bits.append("seed digest")
    if len(artifact_types) >= 6:
        reason_bits.append("broad runtime footprint")
    if source_count <= 1 and claim.evidence_level != "product_hypothesis":
        reason_bits.append("thin extraction")
    if artifact_types.intersection({"frontend_result", "readable_renderer", "narrative_prompt"}):
        reason_bits.append("visible result impact")
    if digest.priority in {"P0", "P1"}:
        reason_bits.append(f"{digest.priority} source")
    return score, ", ".join(reason_bits) or "deepen source extraction"


def build_report(records: list[ClaimUsageRecord]) -> str:
    claims = claim_index()
    statuses_by_claim = coverage_statuses_by_claim()
    ranked_rows = []
    blocked_rows = []

    for record in records:
        digest, claim = claims[record.claim_id]
        artifact_types = sorted(active_artifact_types(record))
        active = active_usages(record)
        if record.implementation_status == "blocked":
            blocked_rows.append([
                record.source_id,
                record.claim_id,
                ", ".join(record.runtime_targets),
                "; ".join(claim.must_not_claim),
            ])
            continue
        if not needs_deepening(record, claim, digest):
            continue
        score, reason = score_record(record, claim, digest)
        ranked_rows.append([
            score,
            record.source_id,
            record.claim_id,
            record.implementation_status,
            claim.evidence_level,
            reason,
            extraction_depth(claim),
            ", ".join(statuses_by_claim.get(record.claim_id, [])),
            f"{len(record.runtime_targets)} targets / {len(artifact_types)} artifact types / {len(active)} usages",
            next_action(record, claim),
        ])

    ranked_rows.sort(key=lambda row: (-int(row[0]), str(row[1]), str(row[2])))
    top_rows = ranked_rows[:12]
    source_counts: dict[str, int] = defaultdict(int)
    source_guided_count = 0
    thin_extraction_count = 0
    seed_digest_count = 0
    for row in ranked_rows:
        source_counts[str(row[1])] += 1
        if row[4] != "source_backed":
            source_guided_count += 1
        if str(row[6]).startswith("thin") or str(row[6]) == "no source line range":
            thin_extraction_count += 1
        digest, _claim = claims[str(row[2])]
        if digest.status == "seed":
            seed_digest_count += 1

    lines = [
        "# Western Method Deepening Backlog",
        "",
        "Generated from `kb/book_digests`, `kb/book_coverage`, and method-claim runtime usage.",
        "",
        "## Purpose",
        "",
        "This report ranks active method claims that already touch runtime output but still need deeper source extraction, reducer structure, or scenario coverage. Productized runtime claims can still appear here when their source evidence is thin, source-guided, or still in a seed digest.",
        "",
        "## Summary",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Deepening candidates ranked", len(ranked_rows)],
                ["Source-guided candidates", source_guided_count],
                ["Thin extraction candidates", thin_extraction_count],
                ["Seed digest candidates", seed_digest_count],
                ["Blocked claims tracked separately", len(blocked_rows)],
                ["Deepening candidates by source", dict(sorted(source_counts.items()))],
            ],
        ),
        "",
        "## Highest Priority Claims",
        "",
        md_table(
            [
                "Score",
                "Source",
                "Claim id",
                "Implementation",
                "Evidence",
                "Why now",
                "Extraction depth",
                "Coverage status",
                "Current runtime footprint",
                "Next action",
            ],
            top_rows,
        ),
        "",
        "## Full Deepening Backlog",
        "",
        md_table(
            [
                "Score",
                "Source",
                "Claim id",
                "Implementation",
                "Evidence",
                "Why now",
                "Extraction depth",
                "Coverage status",
                "Current runtime footprint",
                "Next action",
            ],
            ranked_rows,
        ),
        "",
        "## Blocked Method Limits",
        "",
        md_table(["Source", "Claim id", "Runtime targets", "Must not claim"], blocked_rows),
        "",
        "## Deepening Rule",
        "",
        "An implemented claim is allowed to power the paid V1 result only when runtime validation passes, but source digestion can still be deepened. Before adding new UI sections, prioritize candidates with source-guided evidence, seed digests, broad runtime footprint, or only one source line range. Deepening means at least one of: more precise source line extraction, a structured atom/rule/reducer, a runtime trace entry, and scenario tests proving the result changes for the intended chart/context variation.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western method deepening backlog.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(build_method_claim_usage_records()), encoding="utf-8")
    print(f"Wrote method deepening backlog -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
