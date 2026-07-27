#!/usr/bin/env python3
"""
Select a compact, slot-balanced primary article set for free-result retrieval.

This runs before Supabase retrieval. It uses local compiled metadata so the
retriever can keep prompt input small without relying on embeddings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from kb_utils import ROOT


DEFAULT_ARTICLES_PATH = ROOT / "dist" / "kb" / "kb_articles.json"
DEFAULT_PRODUCT_SURFACE = "free"
DEFAULT_MAX_PRIMARY = 6
RELATIONSHIP_PRODUCT = "relationship_compatibility"

CONFIDENCE_RANK = {
    "DOCTRINE": 3,
    "INTERPRETATION": 2,
    "SPECULATIVE": 1,
}

FREE_RESULT_SLOTS = [
    {"slot": "stage", "required": True, "max": 1},
    {"slot": "question", "required": True, "max": 1},
    {"slot": "bazi_core", "required": True, "max": 1},
    {"slot": "western_core", "required": True, "max": 1},
    {"slot": "timing", "required": False, "max": 1},
    {"slot": "safety", "required": False, "max": 1},
]

FREE_CLUSTER_LIMITS = {
    "attraction": 1,
    "safety_validation": 1,
    "commitment_pressure": 1,
    "conflict_pattern": 1,
    "timing_action": 1,
    "method_guardrail": 1,
}

ARTICLE_CLUSTER_OVERRIDES = {
    "bazi-hehun-day-branch-conflict-combination": "conflict_pattern",
    "bazi-hehun-marriage-palace": "conflict_pattern",
    "bazi-hehun-spouse-star": "commitment_pressure",
    "bazi-hehun-year-only-matching-is-insufficient": "method_guardrail",
    "western-aspects-moon-saturn": "commitment_pressure",
    "western-aspects-moon-venus": "safety_validation",
    "western-aspects-saturn-pressure": "commitment_pressure",
    "western-aspects-sun-moon": "safety_validation",
    "western-aspects-sun-mars": "attraction",
    "western-aspects-sun-saturn": "commitment_pressure",
    "western-aspects-venus-mars": "attraction",
    "western-aspects-venus-saturn": "commitment_pressure",
    "western-aspects-mars-saturn": "commitment_pressure",
    "western-synastry-method": "method_guardrail",
    "western-synastry-relationship-framework": "method_guardrail",
    "western-transits-timing-window": "timing_action",
}

QUESTION_SLOT_HINTS = {
    "when-to-contact": {"timing"},
    "stay-or-let-go": {"safety", "timing"},
    "what-did-i-do-wrong": {"safety"},
    "any-chance": {"timing", "safety"},
    "still-love-me": {"safety"},
}

SAFETY_REQUIRED_STAGES = {"broke-up-recent"}
SAFETY_REQUIRED_QUESTIONS = {"what-did-i-do-wrong"}
SAFETY_ACTIVE_RISKS = {"anxious", "self-blaming", "desperate", "unsafe-or-overwhelmed"}
SAFETY_REQUIRED_RISKS = {"self-blaming", "desperate", "unsafe-or-overwhelmed"}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON payload must be an object: {path}")
    return payload


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def as_signal_entries(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else [value]
    entries: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        if isinstance(item, dict):
            article_id = str(item.get("id") or item.get("article_id") or "").strip()
            if not article_id:
                continue
            strength = item.get("strength", item.get("priority"))
            try:
                calculation_strength = float(strength) if strength is not None else 1.0 - (index * 0.08)
            except (TypeError, ValueError):
                calculation_strength = 1.0 - (index * 0.08)
        else:
            article_id = str(item).strip()
            if not article_id:
                continue
            calculation_strength = 1.0 - (index * 0.08)
        entries.append(
            {
                "id": article_id,
                "index": index,
                "calculation_strength": max(0.2, min(1.0, calculation_strength)),
            }
        )
    return entries


def normalize_stage_slug(stage: str) -> str:
    stage = stage.strip()
    if stage.startswith("context-stage-"):
        return stage.removeprefix("context-stage-")
    return stage


def normalize_question_slug(question: str) -> str:
    question = question.strip()
    if question.startswith("context-question-"):
        return question.removeprefix("context-question-")
    return question


def normalize_slug(value: str) -> str:
    return value.strip().replace("_", "-")


def stage_article_id(stage: str) -> str:
    stage = normalize_stage_slug(stage)
    return f"context-stage-{stage}" if stage else ""


def question_article_id(question: str) -> str:
    question = normalize_question_slug(question)
    return f"context-question-{question}" if question else ""


def relationship_stage_for_context(stage: str) -> str:
    return "in_relationship" if normalize_stage_slug(stage) == "crisis" else "in_breakup"


def load_articles(path: Path = DEFAULT_ARTICLES_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise SystemExit(
            f"Compiled article metadata not found: {path}. "
            "Run `python3 scripts/compile_kb.py` first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit(f"Compiled article metadata must be a JSON array: {path}")
    return {
        str(article.get("id")): article
        for article in payload
        if isinstance(article, dict) and article.get("id")
    }


def article_cluster(article: dict[str, Any]) -> str:
    article_id = str(article.get("id", ""))
    if article_id in ARTICLE_CLUSTER_OVERRIDES:
        return ARTICLE_CLUSTER_OVERRIDES[article_id]

    category = str(article.get("category", ""))
    if category.startswith("context/stages"):
        return "stage_context"
    if category.startswith("context/questions"):
        return "question_context"
    if category.startswith("bazi/hehun"):
        return "bazi_relationship_structure"
    if category.startswith("bazi/"):
        return "bazi_support_pattern"
    if category.startswith("western/transits"):
        return "timing_action"
    if category.startswith("western/synastry"):
        return "method_guardrail"
    if category.startswith("western/aspects"):
        return "western_relationship_signal"
    return category or "uncategorized"


def article_status_allowed(article: dict[str, Any], include_drafts: bool) -> bool:
    status = str(article.get("status", ""))
    if include_drafts:
        return status in {"draft", "review", "published"}
    return status == "published"


def article_answers_question(article: dict[str, Any], question: str) -> float:
    question = normalize_question_slug(question)
    if not question:
        return 0.0
    if str(article.get("id")) == question_article_id(question):
        return 1.0
    relevance = [str(item) for item in article.get("question_relevance") or []]
    if question in relevance or "all" in relevance:
        return 1.0
    return 0.0


def article_matches_stage(article: dict[str, Any], stage: str) -> float:
    stage = normalize_stage_slug(stage)
    if not stage:
        return 0.0
    if str(article.get("id")) == stage_article_id(stage):
        return 1.0

    desired_stage = relationship_stage_for_context(stage)
    stages = [str(item) for item in article.get("relationship_stage") or []]
    if "all" in stages or desired_stage in stages:
        return 1.0
    return 0.0


def product_surface_fit(article: dict[str, Any], product_surface: str) -> float:
    applicable = [str(item) for item in article.get("applicable_products") or []]
    if RELATIONSHIP_PRODUCT not in applicable:
        return 0.0
    if product_surface == "free":
        return 1.0
    return 1.0


def slot_fit(slot: str, article: dict[str, Any], scenario: dict[str, Any]) -> float:
    article_id = str(article.get("id", ""))
    category = str(article.get("category", ""))
    question = normalize_question_slug(str(scenario.get("main_question", "")))
    emotional_risk = normalize_slug(str(scenario.get("emotional_risk", "")))
    cluster = article_cluster(article)

    if slot == "stage":
        if article_id == stage_article_id(str(scenario.get("stage", ""))):
            return 1.0
        return 0.65 if category == "context/stages" else 0.0

    if slot == "question":
        if article_id == question_article_id(question):
            return 1.0
        if category == "context/questions" and article_answers_question(article, question):
            return 0.75
        return 0.0

    if slot == "bazi_core":
        if category == "bazi/hehun" and cluster != "method_guardrail":
            return 1.0
        if category.startswith("bazi/") and cluster != "method_guardrail":
            return 0.85
        if category.startswith("bazi/"):
            return 0.55
        return 0.0

    if slot == "western_core":
        if category == "western/aspects":
            return 1.0
        if category == "western/synastry" and cluster != "method_guardrail":
            return 0.9
        if category.startswith("western/") and cluster != "timing_action":
            return 0.75
        if category == "western/transits":
            return 0.5
        return 0.0

    if slot == "timing":
        if cluster == "timing_action":
            return 1.0
        if article_id == "context-question-when-to-contact":
            return 0.9
        if "when-to-contact" in [str(item) for item in article.get("question_relevance") or []]:
            return 0.5
        return 0.0

    if slot == "safety":
        if cluster in {"safety_validation", "method_guardrail"}:
            return 1.0
        if emotional_risk in SAFETY_ACTIVE_RISKS and cluster in {
            "commitment_pressure",
            "conflict_pattern",
        }:
            return 0.75
        if question in {"what-did-i-do-wrong", "stay-or-let-go"} and cluster in {
            "commitment_pressure",
            "conflict_pattern",
        }:
            return 0.65
        return 0.0

    return 0.0


def is_safety_slot_active(scenario: dict[str, Any]) -> bool:
    stage = normalize_stage_slug(str(scenario.get("stage", "")))
    question = normalize_question_slug(str(scenario.get("main_question", "")))
    emotional_risk = normalize_slug(str(scenario.get("emotional_risk", "")))
    return (
        stage in SAFETY_REQUIRED_STAGES
        or question in SAFETY_REQUIRED_QUESTIONS
        or emotional_risk in SAFETY_ACTIVE_RISKS
        or "safety" in QUESTION_SLOT_HINTS.get(question, set())
    )


def is_slot_active(slot: str, scenario: dict[str, Any]) -> bool:
    if slot == "safety":
        return is_safety_slot_active(scenario)
    if slot == "timing":
        question = normalize_question_slug(str(scenario.get("main_question", "")))
        return "timing" in QUESTION_SLOT_HINTS.get(question, set()) or question == "when-to-contact"
    return True


def slot_is_required(slot: str, scenario: dict[str, Any]) -> bool:
    if slot == "safety":
        stage = normalize_stage_slug(str(scenario.get("stage", "")))
        question = normalize_question_slug(str(scenario.get("main_question", "")))
        emotional_risk = normalize_slug(str(scenario.get("emotional_risk", "")))
        return (
            stage in SAFETY_REQUIRED_STAGES
            or question in SAFETY_REQUIRED_QUESTIONS
            or emotional_risk in SAFETY_REQUIRED_RISKS
        )
    for definition in FREE_RESULT_SLOTS:
        if definition["slot"] == slot:
            return bool(definition["required"])
    return False


def build_candidates(
    scenario: dict[str, Any],
    extra_articles: list[str] | None = None,
) -> list[dict[str, Any]]:
    raw_candidates: list[dict[str, Any]] = []

    stage = stage_article_id(str(scenario.get("stage", "")))
    if stage:
        raw_candidates.append({"id": stage, "origin": "stage", "index": 0, "calculation_strength": 1.0})

    question = question_article_id(str(scenario.get("main_question", "")))
    if question:
        raw_candidates.append({"id": question, "origin": "main_question", "index": 0, "calculation_strength": 1.0})

    for origin in ("article_ids", "bazi_signals", "western_signals", "cross_signals"):
        for entry in as_signal_entries(scenario.get(origin)):
            raw_candidates.append({**entry, "origin": origin})

    for entry in as_signal_entries(extra_articles or []):
        raw_candidates.append({**entry, "origin": "extra_articles"})

    merged: dict[str, dict[str, Any]] = {}
    for candidate in raw_candidates:
        article_id = str(candidate["id"])
        existing = merged.get(article_id)
        if existing is None:
            merged[article_id] = {
                "id": article_id,
                "origins": [candidate["origin"]],
                "first_index": int(candidate.get("index", 0)),
                "calculation_strength": float(candidate.get("calculation_strength", 1.0)),
            }
            continue
        existing["origins"].append(candidate["origin"])
        existing["first_index"] = min(existing["first_index"], int(candidate.get("index", 0)))
        existing["calculation_strength"] = max(
            float(existing["calculation_strength"]),
            float(candidate.get("calculation_strength", 1.0)),
        )

    return list(merged.values())


def candidate_gate_reason(
    candidate: dict[str, Any],
    articles_by_id: dict[str, dict[str, Any]],
    include_drafts: bool,
) -> str | None:
    article = articles_by_id.get(candidate["id"])
    if article is None:
        return "missing_compiled_article"
    if not article_status_allowed(article, include_drafts):
        return "status_not_allowed"
    if RELATIONSHIP_PRODUCT not in [str(item) for item in article.get("applicable_products") or []]:
        return "not_relationship_product"
    if not article.get("claim_ids"):
        return "no_claim_backed_article"
    return None


def selected_cluster_counts(assignments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for assignment in assignments:
        cluster = str(assignment.get("cluster", ""))
        if cluster:
            counts[cluster] = counts.get(cluster, 0) + 1
    return counts


def confidence_rank(article: dict[str, Any]) -> int:
    return CONFIDENCE_RANK.get(str(article.get("confidence", "")), 0)


def bool_rank(value: float | bool) -> int:
    return 1 if bool(value) else 0


def rank_reason(
    slot: str,
    article: dict[str, Any],
    scenario: dict[str, Any],
    components: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    article_id = str(article.get("id", ""))
    question = normalize_question_slug(str(scenario.get("main_question", "")))
    stage = normalize_stage_slug(str(scenario.get("stage", "")))

    if slot == "stage" and article_id == stage_article_id(stage):
        reasons.append("exact_stage_context")
    elif slot == "question" and article_id == question_article_id(question):
        reasons.append("exact_question_context")
    elif components["slot_fit"] >= 1:
        reasons.append(f"strong_{slot}_fit")
    elif components["slot_fit"] > 0:
        reasons.append(f"partial_{slot}_fit")

    if components["answers_question"]:
        reasons.append("answers_current_question")
    if components["matches_stage"]:
        reasons.append("matches_relationship_stage")
    if components["calculation_strength"] >= 0.9:
        reasons.append("high_calculation_priority")
    if components["confidence_rank"] >= 3:
        reasons.append("doctrine_level_confidence")
    elif components["confidence_rank"] == 2:
        reasons.append("interpretation_level_confidence")
    if components["has_claim_backed_article"]:
        reasons.append("claim_backed_article")
    if components["redundant_cluster"]:
        reasons.append("cluster_already_selected")
    if components["safety_conflict"]:
        reasons.append("not_suitable_for_safety_slot")

    return reasons


def rank_candidate(
    slot: str,
    candidate: dict[str, Any],
    article: dict[str, Any],
    scenario: dict[str, Any],
    product_surface: str,
    assignments: list[dict[str, Any]],
) -> dict[str, Any]:
    fit = slot_fit(slot, article, scenario)
    cluster = article_cluster(article)
    cluster_counts = selected_cluster_counts(assignments)
    redundant_cluster = cluster_counts.get(cluster, 0) >= FREE_CLUSTER_LIMITS.get(cluster, 99)
    safety_conflict = slot == "safety" and cluster in {"attraction", "timing_action"}

    components = {
        "slot_fit": fit,
        "answers_question": bool_rank(
            article_answers_question(article, str(scenario.get("main_question", "")))
        ),
        "matches_stage": bool_rank(article_matches_stage(article, str(scenario.get("stage", "")))),
        "calculation_strength": float(candidate.get("calculation_strength", 1.0)),
        "confidence_rank": confidence_rank(article),
        "product_surface_fit": bool_rank(product_surface_fit(article, product_surface)),
        "has_claim_backed_article": bool_rank(bool(article.get("claim_ids"))),
        "non_redundant_cluster": 0 if redundant_cluster else 1,
        "not_safety_conflict": 0 if safety_conflict else 1,
        "redundant_cluster": redundant_cluster,
        "safety_conflict": safety_conflict,
        "first_index": int(candidate.get("first_index", 0)),
    }

    rank_key = (
        round(float(components["slot_fit"]), 3),
        components["answers_question"],
        components["matches_stage"],
        round(float(components["calculation_strength"]), 3),
        components["confidence_rank"],
        components["product_surface_fit"],
        components["has_claim_backed_article"],
        components["non_redundant_cluster"],
        components["not_safety_conflict"],
        -components["first_index"],
    )

    return {
        "article_id": candidate["id"],
        "slot": slot,
        "rank_key": list(rank_key),
        "rank_reason": rank_reason(slot, article, scenario, components),
        "cluster": cluster,
        "components": components,
        "origins": candidate.get("origins", []),
    }


def optional_slot_acceptable(slot: str, ranked: dict[str, Any]) -> bool:
    components = ranked["components"]
    if components["safety_conflict"]:
        return False
    if slot == "timing":
        return float(components["slot_fit"]) >= 0.9
    if slot == "safety":
        return float(components["slot_fit"]) >= 0.65
    return True


def rank_sort_key(ranked: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(-float(value) for value in ranked["rank_key"]) + (str(ranked["article_id"]),)


def select_signals_for_scenario(
    scenario: dict[str, Any],
    articles_by_id: dict[str, dict[str, Any]] | None = None,
    extra_articles: list[str] | None = None,
    include_drafts: bool = False,
    product_surface: str = DEFAULT_PRODUCT_SURFACE,
    max_primary: int = DEFAULT_MAX_PRIMARY,
) -> dict[str, Any]:
    articles_by_id = articles_by_id or load_articles()
    candidates = build_candidates(scenario, extra_articles=extra_articles)
    eligible: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []

    for candidate in candidates:
        reason = candidate_gate_reason(candidate, articles_by_id, include_drafts)
        if reason:
            dropped.append({"article_id": candidate["id"], "reason": reason, "origins": candidate.get("origins", [])})
        else:
            eligible.append(candidate)
    eligible_by_id = {str(candidate["id"]): candidate for candidate in eligible}

    assignments: list[dict[str, Any]] = []
    selected_ids: list[str] = []
    missing_slots: list[dict[str, Any]] = []

    for slot_definition in FREE_RESULT_SLOTS:
        slot = str(slot_definition["slot"])
        if not is_slot_active(slot, scenario):
            continue
        if len(selected_ids) >= max_primary:
            break

        required = slot_is_required(slot, scenario)
        if required:
            already_covering = []
            for assignment in assignments:
                article_id = str(assignment["article_id"])
                article = articles_by_id[article_id]
                if slot_fit(slot, article, scenario) <= 0:
                    continue
                ranked = rank_candidate(
                    slot,
                    eligible_by_id[article_id],
                    article,
                    scenario,
                    product_surface,
                    assignments,
                )
                ranked["covered_by_existing_primary"] = True
                ranked["rank_reason"] = [
                    *ranked["rank_reason"],
                    "covered_by_existing_primary",
                ]
                already_covering.append(ranked)
            if already_covering:
                already_covering.sort(key=rank_sort_key)
                assignments.append(already_covering[0])
                continue

        ranked_candidates: list[dict[str, Any]] = []
        for candidate in eligible:
            if candidate["id"] in selected_ids:
                continue
            article = articles_by_id[candidate["id"]]
            ranked = rank_candidate(slot, candidate, article, scenario, product_surface, assignments)
            if ranked["components"]["slot_fit"] <= 0:
                continue
            if not required and ranked["components"]["redundant_cluster"] and slot in {"timing", "safety"}:
                dropped.append(
                    {
                        "article_id": candidate["id"],
                        "reason": f"redundant_for_optional_{slot}",
                        "slot": slot,
                        "cluster": ranked["cluster"],
                    }
                )
                continue
            ranked_candidates.append(ranked)

        if not ranked_candidates:
            if required:
                missing_slots.append({"slot": slot, "reason": "no_eligible_candidate"})
            continue

        ranked_candidates.sort(key=rank_sort_key)
        winner = ranked_candidates[0]
        if not required and not optional_slot_acceptable(slot, winner):
            missing_slots.append(
                {
                    "slot": slot,
                    "reason": "optional_candidate_below_threshold",
                    "best_rank_key": winner["rank_key"],
                    "best_article_id": winner["article_id"],
                }
            )
            continue

        selected_ids.append(str(winner["article_id"]))
        assignments.append(winner)
        for loser in ranked_candidates[1:]:
            dropped.append(
                {
                    "article_id": loser["article_id"],
                    "reason": f"lost_{slot}_slot",
                    "slot": slot,
                    "rank_key": loser["rank_key"],
                    "rank_reason": loser["rank_reason"],
                    "winner": winner["article_id"],
                    "cluster": loser["cluster"],
                }
            )

    return {
        "input": {
            "stage": scenario.get("stage"),
            "main_question": scenario.get("main_question"),
            "include_drafts": include_drafts,
            "product_surface": product_surface,
            "max_primary": max_primary,
        },
        "selected_primary_ids": stable_unique(selected_ids),
        "slot_assignments": assignments,
        "dropped_candidates": dropped,
        "missing_slots": missing_slots,
        "budget": {
            "max_primary": max_primary,
            "max_expanded_recommended": 3,
            "max_claims_warn": 20,
        },
    }


def print_summary(selection: dict[str, Any]) -> None:
    print("Signal selection")
    print(f"- selected primary ids: {', '.join(selection['selected_primary_ids']) or 'none'}")
    print(f"- missing slots: {selection['missing_slots'] or 'none'}")
    print()
    print("Slot assignments:")
    for assignment in selection["slot_assignments"]:
        print(
            f"- {assignment['slot']}: {assignment['article_id']} "
            f"cluster={assignment['cluster']} reason={', '.join(assignment['rank_reason'])}"
        )
    if not selection["slot_assignments"]:
        print("- none")


def scenario_from_args(args: argparse.Namespace) -> dict[str, Any]:
    scenario: dict[str, Any] = {}
    if args.scenario:
        scenario = read_json(Path(args.scenario).expanduser())
    if args.stage:
        scenario["stage"] = args.stage
    if args.question:
        scenario["main_question"] = args.question
    if args.bazi_signal:
        scenario["bazi_signals"] = [
            *as_signal_entries(scenario.get("bazi_signals")),
            *as_signal_entries(args.bazi_signal),
        ]
    if args.western_signal:
        scenario["western_signals"] = [
            *as_signal_entries(scenario.get("western_signals")),
            *as_signal_entries(args.western_signal),
        ]
    if args.cross_signal:
        scenario["cross_signals"] = [
            *as_signal_entries(scenario.get("cross_signals")),
            *as_signal_entries(args.cross_signal),
        ]
    return scenario


def main() -> int:
    parser = argparse.ArgumentParser(description="Select slot-balanced KB primary signals for a scenario.")
    parser.add_argument("--scenario", help="Path to scenario JSON.")
    parser.add_argument("--stage", help="Context stage slug, e.g. cold-war.")
    parser.add_argument("--question", help="Main question slug, e.g. still-love-me.")
    parser.add_argument("--article", action="append", default=[], help="Additional candidate article id. Repeatable.")
    parser.add_argument(
        "--bazi-signal",
        action="append",
        default=[],
        help="Additional BaZi candidate article id. Repeatable.",
    )
    parser.add_argument(
        "--western-signal",
        action="append",
        default=[],
        help="Additional Western candidate article id. Repeatable.",
    )
    parser.add_argument(
        "--cross-signal",
        action="append",
        default=[],
        help="Additional cross-system candidate article id. Repeatable.",
    )
    parser.add_argument("--articles-path", default=str(DEFAULT_ARTICLES_PATH), help="Compiled kb_articles.json path.")
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Allow draft/review compiled articles for private testing.",
    )
    parser.add_argument(
        "--product-surface",
        default=DEFAULT_PRODUCT_SURFACE,
        help="Selection surface, e.g. free or paid.",
    )
    parser.add_argument("--max-primary", type=int, default=DEFAULT_MAX_PRIMARY, help="Maximum selected primary ids.")
    parser.add_argument("--json", action="store_true", help="Print full JSON selection payload.")
    args = parser.parse_args()

    articles_path = Path(args.articles_path).expanduser()
    if not articles_path.is_absolute():
        articles_path = ROOT / articles_path

    scenario = scenario_from_args(args)
    selection = select_signals_for_scenario(
        scenario=scenario,
        articles_by_id=load_articles(articles_path),
        extra_articles=args.article,
        include_drafts=args.include_drafts,
        product_surface=args.product_surface,
        max_primary=args.max_primary,
    )
    if args.json:
        print(json.dumps(selection, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_summary(selection)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
