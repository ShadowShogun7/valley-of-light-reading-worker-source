#!/usr/bin/env python3
"""Turn exported Phase 5 reviewer comments into permanent copy regressions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from readable_interpretation.copy_contract import intra_page_overlap_hits


CORPUS_PATH = ROOT / "data" / "reading-production-calibration" / "v1" / "holdout-corpus.json"
FEEDBACK_PATH = ROOT / "data" / "reading-human-feedback" / "phase5-review-v2-regressions.json"
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def visible_text(section: dict[str, Any]) -> str:
    return "\n".join(str(section.get(field) or "") for field in VISIBLE_FIELDS if section.get(field))


def main() -> int:
    corpus = read_json(CORPUS_PATH)
    feedback = read_json(FEEDBACK_PATH)
    cases = [item for item in corpus.get("matrixCases") or [] if isinstance(item, dict)]
    failures: list[str] = []
    all_text = "\n".join(
        visible_text(section)
        for case in cases
        for section in (case.get("sections") or {}).values()
        if isinstance(section, dict)
    )
    for phrase in feedback.get("forbiddenExactPhrases") or []:
        if phrase and phrase in all_text:
            failures.append(f"reviewed bad phrase returned: {phrase}")

    advice_markers = [str(item) for item in feedback.get("overusedAdviceMarkers") or []]
    action_texts = [visible_text((case.get("sections") or {}).get("action-direction") or {}) for case in cases]
    advice_hits = sum(1 for text in action_texts if any(marker in text for marker in advice_markers))
    advice_coverage = advice_hits / len(action_texts) if action_texts else 0.0
    maximum_coverage = float(feedback.get("maximumAdviceFamilyCoverage") or 0.45)
    if advice_coverage > maximum_coverage:
        failures.append(f"one-small-thing advice family covers {advice_coverage:.1%}, maximum is {maximum_coverage:.1%}")

    boundary_markers = [str(item) for item in feedback.get("blockedBoundaryMarkers") or []]
    prompt_markers = [str(item) for item in feedback.get("blockedContactPromptMarkers") or []]
    blocked_cases = [case for case in cases if str((case.get("context") or {}).get("contact_status") or "") == "blocked"]
    for case in blocked_cases:
        action = (case.get("sections") or {}).get("action-direction") or {}
        action_text = visible_text(action)
        if not any(marker in action_text for marker in boundary_markers):
            failures.append(f"{case.get('id')}: blocked action has no explicit boundary")
        headline = str(action.get("headline") or "")
        if any(marker in headline for marker in prompt_markers):
            failures.append(f"{case.get('id')}: blocked headline still prompts contact: {headline}")

    overlap_count = 0
    for case in cases:
        for section_id, section in (case.get("sections") or {}).items():
            if not isinstance(section, dict):
                continue
            for hit in intra_page_overlap_hits(section):
                overlap_count += 1
                failures.append(
                    f"{case.get('id')}:{section_id}: repeats {hit.get('phrase')} across "
                    f"{hit.get('leftField')} and {hit.get('rightField')}"
                )
    maximum_overlaps = int(((feedback.get("intraPageOverlapPolicy") or {}).get("maximumViolations") or 0))
    if overlap_count <= maximum_overlaps:
        failures = [item for item in failures if " repeats " not in item]

    if failures:
        print("Phase 5 human-feedback regressions failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Phase 5 human-feedback regressions passed")
    print(f"- cases: {len(cases)}")
    print(f"- one-small-thing advice coverage: {advice_coverage:.1%}")
    print(f"- blocked cases checked: {len(blocked_cases)}")
    print(f"- intra-page overlap violations: {overlap_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
