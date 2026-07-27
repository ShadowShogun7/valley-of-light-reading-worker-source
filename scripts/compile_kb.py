#!/usr/bin/env python3
"""
Compile Valley of Light markdown wiki articles into local JSON artifacts.

This is the build-phase compiler, not the final Supabase sync. It gives us a
machine-readable contract early:
- dist/kb/kb_articles.json
- dist/kb/kb_claims.json
- dist/kb/kb_links.json
- dist/kb/manifest.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kb_utils import (
    ROOT,
    SOURCE_MANIFEST_PATH,
    WIKI_DIR,
    article_files,
    get_sections,
    load_source_manifest,
    parse_claim_citations,
    parse_claims,
    parse_source_location,
    parse_typed_links,
    parse_wiki_links,
    read_text,
    serializable_metadata,
    source_maps,
    split_frontmatter,
)
from structured_kb import compile_structured_kb


DEFAULT_OUT_DIR = ROOT / "dist" / "kb"


def run_validation() -> None:
    from validate import main as validate_main

    exit_code = validate_main()
    if exit_code != 0:
        raise SystemExit(exit_code)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def compile_article(
    path: Path,
    source_aliases: dict[str, str],
    source_paths: dict[str, str],
    title_to_id: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    metadata, body = split_frontmatter(read_text(path))
    metadata = serializable_metadata(metadata)
    article_id = str(metadata["id"])
    sections = get_sections(body)
    claims_by_id = parse_claims(sections, article_id)

    variants: dict[str, str] = {}
    variant_claims: dict[str, list[str]] = {}
    for variant in metadata.get("variants") or []:
        content = sections.get(variant, "")
        variants[variant] = content
        variant_claims[variant] = parse_claim_citations(content)

    source_primary = str(metadata.get("source_primary", "")).strip()
    source_secondary = [str(item).strip() for item in metadata.get("source_secondary") or []]

    article_record = {
        "id": article_id,
        "path": str(path.relative_to(ROOT)),
        "title": metadata.get("title"),
        "title_en": metadata.get("title_en"),
        "category": metadata.get("category"),
        "type": metadata.get("type"),
        "status": metadata.get("status"),
        "confidence": metadata.get("confidence"),
        "source_primary": source_primary,
        "source_primary_id": source_aliases.get(source_primary),
        "source_chapter": metadata.get("source_chapter"),
        "source_secondary": source_secondary,
        "source_secondary_ids": [source_aliases.get(name) for name in source_secondary],
        "applicable_products": metadata.get("applicable_products") or [],
        "relationship_stage": metadata.get("relationship_stage") or [],
        "question_relevance": metadata.get("question_relevance") or [],
        "related": metadata.get("related") or [],
        "links": [
            {
                "target": link.target,
                "type": link.type,
                "reason": link.reason,
            }
            for link in parse_typed_links(metadata)
        ],
        "variants": variants,
        "variant_claims": variant_claims,
        "claim_ids": sorted(claims_by_id),
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "last_reviewed": metadata.get("last_reviewed"),
    }

    claim_records: list[dict[str, Any]] = []
    for claim in claims_by_id.values():
        location = parse_source_location(claim.source_location)
        source_id = source_paths.get(location.raw_path) if location else None
        claim_records.append(
            {
                "claim_id": claim.claim_id,
                "article_id": article_id,
                "article_path": str(path.relative_to(ROOT)),
                "claim": claim.claim,
                "source_quote": claim.source_quote,
                "source_location": claim.source_location,
                "source_raw_path": location.raw_path if location else None,
                "source_id": source_id,
                "source_start_line": location.start_line if location else None,
                "source_end_line": location.end_line if location else None,
                "confidence": claim.confidence,
                "reasoning": claim.reasoning,
                "product_use": claim.product_use,
                "variants_supported": claim.variants_supported,
            }
        )

    links: list[dict[str, Any]] = []
    for link in parse_typed_links(metadata):
        links.append(
            {
                "from_id": article_id,
                "to_id": link.target if link.target in title_to_id.values() else None,
                "target": link.target,
                "type": link.type,
                "reason": link.reason,
                "source": "frontmatter_links",
                "resolved": link.target in title_to_id.values(),
            }
        )

    for target in metadata.get("related") or []:
        target_id = str(target)
        links.append(
            {
                "from_id": article_id,
                "to_id": target_id,
                "target": target_id,
                "type": "related",
                "reason": None,
                "source": "frontmatter_related",
                "resolved": target_id in title_to_id.values(),
            }
        )

    for target in parse_wiki_links(body):
        target_id = title_to_id.get(target)
        links.append(
            {
                "from_id": article_id,
                "to_id": target_id,
                "target": target,
                "type": "wiki",
                "reason": None,
                "source": "body_wiki",
                "resolved": target_id is not None,
            }
        )

    return article_record, claim_records, links


def build_title_map(files: list[Path]) -> dict[str, str]:
    title_to_id: dict[str, str] = {}
    for path in files:
        metadata, _body = split_frontmatter(read_text(path))
        article_id = str(metadata["id"])
        for key in ("id", "title", "title_en"):
            value = metadata.get(key)
            if value:
                title_to_id[str(value)] = article_id
    return title_to_id


def compile_kb(out_dir: Path, published_only: bool = False) -> dict[str, int]:
    files = article_files()
    title_to_id = build_title_map(files)

    manifest = load_source_manifest()
    _sources_by_id, source_aliases, source_paths = source_maps(manifest)

    articles: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    for path in files:
        metadata, _body = split_frontmatter(read_text(path))
        if published_only and metadata.get("status") != "published":
            continue

        article_record, claim_records, link_records = compile_article(
            path=path,
            source_aliases=source_aliases,
            source_paths=source_paths,
            title_to_id=title_to_id,
        )
        articles.append(article_record)
        claims.extend(claim_records)
        links.extend(link_records)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "kb_articles.json", articles)
    write_json(out_dir / "kb_claims.json", claims)
    write_json(out_dir / "kb_links.json", links)
    structured_counts = compile_structured_kb(out_dir=out_dir, articles=articles, claims=claims)

    write_json(
        out_dir / "manifest.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_manifest": str(SOURCE_MANIFEST_PATH.relative_to(ROOT)),
            "article_count": len(articles),
            "claim_count": len(claims),
            "link_count": len(links),
            "atom_count": structured_counts.atom_count,
            "rule_count": structured_counts.rule_count,
            "question_blueprint_count": structured_counts.question_blueprint_count,
            "guardrail_count": structured_counts.guardrail_count,
            "published_only": published_only,
        },
    )

    return {
        "article_count": len(articles),
        "claim_count": len(claims),
        "link_count": len(links),
        "atom_count": structured_counts.atom_count,
        "rule_count": structured_counts.rule_count,
        "question_blueprint_count": structured_counts.question_blueprint_count,
        "guardrail_count": structured_counts.guardrail_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Valley of Light KB markdown to local JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory. Defaults to dist/kb.")
    parser.add_argument("--published-only", action="store_true", help="Compile only articles with status: published.")
    parser.add_argument("--skip-validate", action="store_true", help="Skip validate.py before compiling.")
    args = parser.parse_args()

    if not args.skip_validate:
        run_validation()

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    counts = compile_kb(out_dir=out_dir, published_only=args.published_only)
    print(
        "Compiled KB JSON: "
        f"{counts['article_count']} article(s), "
        f"{counts['claim_count']} claim(s), "
        f"{counts['link_count']} link(s), "
        f"{counts['atom_count']} atom(s), "
        f"{counts['rule_count']} rule(s), "
        f"{counts['question_blueprint_count']} question blueprint(s), "
        f"{counts['guardrail_count']} guardrail(s) -> {display_path(out_dir)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
