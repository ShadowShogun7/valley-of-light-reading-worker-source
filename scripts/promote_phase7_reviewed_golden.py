#!/usr/bin/env python3
"""Promote genuinely reviewed Phase 7 cases into the production golden set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_reading_phase7_calibration import (
    CORPUS_VERSION,
    DEFAULT_CONTRACT_PATH,
    DEFAULT_OUTPUT_DIR,
    REVIEW_VERSION,
    review_coverage,
)
from kb_utils import ROOT


DEFAULT_CORPUS_PATH = DEFAULT_OUTPUT_DIR / "holdout-corpus.json"
DEFAULT_REVIEW_MANIFEST_PATH = DEFAULT_OUTPUT_DIR / "review-manifest.json"
DEFAULT_OUTPUT_PATH = DEFAULT_OUTPUT_DIR / "production-golden-cases.json"
GOLDEN_VERSION = "relationship-reading-production-golden-v3"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST_PATH)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    corpus = read_json(args.corpus)
    manifest = read_json(args.review_manifest)
    contract = read_json(args.contract)
    export = read_json(args.reviews)
    review_contract = contract.get("humanReview") or {}
    dimensions = list(review_contract.get("dimensions") or [])
    minimum_score = int(review_contract.get("minimumDimensionScore") or 0)
    required_accepted = int(review_contract.get("requiredAcceptedCount") or 0)
    if export.get("version") != REVIEW_VERSION:
        raise ValueError(f"review export version mismatch: {export.get('version')}")
    if export.get("corpusVersion") != CORPUS_VERSION:
        raise ValueError("review export does not match the Phase 7 corpus version")
    if export.get("corpusFingerprint") != corpus.get("corpusFingerprint"):
        raise ValueError("review export does not match the current Phase 7 corpus")
    matrix_records = {
        str(item.get("id") or ""): item
        for item in corpus.get("matrixCases") or []
        if isinstance(item, dict)
    }
    review_ids = {str(item.get("id") or "") for item in manifest.get("cases") or [] if isinstance(item, dict)}
    accepted_records: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    rejected_count = 0
    noted_count = 0
    for review in export.get("reviews") or []:
        if not isinstance(review, dict):
            continue
        case_id = str(review.get("caseId") or "")
        if case_id not in review_ids or case_id not in matrix_records:
            raise ValueError(f"unknown Phase 7 reviewed case: {case_id}")
        status = str(review.get("status") or "pending")
        if status == "rejected":
            rejected_count += 1
            continue
        if status != "accepted":
            continue
        notes = str(review.get("notes") or "").strip()
        if notes:
            noted_count += 1
            continue
        scores = review.get("scores") if isinstance(review.get("scores"), dict) else {}
        normalized_scores = {dimension: int(scores.get(dimension) or 0) for dimension in dimensions}
        if any(score < minimum_score or score > 5 for score in normalized_scores.values()):
            continue
        record = matrix_records[case_id]
        accepted_records.append(record)
        accepted.append(
            {
                "id": case_id,
                "context": record.get("context") or {},
                "calibrationAxes": record.get("calibrationAxes") or {},
                "hiddenModel": record.get("hiddenModel") or {},
                "sections": record.get("sections") or {},
                "review": {"scores": normalized_scores, "notes": ""},
            }
        )
    if len(accepted) < required_accepted:
        raise ValueError(
            f"at least {required_accepted} accepted cases with every score >= {minimum_score} are required; got {len(accepted)}"
        )
    accepted_coverage = review_coverage(accepted_records)
    for group, values in (manifest.get("coverage") or {}).items():
        missing = set(values) - set(accepted_coverage.get(group) or [])
        if missing:
            raise ValueError(f"accepted Phase 7 cases miss {group} coverage: {sorted(missing)}")
    averages = {
        dimension: round(sum(item["review"]["scores"][dimension] for item in accepted) / len(accepted), 2)
        for dimension in dimensions
    }
    output = {
        "version": GOLDEN_VERSION,
        "corpusVersion": CORPUS_VERSION,
        "corpusFingerprint": corpus.get("corpusFingerprint"),
        "acceptedCount": len(accepted),
        "rejectedCount": rejected_count,
        "acceptedWithNotesExcludedCount": noted_count,
        "dimensionAverages": averages,
        "coverage": accepted_coverage,
        "records": sorted(accepted, key=lambda item: item["id"]),
    }
    write_json(args.out, output)
    print(f"Promoted {len(accepted)} Phase 7 human-reviewed cases -> {display_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
