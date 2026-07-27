#!/usr/bin/env python3
"""
Build the V0 reading context from a user intake JSON.

This is the bridge test harness:
reading intake + mock/calculated signals -> selector scenario -> selected slots
-> optional Supabase retrieval bundle -> free/paid output contract.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from retrieve_kb import (
    DEFAULT_EXPANSION_TYPES,
    DEFAULT_MAX_EXPANDED,
    DEFAULT_PRODUCT_USE,
    build_bundle,
    connect_supabase,
    default_variants_for_scenario,
)
from select_signals import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_MAX_PRIMARY,
    DEFAULT_PRODUCT_SURFACE,
    load_articles,
    select_signals_for_scenario,
)


DEFAULT_READING_DIR = ROOT / "examples" / "readings"
ROLE_LABELS = {
    "person_a": "你",
    "person_b": "對方",
}
PAID_EXPANSION_BY_SLOT = {
    "stage": ["opening", "part_7_healing_close"],
    "question": ["report_title", "section_framing"],
    "bazi_core": ["part_1_bazi_relationship", "part_5_strategy"],
    "western_core": ["part_2_synastry", "part_6_partner_psychology"],
    "timing": ["part_4_timing_windows", "contact_strategy"],
    "safety": ["part_5_do_not_do", "part_7_grounding"],
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Reading input must be a JSON object: {path}")
    return payload


def normalize_slug(value: Any) -> str:
    return str(value or "").strip().replace("_", "-")


def first_present(mapping: dict[str, Any], keys: tuple[str, ...], default: Any = "") -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return default


def person_summary(reading: dict[str, Any], key: str) -> dict[str, Any]:
    person = reading.get(key) or {}
    if not isinstance(person, dict):
        person = {}
    role_label = ROLE_LABELS[key]
    birth_time = person.get("birth_time")
    return {
        "role_label": role_label,
        "birth_date": person.get("birth_date"),
        "birth_time": birth_time,
        "birth_timezone": person.get("birth_timezone") or "Asia/Taipei",
        "birth_place": person.get("birth_place"),
        "gender": person.get("gender"),
        "birth_precision": "date_time" if birth_time else "date_only",
        "label_usage": "role_label_only",
    }


def normalized_context(reading: dict[str, Any]) -> dict[str, Any]:
    context = reading.get("context") or {}
    if not isinstance(context, dict):
        raise SystemExit("reading.context must be an object")

    relationship_stage = normalize_slug(first_present(context, ("relationship_stage", "stage")))
    main_question = normalize_slug(context.get("main_question"))
    if not relationship_stage:
        raise SystemExit("reading.context.relationship_stage is required")
    if not main_question:
        raise SystemExit("reading.context.main_question is required")

    return {
        "relationship_stage": relationship_stage,
        "main_question": main_question,
        "contact_status": normalize_slug(context.get("contact_status")),
        "desired_outcome": normalize_slug(context.get("desired_outcome")),
        "emotional_risk": normalize_slug(context.get("emotional_risk")),
        "who_initiated": normalize_slug(context.get("who_initiated")),
        "relationship_length": normalize_slug(context.get("relationship_length")),
    }


def candidate_signals(reading: dict[str, Any]) -> dict[str, Any]:
    calculation = reading.get("calculation") or {}
    if not isinstance(calculation, dict):
        calculation = {}
    signals = calculation.get("candidate_signals") or reading.get("candidate_signals") or {}
    if not isinstance(signals, dict):
        raise SystemExit("calculation.candidate_signals must be an object when provided")
    return signals


def signal_list(signals: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = signals.get(key)
        if value:
            return value if isinstance(value, list) else [value]
    return []


def build_scenario(reading: dict[str, Any]) -> dict[str, Any]:
    context = normalized_context(reading)
    signals = candidate_signals(reading)
    scenario = {
        "stage": context["relationship_stage"],
        "main_question": context["main_question"],
        "contact_status": context.get("contact_status"),
        "desired_outcome": context.get("desired_outcome"),
        "emotional_risk": context.get("emotional_risk"),
        "article_ids": signal_list(signals, "article_ids", "articles"),
        "bazi_signals": signal_list(signals, "bazi_signals", "bazi"),
        "western_signals": signal_list(signals, "western_signals", "western"),
        "cross_signals": signal_list(signals, "cross_signals", "cross"),
    }
    return {key: value for key, value in scenario.items() if value not in (None, "", [])}


def slot_article_map(selection: dict[str, Any]) -> dict[str, str]:
    slot_map: dict[str, str] = {}
    for assignment in selection.get("slot_assignments") or []:
        slot = str(assignment.get("slot", ""))
        article_id = str(assignment.get("article_id", ""))
        if slot and article_id and slot not in slot_map:
            slot_map[slot] = article_id
    return slot_map


def present_ids(values: list[str | None]) -> list[str]:
    return [value for value in values if value]


def free_answer_contract(selection: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    slot_map = slot_article_map(selection)
    evidence_cards = []
    for slot in ("bazi_core", "western_core"):
        evidence_cards.append(
            {
                "slot": slot,
                "article_id": slot_map.get(slot),
                "purpose": (
                    "Explain the strongest BaZi relationship signal in plain language."
                    if slot == "bazi_core"
                    else "Explain the strongest Western relationship signal in plain language."
                ),
            }
        )

    supplemental = []
    for slot in ("timing", "safety"):
        if slot in slot_map:
            supplemental.append(
                {
                    "slot": slot,
                    "article_id": slot_map[slot],
                    "purpose": "Use only if it makes the next step clearer or safer.",
                }
            )

    return {
        "direct_answer": {
            "source_slots": ["question", "stage"],
            "question": context["main_question"],
            "article_ids": present_ids([slot_map.get("question"), slot_map.get("stage")]),
            "target_length": "2-3 sentences",
        },
        "evidence_cards": evidence_cards,
        "stage_meaning": {
            "source_slots": ["stage"],
            "article_id": slot_map.get("stage"),
        },
        "next_step": {
            "source_slots": ["timing", "safety"],
            "article_ids": present_ids([slot_map.get("timing"), slot_map.get("safety")]),
            "contact_status": context.get("contact_status"),
            "emotional_risk": context.get("emotional_risk"),
        },
        "supplemental_cards": supplemental,
        "paid_preview": {
            "message": (
                "Paid report expands timing, hidden pattern, conflict root, "
                "repairability, and next-step strategy from the same selected signals."
            )
        },
    }


def paid_expansion_contract(selection: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for assignment in selection.get("slot_assignments") or []:
        slot = str(assignment.get("slot", ""))
        rows.append(
            {
                "slot": slot,
                "article_id": assignment.get("article_id"),
                "paid_sections": PAID_EXPANSION_BY_SLOT.get(slot, []),
            }
        )
    return rows


def build_reading_context(
    reading: dict[str, Any],
    include_drafts: bool,
    product_surface: str,
    max_primary: int,
    articles_path: Path,
    selection_only: bool,
    env_file: str | None,
    product_use: str | None,
    max_expanded: int,
) -> dict[str, Any]:
    scenario = build_scenario(reading)
    context = normalized_context(reading)
    articles_by_id = load_articles(articles_path)
    selection = select_signals_for_scenario(
        scenario=scenario,
        articles_by_id=articles_by_id,
        include_drafts=include_drafts,
        product_surface=product_surface,
        max_primary=max_primary,
    )

    bundle = None
    if not selection_only:
        client = connect_supabase(env_file)
        variants = default_variants_for_scenario(scenario)
        bundle = build_bundle(
            client=client,
            scenario=scenario,
            extra_articles=[],
            include_drafts=include_drafts,
            expansion_types=DEFAULT_EXPANSION_TYPES,
            variants=variants,
            product_use=product_use,
            max_expanded=max_expanded,
            selected_primary_ids=selection["selected_primary_ids"],
            selection=selection,
        )

    return {
        "reading_id": reading.get("reading_id"),
        "people": {
            "person_a": person_summary(reading, "person_a"),
            "person_b": person_summary(reading, "person_b"),
        },
        "runtime_context": context,
        "scenario": scenario,
        "selection": selection,
        "free_answer_contract": free_answer_contract(selection, context),
        "paid_expansion_contract": paid_expansion_contract(selection),
        "kb_bundle": bundle,
    }


def print_summary(payload: dict[str, Any]) -> None:
    people = payload["people"]
    context = payload["runtime_context"]
    selection = payload["selection"]
    print("Reading context")
    print(f"- reading_id: {payload.get('reading_id')}")
    print(f"- person_a: {people['person_a']['role_label']} ({people['person_a']['birth_precision']})")
    print(f"- person_b: {people['person_b']['role_label']} ({people['person_b']['birth_precision']})")
    print("- note: names are not collected; role labels are not calculation inputs")
    print(f"- stage: {context['relationship_stage']}")
    print(f"- main question: {context['main_question']}")
    print(f"- emotional risk: {context.get('emotional_risk') or 'unspecified'}")
    print()
    print("Selected slots:")
    for assignment in selection.get("slot_assignments") or []:
        reasons = ", ".join(assignment.get("rank_reason") or [])
        print(f"- {assignment['slot']}: {assignment['article_id']} ({reasons})")
    if selection.get("missing_slots"):
        print(f"- missing slots: {selection['missing_slots']}")

    bundle = payload.get("kb_bundle")
    if bundle:
        retrieval = bundle["retrieval"]
        print()
        print("KB bundle:")
        print(
            f"- primary={retrieval['primary_count']} "
            f"expanded={retrieval['expanded_count']} "
            f"claims={retrieval['claim_count']} "
            f"missing={retrieval['missing_primary_ids']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Valley of Light V0 reading context.")
    parser.add_argument("--reading", required=True, help="Path to reading intake JSON.")
    parser.add_argument("--include-drafts", action="store_true", help="Allow draft/review KB rows for private tests.")
    parser.add_argument("--selection-only", action="store_true", help="Skip Supabase retrieval and output selector contract only.")
    parser.add_argument("--articles-path", default=str(DEFAULT_ARTICLES_PATH), help="Compiled kb_articles.json path.")
    parser.add_argument("--product-surface", default=DEFAULT_PRODUCT_SURFACE, help="Selection surface, e.g. free.")
    parser.add_argument("--max-primary", type=int, default=DEFAULT_MAX_PRIMARY, help="Maximum selected primary ids.")
    parser.add_argument("--product-use", default=DEFAULT_PRODUCT_USE, help="Claim product_use filter. Empty string for all.")
    parser.add_argument("--max-expanded", type=int, default=DEFAULT_MAX_EXPANDED, help="Maximum expanded articles.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase vars.")
    parser.add_argument("--json", action="store_true", help="Print full JSON payload.")
    args = parser.parse_args()

    reading_path = Path(args.reading).expanduser()
    if not reading_path.is_absolute():
        reading_path = ROOT / reading_path
    articles_path = Path(args.articles_path).expanduser()
    if not articles_path.is_absolute():
        articles_path = ROOT / articles_path

    payload = build_reading_context(
        reading=read_json(reading_path),
        include_drafts=args.include_drafts,
        product_surface=args.product_surface,
        max_primary=args.max_primary,
        articles_path=articles_path,
        selection_only=args.selection_only,
        env_file=args.env_file,
        product_use=args.product_use.strip() or None,
        max_expanded=args.max_expanded,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_summary(payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
