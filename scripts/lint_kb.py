#!/usr/bin/env python3
"""
Report Valley of Light KB health signals beyond strict validation.

`validate.py` answers: "is this structurally correct?"
`lint_kb.py` answers: "is this KB healthy enough to scale and ship?"
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kb_utils import (
    ROOT,
    article_files,
    get_sections,
    parse_claims,
    parse_typed_links,
    parse_wiki_links,
    read_text,
    split_frontmatter,
)


MIN_TYPED_LINKS = 2
MAX_TYPED_LINKS = 5
DEFAULT_DIST_MANIFEST = ROOT / "dist" / "kb" / "manifest.json"


@dataclass(frozen=True)
class Issue:
    severity: str
    path: Path | None
    message: str

    def format(self) -> str:
        if self.path is None:
            return f"{self.severity}: {self.message}"
        return f"{self.severity}: {self.path.relative_to(ROOT)}: {self.message}"


@dataclass(frozen=True)
class Article:
    path: Path
    metadata: dict[str, Any]
    body: str
    claims: dict[str, Any]

    @property
    def article_id(self) -> str:
        return str(self.metadata.get("id", "")).strip()


def load_articles() -> tuple[list[Article], list[Issue]]:
    articles: list[Article] = []
    issues: list[Issue] = []

    for path in article_files():
        try:
            metadata, body = split_frontmatter(read_text(path))
            sections = get_sections(body)
            article_id = str(metadata.get("id", "")).strip()
            articles.append(
                Article(
                    path=path,
                    metadata=metadata,
                    body=body,
                    claims=parse_claims(sections, article_id),
                )
            )
        except Exception as exc:
            issues.append(Issue("ERROR", path, f"could not parse article: {exc}"))

    return articles, issues


def count_body_links(articles: list[Article]) -> int:
    return sum(len(parse_wiki_links(article.body)) for article in articles)


def known_wiki_targets(articles: list[Article]) -> set[str]:
    targets: set[str] = set()
    for article in articles:
        for key in ("id", "title", "title_en"):
            value = article.metadata.get(key)
            if value:
                targets.add(str(value))
    return targets


def check_duplicates(articles: list[Article]) -> list[Issue]:
    issues: list[Issue] = []
    id_to_paths: defaultdict[str, list[Path]] = defaultdict(list)
    claim_to_paths: defaultdict[str, list[Path]] = defaultdict(list)

    for article in articles:
        if article.article_id:
            id_to_paths[article.article_id].append(article.path)
        for claim_id in article.claims:
            claim_to_paths[claim_id].append(article.path)

    for article_id, paths in sorted(id_to_paths.items()):
        if len(paths) > 1:
            joined = ", ".join(str(path.relative_to(ROOT)) for path in paths)
            issues.append(Issue("ERROR", None, f"duplicate article id `{article_id}` in {joined}"))

    for claim_id, paths in sorted(claim_to_paths.items()):
        if len(paths) > 1:
            joined = ", ".join(str(path.relative_to(ROOT)) for path in paths)
            issues.append(Issue("ERROR", None, f"duplicate claim id `{claim_id}` in {joined}"))

    return issues


def check_graph(articles: list[Article]) -> tuple[list[Issue], Counter[str], int]:
    issues: list[Issue] = []
    known_ids = {article.article_id for article in articles if article.article_id}
    known_targets = known_wiki_targets(articles)
    inbound: Counter[str] = Counter()
    link_type_counts: Counter[str] = Counter()
    typed_link_count = 0

    for article in articles:
        typed_links = parse_typed_links(article.metadata)
        typed_link_count += len(typed_links)

        if article.metadata.get("status") != "deprecated":
            if len(typed_links) < MIN_TYPED_LINKS:
                issues.append(
                    Issue(
                        "WARN",
                        article.path,
                        f"has {len(typed_links)} typed link(s); target range is {MIN_TYPED_LINKS}-{MAX_TYPED_LINKS}",
                    )
                )
            if len(typed_links) > MAX_TYPED_LINKS:
                issues.append(
                    Issue(
                        "WARN",
                        article.path,
                        f"has {len(typed_links)} typed links; consider pruning to {MAX_TYPED_LINKS} or fewer",
                    )
                )

        for link in typed_links:
            link_type_counts[link.type] += 1
            if link.target not in known_ids:
                issues.append(Issue("ERROR", article.path, f"unresolved typed link target `{link.target}`"))
            else:
                inbound[link.target] += 1

        for target in parse_wiki_links(article.body):
            if target not in known_targets:
                issues.append(Issue("WARN", article.path, f"unresolved body wiki link `[[{target}]]`"))

    for article in articles:
        if article.metadata.get("status") == "deprecated":
            continue
        if inbound[article.article_id] == 0:
            issues.append(Issue("INFO", article.path, "has no typed inbound links yet"))

    return issues, link_type_counts, typed_link_count


def check_status(articles: list[Article]) -> list[Issue]:
    issues: list[Issue] = []
    status_counts = Counter(str(article.metadata.get("status", "missing")) for article in articles)

    if articles and status_counts.get("published", 0) == 0:
        issues.append(Issue("WARN", None, "0 published articles; production sync should stay gated"))

    return issues


def check_dist_manifest(
    articles: list[Article],
    typed_link_count: int,
    dist_manifest: Path,
) -> list[Issue]:
    issues: list[Issue] = []
    if not dist_manifest.exists():
        issues.append(Issue("INFO", dist_manifest, "compiled manifest does not exist yet"))
        return issues

    try:
        manifest = json.loads(dist_manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [Issue("ERROR", dist_manifest, f"compiled manifest is not valid JSON: {exc}")]

    article_count = len(articles)
    claim_count = sum(len(article.claims) for article in articles)
    related_count = sum(len(article.metadata.get("related") or []) for article in articles)
    body_link_count = count_body_links(articles)
    total_link_count = typed_link_count + related_count + body_link_count

    expected = {
        "article_count": article_count,
        "claim_count": claim_count,
        "link_count": total_link_count,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            issues.append(
                Issue(
                    "WARN",
                    dist_manifest,
                    f"compiled `{key}` is {manifest.get(key)}, expected {value}; run `python3 scripts/compile_kb.py`",
                )
            )

    return issues


def print_summary(articles: list[Article], typed_link_count: int, link_type_counts: Counter[str]) -> None:
    article_status = Counter(str(article.metadata.get("status", "missing")) for article in articles)
    article_confidence = Counter(str(article.metadata.get("confidence", "missing")) for article in articles)
    claim_confidence: Counter[str] = Counter()
    category_counts = Counter(str(article.metadata.get("category", "missing")) for article in articles)

    claim_count = 0
    related_count = 0
    for article in articles:
        claim_count += len(article.claims)
        related_count += len(article.metadata.get("related") or [])
        for claim in article.claims.values():
            claim_confidence[claim.confidence] += 1

    print("KB lint summary")
    print(f"- articles: {len(articles)}")
    print(f"- claims: {claim_count}")
    print(f"- links: {typed_link_count} typed, {related_count} related, {count_body_links(articles)} body wiki")
    print(f"- status: {dict(sorted(article_status.items()))}")
    print(f"- article confidence: {dict(sorted(article_confidence.items()))}")
    print(f"- claim confidence: {dict(sorted(claim_confidence.items()))}")
    print(f"- categories: {dict(sorted(category_counts.items()))}")
    print(f"- typed link types: {dict(sorted(link_type_counts.items()))}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Report KB health signals beyond validate.py.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings as well as errors.")
    parser.add_argument(
        "--dist-manifest",
        default=str(DEFAULT_DIST_MANIFEST),
        help="Compiled dist manifest to compare against. Defaults to dist/kb/manifest.json.",
    )
    args = parser.parse_args()

    dist_manifest = Path(args.dist_manifest)
    if not dist_manifest.is_absolute():
        dist_manifest = ROOT / dist_manifest

    articles, issues = load_articles()
    issues.extend(check_duplicates(articles))
    graph_issues, link_type_counts, typed_link_count = check_graph(articles)
    issues.extend(graph_issues)
    issues.extend(check_status(articles))
    issues.extend(check_dist_manifest(articles, typed_link_count, dist_manifest))

    print_summary(articles, typed_link_count, link_type_counts)
    print()

    errors = [issue for issue in issues if issue.severity == "ERROR"]
    warnings = [issue for issue in issues if issue.severity == "WARN"]
    infos = [issue for issue in issues if issue.severity == "INFO"]

    for issue in errors + warnings + infos:
        print(issue.format())

    print()
    print(f"Linted {len(articles)} article(s): {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info(s)")

    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
