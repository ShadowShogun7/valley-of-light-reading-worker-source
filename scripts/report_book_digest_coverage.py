#!/usr/bin/env python3
"""Generate the Western relationship method bible from structured book digests."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from book_digests import BOOK_DIGEST_DIR, BookDigest, digest_stats, flattened_digests, load_book_digest_files, validate_book_digest_contract
from kb_utils import ROOT, load_source_manifest


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "11-western-relationship-method-bible.md"


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


def source_map() -> dict[str, dict[str, Any]]:
    return {
        str(source.get("id")): source
        for source in load_source_manifest().get("sources", [])
        if isinstance(source, dict) and source.get("id")
    }


def status_icon(status: str) -> str:
    return {
        "implemented": "done",
        "partial": "partial",
        "not_started": "todo",
        "blocked": "blocked",
    }.get(status, status)


def digest_source_label(digest: BookDigest, sources: dict[str, dict[str, Any]]) -> str:
    source = sources.get(digest.source_id) or {}
    author = source.get("author")
    title = source.get("title") or digest.source_id
    return f"{title} ({author})" if author else str(title)


def claim_location_label(locations: list[str]) -> str:
    if not locations:
        return ""
    return "; ".join(locations[:3])


def build_report(digests: list[BookDigest], out_path: Path) -> str:
    sources = source_map()
    stats = digest_stats(digests)
    lane_groups: dict[str, list[BookDigest]] = defaultdict(list)
    for digest in digests:
        lane_groups[digest.lane].append(digest)

    source_rows = []
    for digest in sorted(digests, key=lambda item: (item.lane, item.priority, item.id)):
        source_rows.append(
            [
                digest.priority,
                digest.lane,
                digest_source_label(digest, sources),
                digest.status,
                ", ".join(digest.method_scope[:4]),
                digest.product_role,
            ]
        )

    method_rows = []
    for digest in sorted(lane_groups.get("astrology_method", []), key=lambda item: (item.priority, item.id)):
        for claim in digest.method_claims:
            method_rows.append(
                [
                    digest_source_label(digest, sources),
                    claim.claim_type,
                    claim.summary,
                    ", ".join(claim.runtime_targets),
                    claim.evidence_level,
                    claim_location_label(claim.source_locations),
                    status_icon(claim.implementation_status),
                ]
            )

    situation_rows = []
    for digest in sorted(lane_groups.get("situation_handling", []), key=lambda item: (item.priority, item.id)):
        for claim in digest.method_claims:
            situation_rows.append(
                [
                    digest_source_label(digest, sources),
                    claim.claim_type,
                    claim.summary,
                    ", ".join(claim.runtime_targets),
                    claim.evidence_level,
                    claim_location_label(claim.source_locations),
                    status_icon(claim.implementation_status),
                ]
            )

    reviewed_rows = []
    for digest in sorted(digests, key=lambda item: (item.lane, item.priority, item.id)):
        for claim in digest.method_claims:
            if claim.evidence_level != "source_backed":
                continue
            reviewed_rows.append(
                [
                    digest_source_label(digest, sources),
                    claim.id,
                    "; ".join(claim.review_notes[:2]),
                    claim_location_label(claim.source_locations),
                ]
            )

    target_rows = []
    target_claims: dict[str, list[str]] = defaultdict(list)
    target_statuses: dict[str, list[str]] = defaultdict(list)
    for digest in digests:
        for claim in digest.method_claims:
            for target in claim.runtime_targets:
                target_claims[target].append(claim.id)
                target_statuses[target].append(claim.implementation_status)
    for target in sorted(target_claims):
        statuses = target_statuses[target]
        if "blocked" in statuses and len(set(statuses)) == 1:
            status = "blocked"
        elif "not_started" in statuses and len(set(statuses)) == 1:
            status = "todo"
        elif "partial" in statuses or "not_started" in statuses or "blocked" in statuses:
            status = "partial"
        else:
            status = "done"
        target_rows.append([target, status, len(target_claims[target]), ", ".join(target_claims[target][:4])])

    gap_rows = []
    for digest in digests:
        for claim in digest.method_claims:
            if claim.implementation_status in {"partial", "not_started", "blocked"}:
                gap_rows.append(
                    [
                        claim.implementation_status,
                        digest_source_label(digest, sources),
                        claim.id,
                        "; ".join(claim.must_not_claim[:2]),
                    ]
                )

    lines = [
        "# Western Relationship Method Bible",
        "",
        "Generated from `kb/book_digests/**/*.yml`.",
        "",
        "## Purpose",
        "",
        "This document separates book interpretation method from product situation handling.",
        "",
        "- Astrology method sources decide what the chart evidence means.",
        "- Situation-handling sources decide how advice should be bounded in real-life contexts.",
        "- Product reducers may combine both, but context must not create astrology conclusions by itself.",
        "",
        "## Current Digest Coverage",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Digests", stats["digest_count"]],
                ["Method claims", stats["method_claim_count"]],
                ["Lanes", stats["lane_counts"]],
                ["Implementation status", stats["implementation_counts"]],
                ["Evidence level", stats["evidence_counts"]],
            ],
        ),
        "",
        "## Source Lanes",
        "",
        md_table(["Priority", "Lane", "Source", "Status", "Scope", "Product role"], source_rows),
        "",
        "## Astrology Method Order",
        "",
        "The reading should follow this order unless a later reviewed digest changes the method:",
        "",
        "1. Read each person's natal relationship needs and function styles.",
        "2. Use initial comparison only as orientation, never as verdict.",
        "3. Select relationship-critical synastry evidence by pair family, contact type, and strength.",
        "4. Separate attraction, safety, pressure, communication, and repair conditions.",
        "5. Use transits as timing climate, not guaranteed outcomes.",
        "6. Apply relationship stage/contact status only as action boundary and tone modifier.",
        "7. Block houses, angles, overlays, composite, and Davison until calculation precision supports them.",
        "",
        md_table(["Source", "Claim type", "Method claim", "Runtime targets", "Evidence", "Source locations", "Status"], method_rows),
        "",
        "## Reviewed Claim Notes",
        "",
        "Only `source_backed` claims appear here. `source_guided` claims remain book-informed seeds until reviewed with line-level anchors.",
        "",
        md_table(["Source", "Claim id", "Review notes", "Source locations"], reviewed_rows),
        "",
        "## Situation Handling",
        "",
        "Situation handling is not astrology evidence. It controls action safety, wording, and boundaries.",
        "",
        md_table(["Source", "Claim type", "Situation claim", "Runtime targets", "Evidence level", "Source locations", "Status"], situation_rows),
        "",
        "## Runtime Target Audit",
        "",
        md_table(["Runtime target", "Status", "Claim count", "Example claim ids"], target_rows),
        "",
        "## Gaps Before We Trust The Reading More",
        "",
        md_table(["Status", "Source", "Claim id", "Guardrail / gap"], gap_rows),
        "",
        "## Implementation Rule",
        "",
        "A runtime atom/rule should only be considered method-correct when it can point back to one of these digest claims and, where needed, a claim-backed wiki article.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western relationship method bible from book digests.")
    parser.add_argument("--dir", default=str(BOOK_DIGEST_DIR), help="Digest directory. Defaults to kb/book_digests.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    args = parser.parse_args()

    digest_dir = Path(args.dir)
    if not digest_dir.is_absolute():
        digest_dir = ROOT / digest_dir
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    digests = flattened_digests(load_book_digest_files(digest_dir))
    errors = validate_book_digest_contract(digests)
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(digests, out_path), encoding="utf-8")
    print(f"Wrote method bible -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
