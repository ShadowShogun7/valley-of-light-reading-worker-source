#!/usr/bin/env python3
"""
Run retrieval smoke tests for all example scenarios.

This is a build-phase quality loop. It summarizes how many articles/claims each
scenario retrieves and shows which expanded articles repeat across scenarios.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from kb_utils import ROOT
from retrieve_kb import (
    DEFAULT_EXPANSION_TYPES,
    DEFAULT_MAX_EXPANDED,
    DEFAULT_PRODUCT_USE,
    build_bundle,
    connect_supabase,
    default_variants_for_scenario,
    read_json,
)
from select_signals import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_MAX_PRIMARY,
    DEFAULT_PRODUCT_SURFACE,
    load_articles,
    select_signals_for_scenario,
)


DEFAULT_SCENARIO_DIR = ROOT / "examples" / "retrieval"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run retrieval smoke tests for example scenarios.")
    parser.add_argument(
        "--scenario-dir",
        default=str(DEFAULT_SCENARIO_DIR),
        help="Directory containing scenario JSON files.",
    )
    parser.add_argument("--include-drafts", action="store_true", help="Allow draft/review KB rows for private testing.")
    parser.add_argument(
        "--max-expanded",
        type=int,
        default=DEFAULT_MAX_EXPANDED,
        help="Maximum expanded articles per scenario.",
    )
    parser.add_argument(
        "--max-claims-warn",
        type=int,
        default=20,
        help="Warn when a scenario retrieves more claims than this.",
    )
    parser.add_argument(
        "--product-use",
        default=DEFAULT_PRODUCT_USE,
        help="Claim product_use filter. Use empty string for all.",
    )
    parser.add_argument(
        "--select-signals",
        dest="select_signals",
        action="store_true",
        help="Use slot-based primary signal selection.",
    )
    parser.add_argument(
        "--no-select-signals",
        dest="select_signals",
        action="store_false",
        help="Use raw scenario primary ids.",
    )
    parser.add_argument(
        "--articles-path",
        default=str(DEFAULT_ARTICLES_PATH),
        help="Compiled kb_articles.json path for selection.",
    )
    parser.add_argument(
        "--product-surface",
        default=DEFAULT_PRODUCT_SURFACE,
        help="Selection surface, e.g. free or paid.",
    )
    parser.add_argument("--max-primary", type=int, default=DEFAULT_MAX_PRIMARY, help="Maximum selected primary ids.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase vars.")
    parser.set_defaults(select_signals=True)
    args = parser.parse_args()

    scenario_dir = Path(args.scenario_dir)
    if not scenario_dir.is_absolute():
        scenario_dir = ROOT / scenario_dir

    scenario_paths = sorted(scenario_dir.glob("*.json"))
    if not scenario_paths:
        raise SystemExit(f"No scenario JSON files found in {scenario_dir}")

    client = connect_supabase(args.env_file)
    articles_by_id = None
    if args.select_signals:
        articles_path = Path(args.articles_path).expanduser()
        if not articles_path.is_absolute():
            articles_path = ROOT / articles_path
        articles_by_id = load_articles(articles_path)

    product_use = args.product_use.strip() or None
    expanded_counter: Counter[str] = Counter()
    primary_counter: Counter[str] = Counter()
    total_claims = 0
    failures = 0
    claim_warnings = 0

    print("Retrieval smoke suite")
    print(f"- scenarios: {len(scenario_paths)}")
    print(f"- include drafts: {args.include_drafts}")
    print(f"- signal selector: {args.select_signals}")
    print(f"- max expanded: {args.max_expanded}")
    print(f"- claim warning threshold: {args.max_claims_warn}")
    print()

    for path in scenario_paths:
        scenario = read_json(path)
        variants = default_variants_for_scenario(scenario)
        selection = None
        selected_primary_ids = None
        if args.select_signals:
            selection = select_signals_for_scenario(
                scenario=scenario,
                articles_by_id=articles_by_id,
                include_drafts=args.include_drafts,
                product_surface=args.product_surface,
                max_primary=args.max_primary,
            )
            selected_primary_ids = selection["selected_primary_ids"]
        bundle = build_bundle(
            client=client,
            scenario=scenario,
            extra_articles=[],
            include_drafts=args.include_drafts,
            expansion_types=DEFAULT_EXPANSION_TYPES,
            variants=variants,
            product_use=product_use,
            max_expanded=args.max_expanded,
            selected_primary_ids=selected_primary_ids,
            selection=selection,
        )
        retrieval = bundle["retrieval"]
        primary_ids = [article["id"] for article in bundle["primary_articles"]]
        expanded_ids = [article["id"] for article in bundle["expanded_articles"]]
        primary_counter.update(primary_ids)
        expanded_counter.update(expanded_ids)
        total_claims += retrieval["claim_count"]

        if retrieval["missing_primary_ids"]:
            failures += 1
        if retrieval["claim_count"] > args.max_claims_warn:
            claim_warnings += 1

        print(path.name)
        print(
            f"  primary={retrieval['primary_count']} "
            f"expanded={retrieval['expanded_count']} "
            f"claims={retrieval['claim_count']} "
            f"missing={retrieval['missing_primary_ids']}"
        )
        if retrieval["claim_count"] > args.max_claims_warn:
            print(f"  warning=claim_count>{args.max_claims_warn}")
        print(f"  variants={', '.join(variants)}")
        if selection:
            slot_summary = ", ".join(
                f"{item['slot']}={item['article_id']}" for item in selection["slot_assignments"]
            )
            print(f"  selected_slots={slot_summary if slot_summary else 'none'}")
            if selection["missing_slots"]:
                print(f"  missing_slots={selection['missing_slots']}")
        print(f"  primary_ids={', '.join(primary_ids)}")
        print(f"  expanded_ids={', '.join(expanded_ids) if expanded_ids else 'none'}")

    print()
    print("Repeated expanded articles:")
    for article_id, count in expanded_counter.most_common():
        if count > 1:
            print(f"- {article_id}: {count}/{len(scenario_paths)}")

    print()
    print(f"Total claims across scenarios: {total_claims}")
    print(f"Scenarios over claim warning threshold: {claim_warnings}")
    print(f"Scenarios with missing primary ids: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
