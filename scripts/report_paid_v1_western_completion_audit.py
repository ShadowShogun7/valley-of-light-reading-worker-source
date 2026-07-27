#!/usr/bin/env python3
"""Generate the paid V1 Western book-digestion completion audit."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kb_utils import ROOT, read_text


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "22-paid-v1-western-completion-audit.md"
FUNCTION_COVERAGE_REPORT = ROOT / "docs" / "research" / "15-western-v1-reading-function-coverage.md"
EXECUTION_MATRIX_REPORT = ROOT / "docs" / "research" / "17-western-book-digestion-execution-matrix.md"
SURFACE_EVIDENCE_REPORT = ROOT / "docs" / "research" / "18-paid-v1-result-surface-evidence.md"
TIMING_BRANCH_REPORT = ROOT / "docs" / "research" / "19-western-timing-reducer-branch-evidence.md"
METHOD_USAGE_REPORT = ROOT / "docs" / "research" / "13-western-method-claim-runtime-usage.md"
PRECISION_DEPTH_REPORT = ROOT / "docs" / "research" / "23-paid-v11-precision-depth-audit.md"
STACK_VERIFIER = ROOT / "scripts" / "verify_paid_v1_reading_stack.py"

REQUIRED_V1_SECTIONS = (
    ("01 星盤定位", "profile positioning"),
    ("02 兩個人的關係契合度分析", "relationship fit"),
    ("03 核心問題解讀", "core question answer"),
    ("04 時機判讀", "timing judgment"),
    ("05 行動方向", "action direction"),
)
REQUIRED_SURFACE_TIMING_ACTIONS = ("avoid_push", "low_pressure_message", "observe_only")
REQUIRED_TIMING_BRANCH_SCENARIOS = (
    "missing-timing-scan",
    "mercury-low-pressure-message",
    "venus-softening-message",
    "mixed-neutral-observe",
    "mars-activation-caution",
    "saturn-boundary-pressure",
    "background-observe-only",
)
REQUIRED_RULE_PRIORITY_SCENARIOS = (
    "blocked-overrides-timing",
    "shared-space-overrides-avoid",
)
REQUIRED_BLOCKED_LAYER_ROWS = (
    ("western-suskin-synastry", "relationship-chart-later", "Composite and Davison layers are not calculated in paid V1."),
    (
        "western-forrest-skymates",
        "house-transpositions-secondary",
        "House overlays require reliable birth time and place and are not fully productized in paid V1.",
    ),
    (
        "western-greene-saturn",
        "full-saturn-body-extraction",
        "Current local extraction is not enough chapter body for detailed Saturn claims.",
    ),
    ("western-davison-synastry", "relationship-chart-reserve", "Davison relationship chart is not calculated or exposed in paid V1."),
    ("western-hand-composite", "composite-chart-reserve", "Composite charts are not calculated in paid V1."),
)
REQUIRED_VERIFIER_STEPS = (
    "book_coverage_validate",
    "book_digests_validate",
    "method_claim_validate",
    "paid_v1_contract",
    "timing_window_matrix",
    "native_copy_contract",
    "precision_layer_boundaries",
    "context_matrix",
    "chart_variation_matrix",
    "paid_surface_report",
    "timing_branch_report",
    "paid_v11_precision_depth_audit_report",
    "web_dashboard_smoke",
)


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


def report_texts() -> dict[Path, str]:
    return {
        FUNCTION_COVERAGE_REPORT: read_text(FUNCTION_COVERAGE_REPORT),
        EXECUTION_MATRIX_REPORT: read_text(EXECUTION_MATRIX_REPORT),
        SURFACE_EVIDENCE_REPORT: read_text(SURFACE_EVIDENCE_REPORT),
        TIMING_BRANCH_REPORT: read_text(TIMING_BRANCH_REPORT),
        METHOD_USAGE_REPORT: read_text(METHOD_USAGE_REPORT),
        PRECISION_DEPTH_REPORT: read_text(PRECISION_DEPTH_REPORT),
        STACK_VERIFIER: read_text(STACK_VERIFIER),
    }


def table_row(text: str, first_cell: str) -> list[str]:
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == first_cell:
            return cells
    return []


def contains_all(text: str, values: tuple[str, ...]) -> list[str]:
    return [value for value in values if value not in text]


def section_readiness_checks(texts: dict[Path, str]) -> tuple[list[Check], list[list[Any]]]:
    function_text = texts[FUNCTION_COVERAGE_REPORT]
    surface_text = texts[SURFACE_EVIDENCE_REPORT]
    matrix_text = texts[EXECUTION_MATRIX_REPORT]
    checks: list[Check] = []
    rows: list[list[Any]] = []
    matrix_section_aliases = {
        "01 星盤定位": "星盤定位",
        "02 兩個人的關係契合度分析": "兩個人的關係契合度分析",
        "03 核心問題解讀": "核心問題解讀",
        "04 時機判讀": "時機判讀",
        "05 行動方向": "行動方向",
    }

    for title, role in REQUIRED_V1_SECTIONS:
        function_row = table_row(function_text, title)
        surface_row = table_row(surface_text, title)
        matrix_alias = matrix_section_aliases[title]
        matrix_ok = f"| {matrix_alias} |" in matrix_text and "Scenario gaps" in matrix_text
        strong_ok = len(function_row) >= 4 and function_row[1] == "strong" and function_row[3] == "0 weak, 0 thin, 0 missing"
        surface_ok = len(surface_row) >= 4 and "/" in surface_row[2] and not surface_row[2].startswith("0/")
        ok = strong_ok and surface_ok and matrix_ok
        checks.append(
            Check(
                id=f"section-{title}",
                result="PASS" if ok else "FAIL",
                evidence=(
                    f"{rel(FUNCTION_COVERAGE_REPORT)} summary={function_row[1:4] if function_row else 'missing'}; "
                    f"{rel(SURFACE_EVIDENCE_REPORT)} surface={surface_row[1:3] if surface_row else 'missing'}"
                ),
            )
        )
        rows.append(
            [
                title,
                role,
                function_row[1] if len(function_row) > 1 else "missing",
                function_row[3] if len(function_row) > 3 else "missing",
                surface_row[2] if len(surface_row) > 2 else "missing",
                "none" if matrix_ok else "missing crosswalk evidence",
            ]
        )
    return checks, rows


def surface_evidence_checks(texts: dict[Path, str]) -> list[Check]:
    text = texts[SURFACE_EVIDENCE_REPORT]
    checks = [
        Check(
            id="surface-report-pass",
            result="PASS" if "Status: PASS" in text else "FAIL",
            evidence=f"{rel(SURFACE_EVIDENCE_REPORT)} gate result",
        )
    ]
    missing_actions = contains_all(text, REQUIRED_SURFACE_TIMING_ACTIONS)
    checks.append(
        Check(
            id="paid-example-timing-actions",
            result="PASS" if not missing_actions else "FAIL",
            evidence=(
                "paid examples cover actions "
                + ", ".join(REQUIRED_SURFACE_TIMING_ACTIONS)
                + ("" if not missing_actions else f"; missing {', '.join(missing_actions)}")
            ),
        )
    )
    return checks


def timing_branch_checks(texts: dict[Path, str]) -> list[Check]:
    text = texts[TIMING_BRANCH_REPORT]
    checks = [
        Check(
            id="timing-branch-report-pass",
            result="PASS" if "Status: PASS" in text else "FAIL",
            evidence=f"{rel(TIMING_BRANCH_REPORT)} gate result",
        )
    ]
    missing_branches = contains_all(text, REQUIRED_TIMING_BRANCH_SCENARIOS)
    checks.append(
        Check(
            id="timing-reducer-branch-fixtures",
            result="PASS" if not missing_branches else "FAIL",
            evidence=(
                "required branches: "
                + ", ".join(REQUIRED_TIMING_BRANCH_SCENARIOS)
                + ("" if not missing_branches else f"; missing {', '.join(missing_branches)}")
            ),
        )
    )
    missing_rules = contains_all(text, REQUIRED_RULE_PRIORITY_SCENARIOS)
    checks.append(
        Check(
            id="timing-rule-priority-fixtures",
            result="PASS" if not missing_rules else "FAIL",
            evidence=(
                "required priority scenarios: "
                + ", ".join(REQUIRED_RULE_PRIORITY_SCENARIOS)
                + ("" if not missing_rules else f"; missing {', '.join(missing_rules)}")
            ),
        )
    )
    if "public payload blocks exact dates and date ranges" in text:
        precise_result = "PASS"
        precise_evidence = "public timing payload blocks exact dates/date ranges"
    else:
        precise_result = "FAIL"
        precise_evidence = "missing public precise-date policy proof"
    checks.append(Check(id="timing-no-precise-date-policy", result=precise_result, evidence=precise_evidence))
    return checks


def execution_matrix_checks(texts: dict[Path, str]) -> tuple[list[Check], list[list[Any]]]:
    text = texts[EXECUTION_MATRIX_REPORT]
    metric_values: dict[str, int] = {}
    for metric, value in re.findall(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|$", text, flags=re.MULTILINE):
        metric_values[metric.strip()] = int(value)
    runtime_targets = metric_values.get("Runtime targets")
    scenario_covered_targets = metric_values.get("Scenario-covered targets")
    coverage_matches = (
        runtime_targets is not None
        and scenario_covered_targets is not None
        and runtime_targets > 0
        and runtime_targets == scenario_covered_targets
    )
    checks = [
        Check(
            id="no-missing-scenario-targets",
            result="PASS" if "| Missing scenario targets | none |" in text else "FAIL",
            evidence=f"{rel(EXECUTION_MATRIX_REPORT)} summary row",
        ),
        Check(
            id="runtime-target-scenario-coverage",
            result="PASS" if coverage_matches else "FAIL",
            evidence=(
                "runtime target count equals scenario-covered target count in execution matrix"
                f" ({runtime_targets} / {scenario_covered_targets})"
            ),
        ),
    ]
    rows: list[list[Any]] = []
    for source_id, section_id, reason in REQUIRED_BLOCKED_LAYER_ROWS:
        row_ok = source_id in text and section_id in text and "blocked" in text
        checks.append(
            Check(
                id=f"blocked-layer-{section_id}",
                result="PASS" if row_ok else "FAIL",
                evidence=f"{source_id} / {section_id} is documented as blocked/future-layer",
            )
        )
        rows.append([source_id, section_id, "blocked/future-layer" if row_ok else "missing", reason])
    return checks, rows


def method_usage_checks(texts: dict[Path, str]) -> list[Check]:
    text = texts[METHOD_USAGE_REPORT]
    fail_patterns = (
        r"\|\s*missing\s*\|",
        r"\|\s*unused\s*\|",
        r"\|\s*FAIL\s*\|",
    )
    has_failure = any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in fail_patterns)
    return [
        Check(
            id="method-claim-runtime-usage-report",
            result="PASS" if not has_failure else "FAIL",
            evidence=f"{rel(METHOD_USAGE_REPORT)} has no missing/unused/failing usage rows by audit pattern",
        )
    ]


def precision_depth_checks(texts: dict[Path, str]) -> list[Check]:
    text = texts[PRECISION_DEPTH_REPORT]
    required = (
        "Status: PASS",
        "Phase 3: Deeper Saturn Body Extraction",
        "blocked until source quality changes",
        "Phase 4: House Overlay Precision Layer",
        "prepared but not exposed",
        "Phase 5: Composite/Davison Relationship Chart Layer",
        "blocked until calculation exists",
    )
    missing = contains_all(text, required)
    return [
        Check(
            id="paid-v11-precision-depth-audit",
            result="PASS" if not missing else "FAIL",
            evidence=(
                f"{rel(PRECISION_DEPTH_REPORT)} proves Saturn source quality, house overlay, and Composite/Davison boundaries"
                + ("" if not missing else f"; missing {', '.join(missing)}")
            ),
        )
    ]


def verifier_wiring_checks(texts: dict[Path, str]) -> list[Check]:
    text = texts[STACK_VERIFIER]
    missing = [step_id for step_id in REQUIRED_VERIFIER_STEPS if step_id not in text]
    return [
        Check(
            id="paid-v1-verifier-wiring",
            result="PASS" if not missing else "FAIL",
            evidence=(
                f"{rel(STACK_VERIFIER)} includes validation, native copy, precision boundaries, context, chart, timing, surface, branch, and rendered web smoke steps"
                + ("" if not missing else f"; missing {', '.join(missing)}")
            ),
        )
    ]


def build_report() -> str:
    texts = report_texts()
    section_checks, section_rows = section_readiness_checks(texts)
    execution_checks, blocked_rows = execution_matrix_checks(texts)
    checks = [
        *section_checks,
        *surface_evidence_checks(texts),
        *timing_branch_checks(texts),
        *execution_checks,
        *method_usage_checks(texts),
        *precision_depth_checks(texts),
        *verifier_wiring_checks(texts),
    ]
    errors = [check for check in checks if not check.ok]

    lines = [
        "# Paid V1 Western Completion Audit",
        "",
        "Generated from the current Western function coverage, execution matrix, paid surface evidence, timing branch evidence, method-claim usage, precision/depth audit, precision-layer boundaries, and paid V1 stack verifier wiring.",
        "",
        "## Gate Result",
        "",
        "Status: " + ("PASS" if not errors else "FAIL"),
        "",
        md_table(
            ["Check", "Result", "Evidence"],
            [[check.id, check.result, check.evidence] for check in checks],
        ),
        "",
        "## Five Section Readiness",
        "",
        md_table(
            ["Section", "Role", "Function coverage", "Function gaps", "Visible surface checks", "Scenario gaps"],
            section_rows,
        ),
        "",
        "## Runtime Evidence Boundary",
        "",
        "- `docs/research/15-western-v1-reading-function-coverage.md` proves source-backed/source-guided method claims are structured, runtime-wired, visible where required, and scenario-covered for the five result sections.",
        "- `docs/research/18-paid-v1-result-surface-evidence.md` proves the live paid examples render all five visible sections from Western evidence reducers, repeated-theme reducers, context policy, and timing reducers.",
        "- `docs/research/19-western-timing-reducer-branch-evidence.md` proves lower-level timing branches beyond the paid examples, including missing scans, Mercury, Venus, Mars, Saturn, neutral/background states, and rule-priority overrides.",
        "- `docs/research/23-paid-v11-precision-depth-audit.md` proves the V1.1 depth boundary: detailed Greene Saturn body extraction is blocked by source quality, house overlays are prepared but not exposed, and Composite/Davison remain uncalculated.",
        "- `scripts/verify_paid_v1_reading_stack.py` keeps the validation suite, runtime contracts, native Traditional Chinese copy contract, precision-layer boundary contract, V1.1 precision/depth audit, context matrix, chart variation matrix, timing matrix, generated reports, rendered dashboard smoke, typecheck, and web build tied to one command.",
        "",
        "## Blocked Or Future Layers",
        "",
        md_table(["Source id", "Section id", "Audit state", "Paid V1 boundary"], blocked_rows),
        "",
        "## Completion Boundary",
        "",
        "This audit supports the paid V1 claim that the current Western source set is ready for the five required result sections. It does not claim every page of every source has been exhausted. The remaining rows above are explicitly blocked or future-layer work because paid V1 does not calculate composite/Davison charts, does not fully productize house overlays, and does not have usable local Saturn chapter body text for detailed Saturn extraction.",
        "",
        "## Next Improvement Policy",
        "",
        "Future improvements should start from a concrete weak output or new runtime requirement. Add a source-backed method claim first, wire it into structured atoms/rules/runtime/readable output, add scenario proof, regenerate reports, and keep exact-date, mind-reading, single-aspect verdict, BaZi, free/locked, and upsell language out of paid V1.",
        "",
    ]
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {check.id}: {check.evidence}" for check in errors)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate paid V1 Western completion audit report.")
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
            print(f"Missing paid V1 Western completion audit report: {out_path.relative_to(ROOT)}")
            return 1
        if out_path.read_text(encoding="utf-8") != report:
            print(f"Paid V1 Western completion audit report is stale: {out_path.relative_to(ROOT)}")
            return 1
        print("Paid V1 Western completion audit report passed")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    if errors_present:
        print(f"Wrote failing paid V1 Western completion audit report -> {out_path.relative_to(ROOT)}")
        return 1
    print(f"Wrote paid V1 Western completion audit report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
