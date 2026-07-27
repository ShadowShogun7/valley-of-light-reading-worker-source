#!/usr/bin/env python3
"""Require a complete human-reviewed Phase 5 production golden set."""

from __future__ import annotations

import json
from pathlib import Path

from build_reading_phase5_calibration import CORPUS_VERSION, REVIEW_DIMENSIONS
from kb_utils import ROOT
from promote_phase5_reviewed_golden import GOLDEN_VERSION


CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "holdout-corpus.json"
GOLDEN_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "production-golden-cases.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(GOLDEN_PATH.exists(), "Phase 5 human acceptance is pending. Complete /review and promote the exported reviews.")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    require(golden.get("version") == GOLDEN_VERSION, "production golden version mismatch")
    require(golden.get("corpusVersion") == CORPUS_VERSION, "production golden corpus version mismatch")
    require(golden.get("corpusFingerprint") == corpus.get("corpusFingerprint"), "production golden corpus is stale")
    require(int(golden.get("acceptedCount") or 0) >= 30, "production golden requires at least 30 accepted cases")
    require(len(golden.get("records") or []) == int(golden.get("acceptedCount") or 0), "production golden record count mismatch")
    require(
        all(not str(((record.get("review") or {}).get("notes") or "")).strip() for record in golden.get("records") or []),
        "production golden contains unresolved review notes",
    )
    averages = golden.get("dimensionAverages") or {}
    for dimension in REVIEW_DIMENSIONS:
        require(float(averages.get(dimension) or 0) >= 4.0, f"human score below 4.0: {dimension}")
    print("Phase 5 human acceptance passed")
    print(f"- accepted cases: {golden.get('acceptedCount')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
