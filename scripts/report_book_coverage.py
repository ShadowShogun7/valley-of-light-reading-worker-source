#!/usr/bin/env python3
"""Generate a Western book coverage report from structured coverage maps."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from book_coverage import BOOK_COVERAGE_DIR, SourceCoverage, coverage_stats, flattened_coverages, load_book_coverage_files, source_manifest_map, validate_book_coverage_contract
from kb_utils import ROOT


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "12-western-book-coverage.md"


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


def source_label(source_id: str, sources: dict[str, dict[str, Any]]) -> str:
    source = sources.get(source_id) or {}
    title = source.get("title") or source_id
    author = source.get("author")
    return f"{title} ({author})" if author else str(title)


def section_status_label(status: str, blocked_reason: str) -> str:
    if status == "blocked" and blocked_reason:
        return f"blocked: {blocked_reason}"
    return status


def build_report(coverages: list[SourceCoverage], out_path: Path) -> str:
    sources = source_manifest_map()
    stats = coverage_stats(coverages)

    source_rows = []
    section_rows = []
    target_rows = []
    gap_rows = []
    target_sections: dict[str, list[str]] = defaultdict(list)

    for coverage in sorted(coverages, key=lambda item: (item.priority, item.source_id)):
        statuses = stats["source_statuses"].get(coverage.source_id, {})
        source_rows.append(
            [
                coverage.priority,
                source_label(coverage.source_id, sources),
                len(coverage.sections),
                statuses,
                coverage.product_role,
            ]
        )
        for section in coverage.sections:
            section_rows.append(
                [
                    coverage.source_id,
                    section.section_id,
                    section.title,
                    section_status_label(section.status, section.blocked_reason),
                    ", ".join(section.runtime_targets),
                    ", ".join(section.digest_claim_ids[:4]),
                    section.line_range,
                ]
            )
            if section.status in {"unread", "mapped", "extracted", "blocked"}:
                gap_rows.append(
                    [
                        coverage.source_id,
                        section.section_id,
                        section_status_label(section.status, section.blocked_reason),
                        ", ".join(section.runtime_targets),
                    ]
                )
            for target in section.runtime_targets:
                target_sections[target].append(f"{coverage.source_id}:{section.section_id}")

    for target in sorted(target_sections):
        target_rows.append([target, len(target_sections[target]), ", ".join(target_sections[target][:5])])

    lines = [
        "# Western Book Coverage",
        "",
        "Generated from `kb/book_coverage/**/*.yml`.",
        "",
        "## Purpose",
        "",
        "This report tracks which source sections have been mapped, reviewed, implemented, or blocked before they become runtime reading method.",
        "",
        "## Coverage Summary",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Sources", stats["source_count"]],
                ["Sections", stats["section_count"]],
                ["Status counts", stats["status_counts"]],
                ["Linked digest claims", stats["digest_claim_count"]],
            ],
        ),
        "",
        "## Source Coverage",
        "",
        md_table(["Priority", "Source", "Sections", "Statuses", "Product role"], source_rows),
        "",
        "## Section Coverage",
        "",
        md_table(["Source id", "Section id", "Title", "Status", "Runtime targets", "Digest claims", "Line range"], section_rows),
        "",
        "## Runtime Target Coverage",
        "",
        md_table(["Runtime target", "Section count", "Example sections"], target_rows),
        "",
        "## Gaps To Deepen",
        "",
        md_table(["Source id", "Section id", "Status / reason", "Runtime targets"], gap_rows),
        "",
        "## Implementation Rule",
        "",
        "A book section is not allowed to power runtime interpretation until it has reviewed or implemented coverage and linked digest claim IDs. Blocked sections may only appear as method limits.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western book coverage report.")
    parser.add_argument("--dir", default=str(BOOK_COVERAGE_DIR), help="Coverage directory. Defaults to kb/book_coverage.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    args = parser.parse_args()

    coverage_dir = Path(args.dir)
    if not coverage_dir.is_absolute():
        coverage_dir = ROOT / coverage_dir
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    coverages = flattened_coverages(load_book_coverage_files(coverage_dir))
    errors = validate_book_coverage_contract(coverages)
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(coverages, out_path), encoding="utf-8")
    print(f"Wrote book coverage report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
