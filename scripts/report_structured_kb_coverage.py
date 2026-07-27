#!/usr/bin/env python3
"""
Generate a coverage report for structured KB atoms/rules.

The report answers:
- which atom/rule records are backed by source articles and claim ids
- which Western wiki articles are currently unused by the structured runtime
- which product questions have reducer coverage, fallbacks, and missing layers
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from kb_utils import ROOT, WIKI_DIR


DEFAULT_KB_DIR = ROOT / "dist" / "kb"
DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "06-structured-kb-coverage.md"

EXPECTED_QUESTIONS = [
    "still-love-me",
    "any-chance",
    "when-to-contact",
    "what-did-i-do-wrong",
    "stay-or-let-go",
]

EXPECTED_QUESTION_LAYERS = {
    "still-love-me": ["identityNeeds", "attraction", "emotionalSafety", "pressure"],
    "any-chance": ["attraction", "pressure", "repair", "currentTransits"],
    "when-to-contact": ["pressure", "repair", "currentTransits", "birthDataQuality"],
    "what-did-i-do-wrong": ["identityNeeds", "communication", "emotionalSafety", "pressure"],
    "stay-or-let-go": ["emotionalSafety", "pressure", "repair", "currentTransits"],
}

MIN_ATOM_CLAIMS = 2


def read_json(path: Path) -> Any:
    if not path.exists():
        raise SystemExit(f"Missing compiled artifact: {path.relative_to(ROOT)}. Run scripts/compile_kb.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def as_list(payload: Any, key: str | None = None) -> list[dict[str, Any]]:
    if key and isinstance(payload, dict):
        payload = payload.get(key)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def by_id(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(record.get(key)): record for record in records if record.get(key)}


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(md_escape(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def rel_link(repo_relative_path: str | None, out_path: Path, label: str | None = None) -> str:
    if not repo_relative_path:
        return ""
    target = ROOT / repo_relative_path
    href = os.path.relpath(target, out_path.parent).replace(os.sep, "/")
    return f"[{label or repo_relative_path}]({href})"


def condition_clusters(rule: dict[str, Any]) -> list[str]:
    clusters: list[str] = []
    when = rule.get("when") or {}
    for group_name in ("all", "any"):
        for condition in when.get(group_name) or []:
            if isinstance(condition, dict) and condition.get("cluster"):
                clusters.append(str(condition["cluster"]))
    return unique(clusters)


def output_clusters(rule: dict[str, Any]) -> list[str]:
    output = rule.get("output") or {}
    return unique([str(cluster) for cluster in output.get("because_clusters") or [] if cluster])


def format_rule_conditions(rule: dict[str, Any]) -> str:
    parts: list[str] = []
    when = rule.get("when") or {}
    for group_name in ("all", "any"):
        conditions = []
        for condition in when.get(group_name) or []:
            if not isinstance(condition, dict):
                continue
            cluster = condition.get("cluster") or "context"
            field = condition.get("field") or "field"
            op = condition.get("op") or "op"
            value = condition.get("value")
            if op in {"exists", "missing"}:
                conditions.append(f"{cluster}.{field} {op}")
            else:
                conditions.append(f"{cluster}.{field} {op} {value}")
        if conditions:
            parts.append(f"{group_name}: " + "; ".join(conditions))
    return "<br>".join(parts) if parts else "fallback"


def western_subdir_article_counts() -> dict[str, int]:
    western_dir = WIKI_DIR / "western"
    counts: dict[str, int] = {}
    if not western_dir.exists():
        return counts
    for path in sorted(western_dir.iterdir()):
        if not path.is_dir():
            continue
        count = len([item for item in path.glob("*.md") if item.name != "README.md"])
        counts[path.name] = count
    return counts


def atom_gap_summary(
    atom: dict[str, Any],
    articles_by_id: dict[str, dict[str, Any]],
    claims_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    gaps: list[str] = []
    source_article_id = str(atom.get("source_article_id") or "")
    if source_article_id not in articles_by_id:
        gaps.append("missing source article")
    claim_ids = [str(claim_id) for claim_id in atom.get("claim_ids") or []]
    if not claim_ids:
        gaps.append("no claim ids")
    if len(claim_ids) < MIN_ATOM_CLAIMS:
        gaps.append(f"thin atom claim link (<{MIN_ATOM_CLAIMS})")
    for claim_id in claim_ids:
        claim = claims_by_id.get(claim_id)
        if not claim:
            gaps.append(f"missing claim {claim_id}")
            continue
        if source_article_id and claim.get("article_id") != source_article_id:
            gaps.append(f"claim outside source article: {claim_id}")
        if "free" not in (claim.get("product_use") or []):
            gaps.append(f"claim not marked free: {claim_id}")
    return unique(gaps)


def build_report(kb_dir: Path, out_path: Path) -> str:
    articles = as_list(read_json(kb_dir / "kb_articles.json"))
    claims = as_list(read_json(kb_dir / "kb_claims.json"))
    atoms = as_list(read_json(kb_dir / "kb_atoms.json"), "atoms")
    rules = as_list(read_json(kb_dir / "kb_rules.json"), "rules")
    question_blueprints = as_list(read_json(kb_dir / "kb_question_blueprints.json"), "blueprints")
    guardrails = as_list(read_json(kb_dir / "kb_guardrails.json"), "guardrails")
    manifest = read_json(kb_dir / "manifest.json")

    articles_by_id = by_id(articles, "id")
    claims_by_id = by_id(claims, "claim_id")

    atoms_by_category = {
        str(atom.get("category")): atom
        for atom in atoms
        if atom.get("system") == "western" and atom.get("category")
    }
    atom_source_ids = {str(atom.get("source_article_id")) for atom in atoms if atom.get("source_article_id")}
    guardrail_source_ids = {
        str(guardrail.get("source_article_id"))
        for guardrail in guardrails
        if guardrail.get("source_article_id")
    }
    used_condition_categories = set()
    used_output_categories = set()
    for rule in rules:
        used_condition_categories.update(condition_clusters(rule))
        used_output_categories.update(output_clusters(rule))
    used_rule_categories = used_condition_categories | used_output_categories
    unused_atom_categories = sorted(set(atoms_by_category) - used_rule_categories)

    missing_source_atoms = [
        str(atom.get("id"))
        for atom in atoms
        if str(atom.get("source_article_id") or "") not in articles_by_id
    ]
    missing_claim_atoms = [
        str(atom.get("id"))
        for atom in atoms
        for claim_id in atom.get("claim_ids") or []
        if str(claim_id) not in claims_by_id
    ]
    unknown_rule_categories = sorted(
        category
        for category in used_rule_categories
        if category not in atoms_by_category
    )

    rules_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rule in rules:
        rules_by_question[str(rule.get("question") or "")].append(rule)
    for question in rules_by_question:
        rules_by_question[question].sort(key=lambda rule: int(rule.get("priority") or 0), reverse=True)

    western_articles = [
        article
        for article in articles
        if str(article.get("category") or "").startswith("western")
    ]
    western_claim_count = sum(len(article.get("claim_ids") or []) for article in western_articles)
    western_published = [article for article in western_articles if article.get("status") == "published"]
    western_structured_source_ids = atom_source_ids | guardrail_source_ids
    unatomized_western_articles = [
        article
        for article in western_articles
        if article.get("id") not in atom_source_ids
    ]
    unstructured_western_articles = [
        article
        for article in western_articles
        if article.get("id") not in western_structured_source_ids
    ]

    rule_question_errors = []
    for question in EXPECTED_QUESTIONS:
        question_rules = rules_by_question.get(question) or []
        if not question_rules:
            rule_question_errors.append(f"missing rules for {question}")
        if question_rules and not any(int(rule.get("priority") or 0) == 0 for rule in question_rules):
            rule_question_errors.append(f"missing fallback rule for {question}")

    blueprint_question_ids = {
        str(question.get("question"))
        for blueprint in question_blueprints
        for question in blueprint.get("questions") or []
        if isinstance(question, dict) and question.get("question")
    }
    question_source_article_ids = {
        str(question.get("source_article_id"))
        for blueprint in question_blueprints
        for question in blueprint.get("questions") or []
        if isinstance(question, dict) and question.get("source_article_id")
    }
    missing_blueprint_questions = sorted(set(EXPECTED_QUESTIONS) - blueprint_question_ids)
    unpublished_question_sources = sorted(
        article_id
        for article_id in question_source_article_ids
        if (articles_by_id.get(article_id) or {}).get("status") != "published"
    )
    guardrail_missing_sources = [
        str(guardrail.get("id"))
        for guardrail in guardrails
        if str(guardrail.get("source_article_id") or "") not in articles_by_id
    ]
    guardrail_missing_claims = [
        str(guardrail.get("id"))
        for guardrail in guardrails
        for claim_id in guardrail.get("claim_ids") or []
        if str(claim_id) not in claims_by_id
    ]

    gaps: list[tuple[str, str, str, str]] = []
    for atom_id in missing_source_atoms:
        gaps.append(("P0", "Atom contract", atom_id, "Add the missing source article or correct source_article_id."))
    for atom_id in missing_claim_atoms:
        gaps.append(("P0", "Atom contract", atom_id, "Correct claim_ids or add the missing claim block."))
    for category in unknown_rule_categories:
        gaps.append(("P0", "Rule contract", category, "Add a matching atom category or correct the rule cluster."))
    for item in rule_question_errors:
        gaps.append(("P0", "Question reducer", item, "Add a rule and priority-0 fallback before this question ships."))
    for question in missing_blueprint_questions:
        gaps.append(("P0", "Question blueprint", question, "Add a structured question blueprint before this question ships."))
    for article_id in unpublished_question_sources:
        gaps.append(("P1", "Question blueprint", article_id, "Promote this question source article before published-only sync."))
    for guardrail_id in guardrail_missing_sources:
        gaps.append(("P0", "Guardrail contract", guardrail_id, "Correct source_article_id or add the missing source article."))
    for guardrail_id in guardrail_missing_claims:
        gaps.append(("P0", "Guardrail contract", guardrail_id, "Correct claim_ids or add the missing claim block."))

    if unused_atom_categories:
        if unused_atom_categories == ["identityNeeds"]:
            unused_next_step = "Add identity-needs conditions or output clusters so answers can explain each person's needs before synastry judgment."
        elif {"currentTransits", "birthDataQuality"}.intersection(unused_atom_categories):
            unused_next_step = "Wire timing and precision atoms into answer-layer conditions or outputs before promising contact timing."
        else:
            unused_next_step = "Wire these atoms into answer-layer conditions or outputs, or remove them from the runtime ruleset if they are not product-critical."
        gaps.append(
            (
                "P1",
                "Reducer breadth",
                ", ".join(unused_atom_categories),
                unused_next_step,
            )
        )

    for atom in atoms:
        atom_gaps = atom_gap_summary(atom, articles_by_id, claims_by_id)
        if any("thin atom claim" in gap for gap in atom_gaps):
            gaps.append(
                (
                    "P1",
                    "Atom evidence depth",
                    str(atom.get("id")),
                    f"Link at least {MIN_ATOM_CLAIMS} source-backed claims to this atom if it affects runtime interpretation.",
                )
            )

    aspect_articles = [article for article in unatomized_western_articles if article.get("category") == "western/aspects"]
    if aspect_articles:
        gaps.append(
            (
                "P1",
                "Aspect specificity",
                f"{len(aspect_articles)} aspect articles not atomized",
                "Add aspect-family atoms or selector hooks so broad attraction/pressure clusters can cite the exact aspect article when available.",
            )
        )

    if len(western_published) == 0 and western_articles:
        gaps.append(
            (
                "P2",
                "Production readiness",
                "0 Western articles are published",
                "After source review, promote the minimum Western complete-result article set from draft to published before production sync.",
            )
        )

    subdir_counts = western_subdir_article_counts()
    for area in ("houses", "signs"):
        if subdir_counts.get(area, 0) == 0:
            next_step = (
                "Add this only after reliable time and location support exists; house claims must stay blocked until then."
                if area == "houses"
                else "Defer unless sign-based selectors become product-critical; this is lower priority than houses, timing, and aspect specificity."
            )
            gaps.append(
                (
                    "P2",
                    "Western area coverage",
                    f"wiki/western/{area} has no article",
                    next_step,
                )
            )

    if "currentTransits" not in {
        *[cluster for rule in rules_by_question.get("when-to-contact", []) for cluster in condition_clusters(rule)],
        *[cluster for rule in rules_by_question.get("when-to-contact", []) for cluster in output_clusters(rule)],
    }:
        gaps.append(
            (
                "P1",
                "Timing reducer",
                "when-to-contact rules do not use currentTransits",
                "Expose timing atom fields to rule evaluation before promising contact-window reasoning.",
            )
        )

    lines: list[str] = []
    lines.append("# 06 - Structured KB Coverage Report")
    lines.append("")
    lines.append("Generated from compiled local artifacts in `dist/kb`. Run `python3 scripts/compile_kb.py` before regenerating this report.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(
        md_table(
            ["Metric", "Count"],
            [
                ["Compiled articles", manifest.get("article_count", len(articles))],
                ["Compiled claims", manifest.get("claim_count", len(claims))],
                ["Structured atoms", len(atoms)],
                ["Structured rules", len(rules)],
                ["Question blueprints", len(question_blueprints)],
                ["Guardrails", len(guardrails)],
                ["Western articles", len(western_articles)],
                ["Western claims", western_claim_count],
                ["Western atom source articles", len(atom_source_ids)],
                ["Western articles not used by atoms", len(unatomized_western_articles)],
                ["Western articles not used by structured runtime", len(unstructured_western_articles)],
            ],
        )
    )

    score_rows = [
        ["Atom source articles resolve", "PASS" if not missing_source_atoms else "FAIL", ", ".join(missing_source_atoms) or "-"],
        ["Atom claim ids resolve", "PASS" if not missing_claim_atoms else "FAIL", ", ".join(missing_claim_atoms) or "-"],
        ["Rule clusters map to atoms", "PASS" if not unknown_rule_categories else "FAIL", ", ".join(unknown_rule_categories) or "-"],
        ["All free questions have fallbacks", "PASS" if not rule_question_errors else "FAIL", "; ".join(rule_question_errors) or "-"],
        ["All free questions have blueprints", "PASS" if not missing_blueprint_questions else "FAIL", ", ".join(missing_blueprint_questions) or "-"],
        ["Question blueprint sources published", "PASS" if not unpublished_question_sources else "WARN", ", ".join(unpublished_question_sources) or "-"],
        ["Guardrail source articles resolve", "PASS" if not guardrail_missing_sources else "FAIL", ", ".join(guardrail_missing_sources) or "-"],
        ["Guardrail claim ids resolve", "PASS" if not guardrail_missing_claims else "FAIL", ", ".join(guardrail_missing_claims) or "-"],
        ["Reducer uses all atom categories", "PASS" if not unused_atom_categories else "WARN", ", ".join(unused_atom_categories) or "-"],
        ["Western articles published", "PASS" if western_published else "WARN", f"{len(western_published)} / {len(western_articles)}"],
    ]
    lines.append("")
    lines.append("## Scorecard")
    lines.append("")
    lines.append(md_table(["Check", "Status", "Detail"], score_rows))

    lines.append("")
    lines.append("## Atom Coverage")
    lines.append("")
    atom_rows: list[list[Any]] = []
    for atom in sorted(atoms, key=lambda item: (str(item.get("layer")), str(item.get("category")), str(item.get("id")))):
        article = articles_by_id.get(str(atom.get("source_article_id") or ""), {})
        claim_ids = [str(claim_id) for claim_id in atom.get("claim_ids") or []]
        claim_confidence = Counter(
            str((claims_by_id.get(claim_id) or {}).get("confidence") or "missing")
            for claim_id in claim_ids
        )
        claim_confidence_text = ", ".join(f"{key}:{value}" for key, value in sorted(claim_confidence.items())) or "-"
        atom_gaps = atom_gap_summary(atom, articles_by_id, claims_by_id)
        atom_rows.append(
            [
                atom.get("id"),
                atom.get("category"),
                atom.get("layer"),
                rel_link(str(article.get("path") or ""), out_path, str(atom.get("source_article_id") or "")) if article else str(atom.get("source_article_id") or ""),
                article.get("status") or "missing",
                len(claim_ids),
                claim_confidence_text,
                ", ".join(claim_ids),
                "; ".join(atom_gaps) or "-",
            ]
        )
    lines.append(
        md_table(
            ["Atom", "Category", "Layer", "Source Article", "Article Status", "Claims", "Claim Confidence", "Claim IDs", "Gaps"],
            atom_rows,
        )
    )

    lines.append("")
    lines.append("## Rule Coverage")
    lines.append("")
    rule_rows: list[list[Any]] = []
    for rule in sorted(rules, key=lambda item: (str(item.get("question")), -int(item.get("priority") or 0), str(item.get("id")))):
        categories = unique([*condition_clusters(rule), *output_clusters(rule)])
        source_atoms = [str((atoms_by_category.get(category) or {}).get("id") or f"missing:{category}") for category in categories]
        rule_rows.append(
            [
                rule.get("id"),
                rule.get("question"),
                rule.get("priority"),
                format_rule_conditions(rule),
                ", ".join(output_clusters(rule)) or "-",
                ", ".join(source_atoms) or "-",
                (rule.get("output") or {}).get("confidence") or "-",
            ]
        )
    lines.append(
        md_table(
            ["Rule", "Question", "Priority", "Conditions", "Because Clusters", "Mapped Atoms", "Output Confidence"],
            rule_rows,
        )
    )

    lines.append("")
    lines.append("## Question Matrix")
    lines.append("")
    question_rows: list[list[Any]] = []
    for question in EXPECTED_QUESTIONS:
        question_rules = rules_by_question.get(question) or []
        condition_set = sorted({cluster for rule in question_rules for cluster in condition_clusters(rule)})
        output_set = sorted({cluster for rule in question_rules for cluster in output_clusters(rule)})
        touched = set(condition_set) | set(output_set)
        expected_layers = EXPECTED_QUESTION_LAYERS.get(question, [])
        missing_expected = [layer for layer in expected_layers if layer not in touched]
        question_rows.append(
            [
                question,
                len(question_rules),
                "yes" if any(int(rule.get("priority") or 0) == 0 for rule in question_rules) else "no",
                ", ".join(condition_set) or "-",
                ", ".join(output_set) or "-",
                ", ".join(missing_expected) or "-",
            ]
        )
    lines.append(
        md_table(
            ["Question", "Rules", "Fallback", "Condition Clusters", "Output Clusters", "Missing Expected Layers"],
            question_rows,
        )
    )

    lines.append("")
    lines.append("## Question Blueprint Coverage")
    lines.append("")
    blueprint_rows: list[list[Any]] = []
    for blueprint in question_blueprints:
        questions = [
            str(question.get("question"))
            for question in blueprint.get("questions") or []
            if isinstance(question, dict) and question.get("question")
        ]
        chapters = [
            str(chapter.get("id"))
            for chapter in blueprint.get("chapters") or []
            if isinstance(chapter, dict) and chapter.get("id")
        ]
        blueprint_rows.append(
            [
                blueprint.get("blueprint_id"),
                ", ".join(questions) or "-",
                ", ".join(blueprint.get("chapter_order") or chapters) or "-",
                len(blueprint.get("global_forbidden_claims") or []),
                len(blueprint.get("style_rules") or []),
                rel_link(blueprint.get("path"), out_path, str(blueprint.get("blueprint_id") or "")),
            ]
        )
    lines.append(
        md_table(
            ["Blueprint", "Questions", "Chapter Order", "Forbidden Claims", "Style Rules", "Path"],
            blueprint_rows,
        )
        if blueprint_rows
        else "No structured question blueprints compiled."
    )

    lines.append("")
    lines.append("## Guardrail Coverage")
    lines.append("")
    guardrail_rows: list[list[Any]] = []
    for guardrail in sorted(guardrails, key=lambda item: str(item.get("id"))):
        guardrail_rows.append(
            [
                guardrail.get("id"),
                ", ".join(guardrail.get("applies_to") or []) or "-",
                ", ".join(guardrail.get("points_any") or []) or "-",
                ", ".join(guardrail.get("precision_any") or []) or "-",
                guardrail.get("display"),
                rel_link(
                    (articles_by_id.get(str(guardrail.get("source_article_id") or "")) or {}).get("path"),
                    out_path,
                    str(guardrail.get("source_article_id") or ""),
                ),
                ", ".join(str(claim_id) for claim_id in guardrail.get("claim_ids") or []) or "-",
            ]
        )
    lines.append(
        md_table(
            ["Guardrail", "Applies To", "Points", "Precision", "Display", "Source", "Claims"],
            guardrail_rows,
        )
        if guardrail_rows
        else "No structured guardrails compiled."
    )

    lines.append("")
    lines.append("## Western Article Coverage")
    lines.append("")
    category_counts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for article in western_articles:
        category_counts[str(article.get("category") or "")].append(article)
    category_rows = []
    for category in sorted(category_counts):
        category_articles = category_counts[category]
        atom_used_count = sum(1 for article in category_articles if article.get("id") in atom_source_ids)
        guardrail_used_count = sum(1 for article in category_articles if article.get("id") in guardrail_source_ids)
        structured_used_count = sum(1 for article in category_articles if article.get("id") in western_structured_source_ids)
        claim_count = sum(len(article.get("claim_ids") or []) for article in category_articles)
        category_rows.append([
            category,
            len(category_articles),
            claim_count,
            atom_used_count,
            guardrail_used_count,
            len(category_articles) - structured_used_count,
        ])
    lines.append(
        md_table(
            ["Category", "Articles", "Claims", "Atom Sources", "Guardrail Sources", "Not Structured"],
            category_rows,
        )
    )

    lines.append("")
    lines.append("### Article Detail")
    lines.append("")
    article_rows: list[list[Any]] = []
    for article in sorted(western_articles, key=lambda item: (str(item.get("category")), str(item.get("id")))):
        usage_parts = []
        if article.get("id") in atom_source_ids:
            usage_parts.append("atom source")
        if article.get("id") in guardrail_source_ids:
            usage_parts.append("guardrail source")
        usage = ", ".join(usage_parts) or "not structured"
        atom_refs = [str(atom.get("id")) for atom in atoms if atom.get("source_article_id") == article.get("id")]
        guardrail_refs = [
            str(guardrail.get("id"))
            for guardrail in guardrails
            if guardrail.get("source_article_id") == article.get("id")
        ]
        article_rows.append(
            [
                rel_link(str(article.get("path") or ""), out_path, str(article.get("id") or "")),
                article.get("category"),
                article.get("status"),
                len(article.get("claim_ids") or []),
                usage,
                ", ".join(atom_refs) or "-",
                ", ".join(guardrail_refs) or "-",
                ", ".join(article.get("question_relevance") or []),
            ]
        )
    lines.append(
        md_table(
            ["Article", "Category", "Status", "Claims", "Structured Usage", "Atom Refs", "Guardrail Refs", "Questions"],
            article_rows,
        )
    )

    lines.append("")
    lines.append("## Gap Backlog")
    lines.append("")
    if gaps:
        priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        display_gaps = sorted(gaps, key=lambda gap: (priority_rank.get(gap[0], 9), gap[1], gap[2]))
        lines.append(md_table(["Priority", "Area", "Finding", "Next Step"], display_gaps))
    else:
        lines.append("No coverage gaps detected.")

    lines.append("")
    lines.append("## Recommended Build Order")
    lines.append("")
    recommended_steps = []
    if not western_published:
        recommended_steps.append("Promote the minimum Western complete-result article set from draft to published after source review.")
    if any(article.get("id") == "western-composite-composite-chart" for article in unstructured_western_articles):
        recommended_steps.append(
            "Keep `western-composite-composite-chart` draft until paid-depth composite calculation exists, or define its paid-depth atom/rule contract when that engine is wired."
        )
    recommended_steps.extend(
        [
            "Keep house/Asc/Desc/overlay interpretation blocked until reliable time and location support exists.",
            "Prepare Supabase sync only after the published complete-result article set is stable.",
        ]
    )
    for index, step in enumerate(recommended_steps, start=1):
        lines.append(f"{index}. {step}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate structured KB atom/rule coverage report.")
    parser.add_argument("--kb-dir", default=str(DEFAULT_KB_DIR), help="Compiled KB artifact directory. Defaults to dist/kb.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Markdown report path.")
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir)
    if not kb_dir.is_absolute():
        kb_dir = ROOT / kb_dir
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    report = build_report(kb_dir=kb_dir, out_path=out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote structured KB coverage report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
