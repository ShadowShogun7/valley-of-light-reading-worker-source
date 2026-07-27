#!/usr/bin/env python3
"""
Describe and guard hosted Supabase write targets.

The sync scripts can only see a Supabase URL/key pair. This module adds an
explicit target check so a hosted project is not accidentally treated as
staging when the env actually points at the main app project.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kb_utils import ROOT
from sync_supabase import DEFAULT_SHARED_ENV, first_env, load_env_file


TARGET_ENV_NAMES = (
    "VALLEY_SUPABASE_TARGET",
    "SUPABASE_TARGET",
    "VALLEY_DEPLOY_TARGET",
)
STAGING_RE = re.compile(r"\b(staging|stage|preview|dev|development|test|testing)\b", re.IGNORECASE)
PRODUCTION_RE = re.compile(r"\b(production|prod|live)\b", re.IGNORECASE)


def load_supabase_env(env_file: str | None) -> None:
    if env_file:
        load_env_file(Path(env_file).expanduser())
    load_env_file(ROOT / ".env")
    load_env_file(DEFAULT_SHARED_ENV)


def project_ref_from_host(host: str) -> str | None:
    if not host.endswith(".supabase.co"):
        return None
    first_label = host.split(".", 1)[0]
    return first_label or None


def explicit_target() -> tuple[str | None, str | None]:
    for name in TARGET_ENV_NAMES:
        value = os.environ.get(name, "").strip().lower()
        if not value:
            continue
        if value in {"stage", "staging", "preview", "dev", "development", "test", "testing"}:
            return "staging", name
        if value in {"prod", "production", "live"}:
            return "production", name
        return "unknown", name
    return None, None


def infer_target_from_name(name: str | None) -> str | None:
    if not name:
        return None
    if STAGING_RE.search(name):
        return "staging"
    if PRODUCTION_RE.search(name):
        return "production"
    return None


def project_metadata(ref: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if not ref:
        return None, None
    try:
        result = subprocess.run(
            ["supabase", "projects", "list", "-o", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)

    if result.returncode != 0:
        return None, (result.stderr or result.stdout).strip()

    try:
        projects = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"Could not parse supabase projects output: {exc}"

    if not isinstance(projects, list):
        return None, "Supabase projects output was not a list."

    for project in projects:
        if not isinstance(project, dict):
            continue
        if project.get("ref") == ref or project.get("id") == ref:
            return {
                "ref": project.get("ref") or project.get("id"),
                "name": project.get("name"),
                "region": project.get("region"),
                "status": project.get("status"),
                "linked": bool(project.get("linked")),
            }, None

    return None, f"Project ref {ref} was not found in supabase projects list."


def describe_target(env_file: str | None = None) -> dict[str, Any]:
    load_supabase_env(env_file)
    url = first_env("VALLEY_SUPABASE_URL", "SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    parsed = urlparse(url)
    host = parsed.netloc or "<invalid-url>"
    ref = project_ref_from_host(host)
    metadata, metadata_error = project_metadata(ref)
    env_target, env_target_source = explicit_target()
    inferred_target = infer_target_from_name((metadata or {}).get("name"))
    resolved_target = env_target or inferred_target or "unknown"
    target_source = env_target_source or ("project_name" if inferred_target else "unknown")

    return {
        "host": host,
        "projectRef": ref,
        "project": metadata,
        "metadataError": metadata_error,
        "explicitTarget": env_target,
        "explicitTargetSource": env_target_source,
        "inferredTarget": inferred_target,
        "resolvedTarget": resolved_target,
        "targetSource": target_source,
    }


def validate_requested_target(
    requested_target: str | None,
    *,
    env_file: str | None = None,
    confirm_production: bool = False,
    allow_unknown_staging_target: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    description = describe_target(env_file)
    errors: list[str] = []
    resolved = description["resolvedTarget"]

    if not requested_target:
        errors.append("--sync requires --target staging or --target production.")
        return description, errors

    if requested_target == "production" and not confirm_production:
        errors.append("--target production requires --confirm-production.")

    if resolved not in {"staging", "production"}:
        if requested_target == "staging" and not allow_unknown_staging_target:
            errors.append(
                "Supabase target is not explicitly marked as staging. "
                "Set VALLEY_SUPABASE_TARGET=staging, use a staging-named project, "
                "or pass --allow-unknown-staging-target after manual verification."
            )
        elif requested_target == "production":
            errors.append(
                "Supabase target is not explicitly marked as production. "
                "Set VALLEY_SUPABASE_TARGET=production or use a production-named project."
            )
        return description, errors

    if resolved != requested_target:
        errors.append(f"Supabase target classification is {resolved}, but --target is {requested_target}.")

    return description, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Describe and validate hosted Supabase write target.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase credentials/target label.")
    parser.add_argument("--target", choices=["staging", "production"], default=None)
    parser.add_argument("--confirm-production", action="store_true")
    parser.add_argument("--allow-unknown-staging-target", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    if args.target:
        description, errors = validate_requested_target(
            args.target,
            env_file=args.env_file,
            confirm_production=args.confirm_production,
            allow_unknown_staging_target=args.allow_unknown_staging_target,
        )
    else:
        description = describe_target(args.env_file)
        errors = []
    summary = {**description, "requestedTarget": args.target, "errors": errors, "ok": not errors}

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        project = description.get("project") or {}
        print("Supabase hosted target")
        print(f"- host: {description['host']}")
        print(f"- project_ref: {description.get('projectRef')}")
        print(f"- project_name: {project.get('name') or 'unknown'}")
        print(f"- resolved_target: {description['resolvedTarget']} ({description['targetSource']})")
        if description.get("metadataError"):
            print(f"- metadata_warning: {description['metadataError']}")
        if errors:
            print("Errors:")
            for error in errors:
                print(f"- {error}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
