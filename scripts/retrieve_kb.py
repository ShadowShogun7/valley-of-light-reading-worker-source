#!/usr/bin/env python3
"""
Build a deterministic Valley of Light KB retrieval bundle from Supabase.

This is a test harness for the future backend retriever. It deliberately avoids
embeddings for now:
- primary article ids come from calculation/context rules
- expansion is one hop through selected typed links
- claims are attached from kb_claims for prompt construction
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from select_signals import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_MAX_PRIMARY,
    DEFAULT_PRODUCT_SURFACE,
    load_articles,
    select_signals_for_scenario,
)
from sync_supabase import DEFAULT_SHARED_ENV, SupabaseClient, first_env, load_env_file


DEFAULT_EXPANSION_TYPES = [
    "requires",
    "timing",
    "cross_checks",
    "cautions",
    "supports",
]
DEFAULT_VARIANTS = ["core", "in_relationship", "in_breakup"]
DEFAULT_PRODUCT_USE = "free"
DEFAULT_MAX_EXPANDED = 4
STAGE_DEFAULT_VARIANTS = {
    "broke-up-recent": ["core", "in_breakup"],
    "cold-war": ["core", "in_breakup"],
    "broke-up-long": ["core", "in_breakup"],
    "crisis": ["core", "in_relationship"],
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Scenario must be a JSON object: {path}")
    return payload


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def normalize_stage_slug(stage: str) -> str:
    stage = stage.strip()
    if stage.startswith("context-stage-"):
        return stage.removeprefix("context-stage-")
    return stage


def default_variants_for_scenario(scenario: dict[str, Any]) -> list[str]:
    scenario_variants = stable_unique(as_list(scenario.get("variants")))
    if scenario_variants:
        return stable_unique(["core", *scenario_variants])

    stage = normalize_stage_slug(str(scenario.get("stage", "")))
    return STAGE_DEFAULT_VARIANTS.get(stage, DEFAULT_VARIANTS)


def query_string(params: dict[str, str]) -> str:
    return urllib.parse.urlencode(params, safe="(),.*")


def in_filter(values: list[str]) -> str:
    return f"in.({','.join(values)})"


def status_filter(include_drafts: bool) -> str:
    if include_drafts:
        return "in.(draft,review,published)"
    return "eq.published"


def scenario_primary_ids(scenario: dict[str, Any], extra_articles: list[str]) -> list[str]:
    ids: list[str] = []

    stage = str(scenario.get("stage", "")).strip()
    if stage:
        ids.append(stage if stage.startswith("context-stage-") else f"context-stage-{stage}")

    question = str(scenario.get("main_question", "")).strip()
    if question:
        ids.append(question if question.startswith("context-question-") else f"context-question-{question}")

    for key in ("article_ids", "bazi_signals", "western_signals", "cross_signals"):
        ids.extend(as_list(scenario.get(key)))
    ids.extend(extra_articles)

    return stable_unique(ids)


def connect_supabase(env_file: str | None) -> SupabaseClient:
    if env_file:
        load_env_file(Path(env_file).expanduser())
    load_env_file(ROOT / ".env")
    load_env_file(DEFAULT_SHARED_ENV)

    supabase_url = first_env("VALLEY_SUPABASE_URL", "SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    service_role_key = first_env("VALLEY_SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    return SupabaseClient(supabase_url, service_role_key)


def fetch_articles(client: SupabaseClient, article_ids: list[str], include_drafts: bool) -> list[dict[str, Any]]:
    if not article_ids:
        return []
    params = query_string(
        {
            "select": "*",
            "id": in_filter(article_ids),
            "status": status_filter(include_drafts),
        }
    )
    rows = client.request("GET", f"kb_articles?{params}") or []
    order = {article_id: index for index, article_id in enumerate(article_ids)}
    return sorted(rows, key=lambda row: order.get(str(row.get("id")), len(order)))


def fetch_links(
    client: SupabaseClient,
    from_ids: list[str],
    expansion_types: list[str],
) -> list[dict[str, Any]]:
    if not from_ids or not expansion_types:
        return []
    params = query_string(
        {
            "select": "*",
            "from_id": in_filter(from_ids),
            "source": "eq.frontmatter_links",
            "resolved": "eq.true",
            "link_type": in_filter(expansion_types),
        }
    )
    rows = client.request("GET", f"kb_links?{params}") or []
    type_rank = {link_type: index for index, link_type in enumerate(expansion_types)}
    return sorted(
        rows,
        key=lambda row: (
            from_ids.index(row["from_id"]) if row.get("from_id") in from_ids else len(from_ids),
            type_rank.get(str(row.get("link_type")), len(type_rank)),
            str(row.get("target")),
        ),
    )


def fetch_claims(client: SupabaseClient, article_ids: list[str], product_use: str | None) -> list[dict[str, Any]]:
    if not article_ids:
        return []
    params = query_string(
        {
            "select": "*",
            "article_id": in_filter(article_ids),
        }
    )
    rows = client.request("GET", f"kb_claims?{params}") or []
    if product_use:
        rows = [row for row in rows if product_use in (row.get("product_use") or [])]
    order = {article_id: index for index, article_id in enumerate(article_ids)}
    return sorted(rows, key=lambda row: (order.get(str(row.get("article_id")), len(order)), str(row.get("claim_id"))))


def compact_article(article: dict[str, Any], variants: list[str]) -> dict[str, Any]:
    article_variants = article.get("variants") or {}
    selected_variants = {
        variant: article_variants[variant]
        for variant in variants
        if isinstance(article_variants, dict) and article_variants.get(variant)
    }
    return {
        "id": article["id"],
        "title": article["title"],
        "category": article["category"],
        "status": article["status"],
        "confidence": article["confidence"],
        "source_primary": article.get("source_primary"),
        "source_chapter": article.get("source_chapter"),
        "variants": selected_variants,
        "claim_ids": article.get("claim_ids") or [],
    }


def compact_claim(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": claim["claim_id"],
        "article_id": claim["article_id"],
        "claim": claim["claim"],
        "confidence": claim["confidence"],
        "product_use": claim.get("product_use") or [],
        "variants_supported": claim.get("variants_supported") or [],
        "source_location": claim.get("source_location"),
    }


def link_reasons_by_target(links: list[dict[str, Any]]) -> dict[str, list[dict[str, str | None]]]:
    grouped: dict[str, list[dict[str, str | None]]] = {}
    for link in links:
        target = link.get("to_id") or link.get("target")
        if not target:
            continue
        grouped.setdefault(str(target), []).append(
            {
                "from_id": link.get("from_id"),
                "type": link.get("link_type"),
                "reason": link.get("reason"),
            }
        )
    return grouped


def build_prompt_context(
    primary: list[dict[str, Any]],
    expanded: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    variants: list[str],
    expansion_links: list[dict[str, Any]],
) -> str:
    claims_by_article: dict[str, list[dict[str, Any]]] = {}
    for claim in claims:
        claims_by_article.setdefault(str(claim["article_id"]), []).append(claim)

    reasons = link_reasons_by_target(expansion_links)
    lines = [
        "Valley of Light KB bundle",
        "Use these claim-backed notes as evidence. Do not invent doctrine beyond this bundle.",
        "",
    ]

    for section_name, articles in (("PRIMARY", primary), ("EXPANDED", expanded)):
        lines.append(f"## {section_name} ARTICLES")
        for article in articles:
            lines.append(f"### {article['id']} | {article['title']} | {article['confidence']}")
            if section_name == "EXPANDED":
                for reason in reasons.get(article["id"], []):
                    lines.append(f"- Expanded via {reason['type']} from {reason['from_id']}: {reason['reason']}")
            for variant in variants:
                content = (article.get("variants") or {}).get(variant)
                if content:
                    lines.append(f"- {variant}: {content}")
            article_claims = claims_by_article.get(article["id"], [])
            if article_claims:
                lines.append("Claims:")
                for claim in article_claims:
                    source_location = claim.get("source_location")
                    source_note = f" Source: {source_location}" if source_location else ""
                    lines.append(f"- {claim['claim_id']} [{claim['confidence']}]: {claim['claim']}{source_note}")
            lines.append("")
    return "\n".join(lines).strip()


def build_bundle(
    client: SupabaseClient,
    scenario: dict[str, Any],
    extra_articles: list[str],
    include_drafts: bool,
    expansion_types: list[str],
    variants: list[str],
    product_use: str | None,
    max_expanded: int,
    selected_primary_ids: list[str] | None = None,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    primary_ids = (
        selected_primary_ids
        if selected_primary_ids is not None
        else scenario_primary_ids(scenario, extra_articles)
    )
    primary_rows = fetch_articles(client, primary_ids, include_drafts=include_drafts)
    found_primary_ids = [row["id"] for row in primary_rows]
    missing_primary_ids = [article_id for article_id in primary_ids if article_id not in found_primary_ids]

    links = fetch_links(client, found_primary_ids, expansion_types=expansion_types)
    expanded_ids = stable_unique(
        [
            str(link.get("to_id") or link.get("target"))
            for link in links
            if (link.get("to_id") or link.get("target")) not in found_primary_ids
        ]
    )[:max_expanded]
    expanded_rows = fetch_articles(client, expanded_ids, include_drafts=include_drafts)
    found_expanded_ids = [row["id"] for row in expanded_rows]

    included_ids = stable_unique([*found_primary_ids, *found_expanded_ids])
    claim_rows = fetch_claims(client, included_ids, product_use=product_use)

    primary = [compact_article(row, variants) for row in primary_rows]
    expanded = [compact_article(row, variants) for row in expanded_rows]
    claims = [compact_claim(row) for row in claim_rows]

    return {
        "input": {
            "scenario": scenario,
            "primary_ids": primary_ids,
            "include_drafts": include_drafts,
            "expansion_types": expansion_types,
            "variants": variants,
            "product_use": product_use,
            "max_expanded": max_expanded,
            "selection": selection,
        },
        "retrieval": {
            "primary_count": len(primary),
            "expanded_count": len(expanded),
            "claim_count": len(claims),
            "missing_primary_ids": missing_primary_ids,
            "candidate_expansion_ids": expanded_ids,
            "missing_expansion_ids": [
                article_id for article_id in expanded_ids if article_id not in found_expanded_ids
            ],
        },
        "primary_articles": primary,
        "expanded_articles": expanded,
        "expansion_links": links,
        "claims": claims,
        "prompt_context": build_prompt_context(primary, expanded, claims, variants, links),
    }


def print_summary(bundle: dict[str, Any]) -> None:
    retrieval = bundle["retrieval"]
    print("KB retrieval bundle")
    print(f"- primary articles: {retrieval['primary_count']}")
    print(f"- expanded articles: {retrieval['expanded_count']}")
    print(f"- claims: {retrieval['claim_count']}")
    selection = bundle.get("input", {}).get("selection")
    if selection:
        assignments = selection.get("slot_assignments") or []
        print(
            "- selected slots: "
            + ", ".join(f"{item['slot']}={item['article_id']}" for item in assignments)
        )
        if selection.get("missing_slots"):
            print(f"- missing slots: {selection['missing_slots']}")
    if retrieval["missing_primary_ids"]:
        print(f"- missing primary ids: {', '.join(retrieval['missing_primary_ids'])}")
    print()

    for label, key in (("Primary", "primary_articles"), ("Expanded", "expanded_articles")):
        print(f"{label}:")
        for article in bundle[key]:
            print(f"- {article['id']} | {article['title']} | {article['confidence']}")
        if not bundle[key]:
            print("- none")
        print()

    print("Prompt context:")
    print(bundle["prompt_context"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve a deterministic KB bundle from Supabase.")
    parser.add_argument("--scenario", help="Path to scenario JSON.")
    parser.add_argument("--stage", help="Context stage slug, e.g. cold-war.")
    parser.add_argument("--question", help="Main question slug, e.g. still-love-me.")
    parser.add_argument("--article", action="append", default=[], help="Additional primary article id. Repeatable.")
    parser.add_argument("--bazi-signal", action="append", default=[], help="Additional BaZi article id. Repeatable.")
    parser.add_argument(
        "--western-signal",
        action="append",
        default=[],
        help="Additional Western article id. Repeatable.",
    )
    parser.add_argument(
        "--cross-signal",
        action="append",
        default=[],
        help="Additional cross-system article id. Repeatable.",
    )
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Allow draft/review articles for private testing.",
    )
    parser.add_argument("--expansion-type", action="append", default=[], help="Typed link expansion type. Repeatable.")
    parser.add_argument("--variant", action="append", default=[], help="Variant to include. Repeatable.")
    parser.add_argument(
        "--product-use",
        default=DEFAULT_PRODUCT_USE,
        help="Claim product_use filter. Use empty string for all.",
    )
    parser.add_argument(
        "--max-expanded",
        type=int,
        default=DEFAULT_MAX_EXPANDED,
        help="Maximum expanded articles to include.",
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
    parser.add_argument("--json", action="store_true", help="Print full JSON bundle instead of readable summary.")
    parser.set_defaults(select_signals=True)
    args = parser.parse_args()

    scenario: dict[str, Any] = {}
    if args.scenario:
        scenario = read_json(Path(args.scenario).expanduser())

    if args.stage:
        scenario["stage"] = args.stage
    if args.question:
        scenario["main_question"] = args.question
    if args.bazi_signal:
        scenario["bazi_signals"] = [*as_list(scenario.get("bazi_signals")), *args.bazi_signal]
    if args.western_signal:
        scenario["western_signals"] = [*as_list(scenario.get("western_signals")), *args.western_signal]
    if args.cross_signal:
        scenario["cross_signals"] = [*as_list(scenario.get("cross_signals")), *args.cross_signal]

    expansion_types = args.expansion_type or DEFAULT_EXPANSION_TYPES
    variants = args.variant or default_variants_for_scenario(scenario)
    product_use = args.product_use.strip() or None
    selection = None
    selected_primary_ids = None
    if args.select_signals:
        articles_path = Path(args.articles_path).expanduser()
        if not articles_path.is_absolute():
            articles_path = ROOT / articles_path
        selection = select_signals_for_scenario(
            scenario=scenario,
            articles_by_id=load_articles(articles_path),
            extra_articles=args.article,
            include_drafts=args.include_drafts,
            product_surface=args.product_surface,
            max_primary=args.max_primary,
        )
        selected_primary_ids = stable_unique([*selection["selected_primary_ids"], *args.article])

    client = connect_supabase(args.env_file)
    bundle = build_bundle(
        client=client,
        scenario=scenario,
        extra_articles=args.article,
        include_drafts=args.include_drafts,
        expansion_types=expansion_types,
        variants=variants,
        product_use=product_use,
        max_expanded=args.max_expanded,
        selected_primary_ids=selected_primary_ids,
        selection=selection,
    )

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_summary(bundle)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
