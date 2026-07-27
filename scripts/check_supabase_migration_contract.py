#!/usr/bin/env python3
"""
Static contract check for Supabase structured KB migrations.

This is a no-database gate for hosted-Supabase workflows. It does not prove SQL
execution, but it catches drift between the structured runtime sync shape and
the migration files before applying SQL to a hosted target.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from kb_utils import ROOT


STRUCTURED_MIGRATIONS = (
    ROOT / "supabase/migrations/20260525095713_add_structured_kb_runtime.sql",
    ROOT / "supabase/migrations/20260525112318_add_question_blueprint_version.sql",
)

REQUIRED_TABLES = {
    "kb_atoms": {
        "primary_key": "id",
        "columns": (
            "id",
            "system",
            "layer",
            "category",
            "label",
            "source_article_id",
            "claim_ids",
            "applies_to",
            "selectors",
            "interpretation",
            "path",
            "content_hash",
            "synced_at",
        ),
        "foreign_keys": (
            "source_article_id text not null references public.kb_articles(id)",
        ),
        "required_indexes": (
            "kb_atoms_system_idx",
            "kb_atoms_layer_idx",
            "kb_atoms_source_article_id_idx",
            "kb_atoms_claim_ids_idx",
            "kb_atoms_selectors_idx",
        ),
    },
    "kb_rulesets": {
        "primary_key": "ruleset_id",
        "columns": (
            "ruleset_id",
            "version",
            "applies_to",
            "rule_ids",
            "path",
            "content_hash",
            "synced_at",
        ),
        "foreign_keys": (),
        "required_indexes": ("kb_rulesets_applies_to_idx",),
    },
    "kb_rules": {
        "primary_key": "id",
        "columns": (
            "id",
            "ruleset_id",
            "question",
            "priority",
            "when_clause",
            "rule_output",
            "path",
            "content_hash",
            "synced_at",
        ),
        "foreign_keys": (
            "ruleset_id text not null references public.kb_rulesets(ruleset_id)",
        ),
        "required_indexes": (
            "kb_rules_ruleset_id_idx",
            "kb_rules_question_idx",
            "kb_rules_when_clause_idx",
            "kb_rules_output_idx",
        ),
    },
    "kb_question_blueprints": {
        "primary_key": "blueprint_id",
        "columns": (
            "blueprint_id",
            "version",
            "applies_to",
            "title_direction",
            "story_arc_template",
            "chapter_order",
            "global_forbidden_claims",
            "style_rules",
            "paid_unlock",
            "questions",
            "chapters",
            "path",
            "content_hash",
            "synced_at",
        ),
        "foreign_keys": (),
        "required_indexes": (
            "kb_question_blueprints_applies_to_idx",
            "kb_question_blueprints_questions_idx",
            "kb_question_blueprints_chapters_idx",
        ),
    },
    "kb_guardrail_sets": {
        "primary_key": "guardrail_id",
        "columns": (
            "guardrail_id",
            "version",
            "applies_to",
            "guardrail_ids",
            "path",
            "content_hash",
            "synced_at",
        ),
        "foreign_keys": (),
        "required_indexes": ("kb_guardrail_sets_applies_to_idx",),
    },
    "kb_guardrails": {
        "primary_key": "id",
        "columns": (
            "id",
            "guardrail_id",
            "system",
            "category",
            "source_article_id",
            "claim_ids",
            "applies_to",
            "points_any",
            "precision_any",
            "blocks",
            "lowers_confidence",
            "display",
            "reason",
            "path",
            "content_hash",
            "synced_at",
        ),
        "foreign_keys": (
            "guardrail_id text not null references public.kb_guardrail_sets(guardrail_id)",
            "source_article_id text not null references public.kb_articles(id)",
        ),
        "required_indexes": (
            "kb_guardrails_guardrail_id_idx",
            "kb_guardrails_source_article_id_idx",
            "kb_guardrails_claim_ids_idx",
            "kb_guardrails_blocks_idx",
        ),
    },
}

SYNC_RUN_COLUMNS = (
    "atom_count",
    "rule_count",
    "question_blueprint_count",
    "guardrail_count",
)

VERSION_CHECKS = (
    "check (version = 'kb-rules-v1')",
    "check (version = 'kb-question-blueprints-v1')",
    "check (version = 'kb-guardrails-v1')",
)


def normalize_sql(sql: str) -> str:
    without_line_comments = re.sub(r"--.*", "", sql)
    return re.sub(r"\s+", " ", without_line_comments).strip().lower()


def read_sql(paths: tuple[Path, ...]) -> tuple[str, list[str]]:
    missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
    contents = [path.read_text(encoding="utf-8") for path in paths if path.exists()]
    return "\n\n".join(contents), missing


def extract_create_table_body(sql: str, table: str) -> str | None:
    pattern = re.compile(rf"create\s+table\s+public\.{re.escape(table)}\s*\(", re.IGNORECASE)
    match = pattern.search(sql)
    if not match:
        return None

    depth = 1
    start = match.end()
    index = start
    while index < len(sql):
        char = sql[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return sql[start:index]
        index += 1
    return None


def has_column(body: str, table: str, column: str, normalized_sql: str) -> bool:
    if re.search(rf"^\s*{re.escape(column)}\s+", body, re.IGNORECASE | re.MULTILINE):
        return True
    return bool(
        re.search(
            rf"alter table public\.{re.escape(table)} .* add column if not exists {re.escape(column)}\s+",
            normalized_sql,
        )
    )


def contains_all(normalized_sql: str, fragments: tuple[str, ...]) -> list[str]:
    return [fragment for fragment in fragments if normalize_sql(fragment) not in normalized_sql]


def check_table(table: str, contract: dict[str, Any], sql: str, normalized_sql: str) -> dict[str, Any]:
    body = extract_create_table_body(sql, table)
    errors: list[str] = []
    warnings: list[str] = []

    if body is None:
        return {
            "table": table,
            "ok": False,
            "errors": [f"missing create table public.{table}"],
            "warnings": [],
        }

    body_normalized = normalize_sql(body)
    primary_key = contract["primary_key"]
    missing_columns = [
        column for column in contract["columns"] if not has_column(body, table, column, normalized_sql)
    ]
    if missing_columns:
        errors.append("missing columns: " + ", ".join(missing_columns))

    if f"{primary_key} text primary key" not in body_normalized:
        errors.append(f"missing text primary key on {primary_key}")

    missing_foreign_keys = contains_all(body_normalized, contract["foreign_keys"])
    if missing_foreign_keys:
        errors.append("missing foreign keys: " + "; ".join(missing_foreign_keys))

    if f"alter table public.{table} enable row level security" not in normalized_sql:
        errors.append("missing row level security enablement")

    if f"revoke all on table public.{table} from public" not in normalized_sql:
        errors.append("missing public revoke")

    if f"revoke all on table public.{table} from anon, authenticated" not in normalized_sql:
        errors.append("missing anon/authenticated revoke")

    service_role_grant = f"grant select, insert, update, delete on table public.{table} to service_role"
    if service_role_grant not in normalized_sql:
        errors.append("missing service_role grant")

    missing_indexes = [index for index in contract["required_indexes"] if f"create index {index}" not in normalized_sql]
    if missing_indexes:
        warnings.append("missing expected indexes: " + ", ".join(missing_indexes))

    if f"comment on table public.{table}" not in normalized_sql:
        warnings.append("missing table comment")

    return {
        "table": table,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check structured KB Supabase migration contract.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    sql, missing_migration_files = read_sql(STRUCTURED_MIGRATIONS)
    normalized_sql = normalize_sql(sql)
    table_results = [
        check_table(table, contract, sql, normalized_sql)
        for table, contract in REQUIRED_TABLES.items()
    ]

    errors: list[str] = []
    warnings: list[str] = []

    if missing_migration_files:
        errors.extend(f"missing migration file: {path}" for path in missing_migration_files)

    for column in SYNC_RUN_COLUMNS:
        if f"add column if not exists {column} integer not null default 0" not in normalized_sql:
            errors.append(f"missing kb_sync_runs.{column} migration")

    missing_version_checks = [check for check in VERSION_CHECKS if check not in normalized_sql]
    if missing_version_checks:
        errors.extend(f"missing version constraint: {check}" for check in missing_version_checks)

    for result in table_results:
        errors.extend(f"{result['table']}: {error}" for error in result["errors"])
        warnings.extend(f"{result['table']}: {warning}" for warning in result["warnings"])

    summary = {
        "ok": not errors,
        "checkedMigrations": [str(path.relative_to(ROOT)) for path in STRUCTURED_MIGRATIONS],
        "tables": table_results,
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Supabase structured migration contract")
        print(f"- ok: {summary['ok']}")
        print(f"- migrations: {len(STRUCTURED_MIGRATIONS)}")
        print(f"- tables: {len(table_results)}")
        if errors:
            print("Errors:")
            for error in errors:
                print(f"- {error}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"- {warning}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
