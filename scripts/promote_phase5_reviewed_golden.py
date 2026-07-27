#!/usr/bin/env python3
"""Promote genuinely human-reviewed Phase 5 cases into the production golden set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_reading_phase5_calibration import CORPUS_VERSION, REVIEW_DIMENSIONS, REVIEW_VERSION
from kb_utils import ROOT


DEFAULT_CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "holdout-corpus.json"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "production-golden-cases.json"
GOLDEN_VERSION = "relationship-reading-production-golden-v2"


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
    parser = argparse.ArgumentParser(description="Promote reviewed Phase 5 cases into the production golden set.")
    parser.add_argument("--reviews", type=Path, required=True, help="JSON exported by the local Phase 5 review dashboard.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    corpus = read_json(args.corpus)
    export = read_json(args.reviews)
    if export.get("version") != REVIEW_VERSION:
        raise ValueError(f"review export version mismatch: {export.get('version')}")
    if export.get("corpusVersion") != CORPUS_VERSION or export.get("corpusFingerprint") != corpus.get("corpusFingerprint"):
        raise ValueError("review export does not match the current Phase 5 corpus")
    records = {str(item.get("id") or ""): item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)}
    accepted: list[dict[str, Any]] = []
    rejected_count = 0
    noted_count = 0
    for review in export.get("reviews") or []:
        if not isinstance(review, dict):
            continue
        case_id = str(review.get("caseId") or "")
        if case_id not in records:
            raise ValueError(f"unknown reviewed case: {case_id}")
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
        normalized_scores = {dimension: int(scores.get(dimension) or 0) for dimension in REVIEW_DIMENSIONS}
        if any(score < 4 or score > 5 for score in normalized_scores.values()):
            continue
        accepted.append(
            {
                "id": case_id,
                "context": records[case_id].get("context") or {},
                "hiddenModel": records[case_id].get("hiddenModel") or {},
                "sections": records[case_id].get("sections") or {},
                "review": {
                    "scores": normalized_scores,
                    "notes": "",
                },
            }
        )
    if len(accepted) < 30:
        raise ValueError(f"at least 30 accepted cases with every score >= 4 are required; got {len(accepted)}")
    for key, label in (
        ("relationship_stage", "status"),
        ("main_question", "question"),
        ("contact_status", "contact"),
    ):
        values = {str((item.get("context") or {}).get(key) or "") for item in accepted}
        if len(values) < 5:
            raise ValueError(f"accepted cases do not cover all {label} values: {sorted(values)}")
    averages = {
        dimension: round(sum(item["review"]["scores"][dimension] for item in accepted) / len(accepted), 2)
        for dimension in REVIEW_DIMENSIONS
    }
    output = {
        "version": GOLDEN_VERSION,
        "corpusVersion": CORPUS_VERSION,
        "corpusFingerprint": corpus.get("corpusFingerprint"),
        "acceptedCount": len(accepted),
        "rejectedCount": rejected_count,
        "acceptedWithNotesExcludedCount": noted_count,
        "dimensionAverages": averages,
        "records": sorted(accepted, key=lambda item: item["id"]),
    }
    write_json(args.out, output)
    print(f"Promoted {len(accepted)} human-reviewed cases -> {display_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
