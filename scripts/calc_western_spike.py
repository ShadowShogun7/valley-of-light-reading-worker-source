#!/usr/bin/env python3
"""
Run the Western-only calculation spike for the astrology branch.

This intentionally avoids the legacy mixed BaZi pipeline:
ReadingInput -> Western natal/synastry/transits -> Western candidate signals
-> minimal Western slot selection.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from datetime import date, time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calculation.western import immanuel_adapter
from calculation.western.signals import (
    build_candidate_signals as build_western_signals,
    build_timing_window_scan,
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Reading input must be a JSON object: {path}")
    return payload


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def analysis_date_from_reading(reading: dict[str, Any]) -> date:
    context = reading.get("context") or {}
    raw_datetime = context.get("analysis_datetime") or reading.get("analysis_datetime")
    if raw_datetime:
        return date.fromisoformat(str(raw_datetime).replace("Z", "+00:00").split("T", 1)[0].split(" ", 1)[0])
    raw = context.get("analysis_date") or reading.get("analysis_date")
    if raw:
        return date.fromisoformat(str(raw))
    return date.today()


def analysis_time_from_reading(reading: dict[str, Any]) -> time | None:
    context = reading.get("context") or {}
    raw_datetime = context.get("analysis_datetime") or reading.get("analysis_datetime")
    if raw_datetime:
        normalized = str(raw_datetime).replace("Z", "+00:00")
        time_part = normalized.split("T", 1)[1] if "T" in normalized else normalized.split(" ", 1)[1]
        time_part = time_part.split("+", 1)[0].split("-", 1)[0]
        return time.fromisoformat(time_part if len(time_part.split(":")) > 1 else f"{time_part}:00")
    raw_time = context.get("analysis_time") or reading.get("analysis_time")
    if raw_time:
        value = str(raw_time)
        return time.fromisoformat(value if len(value.split(":")) > 1 else f"{value}:00")
    return None


def analysis_timezone_from_reading(reading: dict[str, Any]) -> str | None:
    context = reading.get("context") or {}
    raw = context.get("analysis_timezone") or reading.get("analysis_timezone")
    return str(raw) if raw else None


def calculate_western(reading: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    source_people = {
        "person_a": reading.get("person_a") or {},
        "person_b": reading.get("person_b") or {},
    }

    natal_a, warnings_a, subject_a, raw_natal_a = immanuel_adapter.calculate_person(source_people["person_a"])
    natal_b, warnings_b, _subject_b, raw_natal_b = immanuel_adapter.calculate_person(source_people["person_b"])
    warnings.extend(f"person_a: {warning}" for warning in warnings_a)
    warnings.extend(f"person_b: {warning}" for warning in warnings_b)

    synastry, synastry_warnings = immanuel_adapter.calculate_synastry(
        subject_a,
        raw_natal_a,
        raw_natal_b,
        natal_a.get("birth_precision", "date_only"),
        natal_b.get("birth_precision", "date_only"),
    )
    warnings.extend(synastry_warnings)

    target_date = analysis_date_from_reading(reading)
    target_time = analysis_time_from_reading(reading)
    target_timezone = analysis_timezone_from_reading(reading)
    transits_a, transit_warnings_a = immanuel_adapter.calculate_transits_for_person(
        source_people["person_a"],
        raw_natal_a,
        natal_a.get("birth_precision", "date_only"),
        target_date,
        target_time,
        target_timezone,
    )
    transits_b, transit_warnings_b = immanuel_adapter.calculate_transits_for_person(
        source_people["person_b"],
        raw_natal_b,
        natal_b.get("birth_precision", "date_only"),
        target_date,
        target_time,
        target_timezone,
    )
    warnings.extend(f"person_a transit: {warning}" for warning in transit_warnings_a)
    warnings.extend(f"person_b transit: {warning}" for warning in transit_warnings_b)

    transits = {
        "engine": "immanuel",
        "target_date": target_date.isoformat(),
        "target_time": (target_time or time(12, 0)).strftime("%H:%M"),
        "timezone": target_timezone or "birth_timezone",
        "datetime_precision": "exact_time" if target_time else "date_noon_fallback",
        "person_a": transits_a,
        "person_b": transits_b,
    }
    signals, analysis = build_western_signals(synastry, transits=transits)
    timing_scan_days, timing_scan_step = timing_scan_settings(reading)
    if timing_scan_days:
        samples, timing_window_warnings = immanuel_adapter.calculate_transit_window_samples(
            source_people,
            raw_natal_a,
            raw_natal_b,
            natal_a.get("birth_precision", "date_only"),
            natal_b.get("birth_precision", "date_only"),
            target_date,
            scan_days=timing_scan_days,
            step_days=timing_scan_step,
        )
        warnings.extend(timing_window_warnings)
        analysis["timing_window_scan"] = build_timing_window_scan(samples, timing_scan_days, timing_scan_step)
    else:
        analysis["timing_window_scan"] = {
            "method": "western-transit-window-scan-v1",
            "status": "not_calculated",
            "scan_days": 0,
            "granularity_days": timing_scan_step,
            "sample_count": 0,
            "top_band": "neutral",
            "better_count": 0,
            "neutral_count": 0,
            "avoid_count": 0,
            "category_counts": {},
            "better_window_count": 0,
            "avoid_window_count": 0,
            "timing_summary": "本次未執行未來三個月 timing scan。",
        }
    western = {
        "people": {
            "person_a": natal_a,
            "person_b": natal_b,
        },
        "synastry": synastry,
        "transits": transits,
        "analysis": analysis,
    }
    return western, signals, analysis, warnings


def timing_scan_settings(reading: dict[str, Any]) -> tuple[int, int]:
    context = reading.get("context") or {}
    raw_days = context.get("timing_scan_days")
    raw_step = context.get("timing_scan_step_days")
    try:
        days = int(raw_days) if raw_days not in (None, "") else 90
    except (TypeError, ValueError):
        days = 90
    try:
        step = int(raw_step) if raw_step not in (None, "") else 2
    except (TypeError, ValueError):
        step = 2
    return max(0, min(days, 90)), max(1, min(step, 7))


def context_from_reading(reading: dict[str, Any]) -> dict[str, Any]:
    context = reading.get("context") or {}
    if not isinstance(context, dict):
        raise SystemExit("reading.context must be an object")
    stage = str(context.get("relationship_stage") or context.get("stage") or "").replace("_", "-")
    question = str(context.get("main_question") or "").replace("_", "-")
    if not stage:
        raise SystemExit("reading.context.relationship_stage is required")
    if not question:
        raise SystemExit("reading.context.main_question is required")
    analysis_datetime = str(context.get("analysis_datetime") or reading.get("analysis_datetime") or "")
    analysis_date = (
        analysis_datetime.replace("Z", "+00:00").split("T", 1)[0].split(" ", 1)[0]
        if analysis_datetime
        else str(context.get("analysis_date") or reading.get("analysis_date") or "")
    )
    return {
        "relationship_stage": stage,
        "main_question": question,
        "contact_status": str(context.get("contact_status") or "").replace("_", "-"),
        "desired_outcome": str(context.get("desired_outcome") or "").replace("_", "-"),
        "emotional_risk": str(context.get("emotional_risk") or "").replace("_", "-"),
        "analysis_date": analysis_date,
        "analysis_datetime": analysis_datetime,
        "analysis_timezone": str(context.get("analysis_timezone") or reading.get("analysis_timezone") or ""),
    }


def strongest_western_signal(western_signals: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not western_signals:
        return None
    return max(western_signals, key=lambda signal: float(signal.get("strength", 0)))


def slot_assignment(slot: str, article_id: str, reason: str, strength: float = 1.0) -> dict[str, Any]:
    return {
        "slot": slot,
        "article_id": article_id,
        "cluster": "western_astrology",
        "rank_reason": [reason],
        "components": {
            "signal_strength": strength,
        },
    }


def selection_for_western_signals(context: dict[str, Any], western_signals: list[dict[str, Any]]) -> dict[str, Any]:
    assignments = [
        slot_assignment("stage", f"context-stage-{context['relationship_stage']}", "relationship_stage_context"),
        slot_assignment("question", f"context-question-{context['main_question']}", "main_question_context"),
    ]
    strongest = strongest_western_signal(western_signals)
    if strongest:
        assignments.append(
            slot_assignment(
                "western_core",
                str(strongest.get("id")),
                str(strongest.get("reason") or "strongest_western_signal"),
                float(strongest.get("strength", 0)),
            )
        )

    return {
        "input": {
            "stage": context.get("relationship_stage"),
            "main_question": context.get("main_question"),
            "product_surface": "free",
            "mode": "western-only",
        },
        "selected_primary_ids": [assignment["article_id"] for assignment in assignments if assignment.get("article_id")],
        "slot_assignments": assignments,
        "dropped_candidates": [],
        "missing_slots": [] if strongest else ["western_core"],
        "budget": {
            "max_primary": 4,
            "max_expanded_recommended": 3,
            "max_claims_warn": 20,
        },
    }


def build_payload(reading: dict[str, Any], include_drafts: bool = False, select: bool = True) -> dict[str, Any]:
    del include_drafts
    western, western_signals, western_analysis, western_warnings = calculate_western(reading)
    context = context_from_reading(reading)
    payload: dict[str, Any] = {
        "reading_id": reading.get("reading_id"),
        "person_a": reading.get("person_a"),
        "person_b": reading.get("person_b"),
        "context": reading.get("context"),
        "runtime_context": context,
        "western": western,
        "candidate_signals": {
            "western_signals": western_signals,
            "cross_signals": [],
        },
        "debug": {
            "engine_versions": {
                "immanuel": package_version("immanuel"),
                "pyswisseph": package_version("pyswisseph"),
            },
            "calculation_warnings": western_warnings,
            "western_analysis": western_analysis,
        },
    }
    if select:
        payload["selection"] = selection_for_western_signals(context, western_signals)
    return payload


def print_summary(payload: dict[str, Any]) -> None:
    print("Western calculation spike")
    print(f"- reading_id: {payload.get('reading_id')}")
    print(f"- stage: {payload['runtime_context']['relationship_stage']}")
    print(f"- question: {payload['runtime_context']['main_question']}")

    warnings = payload["debug"].get("calculation_warnings") or []
    print(f"- warnings: {len(warnings)}")
    for warning in warnings[:5]:
        print(f"  - {warning}")

    western_signals = payload["candidate_signals"]["western_signals"]
    print("\nWestern candidate signals:")
    for signal in western_signals:
        print(f"- {signal['id']} ({signal['strength']}) {signal.get('reason')}")

    selection = payload.get("selection")
    if selection:
        print("\nSelected slots:")
        for assignment in selection.get("slot_assignments") or []:
            print(f"- {assignment['slot']}: {assignment['article_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Western-only calculation spike for one reading JSON.")
    parser.add_argument("--reading", required=True, type=Path, help="Path to examples/readings/*.json")
    parser.add_argument("--include-drafts", action="store_true", help="Accepted for CLI compatibility; ignored.")
    parser.add_argument("--select", action="store_true", help="Attach minimal Western slot selection.")
    parser.add_argument("--json", action="store_true", help="Print full canonical JSON payload.")
    parser.add_argument("--write", type=Path, help="Optional path to write the canonical JSON payload.")
    args = parser.parse_args()

    reading = read_json(args.reading)
    payload = build_payload(reading, include_drafts=args.include_drafts, select=args.select)

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.write:
        print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
