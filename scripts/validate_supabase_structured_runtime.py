#!/usr/bin/env python3
"""
Validate DB-backed structured KB runtime reads.

This script is meant to run after structured KB migrations are applied and the
runtime tables have been synced. It reads Supabase through structured_runtime.py,
compares DB records against compiled local JSON, runs retrieval scenarios, and
builds one Western complete relationship result view model using Supabase as the
structured KB source.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from complete_relationship_result_runtime import (
    build_view_model,
)
from calc_western_spike import build_payload, read_json as read_calculation_json
from kb_utils import ROOT
from retrieve_structured_kb import DEFAULT_PRODUCT, DEFAULT_SYSTEM, build_structured_bundle, read_json_object
from structured_runtime import (
    DEFAULT_KB_DIR,
    load_kb_support,
    load_kb_support_records,
    load_structured_kb,
    load_structured_records,
    local_structured_records,
)
from structured_runtime_contract import (
    canonical_records,
    first_record_mismatch,
    indexed_summary,
    metadata_leaks,
)
from supabase_target_guard import validate_requested_target
from sync_supabase import SupabaseError, canonical_hash


DEFAULT_SCENARIO_DIR = ROOT / "examples" / "retrieval"
DEFAULT_READING_PATH = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
LEGACY_RUNTIME_KEYS = ("relationshipCaseFile", "baziCompatibilityDiagnosis")
FORBIDDEN_RUNTIME_TEXT = ("BaZi", "bazi", "八字", "配偶星", "日主", "四柱", "十神")


def resolve_path(path: str | Path) -> Path:
    resolved = Path(path).expanduser()
    return resolved if resolved.is_absolute() else ROOT / resolved


def run_sync(env_file: str | None, include_drafts: bool, prune: bool) -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "sync_supabase.py")]
    if env_file:
        cmd.extend(["--env-file", env_file])
    if include_drafts:
        cmd.append("--include-drafts")
    if prune:
        cmd.append("--prune")
    subprocess.run(cmd, cwd=ROOT, check=True)


def missing_structured_tables(env_file: str | None) -> list[str]:
    cmd = [sys.executable, str(ROOT / "scripts" / "check_supabase_runtime_readiness.py"), "--json"]
    if env_file:
        cmd.extend(["--env-file", env_file])
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    missing = payload.get("missingStructuredTables") if isinstance(payload, dict) else None
    return [str(table) for table in missing or []]


def compact_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "errors": bundle["retrieval"]["errors"],
        "requiredCategories": bundle["retrieval"]["requiredCategories"],
        "rules": [str(rule.get("id")) for rule in bundle["rules"]],
        "atoms": [str(atom.get("id")) for atom in bundle["atoms"]],
        "questionBlueprint": (bundle.get("questionBlueprint") or {}).get("blueprint_id"),
        "guardrails": [str(guardrail.get("id")) for guardrail in bundle["guardrails"]],
    }


def compare_records(
    local_records: dict[str, list[dict[str, Any]]],
    supabase_records: dict[str, list[dict[str, Any]]],
) -> list[str]:
    errors: list[str] = []
    leaks = metadata_leaks(supabase_records)
    if leaks:
        errors.append("Supabase metadata leaked into runtime records: " + "; ".join(leaks[:5]))

    local_canonical = canonical_records(local_records)
    supabase_canonical = canonical_records(supabase_records)
    if local_canonical != supabase_canonical:
        errors.append(first_record_mismatch(local_canonical, supabase_canonical))

    if indexed_summary(local_records) != indexed_summary(supabase_records):
        errors.append("indexed reducer summary mismatch")

    return errors


def compare_retrieval_scenarios(
    local_records: dict[str, list[dict[str, Any]]],
    supabase_records: dict[str, list[dict[str, Any]]],
    scenario_dir: Path,
    product: str,
    system: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    scenario_paths = sorted(scenario_dir.glob("*.json"))
    if not scenario_paths:
        return [], [f"No scenario JSON files found in {scenario_dir}"]

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in scenario_paths:
        scenario = read_json_object(path)
        local_bundle = build_structured_bundle(
            local_records,
            scenario,
            source="local",
            product=product,
            system=system,
        )
        supabase_bundle = build_structured_bundle(
            supabase_records,
            scenario,
            source="supabase",
            product=product,
            system=system,
        )
        local_summary = compact_bundle(local_bundle)
        supabase_summary = compact_bundle(supabase_bundle)
        scenario_errors = list(supabase_summary["errors"])
        if local_summary != supabase_summary:
            scenario_errors.append("Supabase retrieval differs from local retrieval")
        if scenario_errors:
            errors.append(f"{path.name}: " + "; ".join(scenario_errors))
        results.append(
            {
                "scenario": path.name,
                "rules": len(supabase_bundle["rules"]),
                "atoms": len(supabase_bundle["atoms"]),
                "guardrails": len(supabase_bundle["guardrails"]),
                "errors": scenario_errors,
            }
        )
    return results, errors


def evidence_systems(view_model: dict[str, Any]) -> list[str]:
    systems: list[str] = []
    blueprint = view_model.get("readingBlueprint", {})
    for chapter in blueprint.get("chapters") or []:
        if not isinstance(chapter, dict):
            continue
        for evidence in chapter.get("evidence") or []:
            if isinstance(evidence, dict) and evidence.get("system"):
                systems.append(str(evidence["system"]))
    return systems


def western_cluster_support_errors(view_model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    case_file = view_model.get("westernRelationshipCaseFile") or {}
    for name, cluster in (case_file.get("evidenceClusters") or {}).items():
        if not isinstance(cluster, dict):
            continue
        if cluster.get("atomId") and not cluster.get("claimSupport"):
            errors.append(f"missing claim support for evidence cluster: {name}")
    return errors


def validate_view_model(
    reading_path: Path,
    env_file: str | None,
    include_drafts: bool,
) -> tuple[dict[str, Any], list[str]]:
    reading = read_calculation_json(reading_path)
    calculation_payload = build_payload(reading, include_drafts=include_drafts, select=True)
    support = load_kb_support("supabase", env_file=env_file)
    articles = support["articles"]
    claims_by_article = support["claimsByArticle"]
    structured_kb = load_structured_kb("supabase", env_file=env_file)
    view_model: dict[str, Any] = build_view_model(calculation_payload, articles, claims_by_article, structured_kb)

    errors: list[str] = []
    for key in LEGACY_RUNTIME_KEYS:
        if key in view_model:
            errors.append(f"legacy runtime key present: {key}")
    if (view_model.get("evidence") or {}).get("bazi") is not None:
        errors.append("legacy evidence.bazi present")

    western_file = view_model.get("westernRelationshipCaseFile") or {}
    if western_file.get("version") != "western-relationship-case-file-v1":
        errors.append("westernRelationshipCaseFile version mismatch")
    blueprint = view_model.get("readingBlueprint") or {}
    if blueprint.get("version") != "reading-blueprint-v1":
        errors.append("readingBlueprint version mismatch")
    if view_model.get("contractVersion") != "complete-relationship-result-v1":
        errors.append("contractVersion mismatch")
    if len(blueprint.get("chapters") or []) != 3:
        errors.append("readingBlueprint.chapters must contain 3 chapters")
    if len(view_model.get("includedReadingRows") or []) < 1:
        errors.append("includedReadingRows must contain result sections")

    non_western_systems = sorted({system for system in evidence_systems(view_model) if system != "western"})
    if non_western_systems:
        errors.append("non-Western evidence systems present: " + ", ".join(non_western_systems))

    serialized = json.dumps(view_model, ensure_ascii=False, sort_keys=True)
    forbidden_hits = [term for term in FORBIDDEN_RUNTIME_TEXT if term in serialized]
    if forbidden_hits:
        errors.append("forbidden runtime text present: " + ", ".join(forbidden_hits))
    errors.extend(western_cluster_support_errors(view_model))

    return {
        "id": view_model.get("id"),
        "contractVersion": view_model.get("contractVersion"),
        "westernRelationshipCaseFileVersion": western_file.get("version"),
        "readingBlueprintVersion": blueprint.get("version"),
        "chapterCount": len(blueprint.get("chapters") or []),
        "includedReadingRowCount": len(view_model.get("includedReadingRows") or []),
        "evidenceSystems": sorted(set(evidence_systems(view_model))),
        "kbSupportCounts": {
            "articles": support["articleCount"],
            "claims": support["claimCount"],
        },
    }, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Supabase-backed structured KB runtime reads.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase service credentials.")
    parser.add_argument("--kb-dir", default=str(DEFAULT_KB_DIR), help="Compiled KB directory to compare against.")
    parser.add_argument("--scenario-dir", default=str(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--reading", default=str(DEFAULT_READING_PATH))
    parser.add_argument("--product", default=DEFAULT_PRODUCT)
    parser.add_argument("--system", default=DEFAULT_SYSTEM)
    parser.add_argument("--include-drafts", action="store_true", help="Use draft-inclusive sync/build inputs.")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Run sync_supabase.py before validation. Requires --target and --allow-writes.",
    )
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
    parser.add_argument("--skip-view-model", action="store_true", help="Skip Supabase-backed view-model build.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    kb_dir = resolve_path(args.kb_dir)
    scenario_dir = resolve_path(args.scenario_dir)
    reading_path = resolve_path(args.reading)

    if args.sync:
        if not args.allow_writes:
            raise SystemExit("--sync requires --allow-writes.")
        _, target_errors = validate_requested_target(
            args.target,
            env_file=args.env_file,
            confirm_production=args.confirm_production,
            allow_unknown_staging_target=args.allow_unknown_staging_target,
        )
        if target_errors:
            raise SystemExit("\n".join(target_errors))
        missing_tables = missing_structured_tables(args.env_file)
        if missing_tables:
            raise SystemExit(
                "Structured runtime tables are missing; apply migrations before sync: "
                + ", ".join(missing_tables)
            )
        run_sync(args.env_file, args.include_drafts, args.prune)

    local_records = local_structured_records(kb_dir)
    try:
        supabase_records = load_structured_records("supabase", env_file=args.env_file)
        supabase_support_records = load_kb_support_records("supabase", env_file=args.env_file)
    except SupabaseError as exc:
        print(f"Supabase structured runtime read failed: {exc}", file=sys.stderr)
        print(
            "Run scripts/check_supabase_runtime_readiness.py to inspect missing tables and counts.",
            file=sys.stderr,
        )
        return 1

    errors = compare_records(local_records, supabase_records)
    scenario_results, scenario_errors = compare_retrieval_scenarios(
        local_records,
        supabase_records,
        scenario_dir,
        product=args.product,
        system=args.system,
    )
    errors.extend(scenario_errors)

    view_model_summary: dict[str, Any] | None = None
    if not args.skip_view_model:
        view_model_summary, view_model_errors = validate_view_model(
            reading_path,
            env_file=args.env_file,
            include_drafts=args.include_drafts,
        )
        errors.extend(view_model_errors)

    summary = {
        "source": "supabase",
        "syncRan": args.sync,
        "kbDir": str(kb_dir.relative_to(ROOT)) if kb_dir.is_relative_to(ROOT) else str(kb_dir),
        "counts": {key: len(rows) for key, rows in supabase_records.items()},
        "supportCounts": {key: len(rows) for key, rows in supabase_support_records.items()},
        "recordContractHash": canonical_hash(
            {"records": canonical_records(local_records), "index": indexed_summary(local_records)}
        ),
        "scenarioCount": len(scenario_results),
        "scenariosWithErrors": len([result for result in scenario_results if result["errors"]]),
        "viewModel": view_model_summary,
        "errors": errors,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Supabase structured runtime validation")
        print(f"- sync_ran: {args.sync}")
        print(f"- kb_dir: {summary['kbDir']}")
        for key, rows in supabase_records.items():
            print(f"- {key}: {len(rows)}")
        for key, rows in supabase_support_records.items():
            print(f"- support_{key}: {len(rows)}")
        print(f"- scenarios: {summary['scenarioCount']}")
        print(f"- scenarios_with_errors: {summary['scenariosWithErrors']}")
        if view_model_summary:
            print(f"- view_model: {view_model_summary['id']}")
            print(f"- chapters: {view_model_summary['chapterCount']}")
            print(f"- evidence_systems: {', '.join(view_model_summary['evidenceSystems'])}")
        print(f"- errors: {errors if errors else 'none'}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
