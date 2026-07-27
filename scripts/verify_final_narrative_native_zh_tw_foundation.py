#!/usr/bin/env python3
"""Verify the R0 inventory and R1 native Traditional Chinese foundation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_final_narrative_native_zh_tw import (  # noqa: E402
    DEFAULT_CORPUS_PATH,
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REGRESSION_PATH,
    DEFAULT_REPORT_OUTPUT,
    INVENTORY_VERSION,
    build_audit,
    read_json,
    render_report,
)
from readable_interpretation.final_narrative_chinese_contract import (  # noqa: E402
    audit_native_zh_tw_text,
    native_contract_errors,
    native_contract_payload,
)
from readable_interpretation.final_narrative_chinese_plan import (  # noqa: E402
    FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION,
    ReaderMeaningFrameError,
    frame_from_fact,
    meaning_frame_contract_payload,
    reader_meaning_frame_errors,
)
from readable_interpretation.final_narrative_composition import (  # noqa: E402
    SECTION_COMPOSITION_RULES,
)
from readable_interpretation.final_narrative_realization import REALIZATION_PURPOSES  # noqa: E402
from readable_interpretation.final_narrative_story_arc import (  # noqa: E402
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    is_visible_presentation,
)


DEFAULT_CONTRACT_PATH = (
    ROOT
    / "data"
    / "reading-quality-cases"
    / "final-narrative-native-zh-tw-contract-v1.json"
)
DEFAULT_CANONICAL_PATH = ROOT / "data" / "reading-test-engine" / "v1" / "canonical-record.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_contract_registry() -> None:
    errors = native_contract_errors()
    require(not errors, f"native Chinese contract is invalid: {errors}")
    require(DEFAULT_CONTRACT_PATH.exists(), "machine-readable native Chinese contract is missing")
    require(
        read_json(DEFAULT_CONTRACT_PATH) == native_contract_payload(),
        "machine-readable native Chinese contract is stale",
    )


def verify_regression_recognition(regressions: dict[str, Any]) -> int:
    checked = 0
    for case in regressions.get("cases") or []:
        text = str(case.get("text") or "")
        detected = {issue.id for issue in audit_native_zh_tw_text(text)}
        detected.add("reader-reported-regression")
        expected = {str(item) for item in case.get("expectedDefectIds") or []}
        require(expected <= detected, f"{case.get('id')}: expected defects are not recognized")
        checked += 1
    require(checked > 0, "native Chinese regression registry is empty")
    return checked


def verify_meaning_frame() -> int:
    fact = {
        "id": (
            "relationship-fit.attraction-signal."
            "attraction:venus-mars:persona:mars>personb:venus:conjunction:conjunction"
        ),
        "sectionId": "relationship-fit",
        "role": "attraction-signal",
        "valueKey": "attraction:venus-mars:persona:mars>personb:venus:conjunction:conjunction",
        "sourceBindingFingerprint": "a" * 64,
        "evidenceIds": ["E-relationship-fit"],
        "qualifiers": ["dominant"],
    }
    frame = frame_from_fact(
        fact,
        scene_key="approach-activates-affection",
        purpose="situational",
        certainty="bounded",
    )
    payload = frame.as_payload()
    require(payload.get("version") == FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION, "frame version mismatch")
    require(payload.get("field") == "body", "signal frame lost page-field ownership")
    require(payload.get("direction") == "persona>personb", "signal frame lost person direction")
    require(payload.get("aspectBehavior") == "intensifies-together", "signal frame lost aspect behavior")
    require(not reader_meaning_frame_errors(payload), "valid meaning frame was rejected")

    invalid_prose = {**payload, "text": "你一主動靠近，他也容易表達好感。"}
    require(
        any("visible prose" in error for error in reader_meaning_frame_errors(invalid_prose)),
        "meaning frame accepted visible prose",
    )
    invalid_owner = {**payload, "field": "headline"}
    require(reader_meaning_frame_errors(invalid_owner), "meaning frame accepted wrong page-field owner")
    invalid_signal = {**payload, "aspectBehavior": "flows-naturally"}
    require(reader_meaning_frame_errors(invalid_signal), "meaning frame accepted stale signal semantics")
    invalid_source = {**payload, "sourceFactId": "relationship-fit.attraction-signal.unknown"}
    require(reader_meaning_frame_errors(invalid_source), "meaning frame accepted mismatched source fact")
    invalid_purpose = {**payload, "purpose": "random"}
    require(reader_meaning_frame_errors(invalid_purpose), "meaning frame accepted unsupported purpose")

    try:
        frame_from_fact(
            {**fact, "evidenceIds": []},
            scene_key="approach-activates-affection",
            purpose="situational",
        )
    except ReaderMeaningFrameError:
        pass
    else:
        raise AssertionError("meaning frame accepted a fact without evidence")

    contract = meaning_frame_contract_payload()
    require(contract.get("version") == FINAL_NARRATIVE_READER_MEANING_FRAME_VERSION, "frame contract is stale")
    require("text" in set(contract.get("forbiddenProseKeys") or []), "frame contract does not forbid prose")

    canonical = read_json(DEFAULT_CANONICAL_PATH)
    canonical_sections = ((canonical.get("facts") or {}).get("sections") or {})
    checked = 0
    hidden_checked = 0
    for section_id, section in canonical_sections.items():
        for index, current_fact in enumerate(section.get("facts") or []):
            role = str(current_fact.get("role") or "")
            presentation = str(
                (FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}).get(role) or ""
            )
            if not is_visible_presentation(presentation):
                try:
                    frame_from_fact(
                        current_fact,
                        scene_key=role or "unknown",
                        purpose=REALIZATION_PURPOSES[index % len(REALIZATION_PURPOSES)],
                        certainty="bounded",
                    )
                except ReaderMeaningFrameError:
                    hidden_checked += 1
                    continue
                raise AssertionError(
                    f"hidden story fact entered ReaderMeaningFrame: {section_id}:{role}"
                )
            current = frame_from_fact(
                current_fact,
                scene_key=role or "unknown",
                purpose=REALIZATION_PURPOSES[index % len(REALIZATION_PURPOSES)],
                certainty="bounded",
            )
            require(current.section_id == section_id, "meaning frame changed source section")
            checked += 1
    require(checked > 0, "canonical facts produced no meaning frames")
    require(hidden_checked > 0, "canonical facts exercise no hidden story controls")
    return checked


def verify_inventory(audit: dict[str, Any]) -> None:
    require(audit.get("version") == INVENTORY_VERSION, "R0 inventory version is stale")
    require(
        set(audit.get("sectionSummary") or {}) == set(SECTION_COMPOSITION_RULES),
        "R0 page inventory is incomplete",
    )
    require(int((audit.get("summary") or {}).get("uniqueSentenceCount") or 0) > 0, "R0 sentence inventory is empty")
    summary = audit.get("summary") or {}
    occurrence_count = int(summary.get("sentenceOccurrenceCount") or 0)
    trace_gap_count = int(summary.get("realizationPurposeTraceGapCount") or 0)
    traced_count = int(summary.get("realizationPurposeTracedCount") or 0)
    require(
        trace_gap_count + traced_count == occurrence_count,
        "realization-purpose trace accounting is incomplete",
    )
    require(audit.get("status") == "READY", "R5 native renderer audit is not production-ready")
    for section_id in SECTION_COMPOSITION_RULES:
        section_summary = (audit.get("sectionSummary") or {}).get(section_id) or {}
        require(
            section_summary.get("nativeMigrationStatus") == "READY",
            f"R5 native migration is not production-ready: {section_id}",
        )
        require(
            int(section_summary.get("purposeTraceGapCount") or 0) == 0,
            f"R5 page still has purpose-trace gaps: {section_id}",
        )
        require(
            int(section_summary.get("purposeTracedCount") or 0)
            == int(section_summary.get("occurrenceCount") or -1),
            f"R5 page trace count is incomplete: {section_id}",
        )
        require(
            int(section_summary.get("uniqueFailureSentenceCount") or 0) == 0
            and int(section_summary.get("uniqueWarningSentenceCount") or 0) == 0,
            f"R5 page contains native-Chinese issues: {section_id}",
        )
    require(
        int((audit.get("summary") or {}).get("regressionCaseCount") or 0)
        == int((audit.get("summary") or {}).get("recognizedRegressionCaseCount") or -1),
        "not every reader regression is recognized",
    )
    for entry in audit.get("sentences") or []:
        require(entry.get("text"), "inventory contains an empty sentence")
        require(entry.get("sectionIds"), "inventory sentence lacks page ownership")
        require(entry.get("fields"), "inventory sentence lacks field ownership")
        trace_statuses = set(entry.get("ownershipTraceStatuses") or [])
        require(
            trace_statuses
            and trace_statuses <= {
                "fact-owned",
                "field-level-ambiguous",
                "composition-only-untraced",
                "native-frame-owned",
                "native-composition-owned",
            },
            "inventory sentence has an unexplained ownership trace",
        )
        if entry.get("ownedRoles"):
            require(entry.get("sourceFactIds"), "fact-owned inventory sentence lacks source fact ids")
        else:
            require(
                bool(
                    {"composition-only-untraced", "native-composition-owned"}
                    & trace_statuses
                ),
                "composition-only sentence does not expose its ownership trace gap",
            )
        purposes = set(entry.get("realizationPurposes") or [])
        gap_occurrences = int(entry.get("purposeTraceGapOccurrenceCount") or 0)
        traced_occurrences = int(entry.get("purposeTracedOccurrenceCount") or 0)
        require(
            gap_occurrences + traced_occurrences == int(entry.get("occurrenceCount") or 0),
            "inventory sentence purpose accounting is incomplete",
        )
        if gap_occurrences:
            require(
                "legacy-untraced" in purposes,
                "legacy sentence does not expose its realization-purpose gap",
            )
        if traced_occurrences:
            require(
                purposes - {"legacy-untraced"},
                "migrated sentence lost its realization purpose",
            )
            require(
                {"native-frame-owned", "native-composition-owned"} & trace_statuses,
                "migrated sentence lost native ownership",
            )


def main() -> int:
    try:
        verify_contract_registry()
        regressions = read_json(DEFAULT_REGRESSION_PATH)
        regression_count = verify_regression_recognition(regressions)
        frame_count = verify_meaning_frame()
        current = build_audit(
            read_json(DEFAULT_CORPUS_PATH),
            regressions,
            corpus_path=DEFAULT_CORPUS_PATH,
        )
        verify_inventory(current)
        require(DEFAULT_JSON_OUTPUT.exists(), "tracked R0 inventory is missing")
        require(read_json(DEFAULT_JSON_OUTPUT) == current, "tracked R0 inventory is stale")
        require(DEFAULT_REPORT_OUTPUT.exists(), "tracked R0/R1 report is missing")
        require(
            DEFAULT_REPORT_OUTPUT.read_text(encoding="utf-8").rstrip() == render_report(current).rstrip(),
            "tracked R0/R1 report is stale",
        )
    except (AssertionError, ReaderMeaningFrameError, ValueError) as exc:
        print(f"Final narrative native Chinese foundation failed: {exc}")
        return 1

    print("Final narrative native Traditional Chinese R0-R5 foundation passed")
    print(f"- contract: {current['contract']['version']}")
    print(f"- meaning frame: {current['meaningFrameContract']['version']}")
    print(f"- corpus cases inventoried: {current['sourceCorpus']['caseCount']}")
    print(f"- unique sentences inventoried: {current['summary']['uniqueSentenceCount']}")
    print(f"- reader regressions locked: {regression_count}")
    print(f"- canonical fact frames validated: {frame_count}")
    print(f"- current renderer status: {current['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
