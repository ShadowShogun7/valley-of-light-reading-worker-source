#!/usr/bin/env python3
"""
Read-only Supabase runtime readiness check.

This verifies whether the configured Supabase target has the KB runtime tables
needed before running DB-backed structured readings. It does not run migrations,
does not sync data, and does not print secrets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kb_utils import ROOT
from structured_runtime import DEFAULT_KB_DIR, connect_supabase, local_structured_records
from sync_supabase import DEFAULT_SHARED_ENV, SupabaseError, first_env, load_env_file


BASE_RUNTIME_TABLES = ("kb_articles", "kb_claims", "kb_links", "kb_sync_runs")
STRUCTURED_RUNTIME_TABLES = (
    "kb_atoms",
    "kb_rulesets",
    "kb_rules",
    "kb_question_blueprints",
    "kb_guardrail_sets",
    "kb_guardrails",
)
STRUCTURED_COLLECTION_BY_TABLE = {
    "kb_atoms": "atoms",
    "kb_rulesets": "rulesets",
    "kb_rules": "rules",
    "kb_question_blueprints": "question_blueprints",
    "kb_guardrail_sets": "guardrail_sets",
    "kb_guardrails": "guardrails",
}


def resolve_path(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    return resolved if resolved.is_absolute() else ROOT / resolved


def load_env(env_file: str | None) -> None:
    if env_file:
        load_env_file(Path(env_file).expanduser())
    load_env_file(ROOT / ".env")
    load_env_file(DEFAULT_SHARED_ENV)


def redacted_supabase_host() -> str:
    url = first_env("VALLEY_SUPABASE_URL", "SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    parsed = urlparse(url)
    return parsed.netloc or "<invalid-url>"


def table_status(client: Any, table: str) -> dict[str, Any]:
    try:
        rows = client.request("GET", f"{table}?select=*&limit=10000")
    except SupabaseError as exc:
        message = str(exc)
        status = "missing" if "HTTP 404" in message or "PGRST205" in message else "error"
        return {
            "table": table,
            "status": status,
            "rowCount": None,
            "error": message,
        }

    row_count = len(rows) if isinstance(rows, list) else 0
    return {
        "table": table,
        "status": "ok",
        "rowCount": row_count,
        "error": None,
    }


def expected_structured_counts(kb_dir: Path) -> dict[str, int]:
    records = local_structured_records(kb_dir)
    return {
        table: len(records[collection])
        for table, collection in STRUCTURED_COLLECTION_BY_TABLE.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Supabase KB runtime table readiness.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase service credentials.")
    parser.add_argument("--kb-dir", default=str(DEFAULT_KB_DIR), help="Compiled KB directory for expected counts.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    kb_dir = resolve_path(args.kb_dir)
    load_env(args.env_file)
    host = redacted_supabase_host()
    client = connect_supabase(args.env_file)

    expected_counts = expected_structured_counts(kb_dir)
    table_results = [table_status(client, table) for table in [*BASE_RUNTIME_TABLES, *STRUCTURED_RUNTIME_TABLES]]

    missing_structured = [
        result["table"]
        for result in table_results
        if result["table"] in STRUCTURED_RUNTIME_TABLES and result["status"] == "missing"
    ]
    errored_tables = [result["table"] for result in table_results if result["status"] == "error"]
    count_mismatches: list[dict[str, Any]] = []
    for result in table_results:
        table = result["table"]
        if table not in expected_counts or result["status"] != "ok":
            continue
        expected = expected_counts[table]
        actual = int(result["rowCount"] or 0)
        if actual != expected:
            count_mismatches.append({"table": table, "expected": expected, "actual": actual})

    ready = not missing_structured and not errored_tables and not count_mismatches
    recommendations: list[str] = []
    if missing_structured:
        recommendations.append("Apply structured KB migrations to this Supabase target before DB-backed runtime tests.")
    if count_mismatches:
        recommendations.append("Run the KB sync against hosted staging after confirming the migration state.")
    if not missing_structured and not count_mismatches and not errored_tables:
        recommendations.append("Run scripts/validate_supabase_structured_runtime.py against this target.")

    summary = {
        "host": host,
        "ready": ready,
        "expectedStructuredCounts": expected_counts,
        "tables": table_results,
        "missingStructuredTables": missing_structured,
        "countMismatches": count_mismatches,
        "erroredTables": errored_tables,
        "recommendations": recommendations,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Supabase KB runtime readiness")
        print(f"- host: {host}")
        print(f"- ready: {ready}")
        print()
        print("Tables:")
        for result in table_results:
            suffix = ""
            table = result["table"]
            if table in expected_counts and result["status"] == "ok":
                suffix = f" expected={expected_counts[table]}"
            row_count = result["rowCount"] if result["rowCount"] is not None else "n/a"
            print(f"- {table}: {result['status']} rows={row_count}{suffix}")
            if result["error"]:
                print(f"  error: {result['error']}")
        if recommendations:
            print()
            print("Recommendations:")
            for recommendation in recommendations:
                print(f"- {recommendation}")

    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
