#!/usr/bin/env python3
"""Generate a Western source inventory and extraction-quality audit."""

from __future__ import annotations

import argparse
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from book_coverage import flattened_coverages, load_book_coverage_files
from book_digests import flattened_digests, load_book_digest_files
from kb_utils import ROOT, load_source_manifest, read_text


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "21-western-source-inventory-audit.md"
TRACKED_SYSTEMS = {"western", "consultation", "relationship"}


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


def source_manifest_rows() -> list[dict[str, Any]]:
    sources = load_source_manifest().get("sources", [])
    return [
        source
        for source in sources
        if isinstance(source, dict) and str(source.get("system") or "") in TRACKED_SYSTEMS
    ]


def coverage_statuses() -> dict[str, Counter[str]]:
    output: dict[str, Counter[str]] = defaultdict(Counter)
    for coverage in flattened_coverages(load_book_coverage_files()):
        for section in coverage.sections:
            output[coverage.source_id][section.status] += 1
    return output


def coverage_priorities() -> dict[str, str]:
    return {coverage.source_id: coverage.priority for coverage in flattened_coverages(load_book_coverage_files())}


def blocked_reasons() -> dict[str, list[str]]:
    output: dict[str, list[str]] = defaultdict(list)
    for coverage in flattened_coverages(load_book_coverage_files()):
        for section in coverage.sections:
            if section.status == "blocked" and section.blocked_reason:
                output[coverage.source_id].append(section.blocked_reason)
    return output


def digest_claim_counts() -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for digest in flattened_digests(load_book_digest_files()):
        counts[digest.source_id] += len(digest.method_claims)
    return counts


def raw_metrics(raw_path: str) -> dict[str, Any]:
    path = ROOT / raw_path if raw_path else ROOT / "__missing__"
    if not raw_path or not path.exists():
        return {
            "exists": False,
            "line_count": 0,
            "char_count": 0,
            "nonempty_ratio": "0.00",
            "max_line_length": 0,
        }
    text = read_text(path)
    lines = text.splitlines()
    nonempty = [line for line in lines if line.strip()]
    max_line_length = max((len(line) for line in lines), default=0)
    return {
        "exists": True,
        "line_count": len(lines),
        "char_count": len(text),
        "nonempty_ratio": f"{(len(nonempty) / len(lines)):.2f}" if lines else "0.00",
        "max_line_length": max_line_length,
    }


def extraction_judgment(
    source: dict[str, Any],
    metrics: dict[str, Any],
    statuses: Counter[str],
    reasons: list[str],
    priority: str,
) -> str:
    if not metrics["exists"]:
        return "missing raw file"
    if priority == "reserve" or str(source.get("tier") or "") == "reserve":
        return "reserve / blocked for V1"
    if any("not enough chapter body" in reason for reason in reasons):
        return "needs better extraction before deeper claims"
    if statuses and statuses.get("blocked", 0) == sum(statuses.values()):
        return "blocked by V1 scope"
    if str(source.get("status") or "") == "usable_after_line_normalization":
        return "usable but needs line normalization"
    if str(source.get("raw_path") or "").startswith("raw/cross/"):
        return "source-note support; use as policy guardrail"
    if metrics["char_count"] < 10_000:
        return "thin extraction; review before claims"
    return "ready for deeper digestion"


def short_statuses(statuses: Counter[str]) -> str:
    if not statuses:
        return ""
    return ", ".join(f"{status}:{count}" for status, count in sorted(statuses.items()))


def build_report() -> str:
    statuses_by_source = coverage_statuses()
    priority_by_source = coverage_priorities()
    reasons_by_source = blocked_reasons()
    claim_counts = digest_claim_counts()

    inventory_rows: list[list[Any]] = []
    action_rows: list[list[Any]] = []
    totals = Counter()

    for source in sorted(source_manifest_rows(), key=lambda item: (str(item.get("system")), str(item.get("id")))):
        source_id = str(source.get("id"))
        raw_path = str(source.get("raw_path") or "")
        metrics = raw_metrics(raw_path)
        statuses = statuses_by_source.get(source_id, Counter())
        priority = priority_by_source.get(source_id, "")
        judgment = extraction_judgment(source, metrics, statuses, reasons_by_source.get(source_id, []), priority)
        totals[judgment] += 1

        inventory_rows.append(
            [
                source_id,
                source.get("system"),
                source.get("tier"),
                source.get("status"),
                priority,
                "yes" if metrics["exists"] else "no",
                metrics["line_count"],
                metrics["char_count"],
                metrics["nonempty_ratio"],
                metrics["max_line_length"],
                short_statuses(statuses),
                claim_counts.get(source_id, 0),
                judgment,
            ]
        )

        if judgment != "ready for deeper digestion":
            action_rows.append(
                [
                    source_id,
                    judgment,
                    "; ".join(reasons_by_source.get(source_id, [])) or source.get("product_role") or "",
                ]
            )

    lines = [
        "# Western Source Inventory Audit",
        "",
        "Generated from `docs/research/sources.yml`, `kb/book_coverage`, and `kb/book_digests`.",
        "",
        "## Purpose",
        "",
        "This report is the Phase 0 checkpoint for the Western book digestion plan. It verifies that each tracked Western, consultation, or relationship source has a raw file, explicit coverage status, and a clear extraction-quality judgment before deeper claims are added.",
        "",
        "## Summary",
        "",
        md_table(["Judgment", "Source count"], [[judgment, count] for judgment, count in sorted(totals.items())]),
        "",
        "## Inventory",
        "",
        md_table(
            [
                "Source id",
                "System",
                "Tier",
                "Manifest status",
                "Priority",
                "Raw exists",
                "Lines",
                "Characters",
                "Nonempty ratio",
                "Max line",
                "Coverage statuses",
                "Digest claims",
                "Judgment",
            ],
            inventory_rows,
        ),
        "",
        "## Action Queue",
        "",
        md_table(["Source id", "Action", "Reason"], action_rows),
        "",
        "## Implementation Rule",
        "",
        "Only sources judged `ready for deeper digestion` or `source-note support; use as policy guardrail` should receive new operational claims. Reserve, blocked, missing, or weak-extraction sources can only support method limits until the blocker is resolved.",
        "",
    ]
    return "\n".join(lines)


def write_report(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(), encoding="utf-8")


def check_report(out_path: Path) -> bool:
    expected = build_report()
    actual = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    return expected == actual


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western source inventory audit.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    parser.add_argument("--check", action="store_true", help="Fail if the committed report is stale.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    if args.check:
        if check_report(out_path):
            print("Western source inventory audit is current")
            return 0
        with tempfile.NamedTemporaryFile(
            prefix=f".{out_path.stem}.",
            suffix=out_path.suffix,
            dir=out_path.parent,
            delete=True,
        ):
            pass
        print(
            "Western source inventory audit is stale. "
            "Run `.venv/bin/python scripts/report_western_source_inventory_audit.py`."
        )
        return 1

    write_report(out_path)
    print(f"Wrote Western source inventory audit -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
