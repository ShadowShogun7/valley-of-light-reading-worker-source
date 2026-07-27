#!/usr/bin/env python3
"""
Guarded runner for moving structured KB runtime reads onto Supabase.

Default mode is safe and Supabase-write-free:
- validate the structured Supabase migration contract
- validate local structured runtime contract
- generate a Supabase sync dry-run plan
- check the configured Supabase target readiness

Real writes require both --sync and --allow-writes, and are blocked when the
structured runtime tables are missing. This script never applies migrations by
itself; migrations should be applied through the normal Supabase migration flow
for the chosen hosted Supabase target.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

from kb_utils import ROOT
from supabase_target_guard import validate_requested_target


STRUCTURED_MIGRATIONS = (
    "supabase/migrations/20260525095713_add_structured_kb_runtime.sql",
    "supabase/migrations/20260525112318_add_question_blueprint_version.sql",
)


def python_script(name: str) -> list[str]:
    return [sys.executable, str(ROOT / "scripts" / name)]


def run_command(command: list[str], *, allow_failure: bool = False) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    record = {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "ok": result.returncode == 0,
    }
    if result.returncode != 0 and not allow_failure:
        raise SystemExit(json.dumps(record, ensure_ascii=False, indent=2))
    return record


def parse_json_stdout(record: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(record.get("stdout") or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def command_display(command: list[str]) -> str:
    return " ".join(command)


def print_record(label: str, record: dict[str, Any]) -> None:
    status = "ok" if record["ok"] else f"exit {record['returncode']}"
    print(f"- {label}: {status}")
    if record.get("stderr"):
        print(f"  stderr: {record['stderr']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run guarded Supabase structured runtime cutover checks.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase service credentials.")
    parser.add_argument("--include-drafts", action="store_true", help="Use draft-inclusive sync/build inputs.")
    parser.add_argument("--validate-live", action="store_true", help="Run live DB-backed structured validation.")
    parser.add_argument("--require-ready", action="store_true", help="Fail when the configured Supabase target is not ready.")
    parser.add_argument("--sync", action="store_true", help="Run sync_supabase.py after readiness checks.")
    parser.add_argument("--prune", action="store_true", help="With --sync, delete runtime rows outside the current compiled sync set.")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="Required with --sync. Use hosted staging first; production also requires --confirm-production.",
    )
    parser.add_argument(
        "--target",
        choices=["staging", "production"],
        default=None,
        help="Required with --sync to label the hosted Supabase write target.",
    )
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Required with --sync --target production. Do not use before launch/write approval.",
    )
    parser.add_argument(
        "--allow-unknown-staging-target",
        action="store_true",
        help="Allow --target staging when the hosted project is not explicitly labelled as staging.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    commands: list[dict[str, Any]] = []
    errors: list[str] = []

    migration_contract_cmd = python_script("check_supabase_migration_contract.py")
    commands.append({"label": "migration_contract", **run_command(migration_contract_cmd)})

    contract_cmd = python_script("structured_runtime_contract.py")
    commands.append({"label": "structured_runtime_contract", **run_command(contract_cmd)})

    dry_run_cmd = [*python_script("sync_supabase.py"), "--dry-run", "--plan-out", "default"]
    if args.include_drafts:
        dry_run_cmd.append("--include-drafts")
    commands.append({"label": "sync_dry_run", **run_command(dry_run_cmd)})

    readiness_cmd = [*python_script("check_supabase_runtime_readiness.py"), "--json"]
    if args.env_file:
        readiness_cmd.extend(["--env-file", args.env_file])
    readiness_record = run_command(readiness_cmd, allow_failure=True)
    commands.append({"label": "readiness", **readiness_record})
    readiness = parse_json_stdout(readiness_record)
    missing_structured = readiness.get("missingStructuredTables") or []
    count_mismatches = readiness.get("countMismatches") or []
    ready = bool(readiness.get("ready"))

    sync_record: dict[str, Any] | None = None
    target_description: dict[str, Any] | None = None
    if args.sync:
        if not args.allow_writes:
            errors.append("--sync requires --allow-writes.")
        target_description, target_errors = validate_requested_target(
            args.target,
            env_file=args.env_file,
            confirm_production=args.confirm_production,
            allow_unknown_staging_target=args.allow_unknown_staging_target,
        )
        errors.extend(target_errors)
        if missing_structured:
            errors.append("Structured runtime tables are missing; apply migrations before sync.")
        if not errors:
            sync_cmd = python_script("sync_supabase.py")
            if args.env_file:
                sync_cmd.extend(["--env-file", args.env_file])
            if args.include_drafts:
                sync_cmd.append("--include-drafts")
            if args.prune:
                sync_cmd.append("--prune")
            sync_record = run_command(sync_cmd, allow_failure=True)
            commands.append({"label": "sync", **sync_record})
            if not sync_record["ok"]:
                errors.append("sync_supabase.py failed.")

            readiness_after_cmd = [*python_script("check_supabase_runtime_readiness.py"), "--json"]
            if args.env_file:
                readiness_after_cmd.extend(["--env-file", args.env_file])
            readiness_after_record = run_command(readiness_after_cmd, allow_failure=True)
            commands.append({"label": "readiness_after_sync", **readiness_after_record})
            readiness = parse_json_stdout(readiness_after_record)
            ready = bool(readiness.get("ready"))
            missing_structured = readiness.get("missingStructuredTables") or []
            count_mismatches = readiness.get("countMismatches") or []

    live_record: dict[str, Any] | None = None
    if args.validate_live or (args.sync and not errors and ready):
        live_cmd = python_script("validate_supabase_structured_runtime.py")
        if args.env_file:
            live_cmd.extend(["--env-file", args.env_file])
        if args.include_drafts:
            live_cmd.append("--include-drafts")
        live_record = run_command(live_cmd, allow_failure=True)
        commands.append({"label": "validate_live", **live_record})
        if not live_record["ok"]:
            errors.append("validate_supabase_structured_runtime.py failed.")

    if args.require_ready and not ready:
        errors.append("Supabase target is not ready.")

    summary = {
        "ready": ready,
        "target": args.target,
        "supabaseTarget": target_description,
        "productionConfirmed": args.confirm_production,
        "syncRequested": args.sync,
        "syncRan": bool(sync_record),
        "pruneRequested": args.prune,
        "validateLiveRequested": args.validate_live,
        "missingStructuredTables": missing_structured,
        "countMismatches": count_mismatches,
        "requiredStructuredMigrations": list(STRUCTURED_MIGRATIONS),
        "errors": errors,
        "commands": [
            {
                "label": command["label"],
                "command": command_display(command["command"]),
                "returncode": command["returncode"],
                "ok": command["ok"],
            }
            for command in commands
        ],
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Supabase structured runtime cutover")
        for command in commands:
            print_record(command["label"], command)
        print()
        print(f"Ready: {ready}")
        if missing_structured:
            print("Missing structured tables: " + ", ".join(missing_structured))
        if count_mismatches:
            print("Structured count mismatches:")
            for mismatch in count_mismatches:
                print(f"- {mismatch['table']}: expected {mismatch['expected']}, actual {mismatch['actual']}")
        print("Required structured migrations:")
        for migration in STRUCTURED_MIGRATIONS:
            print(f"- {migration}")
        if errors:
            print("Errors:")
            for error in errors:
                print(f"- {error}")
        elif not ready:
            print("Next: apply the structured migrations to hosted staging, then rerun this script.")
        else:
            print("Next: run validate_supabase_structured_runtime.py, or rerun with --validate-live.")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
