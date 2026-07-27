#!/usr/bin/env python3
"""Compare Phase 3 evidence-to-language depth against the Phase 2 corpus."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from readable_interpretation.final_narrative_pages.timing_renderer import (
    TIMING_BAND_COPY,
    UNRESOLVED_WINDOW_COPY,
)
ROOT = Path(__file__).resolve().parents[1]
V2_DIR = ROOT / "data" / "reading-production-baseline" / "v2"
V3_DIR = ROOT / "data" / "reading-production-baseline" / "v3"
PHASE3_SECTION_NARRATIVE_SPEC_VERSION = "section-narrative-spec-v3"
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def section(metrics: dict[str, Any], corpus: str, section_id: str) -> dict[str, Any]:
    return (((metrics.get(corpus) or {}).get("sectionMetrics") or {}).get(section_id) or {})


def full_page_metrics(corpus: dict[str, Any], section_id: str) -> dict[str, int]:
    pages: Counter[str] = Counter()
    for record in corpus.get("records") or []:
        section_copy = (
            ((record.get("finalInterpretation") or {}).get("sections") or {}).get(section_id)
            or {}
        )
        identity = "|".join(
            re.sub(r"\s+", "", str(section_copy.get(field) or ""))
            for field in VISIBLE_FIELDS
        )
        pages[identity] += 1
    return {
        "uniquePages": len(pages),
        "maxExactPageRepeat": max(pages.values(), default=0),
    }


def main() -> int:
    v2 = read_json(V2_DIR / "metrics.json")
    v3 = read_json(V3_DIR / "metrics.json")
    manifest = read_json(V3_DIR / "manifest.json")
    golden_corpus = read_json(V3_DIR / "golden-cases.json")
    require(v2.get("version") == "relationship-reading-baseline-v2", "Phase 2 metrics version mismatch")
    require(v3.get("version") == "relationship-reading-baseline-v3", "Phase 3 metrics version mismatch")
    require(
        manifest.get("sectionSpecVersion") == PHASE3_SECTION_NARRATIVE_SPEC_VERSION,
        "Phase 3 spec version mismatch",
    )

    distribution = v3.get("distribution") or {}
    require(distribution.get("caseCount") == 500, "Phase 3 distribution corpus is incomplete")
    require(distribution.get("uniqueFitSignatures") == 500, "pair-level fit signatures collapsed")
    require(distribution.get("minimumFitSignalCount", 0) >= 5, "fit signal packet depth is below five")
    require(
        len(distribution.get("coreCentralEvidencePairCounts") or {}) >= 15,
        "core evidence pair-family coverage is too narrow",
    )

    v2_fit = section(v2, "distribution", "relationship-fit")
    v3_fit = section(v3, "distribution", "relationship-fit")
    v2_core = section(v2, "distribution", "core-answer")
    v3_core = section(v3, "distribution", "core-answer")
    v2_timing = section(v2, "distribution", "timing-reading")
    v3_timing = section(v3, "distribution", "timing-reading")
    require(v3_fit.get("uniqueBodies", 0) >= 450, "relationship-fit body depth is below the page-owned gate")
    require(
        v3_fit.get("uniqueBodies", 0) >= v2_fit.get("uniqueBodies", 0),
        "relationship-fit body depth regressed from Phase 2",
    )
    require(v3_fit.get("maxExactBodyRepeat", 99) <= 4, "relationship-fit exact repetition remains too high")
    require(v3_core.get("uniqueBodies", 0) >= 250, "core-answer body depth is below the page-owned gate")
    require(
        v3_core.get("uniqueBodies", 0) >= 3 * v2_core.get("uniqueBodies", 0),
        "core-answer did not improve at least threefold over Phase 2",
    )
    timing_bodies = int(v3_timing.get("uniqueBodies", 0))
    disabled_window_body_limit = len(UNRESOLVED_WINDOW_COPY) * sum(
        len(variants) for variants in TIMING_BAND_COPY.values()
    )
    require(
        timing_bodies >= 5 * int(v2_timing.get("uniqueBodies", 0)),
        "timing page-owned facts did not improve body depth at least fivefold over Phase 2",
    )
    require(
        int(v3_timing.get("maxExactBodyRepeat", 999))
        <= int(v2_timing.get("maxExactBodyRepeat", 0)) // 4,
        "timing exact repetition did not fall to one quarter of the Phase 2 ceiling",
    )
    require(
        timing_bodies <= disabled_window_body_limit,
        "timing body varies beyond the controlled disabled-window sentence catalog",
    )

    golden = v3.get("golden") or {}
    case_count = int(golden.get("caseCount") or 0)
    for section_id, minimum in (
        ("chart-positioning", case_count - 2),
        ("relationship-fit", case_count - 1),
        ("core-answer", case_count),
        ("timing-reading", case_count - 5),
        ("action-direction", case_count),
    ):
        visible = full_page_metrics(golden_corpus, section_id)
        require(
            visible["uniquePages"] >= minimum,
            f"golden {section_id} full-page readings collapsed: {visible['uniquePages']} < {minimum}",
        )
        require(
            visible["maxExactPageRepeat"] <= 2,
            f"golden {section_id} exact full-page repetition remains too high",
        )

    print("Reading Phase 3 depth comparison passed.")
    print(f"- relationship-fit page-owned bodies: {v2_fit.get('uniqueBodies')} -> {v3_fit.get('uniqueBodies')}")
    print(f"- core-answer page-owned bodies: {v2_core.get('uniqueBodies')} -> {v3_core.get('uniqueBodies')}")
    print(f"- pair-level fit signatures: {distribution.get('uniqueFitSignatures')}/500")
    print(f"- central evidence pair families: {len(distribution.get('coreCentralEvidencePairCounts') or {})}")
    print(
        "- controlled disabled-window timing bodies: "
        f"{v2_timing.get('uniqueBodies')} -> {timing_bodies}/{disabled_window_body_limit}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
