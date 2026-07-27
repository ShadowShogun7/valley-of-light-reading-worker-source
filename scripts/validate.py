#!/usr/bin/env python3
"""
Validate Valley of Light wiki articles.

The validator is intentionally local-only and conservative:
- It does not require Supabase.
- It checks that article variants cite real claim ids.
- It checks that claim source locations resolve to immutable raw files.
- It checks that short source quotes can be found at the cited raw line/range.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kb_utils import (
    ROOT,
    SOURCE_MANIFEST_PATH,
    WIKI_DIR,
    article_files,
    claim_blocks,
    expected_category,
    get_sections,
    load_source_manifest,
    normalize_quote_text,
    parse_claim_citations,
    parse_claims,
    parse_source_location,
    parse_wiki_links,
    quote_payloads,
    raw_text_for_location,
    read_text,
    source_maps,
    split_frontmatter,
)


REQUIRED_FRONTMATTER = {
    "id",
    "title",
    "category",
    "type",
    "source_primary",
    "source_chapter",
    "confidence",
    "related",
    "links",
    "applicable_products",
    "relationship_stage",
    "question_relevance",
    "variants",
    "created_at",
    "updated_at",
    "last_reviewed",
    "status",
}

VALID_CONFIDENCE = {"DOCTRINE", "INTERPRETATION", "SPECULATIVE"}
VALID_STATUS = {"draft", "review", "published", "deprecated"}
VALID_TYPES = {"entity", "concept", "bridge", "context"}
VALID_PRODUCT_USE = {"free", "full", "deep", "internal"}
VALID_LINK_TYPES = {
    "requires",
    "supports",
    "contrasts",
    "cross_checks",
    "contextualizes",
    "timing",
    "cautions",
}


@dataclass
class Issue:
    severity: str
    path: Path
    message: str

    def format(self) -> str:
        rel = self.path.relative_to(ROOT)
        return f"{self.severity}: {rel}: {self.message}"


def check_source_manifest() -> tuple[dict[str, str], dict[str, str], list[Issue]]:
    manifest = load_source_manifest()
    _by_id, by_alias, by_path = source_maps(manifest)
    issues: list[Issue] = []

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for source in manifest.get("sources", []):
        if not isinstance(source, dict):
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, "each `sources` entry must be a mapping"))
            continue

        source_id = str(source.get("id", "")).strip()
        raw_path = str(source.get("raw_path", "")).strip()
        title = str(source.get("title", "")).strip()

        if not source_id:
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, "source entry missing `id`"))
        elif source_id in seen_ids:
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, f"duplicate source id `{source_id}`"))
        seen_ids.add(source_id)

        if not title:
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, f"source `{source_id}` missing `title`"))

        if not raw_path.startswith("raw/"):
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, f"source `{source_id}` raw_path must start with `raw/`"))
        elif not (ROOT / raw_path).exists():
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, f"source `{source_id}` raw_path does not exist: `{raw_path}`"))
        elif raw_path in seen_paths:
            issues.append(Issue("ERROR", SOURCE_MANIFEST_PATH, f"duplicate source raw_path `{raw_path}`"))
        seen_paths.add(raw_path)

    return by_alias, by_path, issues


def collect_article_metadata(files: list[Path]) -> dict[str, dict[str, Any]]:
    articles: dict[str, dict[str, Any]] = {}
    for path in files:
        try:
            metadata, _body = split_frontmatter(read_text(path))
        except Exception:
            continue
        article_id = metadata.get("id")
        if article_id:
            articles[str(article_id)] = metadata
    return articles


def collect_known_links(articles: dict[str, dict[str, Any]]) -> set[str]:
    known = set()
    for metadata in articles.values():
        for key in ("id", "title", "title_en"):
            value = metadata.get(key)
            if value:
                known.add(str(value))
    return known


def check_frontmatter(path: Path, metadata: dict[str, Any], source_aliases: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []

    missing = sorted(REQUIRED_FRONTMATTER - set(metadata))
    for key in missing:
        issues.append(Issue("ERROR", path, f"missing frontmatter key `{key}`"))

    article_id = metadata.get("id")
    if article_id and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(article_id)):
        issues.append(Issue("ERROR", path, "`id` must be kebab-case ASCII"))

    category = metadata.get("category")
    expected = expected_category(path)
    if category and category != expected:
        issues.append(Issue("ERROR", path, f"`category` should be `{expected}`, got `{category}`"))

    confidence = metadata.get("confidence")
    if confidence and confidence not in VALID_CONFIDENCE:
        issues.append(Issue("ERROR", path, f"`confidence` must be one of {sorted(VALID_CONFIDENCE)}"))

    status = metadata.get("status")
    if status and status not in VALID_STATUS:
        issues.append(Issue("ERROR", path, f"`status` must be one of {sorted(VALID_STATUS)}"))

    article_type = metadata.get("type")
    if article_type and article_type not in VALID_TYPES:
        issues.append(Issue("ERROR", path, f"`type` must be one of {sorted(VALID_TYPES)}"))

    for list_key in [
        "related",
        "links",
        "applicable_products",
        "relationship_stage",
        "question_relevance",
        "variants",
        "source_secondary",
    ]:
        if list_key in metadata and metadata[list_key] is not None and not isinstance(metadata[list_key], list):
            issues.append(Issue("ERROR", path, f"`{list_key}` must be a YAML list"))

    source_primary = metadata.get("source_primary")
    if source_primary and str(source_primary).strip() not in source_aliases:
        issues.append(Issue("ERROR", path, f"`source_primary` is not in source manifest: `{source_primary}`"))

    for source_name in metadata.get("source_secondary") or []:
        if str(source_name).strip() not in source_aliases:
            issues.append(Issue("WARN", path, f"`source_secondary` is not in source manifest: `{source_name}`"))

    return issues


def check_related(path: Path, metadata: dict[str, Any], known_article_ids: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    related = metadata.get("related") or []
    if not isinstance(related, list):
        return issues

    for target in related:
        if str(target) not in known_article_ids:
            issues.append(Issue("WARN", path, f"`related` target not found yet: `{target}`"))
    return issues


def check_typed_links(path: Path, metadata: dict[str, Any], known_article_ids: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    article_id = str(metadata.get("id", ""))
    related = [str(target) for target in metadata.get("related") or []]
    related_set = set(related)
    raw_links = metadata.get("links") or []

    if not isinstance(raw_links, list):
        return issues

    typed_targets: list[str] = []
    for index, link in enumerate(raw_links, start=1):
        if not isinstance(link, dict):
            issues.append(Issue("ERROR", path, f"`links` item {index} must be a mapping"))
            continue

        target = str(link.get("target", "")).strip()
        link_type = str(link.get("type", "")).strip()
        reason = str(link.get("reason", "")).strip()

        if not target:
            issues.append(Issue("ERROR", path, f"`links` item {index} missing `target`"))
            continue
        typed_targets.append(target)

        if target == article_id:
            issues.append(Issue("ERROR", path, f"`links` item {index} points to itself"))
        if target not in known_article_ids:
            issues.append(Issue("WARN", path, f"`links` target not found yet: `{target}`"))
        if target not in related_set:
            issues.append(Issue("ERROR", path, f"`links` target `{target}` must also appear in `related`"))

        if link_type not in VALID_LINK_TYPES:
            issues.append(Issue("ERROR", path, f"`links` item {index} has invalid type `{link_type}`; expected one of {sorted(VALID_LINK_TYPES)}"))
        if not reason:
            issues.append(Issue("ERROR", path, f"`links` item {index} missing `reason`"))

    duplicate_targets = sorted(target for target in set(typed_targets) if typed_targets.count(target) > 1)
    for target in duplicate_targets:
        issues.append(Issue("ERROR", path, f"`links` contains duplicate target `{target}`"))

    typed_target_set = set(typed_targets)
    for target in sorted(related_set - typed_target_set):
        issues.append(Issue("ERROR", path, f"`related` target `{target}` must have a typed `links` entry"))

    return issues


def check_variants(path: Path, metadata: dict[str, Any], sections: dict[str, str], claim_ids: set[str], claims_by_id: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    variants = metadata.get("variants") or []
    if not isinstance(variants, list):
        return issues

    cited_claims: set[str] = set()
    for variant in variants:
        if not isinstance(variant, str):
            issues.append(Issue("ERROR", path, "`variants` entries must be strings"))
            continue

        if variant not in sections:
            issues.append(Issue("ERROR", path, f"variant section `## {variant}` is missing"))
            continue

        citations = parse_claim_citations(sections[variant])
        if not citations:
            issues.append(Issue("ERROR", path, f"variant `## {variant}` does not cite claim ids with `(claims: ...)`"))
            continue

        for claim_id in citations:
            cited_claims.add(claim_id)
            if claim_id not in claim_ids:
                issues.append(Issue("ERROR", path, f"variant `## {variant}` cites unknown claim `{claim_id}`"))
                continue
            if variant not in claims_by_id[claim_id].variants_supported:
                issues.append(Issue("ERROR", path, f"variant `## {variant}` cites claim `{claim_id}` but claim does not support that variant"))

    for claim_id in sorted(claim_ids - cited_claims):
        issues.append(Issue("ERROR", path, f"claim `{claim_id}` is defined but not cited in article variants"))

    return issues


def check_claim_source(path: Path, claim_id: str, source_quote: str, source_location: str, source_paths: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []
    location = parse_source_location(source_location)
    if not location:
        issues.append(Issue("ERROR", path, f"claim `{claim_id}` has invalid source location format: `{source_location}`"))
        return issues

    if location.raw_path not in source_paths:
        issues.append(Issue("ERROR", path, f"claim `{claim_id}` source raw path is not in source manifest: `{location.raw_path}`"))

    if location.start_line is None:
        issues.append(Issue("WARN", path, f"claim `{claim_id}` source location should include line number before V1"))

    raw_text, raw_error = raw_text_for_location(location)
    if raw_error:
        issues.append(Issue("ERROR", path, f"claim `{claim_id}` {raw_error}"))
        return issues

    payloads = quote_payloads(source_quote)
    if not payloads:
        issues.append(Issue("ERROR", path, f"claim `{claim_id}` source quote has no quoted payload line"))
        return issues

    normalized_raw = normalize_quote_text(raw_text)
    for payload in payloads:
        normalized_payload = normalize_quote_text(payload)
        if normalized_payload and normalized_payload not in normalized_raw:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` quote is not found at cited source location: `{payload}`"))

        if location.raw_path.startswith("raw/western/"):
            words = re.findall(r"[A-Za-z0-9']+", payload)
            if len(words) > 25:
                issues.append(Issue("ERROR", path, f"claim `{claim_id}` Western source quote is too long ({len(words)} words); keep quotes under 25 words"))

    return issues


def check_claims(path: Path, metadata: dict[str, Any], sections: dict[str, str], source_paths: dict[str, str]) -> tuple[list[Issue], dict[str, Any]]:
    issues: list[Issue] = []
    article_id = str(metadata.get("id", ""))
    declared_variants = set(metadata.get("variants") or [])

    claims_section = sections.get("Claims")
    if not claims_section:
        issues.append(Issue("ERROR", path, "missing `## Claims` section"))
        return issues, {}

    raw_blocks = claim_blocks(claims_section)
    if not raw_blocks:
        issues.append(Issue("ERROR", path, "`## Claims` section has no `### claim-id-001` blocks"))
        return issues, {}

    claims_by_id = parse_claims(sections, article_id)
    seen: set[str] = set()
    for claim_id, block in raw_blocks:
        if claim_id in seen:
            issues.append(Issue("ERROR", path, f"duplicate claim id `{claim_id}`"))
        seen.add(claim_id)

        if article_id and not claim_id.startswith(f"{article_id}-"):
            issues.append(Issue("ERROR", path, f"claim id `{claim_id}` must start with article id `{article_id}-`"))

        required_markers = [
            "**Claim:**",
            "**Source quote:**",
            "**Source location:**",
            "**Confidence:**",
            "**Reasoning:**",
            "**Product use:**",
            "**Variants supported:**",
        ]
        for marker in required_markers:
            if marker not in block:
                issues.append(Issue("ERROR", path, f"claim `{claim_id}` missing `{marker}`"))

        claim = claims_by_id.get(claim_id)
        if not claim:
            continue

        if not claim.claim:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` has empty claim text"))

        if not claim.source_quote:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` missing blockquote source quote"))

        if claim.confidence not in VALID_CONFIDENCE:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` has invalid confidence `{claim.confidence}`"))

        if not claim.reasoning:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` has empty reasoning"))

        if not claim.product_use:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` has empty product use list"))
        for product in claim.product_use:
            if product not in VALID_PRODUCT_USE:
                issues.append(Issue("WARN", path, f"claim `{claim_id}` has non-standard product use `{product}`"))

        if not claim.variants_supported:
            issues.append(Issue("ERROR", path, f"claim `{claim_id}` has empty variants supported list"))
        for variant in claim.variants_supported:
            if variant not in declared_variants:
                issues.append(Issue("ERROR", path, f"claim `{claim_id}` supports undeclared variant `{variant}`"))

        if claim.source_location:
            issues.extend(check_claim_source(path, claim_id, claim.source_quote, claim.source_location, source_paths))

    return issues, claims_by_id


def check_sources(path: Path, sections: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []

    if "典籍出處" not in sections:
        issues.append(Issue("ERROR", path, "missing `## 典籍出處` section"))
    elif "> " not in sections["典籍出處"]:
        issues.append(Issue("ERROR", path, "`## 典籍出處` must include at least one blockquote"))

    if "Source Extraction Log" not in sections:
        issues.append(Issue("ERROR", path, "missing `## Source Extraction Log` section"))
    elif "raw/" not in sections["Source Extraction Log"]:
        issues.append(Issue("ERROR", path, "`## Source Extraction Log` must reference raw source paths"))

    return issues


def check_wiki_links(path: Path, body: str, known_links: set[str]) -> list[Issue]:
    issues: list[Issue] = []
    for target in parse_wiki_links(body):
        if target not in known_links:
            issues.append(Issue("WARN", path, f"wiki link target not found yet: `[[{target}]]`"))
    return issues


def validate_article(path: Path, known_links: set[str], known_article_ids: set[str], source_aliases: dict[str, str], source_paths: dict[str, str]) -> list[Issue]:
    issues: list[Issue] = []
    try:
        metadata, body = split_frontmatter(read_text(path))
    except Exception as exc:
        return [Issue("ERROR", path, str(exc))]

    sections = get_sections(body)
    issues.extend(check_frontmatter(path, metadata, source_aliases))
    issues.extend(check_related(path, metadata, known_article_ids))
    issues.extend(check_typed_links(path, metadata, known_article_ids))
    claim_issues, claims_by_id = check_claims(path, metadata, sections, source_paths)
    issues.extend(claim_issues)
    issues.extend(check_variants(path, metadata, sections, set(claims_by_id), claims_by_id))
    issues.extend(check_sources(path, sections))
    issues.extend(check_wiki_links(path, body, known_links))
    return issues


def main() -> int:
    files = article_files()
    if not files:
        print("No wiki articles found. Add articles under wiki/ to validate.")
        return 0

    source_aliases, source_paths, manifest_issues = check_source_manifest()
    articles = collect_article_metadata(files)
    known_links = collect_known_links(articles)
    known_article_ids = set(articles)

    issues: list[Issue] = [*manifest_issues]
    for path in files:
        issues.extend(validate_article(path, known_links, known_article_ids, source_aliases, source_paths))

    errors = [issue for issue in issues if issue.severity == "ERROR"]
    warnings = [issue for issue in issues if issue.severity == "WARN"]

    for issue in errors + warnings:
        print(issue.format())

    print()
    print(f"Validated {len(files)} article(s): {len(errors)} error(s), {len(warnings)} warning(s)")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
