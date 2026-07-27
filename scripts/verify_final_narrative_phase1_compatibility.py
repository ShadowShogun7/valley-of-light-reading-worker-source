#!/usr/bin/env python3
"""Verify that Phase 1 adds typed facts without changing V13 visible copy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = (
    ROOT
    / "data"
    / "reading-production-calibration"
    / "baselines"
    / "final-narrative-composer-v13"
    / "holdout-corpus.json"
)
DEFAULT_CURRENT = ROOT / "data" / "reading-production-calibration" / "v1" / "holdout-corpus.json"
DEFAULT_REPORT = ROOT / "docs" / "research" / "31-final-narrative-phase1-fact-contract.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def visible_records(corpus: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [
        {"id": str(item.get("id") or ""), "sections": item.get("sections") or {}}
        for item in corpus.get(key) or []
        if isinstance(item, dict)
    ]


def evaluate(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    cohorts: dict[str, Any] = {}
    for key in ("matrixCases", "comparisonCases"):
        before = visible_records(baseline, key)
        after = visible_records(current, key)
        changed_ids = [
            str(right.get("id") or "")
            for left, right in zip(before, after, strict=False)
            if left != right
        ]
        if len(before) != len(after):
            failures.append(f"{key} count changed: {len(before)} -> {len(after)}")
        if changed_ids:
            failures.append(f"{key} visible copy changed in {len(changed_ids)} case(s)")
        cohorts[key] = {
            "baselineCount": len(before),
            "currentCount": len(after),
            "baselineVisibleHash": stable_hash(before),
            "currentVisibleHash": stable_hash(after),
            "changedCaseIds": changed_ids[:20],
        }

    matrix = [item for item in current.get("matrixCases") or [] if isinstance(item, dict)]
    invalid_fact_contracts = [
        str(item.get("id") or "")
        for item in matrix
        if str((item.get("finalFactContract") or {}).get("validationStatus") or "") != "valid"
    ]
    if invalid_fact_contracts:
        failures.append(f"invalid final fact contracts: {len(invalid_fact_contracts)}")
    fact_count = sum(
        int(section.get("factCount") or 0)
        for item in matrix
        for section in ((item.get("finalFactContract") or {}).get("sections") or {}).values()
        if isinstance(section, dict)
    )
    unknown_fact_ids = [
        str(fact_id)
        for item in matrix
        for section in ((item.get("finalFactContract") or {}).get("sections") or {}).values()
        if isinstance(section, dict)
        for fact_id in section.get("unknownFactIds") or []
    ]
    compatibility_slots = sum(
        len(section.get("compatibilityProseSlots") or [])
        for item in matrix
        for section in ((item.get("finalFactContract") or {}).get("sections") or {}).values()
        if isinstance(section, dict)
    )
    return {
        "status": "FAIL" if failures else "PASS",
        "failures": failures,
        "baselineComposerVersion": baseline.get("composerVersion"),
        "currentComposerVersion": current.get("composerVersion"),
        "factContractVersion": current.get("factContractVersion"),
        "factRendererMode": current.get("factRendererMode"),
        "cohorts": cohorts,
        "typedFactCount": fact_count,
        "invalidFactContractCount": len(invalid_fact_contracts),
        "unknownFactCount": len(unknown_fact_ids),
        "unknownFactIds": sorted(set(unknown_fact_ids)),
        "compatibilityProseSlotCount": compatibility_slots,
    }


def render_report(result: dict[str, Any]) -> str:
    matrix = result["cohorts"]["matrixCases"]
    comparisons = result["cohorts"]["comparisonCases"]
    lines = [
        "# Final Narrative Phase 1 Fact Contract",
        "",
        "> Verification that the typed fact boundary is active without changing the V13 reader-visible baseline.",
        "",
        "## Verdict",
        "",
        f"- Phase 1 compatibility: **{result['status']}**",
        f"- Baseline composer: `{result['baselineComposerVersion']}`",
        f"- Current composer: `{result['currentComposerVersion']}`",
        f"- Fact contract: `{result['factContractVersion']}`",
        f"- Renderer mode: `{result['factRendererMode']}`",
        "",
        "## Visible Compatibility",
        "",
        f"- Matrix cases: {matrix['currentCount']}",
        f"- Matrix visible hash unchanged: `{matrix['baselineVisibleHash'] == matrix['currentVisibleHash']}`",
        f"- Controlled comparisons: {comparisons['currentCount']}",
        f"- Comparison visible hash unchanged: `{comparisons['baselineVisibleHash'] == comparisons['currentVisibleHash']}`",
        "",
        "## Fact Boundary",
        "",
        f"- Typed facts emitted across matrix: {result['typedFactCount']}",
        f"- Invalid fact contracts: {result['invalidFactContractCount']}",
        f"- Unknown fact diagnostics: {result['unknownFactCount']}",
        f"- Legacy prose compatibility slots: {result['compatibilityProseSlotCount']}",
        "",
        "Unknown facts are explicit diagnostics rather than silent reader-copy fallbacks. In this corpus they are unresolved relationship-fit growth signals where no supported growth pair was available.",
        "",
        "## Phase 2 Exit Condition",
        "",
        "Phase 2 must migrate each section renderer from legacy prose slots to stable fact IDs. Only after all five sections are migrated may `rendererMode` change from `legacy-prose-compatibility` to `fact-only` and the compatibility slot count reach zero.",
        "",
        "## Failures",
        "",
        *([f"- {item}" for item in result["failures"]] or ["- None."]),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    result = evaluate(load_json(args.baseline), load_json(args.current))
    if not args.no_write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(render_report(result), encoding="utf-8")
        print(f"Wrote {args.out.relative_to(ROOT)}")
    print(f"Phase 1 compatibility: {result['status']}")
    print(f"Typed facts: {result['typedFactCount']}")
    print(f"Unknown fact diagnostics: {result['unknownFactCount']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
