#!/usr/bin/env python3
"""
Validate that local structured KB JSON and Supabase-shaped rows normalize to
the same runtime contract.

This is an offline boundary test. It does not contact Supabase; it uses the
same transform functions as sync_supabase.py to create DB-shaped rows, then
uses structured_runtime.py to normalize those rows back into reducer input.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from structured_runtime import (
    DEFAULT_KB_DIR,
    SUPABASE_RUNTIME_METADATA_KEYS,
    index_structured_kb,
    local_kb_support_records,
    local_structured_records,
    normalize_supabase_kb_support_records,
    normalize_supabase_structured_records,
)
from sync_supabase import (
    canonical_hash,
    transform_articles,
    transform_atoms,
    transform_claims,
    transform_guardrail_sets,
    transform_guardrails,
    transform_question_blueprints,
    transform_rules,
    transform_rulesets,
)


DB_SYNCED_AT = "2026-05-25T00:00:00+00:00"
COLLECTION_KEYS = {
    "atoms": "id",
    "rulesets": "ruleset_id",
    "rules": "id",
    "question_blueprints": "blueprint_id",
    "guardrail_sets": "guardrail_id",
    "guardrails": "id",
}
SUPPORT_COLLECTION_KEYS = {
    "articles": "id",
    "claims": "claim_id",
}


def with_db_defaults(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "synced_at": DB_SYNCED_AT} for row in rows]


def supabase_shaped_records(
    local_records: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "atoms": with_db_defaults(transform_atoms(local_records["atoms"])),
        "rulesets": with_db_defaults(transform_rulesets(local_records["rulesets"])),
        "rules": with_db_defaults(transform_rules(local_records["rules"])),
        "question_blueprints": with_db_defaults(
            transform_question_blueprints(local_records["question_blueprints"])
        ),
        "guardrail_sets": with_db_defaults(transform_guardrail_sets(local_records["guardrail_sets"])),
        "guardrails": with_db_defaults(transform_guardrails(local_records["guardrails"])),
    }


def supabase_shaped_support_records(
    local_records: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "articles": with_db_defaults(transform_articles(local_records["articles"])),
        "claims": with_db_defaults(transform_claims(local_records["claims"])),
    }


def sorted_collection(rows: list[dict[str, Any]], identity_key: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: str(row.get(identity_key) or ""))


def canonical_records(
    records: dict[str, list[dict[str, Any]]],
    collection_keys: dict[str, str] = COLLECTION_KEYS,
) -> dict[str, list[dict[str, Any]]]:
    return {
        collection: sorted_collection(records.get(collection, []), identity_key)
        for collection, identity_key in collection_keys.items()
    }


def indexed_summary(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    indexed = index_structured_kb(records)
    return {
        "atomIds": sorted(str(atom.get("id")) for atom in indexed["atoms"] if atom.get("id")),
        "atomCategories": sorted(indexed["atomsByCategory"]),
        "atomSourceArticles": sorted(indexed["atomsBySourceArticle"]),
        "guardrailIds": sorted(indexed["guardrailsById"]),
        "questionBlueprintIds": sorted(indexed["questionBlueprintsById"]),
        "questionContracts": sorted(indexed["questionBlueprintByQuestion"]),
        "rulesByQuestion": {
            question: [str(rule.get("id")) for rule in rules]
            for question, rules in sorted(indexed["rulesByQuestion"].items())
        },
    }


def metadata_leaks(
    records: dict[str, list[dict[str, Any]]],
    collection_keys: dict[str, str] = COLLECTION_KEYS,
) -> list[str]:
    leaks: list[str] = []
    for collection, rows in records.items():
        identity_key = collection_keys.get(collection, "id")
        for row in rows:
            leaked_keys = sorted(set(row).intersection(SUPABASE_RUNTIME_METADATA_KEYS))
            if leaked_keys:
                identity = row.get(identity_key) or row.get("id") or "<unknown>"
                leaks.append(f"{collection}:{identity} leaked {', '.join(leaked_keys)}")
    return leaks


def first_record_mismatch(
    local_records: dict[str, list[dict[str, Any]]],
    normalized_records: dict[str, list[dict[str, Any]]],
    collection_keys: dict[str, str] = COLLECTION_KEYS,
) -> str:
    for collection, identity_key in collection_keys.items():
        local_rows = local_records[collection]
        normalized_rows = normalized_records[collection]
        if len(local_rows) != len(normalized_rows):
            return f"{collection} count mismatch: local={len(local_rows)} normalized={len(normalized_rows)}"

        local_by_id = {str(row.get(identity_key)): row for row in local_rows}
        normalized_by_id = {str(row.get(identity_key)): row for row in normalized_rows}
        if set(local_by_id) != set(normalized_by_id):
            missing = sorted(set(local_by_id).difference(normalized_by_id))
            extra = sorted(set(normalized_by_id).difference(local_by_id))
            return f"{collection} id mismatch: missing={missing[:3]} extra={extra[:3]}"

        for identity in sorted(local_by_id):
            if local_by_id[identity] != normalized_by_id[identity]:
                return f"{collection}:{identity} row mismatch"
    return "unknown mismatch"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate structured KB runtime adapter contract.")
    parser.add_argument("--kb-dir", default=str(DEFAULT_KB_DIR), help="Compiled KB directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).expanduser()
    if not kb_dir.is_absolute():
        kb_dir = ROOT / kb_dir

    local_records = local_structured_records(kb_dir)
    local_support_records = local_kb_support_records(kb_dir)
    normalized_records = normalize_supabase_structured_records(supabase_shaped_records(local_records))
    normalized_support_records = normalize_supabase_kb_support_records(
        supabase_shaped_support_records(local_support_records)
    )

    local_canonical = canonical_records(local_records)
    normalized_canonical = canonical_records(normalized_records)
    local_support_canonical = canonical_records(local_support_records, SUPPORT_COLLECTION_KEYS)
    normalized_support_canonical = canonical_records(normalized_support_records, SUPPORT_COLLECTION_KEYS)
    local_index = indexed_summary(local_records)
    normalized_index = indexed_summary(normalized_records)

    errors: list[str] = []
    leaks = metadata_leaks(normalized_records)
    if leaks:
        errors.append("metadata leakage after Supabase normalization: " + "; ".join(leaks[:5]))
    if local_canonical != normalized_canonical:
        errors.append(first_record_mismatch(local_canonical, normalized_canonical))
    support_leaks = metadata_leaks(normalized_support_records, SUPPORT_COLLECTION_KEYS)
    if support_leaks:
        errors.append("support metadata leakage after Supabase normalization: " + "; ".join(support_leaks[:5]))
    if local_support_canonical != normalized_support_canonical:
        errors.append(first_record_mismatch(local_support_canonical, normalized_support_canonical, SUPPORT_COLLECTION_KEYS))
    if local_index != normalized_index:
        errors.append("indexed reducer summary mismatch")

    summary = {
        "kbDir": str(kb_dir.relative_to(ROOT)) if kb_dir.is_relative_to(ROOT) else str(kb_dir),
        "counts": {collection: len(local_records[collection]) for collection in COLLECTION_KEYS},
        "supportCounts": {
            collection: len(local_support_records[collection])
            for collection in SUPPORT_COLLECTION_KEYS
        },
        "contractHash": canonical_hash({"records": local_canonical, "index": local_index}),
        "supportContractHash": canonical_hash({"records": local_support_canonical}),
        "errors": errors,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Structured runtime contract")
        print(f"- kb_dir: {summary['kbDir']}")
        for collection, count in summary["counts"].items():
            print(f"- {collection}: {count}")
        for collection, count in summary["supportCounts"].items():
            print(f"- support_{collection}: {count}")
        print(f"- contract_hash: {summary['contractHash']}")
        print(f"- support_contract_hash: {summary['supportContractHash']}")
        print(f"- errors: {errors if errors else 'none'}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
