#!/usr/bin/env python3
"""
Run the V0 calculation spike for one reading input.

This script intentionally emits canonical JSON instead of product copy:
birth input -> BaZi / Western raw calculations -> candidate KB signal ids
-> optional selector output.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calculation.bazi import lunar_verifier, sxtwl_adapter
from calculation.bazi.signals import build_candidate_signals as build_bazi_signals
from calculation.western import immanuel_adapter
from calculation.western.signals import build_candidate_signals as build_western_signals
from select_signals import DEFAULT_ARTICLES_PATH, DEFAULT_PRODUCT_SURFACE, load_articles, select_signals_for_scenario


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


def compare_pillars(person_key: str, sxtwl_chart: dict[str, Any], lunar_chart: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    sxtwl_pillars = sxtwl_chart.get("pillars") or {}
    lunar_pillars = lunar_chart.get("pillars") or {}
    for pillar in ("year", "month", "day", "hour"):
        sxtwl_value = (sxtwl_pillars.get(pillar) or {}).get("ganzhi")
        lunar_value = lunar_pillars.get(pillar)
        if sxtwl_value and lunar_value and sxtwl_value != lunar_value:
            warnings.append(
                f"{person_key} {pillar} pillar mismatch: sxtwl={sxtwl_value}, lunar_python={lunar_value}"
            )
    return warnings


def analysis_date_from_reading(reading: dict[str, Any]) -> date:
    context = reading.get("context") or {}
    raw = context.get("analysis_date") or reading.get("analysis_date")
    if raw:
        return date.fromisoformat(str(raw))
    return date.today()


def calculate_bazi(reading: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    people: dict[str, dict[str, Any]] = {}
    target_date = analysis_date_from_reading(reading)
    source_people = {
        "person_a": reading.get("person_a") or {},
        "person_b": reading.get("person_b") or {},
    }

    for person_key, person in source_people.items():
        sxtwl_chart = sxtwl_adapter.calculate_person(person)
        lunar_chart = lunar_verifier.calculate_person(person)
        warnings.extend(compare_pillars(person_key, sxtwl_chart, lunar_chart))
        people[person_key] = {
            "sxtwl": sxtwl_chart,
            "lunar_python": lunar_chart,
            "luck_timing": lunar_verifier.calculate_luck_timing(person, target_date),
        }

    transits = sxtwl_adapter.calculate_transits(target_date)
    signals, analysis = build_bazi_signals(people, source_people, transits=transits)
    return {"people": people, "analysis": analysis, "transits": transits}, signals, analysis, warnings


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
    transits_a, transit_warnings_a = immanuel_adapter.calculate_transits_for_person(
        source_people["person_a"],
        raw_natal_a,
        natal_a.get("birth_precision", "date_only"),
        target_date,
    )
    transits_b, transit_warnings_b = immanuel_adapter.calculate_transits_for_person(
        source_people["person_b"],
        raw_natal_b,
        natal_b.get("birth_precision", "date_only"),
        target_date,
    )
    warnings.extend(f"person_a transit: {warning}" for warning in transit_warnings_a)
    warnings.extend(f"person_b transit: {warning}" for warning in transit_warnings_b)
    transits = {
        "engine": "immanuel",
        "target_date": target_date.isoformat(),
        "person_a": transits_a,
        "person_b": transits_b,
    }

    signals, analysis = build_western_signals(synastry, transits=transits)
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
    return {
        "relationship_stage": stage,
        "main_question": question,
        "contact_status": str(context.get("contact_status") or "").replace("_", "-"),
        "desired_outcome": str(context.get("desired_outcome") or "").replace("_", "-"),
        "emotional_risk": str(context.get("emotional_risk") or "").replace("_", "-"),
        "analysis_date": str(context.get("analysis_date") or reading.get("analysis_date") or ""),
    }


def selection_for_signals(
    context: dict[str, Any],
    bazi_signals: list[dict[str, Any]],
    western_signals: list[dict[str, Any]],
    include_drafts: bool,
) -> dict[str, Any]:
    scenario = {
        "stage": context["relationship_stage"],
        "main_question": context["main_question"],
        "contact_status": context.get("contact_status"),
        "desired_outcome": context.get("desired_outcome"),
        "emotional_risk": context.get("emotional_risk"),
        "bazi_signals": bazi_signals,
        "western_signals": western_signals,
        "cross_signals": [],
    }
    scenario = {key: value for key, value in scenario.items() if value not in (None, "", [])}
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    return select_signals_for_scenario(
        scenario,
        articles,
        include_drafts=include_drafts,
        product_surface=DEFAULT_PRODUCT_SURFACE,
        max_primary=6,
    )


def build_payload(reading: dict[str, Any], include_drafts: bool, select: bool) -> dict[str, Any]:
    calculation_warnings: list[str] = []
    bazi, bazi_signals, bazi_analysis, bazi_warnings = calculate_bazi(reading)
    western, western_signals, western_analysis, western_warnings = calculate_western(reading)
    calculation_warnings.extend(bazi_warnings)
    calculation_warnings.extend(western_warnings)

    context = context_from_reading(reading)
    candidate_signals = {
        "bazi_signals": bazi_signals,
        "western_signals": western_signals,
        "cross_signals": [],
    }
    payload: dict[str, Any] = {
        "reading_id": reading.get("reading_id"),
        "person_a": reading.get("person_a"),
        "person_b": reading.get("person_b"),
        "context": reading.get("context"),
        "runtime_context": context,
        "bazi": bazi,
        "western": western,
        "candidate_signals": candidate_signals,
        "debug": {
            "engine_versions": {
                "sxtwl": package_version("sxtwl"),
                "lunar_python": package_version("lunar_python"),
                "immanuel": package_version("immanuel"),
                "pyswisseph": package_version("pyswisseph"),
            },
            "calculation_warnings": calculation_warnings,
            "bazi_analysis": bazi_analysis,
            "western_analysis": western_analysis,
        },
    }
    if select:
        payload["selection"] = selection_for_signals(context, bazi_signals, western_signals, include_drafts)
    return payload


def print_summary(payload: dict[str, Any]) -> None:
    print("Calculation spike")
    print(f"- reading_id: {payload.get('reading_id')}")
    print(f"- stage: {payload['runtime_context']['relationship_stage']}")
    print(f"- question: {payload['runtime_context']['main_question']}")

    warnings = payload["debug"].get("calculation_warnings") or []
    print(f"- warnings: {len(warnings)}")
    for warning in warnings[:5]:
        print(f"  - {warning}")

    bazi_signals = payload["candidate_signals"]["bazi_signals"]
    western_signals = payload["candidate_signals"]["western_signals"]
    print("\nBaZi candidate signals:")
    for signal in bazi_signals:
        print(f"- {signal['id']} ({signal['strength']}) {signal.get('reason')}")
    print("\nWestern candidate signals:")
    for signal in western_signals:
        print(f"- {signal['id']} ({signal['strength']}) {signal.get('reason')}")

    selection = payload.get("selection")
    if selection:
        print("\nSelected slots:")
        for assignment in selection.get("slot_assignments") or []:
            print(f"- {assignment['slot']}: {assignment['article_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run calculation spike for one reading JSON.")
    parser.add_argument("--reading", required=True, type=Path, help="Path to examples/readings/*.json")
    parser.add_argument("--include-drafts", action="store_true", help="Allow draft articles during selector test.")
    parser.add_argument("--select", action="store_true", help="Run existing KB signal selector against calculated signals.")
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
    else:
        print_summary(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
