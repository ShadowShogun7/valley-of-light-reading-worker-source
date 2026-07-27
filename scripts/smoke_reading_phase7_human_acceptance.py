#!/usr/bin/env python3
"""Require a complete human-reviewed Phase 7 production golden set."""

from __future__ import annotations

import json

from build_reading_phase7_calibration import CORPUS_VERSION, DEFAULT_CONTRACT_PATH, DEFAULT_OUTPUT_DIR
from promote_phase7_reviewed_golden import GOLDEN_VERSION


CORPUS_PATH = DEFAULT_OUTPUT_DIR / "holdout-corpus.json"
GOLDEN_PATH = DEFAULT_OUTPUT_DIR / "production-golden-cases.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    require(GOLDEN_PATH.exists(), "Phase 8 human acceptance is pending. Complete /review and promote the Phase 7 export.")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    contract = json.loads(DEFAULT_CONTRACT_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    review_contract = contract.get("humanReview") or {}
    required = int(review_contract.get("requiredAcceptedCount") or 0)
    minimum = int(review_contract.get("minimumDimensionScore") or 0)
    require(golden.get("version") == GOLDEN_VERSION, "Phase 7 production golden version mismatch")
    require(golden.get("corpusVersion") == CORPUS_VERSION, "Phase 7 production golden corpus version mismatch")
    require(golden.get("corpusFingerprint") == corpus.get("corpusFingerprint"), "Phase 7 production golden corpus is stale")
    require(int(golden.get("acceptedCount") or 0) >= required, f"production golden requires at least {required} accepted cases")
    require(len(golden.get("records") or []) == int(golden.get("acceptedCount") or 0), "production golden record count mismatch")
    require(
        all(not str(((record.get("review") or {}).get("notes") or "")).strip() for record in golden.get("records") or []),
        "production golden contains unresolved review notes",
    )
    for dimension in review_contract.get("dimensions") or []:
        require(
            float((golden.get("dimensionAverages") or {}).get(dimension) or 0) >= minimum,
            f"human score below {minimum}: {dimension}",
        )
    print("Phase 8 human acceptance passed")
    print(f"- accepted Phase 7 cases: {golden.get('acceptedCount')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
