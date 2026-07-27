#!/usr/bin/env python3
"""Generate a report showing where each book method claim is used at runtime."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from method_claim_usage import ClaimUsageRecord, build_method_claim_usage_records, usage_stats, validate_method_claim_usage


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "13-western-method-claim-runtime-usage.md"


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


def short_usage(record: ClaimUsageRecord) -> str:
    parts = []
    artifact_order = {
        "runtime_trace": 0,
        "atom": 1,
        "rule": 2,
        "question_blueprint": 3,
        "guardrail": 4,
        "runtime_builder": 5,
        "readable_renderer": 6,
        "frontend_result": 7,
        "narrative_prompt": 8,
        "blocked_future_layer": 9,
    }
    target_order = {target: index for index, target in enumerate(record.runtime_targets)}

    def usage_sort_key(usage: Any) -> tuple[int, int, int, str]:
        exact_category = 0 if usage.detail == f"category={usage.target}" else 1
        return (
            artifact_order.get(usage.artifact_type, 99),
            exact_category,
            target_order.get(usage.target, 99),
            usage.artifact_id,
        )

    for usage in sorted(record.usages, key=usage_sort_key):
        if usage.artifact_type == "book_coverage":
            continue
        label = usage.artifact_type
        if usage.artifact_id:
            label = f"{label}:{usage.artifact_id}"
        if usage.target:
            label = f"{label}({usage.target})"
        parts.append(label)
        if len(parts) >= 6:
            break
    return ", ".join(parts)


def build_report(records: list[ClaimUsageRecord]) -> str:
    stats = usage_stats(records)
    errors = validate_method_claim_usage(records)

    summary_rows = [
        ["Claims", stats["claim_count"]],
        ["Implementation status", stats["status_counts"]],
        ["Artifact usage", stats["artifact_counts"]],
        ["Validation errors", stats["error_count"]],
    ]
    source_rows = [[source_id, count] for source_id, count in stats["source_counts"].items()]
    target_rows = [[target, count] for target, count in stats["target_counts"].items()]
    claim_rows = [
        [
            record.implementation_status,
            record.evidence_level,
            record.source_id,
            record.claim_id,
            ", ".join(record.runtime_targets),
            ", ".join(record.artifact_types),
            short_usage(record),
        ]
        for record in sorted(records, key=lambda item: (item.implementation_status, item.source_id, item.claim_id))
    ]
    gap_rows = []
    for error in errors:
        claim_id = error.split(":", 1)[0]
        record = next((item for item in records if item.claim_id == claim_id), None)
        gap_rows.append([
            claim_id,
            record.source_id if record else "",
            record.implementation_status if record else "",
            error,
        ])

    lines = [
        "# Western Method Claim Runtime Usage",
        "",
        "Generated from `kb/book_digests`, `kb/book_coverage`, structured KB YAML, runtime code, readable renderer, and result UI files.",
        "",
        "## Purpose",
        "",
        "This report answers a stricter question than source coverage: after a book claim has been digested, where does it actually affect the reading runtime?",
        "",
        "Valid runtime artifact types include atoms, rules, question blueprints, guardrails, readable renderer, runtime builder, runtime trace, frontend result, narrative prompt, or an explicit blocked future layer.",
        "",
        "## Summary",
        "",
        md_table(["Metric", "Value"], summary_rows),
        "",
        "## Source Claim Counts",
        "",
        md_table(["Source id", "Claim count"], source_rows),
        "",
        "## Runtime Target Counts",
        "",
        md_table(["Runtime target", "Claim count"], target_rows),
        "",
        "## Claim Usage Map",
        "",
        md_table(
            ["Status", "Evidence", "Source", "Claim id", "Runtime targets", "Artifact types", "Example artifacts"],
            claim_rows,
        ),
        "",
        "## Validation Gaps",
        "",
        md_table(["Claim id", "Source", "Status", "Gap"], gap_rows) if gap_rows else "No validation gaps.",
        "",
        "## Implementation Rule",
        "",
        "An active method claim should not be considered productized unless this report shows it in a runtime artifact. A blocked method claim is valid only when it appears as an explicit blocked future layer or method gap.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western method claim runtime usage report.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    records = build_method_claim_usage_records()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(records), encoding="utf-8")
    print(f"Wrote method claim runtime usage report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
