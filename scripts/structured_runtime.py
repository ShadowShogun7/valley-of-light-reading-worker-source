#!/usr/bin/env python3
"""
Structured KB runtime adapter.

This module is the loading boundary for deterministic Western runtime records:
atoms, rules, question blueprints, and guardrails. It can read the compiled
local JSON contract today and the Supabase runtime tables after migrations and
sync are applied.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from kb_utils import ROOT
from sync_supabase import DEFAULT_SHARED_ENV, SupabaseClient, first_env, load_env_file


DEFAULT_KB_DIR = ROOT / "dist" / "kb"
DEFAULT_ATOMS_PATH = DEFAULT_KB_DIR / "kb_atoms.json"
DEFAULT_RULES_PATH = DEFAULT_KB_DIR / "kb_rules.json"
DEFAULT_QUESTION_BLUEPRINTS_PATH = DEFAULT_KB_DIR / "kb_question_blueprints.json"
DEFAULT_GUARDRAILS_PATH = DEFAULT_KB_DIR / "kb_guardrails.json"
DEFAULT_ARTICLES_PATH = DEFAULT_KB_DIR / "kb_articles.json"
DEFAULT_CLAIMS_PATH = DEFAULT_KB_DIR / "kb_claims.json"
SUPABASE_RUNTIME_METADATA_KEYS = {"content_hash", "synced_at"}
StructuredSource = Literal["local", "supabase"]


def resolve_path(path: Path | str) -> Path:
    resolved = Path(path).expanduser()
    return resolved if resolved.is_absolute() else ROOT / resolved


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_records(payload: Any, key: str | None = None) -> list[dict[str, Any]]:
    if key and isinstance(payload, dict):
        payload = payload.get(key)
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def local_structured_records(
    kb_dir: Path | str = DEFAULT_KB_DIR,
    *,
    atoms_path: Path | str | None = None,
    rules_path: Path | str | None = None,
    question_blueprints_path: Path | str | None = None,
    guardrails_path: Path | str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    base_dir = resolve_path(kb_dir)
    atoms_file = resolve_path(atoms_path) if atoms_path else base_dir / "kb_atoms.json"
    rules_file = resolve_path(rules_path) if rules_path else base_dir / "kb_rules.json"
    question_blueprints_file = (
        resolve_path(question_blueprints_path)
        if question_blueprints_path
        else base_dir / "kb_question_blueprints.json"
    )
    guardrails_file = resolve_path(guardrails_path) if guardrails_path else base_dir / "kb_guardrails.json"

    rules_payload = read_json(rules_file)
    guardrails_payload = read_json(guardrails_file)
    return {
        "atoms": as_records(read_json(atoms_file), "atoms"),
        "rulesets": as_records(rules_payload, "rulesets"),
        "rules": as_records(rules_payload, "rules"),
        "question_blueprints": as_records(read_json(question_blueprints_file), "blueprints"),
        "guardrail_sets": as_records(guardrails_payload, "guardrail_sets"),
        "guardrails": as_records(guardrails_payload, "guardrails"),
    }


def local_kb_support_records(
    kb_dir: Path | str = DEFAULT_KB_DIR,
    *,
    articles_path: Path | str | None = None,
    claims_path: Path | str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    base_dir = resolve_path(kb_dir)
    articles_file = resolve_path(articles_path) if articles_path else base_dir / "kb_articles.json"
    claims_file = resolve_path(claims_path) if claims_path else base_dir / "kb_claims.json"
    return {
        "articles": as_records(read_json(articles_file)),
        "claims": as_records(read_json(claims_file)),
    }


def connect_supabase(env_file: str | None = None) -> SupabaseClient:
    if env_file:
        load_env_file(Path(env_file).expanduser())
    load_env_file(ROOT / ".env")
    load_env_file(DEFAULT_SHARED_ENV)

    supabase_url = first_env("VALLEY_SUPABASE_URL", "SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    service_role_key = first_env("VALLEY_SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
    return SupabaseClient(supabase_url, service_role_key)


def supabase_rows(client: SupabaseClient, table: str) -> list[dict[str, Any]]:
    rows = client.request("GET", f"{table}?select=*&limit=10000") or []
    return rows if isinstance(rows, list) else []


def normalize_supabase_record(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in SUPABASE_RUNTIME_METADATA_KEYS}


def normalize_supabase_article(row: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_supabase_record(row)
    normalized.pop("search_text", None)
    normalized["type"] = normalized.pop("article_type", normalized.get("type"))
    normalized["related"] = normalized.pop("related_ids", normalized.get("related", []))
    normalized["created_at"] = normalized.pop("created_on", normalized.get("created_at"))
    normalized["updated_at"] = normalized.pop("updated_on", normalized.get("updated_at"))
    normalized["last_reviewed"] = normalized.pop("last_reviewed_on", normalized.get("last_reviewed"))
    return normalized


def normalize_supabase_claim(row: dict[str, Any]) -> dict[str, Any]:
    return normalize_supabase_record(row)


def normalize_supabase_rule(row: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_supabase_record(row)
    normalized["when"] = normalized.pop("when_clause", normalized.get("when", {}))
    normalized["output"] = normalized.pop("rule_output", normalized.get("output", {}))
    return normalized


def normalize_supabase_structured_records(
    records: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "atoms": [normalize_supabase_record(row) for row in records.get("atoms", [])],
        "rulesets": [normalize_supabase_record(row) for row in records.get("rulesets", [])],
        "rules": [normalize_supabase_rule(row) for row in records.get("rules", [])],
        "question_blueprints": [
            normalize_supabase_record(row) for row in records.get("question_blueprints", [])
        ],
        "guardrail_sets": [normalize_supabase_record(row) for row in records.get("guardrail_sets", [])],
        "guardrails": [normalize_supabase_record(row) for row in records.get("guardrails", [])],
    }


def normalize_supabase_kb_support_records(
    records: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "articles": [normalize_supabase_article(row) for row in records.get("articles", [])],
        "claims": [normalize_supabase_claim(row) for row in records.get("claims", [])],
    }


def supabase_structured_records(env_file: str | None = None) -> dict[str, list[dict[str, Any]]]:
    client = connect_supabase(env_file)
    return normalize_supabase_structured_records({
        "atoms": supabase_rows(client, "kb_atoms"),
        "rulesets": supabase_rows(client, "kb_rulesets"),
        "rules": supabase_rows(client, "kb_rules"),
        "question_blueprints": supabase_rows(client, "kb_question_blueprints"),
        "guardrail_sets": supabase_rows(client, "kb_guardrail_sets"),
        "guardrails": supabase_rows(client, "kb_guardrails"),
    })


def supabase_kb_support_records(env_file: str | None = None) -> dict[str, list[dict[str, Any]]]:
    client = connect_supabase(env_file)
    return normalize_supabase_kb_support_records({
        "articles": supabase_rows(client, "kb_articles"),
        "claims": supabase_rows(client, "kb_claims"),
    })


def load_structured_records(
    source: StructuredSource = "local",
    *,
    kb_dir: Path | str = DEFAULT_KB_DIR,
    env_file: str | None = None,
    atoms_path: Path | str | None = None,
    rules_path: Path | str | None = None,
    question_blueprints_path: Path | str | None = None,
    guardrails_path: Path | str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if source == "supabase":
        return supabase_structured_records(env_file)
    return local_structured_records(
        kb_dir,
        atoms_path=atoms_path,
        rules_path=rules_path,
        question_blueprints_path=question_blueprints_path,
        guardrails_path=guardrails_path,
    )


def load_kb_support_records(
    source: StructuredSource = "local",
    *,
    kb_dir: Path | str = DEFAULT_KB_DIR,
    env_file: str | None = None,
    articles_path: Path | str | None = None,
    claims_path: Path | str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if source == "supabase":
        return supabase_kb_support_records(env_file)
    return local_kb_support_records(kb_dir, articles_path=articles_path, claims_path=claims_path)


def index_kb_support(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    articles: dict[str, dict[str, Any]] = {}
    claims_by_article: dict[str, list[dict[str, Any]]] = {}

    for article in records.get("articles", []):
        article_id = str(article.get("id") or "")
        if article_id:
            articles[article_id] = article

    for claim in records.get("claims", []):
        article_id = str(claim.get("article_id") or "")
        if article_id:
            claims_by_article.setdefault(article_id, []).append(claim)

    return {
        "articles": articles,
        "claimsByArticle": claims_by_article,
        "articleCount": len(articles),
        "claimCount": sum(len(claims) for claims in claims_by_article.values()),
    }


def load_kb_support(
    source: StructuredSource = "local",
    *,
    kb_dir: Path | str = DEFAULT_KB_DIR,
    env_file: str | None = None,
    articles_path: Path | str | None = None,
    claims_path: Path | str | None = None,
) -> dict[str, Any]:
    return index_kb_support(
        load_kb_support_records(
            source,
            kb_dir=kb_dir,
            env_file=env_file,
            articles_path=articles_path,
            claims_path=claims_path,
        )
    )


def index_structured_kb(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    atoms = [atom for atom in records.get("atoms", []) if isinstance(atom, dict)]
    rules = [rule for rule in records.get("rules", []) if isinstance(rule, dict)]
    question_blueprints = [
        blueprint
        for blueprint in records.get("question_blueprints", [])
        if isinstance(blueprint, dict)
    ]
    guardrails = [guardrail for guardrail in records.get("guardrails", []) if isinstance(guardrail, dict)]

    atoms_by_category: dict[str, dict[str, Any]] = {}
    atoms_by_source_article: dict[str, dict[str, Any]] = {}
    for atom in atoms:
        category = str(atom.get("category") or "")
        source_article_id = str(atom.get("source_article_id") or "")
        existing_category_atom = atoms_by_category.get(category)
        existing_is_aspect = str((existing_category_atom or {}).get("source_article_id") or "").startswith(
            "western-aspects-"
        )
        atom_is_aspect = source_article_id.startswith("western-aspects-")
        if atom.get("system") == "western" and category and (
            existing_category_atom is None or (existing_is_aspect and not atom_is_aspect)
        ):
            atoms_by_category[category] = atom
        if atom.get("system") == "western" and source_article_id and source_article_id not in atoms_by_source_article:
            atoms_by_source_article[source_article_id] = atom

    question_blueprints_by_id = {
        str(blueprint.get("blueprint_id")): blueprint
        for blueprint in question_blueprints
        if blueprint.get("blueprint_id")
    }
    guardrails_by_id = {
        str(guardrail.get("id")): guardrail
        for guardrail in guardrails
        if guardrail.get("id")
    }
    question_blueprint_by_question: dict[str, dict[str, Any]] = {}
    for blueprint in question_blueprints:
        for question in blueprint.get("questions") or []:
            if isinstance(question, dict) and question.get("question"):
                question_blueprint_by_question[str(question["question"])] = question

    questions = stable_unique([str(rule.get("question") or "") for rule in rules if rule.get("question")])
    return {
        "atoms": atoms,
        "rules": rules,
        "questionBlueprints": question_blueprints,
        "guardrails": guardrails,
        "atomsByCategory": atoms_by_category,
        "atomsBySourceArticle": atoms_by_source_article,
        "questionBlueprintsById": question_blueprints_by_id,
        "questionBlueprintByQuestion": question_blueprint_by_question,
        "guardrailsById": guardrails_by_id,
        "rulesByQuestion": {
            question: sorted(
                [rule for rule in rules if rule.get("question") == question],
                key=lambda rule: int(rule.get("priority") or 0),
                reverse=True,
            )
            for question in questions
        },
    }


def load_structured_kb(
    source: StructuredSource = "local",
    *,
    kb_dir: Path | str = DEFAULT_KB_DIR,
    env_file: str | None = None,
    atoms_path: Path | str | None = None,
    rules_path: Path | str | None = None,
    question_blueprints_path: Path | str | None = None,
    guardrails_path: Path | str | None = None,
) -> dict[str, Any]:
    return index_structured_kb(
        load_structured_records(
            source,
            kb_dir=kb_dir,
            env_file=env_file,
            atoms_path=atoms_path,
            rules_path=rules_path,
            question_blueprints_path=question_blueprints_path,
            guardrails_path=guardrails_path,
        )
    )
