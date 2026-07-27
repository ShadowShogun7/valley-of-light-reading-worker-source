#!/usr/bin/env python3
"""Generate the paid V1.1 Western precision/depth audit.

This report is deliberately conservative. It proves whether the next depth
layers are ready to expose, or whether they must remain blocked until source
quality or calculation support changes.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kb_utils import ROOT, read_text


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "23-paid-v11-precision-depth-audit.md"
SATURN_RAW_PATH = ROOT / "raw" / "western" / "488023677-Liz-Greene-Robert-Hand-Saturn-A-New-Look-at-an-Old-Devil-Weiser-Books-2011-pdf.txt"
COVERAGE_PATH = ROOT / "kb" / "book_coverage" / "western" / "current-sources-v1.yml"
EXECUTION_MATRIX_PATH = ROOT / "docs" / "research" / "17-western-book-digestion-execution-matrix.md"
RUNTIME_PATH = ROOT / "scripts" / "complete_relationship_result_runtime.py"
CALC_SPIKE_PATH = ROOT / "scripts" / "calc_western_spike.py"
IMMANUEL_ADAPTER_PATH = ROOT / "calculation" / "western" / "immanuel_adapter.py"
WESTERN_SIGNALS_PATH = ROOT / "calculation" / "western" / "signals.py"
PRECISION_SMOKE_PATH = ROOT / "scripts" / "smoke_western_precision_layer_boundaries.py"


@dataclass(frozen=True)
class Check:
    id: str
    result: str
    evidence: str

    @property
    def ok(self) -> bool:
        return self.result == "PASS"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


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


def saturn_source_metrics() -> dict[str, Any]:
    text = read_text(SATURN_RAW_PATH)
    lines = text.splitlines()
    layout_marker_lines = sum(1 for line in lines if "45173_TXT.indd" in line or "Saturn Layout Pages" in line)
    synastry_mentions = [
        index + 1
        for index, line in enumerate(lines)
        if "synastry" in line.lower() or "In Synastry" in line
    ]
    chapter_body_markers = [
        index + 1
        for index, line in enumerate(lines)
        if re.search(r"^\s*6\s*[•.-]\s*In Synastry\s*$", line)
    ]
    chapter_start = next((index + 1 for index, line in enumerate(lines) if "TXT147" in line), None)
    chapter_end = next((index + 1 for index, line in enumerate(lines) if "TXT199" in line or "To Our Readers" in line), None)
    chapter_slice = (
        lines[(chapter_start or 1) - 1 : (chapter_end or len(lines) + 1) - 1]
        if chapter_start and chapter_end and chapter_end > chapter_start
        else []
    )
    likely_chapter_body_lines = [
        (chapter_start or 1) + index
        for index, line in enumerate(chapter_slice)
        if len(line.strip()) >= 45
        and "45173" not in line
        and "Saturn Layout" not in line
        and "Black" not in line
        and not re.search(r"\b\d{1,2}:\d{2}", line)
    ]
    return {
        "line_count": len(lines),
        "char_count": len(text),
        "layout_marker_lines": layout_marker_lines,
        "synastry_mentions": synastry_mentions,
        "chapter_body_markers": chapter_body_markers,
        "chapter_start_line": chapter_start,
        "chapter_end_line": chapter_end,
        "likely_chapter_body_lines_after_chapter_start": likely_chapter_body_lines,
        "has_contents_synastry": "6   •   In Synastry" in text,
        "has_front_cover_process_quote": "Saturn symbolizes a psychic process" in text,
        "has_hand_foreword_choice_boundary": "not fixed or determined" in text and "it is always possible" in text,
    }


def phase3_checks(texts: dict[Path, str], metrics: dict[str, Any]) -> tuple[list[Check], list[list[Any]]]:
    coverage_text = texts[COVERAGE_PATH]
    matrix_text = texts[EXECUTION_MATRIX_PATH]
    precision_smoke_text = texts[PRECISION_SMOKE_PATH]
    synastry_mentions = metrics["synastry_mentions"]
    likely_body_lines = metrics["likely_chapter_body_lines_after_chapter_start"]
    saturn_body_unavailable = (
        metrics["has_contents_synastry"]
        and metrics["layout_marker_lines"] >= 100
        and len(synastry_mentions) <= 3
        and len(likely_body_lines) < 20
        and not metrics["chapter_body_markers"]
    )
    existing_guardrail_usable = (
        "saturn-as-process-not-fate" in coverage_text
        and "saturn-awareness-not-fixed-fate" in coverage_text
        and "greene-saturn-defense-not-permanent-rejection" in coverage_text
        and metrics["has_front_cover_process_quote"]
        and metrics["has_hand_foreword_choice_boundary"]
    )
    blocked_row_present = (
        "full-saturn-body-extraction" in coverage_text
        and "not enough chapter body for detailed Saturn claims" in coverage_text
        and "keep detailed Saturn body extraction blocked until usable chapter text exists" in matrix_text
    )
    smoke_wired = (
        "assert_saturn_source_still_blocked" in precision_smoke_text
        and "Saturn synastry body may now exist" in precision_smoke_text
    )
    checks = [
        Check(
            "phase3-saturn-source-body-unavailable",
            "PASS" if saturn_body_unavailable else "FAIL",
            (
                f"{rel(SATURN_RAW_PATH)} has {metrics['line_count']} lines, "
                f"{metrics['layout_marker_lines']} layout marker lines, "
                f"{len(synastry_mentions)} synastry mention(s), "
                f"{len(likely_body_lines)} likely prose line(s) inside the Chapter 6 page span"
            ),
        ),
        Check(
            "phase3-existing-saturn-guardrails-usable",
            "PASS" if existing_guardrail_usable else "FAIL",
            "front-cover process quote and Hand foreword choice boundary remain available for nonfatal Saturn guardrails",
        ),
        Check(
            "phase3-deeper-saturn-claims-blocked",
            "PASS" if blocked_row_present else "FAIL",
            f"{rel(COVERAGE_PATH)} and {rel(EXECUTION_MATRIX_PATH)} keep full Saturn body extraction blocked",
        ),
        Check(
            "phase3-source-quality-smoke-wired",
            "PASS" if smoke_wired else "FAIL",
            f"{rel(PRECISION_SMOKE_PATH)} fails if a real Synastry body appears and is left unextracted",
        ),
    ]
    rows = [
        [
            "Phase 3: Deeper Saturn Body Extraction",
            "blocked until source quality changes",
            "Do not add Moon-Saturn, Venus-Saturn, Mars-Saturn, Sun-Saturn, or Saturn timing depth from Greene beyond existing nonfatal guardrails.",
        ],
        [
            "Existing Saturn runtime",
            "allowed",
            "Keep current process/pressure boundary: Saturn can describe delay, pressure, responsibility, and pacing, but not secret love or permanent rejection.",
        ],
    ]
    return checks, rows


def phase4_checks(texts: dict[Path, str]) -> tuple[list[Check], list[list[Any]]]:
    runtime_text = texts[RUNTIME_PATH]
    calc_text = texts[CALC_SPIKE_PATH]
    adapter_text = texts[IMMANUEL_ADAPTER_PATH]
    low_level_house_data = '"house": house.get("number") or house.get("name")' in adapter_text
    no_overlay_calculation = (
        "calculate_house_overlay" not in adapter_text
        and "calculate_house_overlay" not in calc_text
        and "house_overlays" not in calc_text
    )
    runtime_gate = (
        "def western_house_overlay_layer_status" in runtime_text
        and '"status": "not_available"' in runtime_text
        and '"houseOverlayCalculationAvailable": False' in runtime_text
        and "blocked_by_birth_time" in runtime_text
        and "blocked_by_location" in runtime_text
    )
    checks = [
        Check(
            "phase4-low-level-house-data-present",
            "PASS" if low_level_house_data else "FAIL",
            f"{rel(IMMANUEL_ADAPTER_PATH)} preserves natal object house fields when calculation provides them",
        ),
        Check(
            "phase4-house-overlay-calculation-absent",
            "PASS" if no_overlay_calculation else "FAIL",
            "no productized cross-person house overlay calculation is wired into the Western calculation spike",
        ),
        Check(
            "phase4-house-overlay-runtime-gated",
            "PASS" if runtime_gate else "FAIL",
            f"{rel(RUNTIME_PATH)} blocks missing time/place and marks high-precision overlays as not available",
        ),
    ]
    rows = [
        [
            "Phase 4: House Overlay Precision Layer",
            "prepared but not exposed",
            "Birth precision gates exist and low-level house fields may exist, but cross-person overlay calculation/selectors are not productized.",
        ]
    ]
    return checks, rows


def phase5_checks(texts: dict[Path, str]) -> tuple[list[Check], list[list[Any]]]:
    runtime_text = texts[RUNTIME_PATH]
    calc_text = texts[CALC_SPIKE_PATH]
    adapter_text = texts[IMMANUEL_ADAPTER_PATH]
    signals_text = texts[WESTERN_SIGNALS_PATH]
    calculation_absent = (
        "calculate_composite" not in calc_text
        and "calculate_composite" not in adapter_text
        and "calculate_davison" not in calc_text
        and "calculate_davison" not in adapter_text
        and '"composite"' not in calc_text
        and '"davison"' not in calc_text.lower()
    )
    runtime_blocked = (
        "def western_composite_layer_status" in runtime_text
        and '"status": "not_calculated"' in runtime_text
        and '"requiresCalculatedRelationshipChart": True' in runtime_text
        and '"canCreateAstrologyConclusion": False' in runtime_text
    )
    timing_boundary_mentions = "composite、Davison" in signals_text and "secondary progressions" in signals_text
    checks = [
        Check(
            "phase5-composite-davison-calculation-absent",
            "PASS" if calculation_absent else "FAIL",
            "Western calculation spike does not build composite or Davison chart payloads",
        ),
        Check(
            "phase5-composite-davison-runtime-blocked",
            "PASS" if runtime_blocked else "FAIL",
            f"{rel(RUNTIME_PATH)} keeps relationship chart layer not calculated and non-conclusive",
        ),
        Check(
            "phase5-timing-boundary-explicit",
            "PASS" if timing_boundary_mentions else "FAIL",
            f"{rel(WESTERN_SIGNALS_PATH)} says current timing does not include composite/Davison/progression layers",
        ),
    ]
    rows = [
        [
            "Phase 5: Composite/Davison Relationship Chart Layer",
            "blocked until calculation exists",
            "Reserve source claims stay method-only; visible relationship-chart interpretation must wait for calculated chart payloads and dedicated scenarios.",
        ]
    ]
    return checks, rows


def report_texts() -> dict[Path, str]:
    return {
        COVERAGE_PATH: read_text(COVERAGE_PATH),
        EXECUTION_MATRIX_PATH: read_text(EXECUTION_MATRIX_PATH),
        RUNTIME_PATH: read_text(RUNTIME_PATH),
        CALC_SPIKE_PATH: read_text(CALC_SPIKE_PATH),
        IMMANUEL_ADAPTER_PATH: read_text(IMMANUEL_ADAPTER_PATH),
        WESTERN_SIGNALS_PATH: read_text(WESTERN_SIGNALS_PATH),
        PRECISION_SMOKE_PATH: read_text(PRECISION_SMOKE_PATH),
    }


def build_report() -> str:
    texts = report_texts()
    metrics = saturn_source_metrics()
    phase3, phase3_rows = phase3_checks(texts, metrics)
    phase4, phase4_rows = phase4_checks(texts)
    phase5, phase5_rows = phase5_checks(texts)
    checks = [*phase3, *phase4, *phase5]
    errors = [check for check in checks if not check.ok]
    phase_rows = [*phase3_rows, *phase4_rows, *phase5_rows]

    lines = [
        "# Paid V1.1 Western Precision Depth Audit",
        "",
        "Generated from the current local source extraction, Western calculation spike, paid result runtime, precision boundary smoke, and book coverage matrix.",
        "",
        "## Gate Result",
        "",
        "Status: " + ("PASS" if not errors else "FAIL"),
        "",
        md_table(["Check", "Result", "Evidence"], [[check.id, check.result, check.evidence] for check in checks]),
        "",
        "## Phase Decisions",
        "",
        md_table(["Phase", "Decision", "Boundary"], phase_rows),
        "",
        "## Saturn Source Quality",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["raw lines", metrics["line_count"]],
                ["raw chars", metrics["char_count"]],
                ["layout marker lines", metrics["layout_marker_lines"]],
                ["synastry mentions", ", ".join(str(line) for line in metrics["synastry_mentions"]) or "none"],
                ["chapter body markers", ", ".join(str(line) for line in metrics["chapter_body_markers"]) or "none"],
                ["chapter page span", f"{metrics['chapter_start_line']} to {metrics['chapter_end_line']}"],
                [
                    "likely prose lines inside chapter page span",
                    ", ".join(str(line) for line in metrics["likely_chapter_body_lines_after_chapter_start"][:12]) or "none",
                ],
            ],
        ),
        "",
        "## Runtime Boundary",
        "",
        "- Phase 3 may keep existing Saturn process/pressure guardrails, but cannot add detailed Greene Saturn body claims until the local source contains usable chapter prose.",
        "- Phase 4 has birth-time/place precision gates and low-level natal house fields, but no productized cross-person house overlay calculation or visible overlay interpretation.",
        "- Phase 5 remains reserved: the paid runtime traces relationship chart source/method claims but does not calculate or expose Composite/Davison interpretation.",
        "",
        "## Next Unlock Criteria",
        "",
        "- Replace or re-extract the Greene Saturn source so Chapter 6 and relevant aspect/body text are readable, then add only quote-backed Saturn claims.",
        "- Add an explicit house-overlay calculator and scenario matrix before any visible overlay copy appears.",
        "- Add calculated Composite/Davison chart payloads, method claims, runtime traces, and UI separation before relationship-chart interpretation appears.",
        "",
    ]
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {check.id}: {check.evidence}" for check in errors)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate paid V1.1 Western precision/depth audit report.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    parser.add_argument("--check", action="store_true", help="Validate without writing and fail if the report is stale.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    report = build_report()
    errors_present = "Status: FAIL" in report
    if args.check:
        if errors_present:
            print(report)
            return 1
        if not out_path.exists():
            print(f"Missing paid V1.1 Western precision/depth audit report: {out_path.relative_to(ROOT)}")
            return 1
        if out_path.read_text(encoding="utf-8") != report:
            print(f"Paid V1.1 Western precision/depth audit report is stale: {out_path.relative_to(ROOT)}")
            return 1
        print("Paid V1.1 Western precision/depth audit report passed")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    if errors_present:
        print(f"Wrote failing paid V1.1 Western precision/depth audit report -> {out_path.relative_to(ROOT)}")
        return 1
    print(f"Wrote paid V1.1 Western precision/depth audit report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
