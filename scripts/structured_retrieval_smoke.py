#!/usr/bin/env python3
"""
Smoke test structured KB runtime retrieval across example scenarios.

Default mode is compiled JSON and does not need Supabase credentials. Use
--source supabase after applying hosted migrations and syncing the structured
KB tables.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from kb_utils import ROOT
from retrieve_structured_kb import (
    DEFAULT_PRODUCT,
    DEFAULT_SYSTEM,
    build_structured_bundle,
    read_json_object,
)
from structured_runtime import DEFAULT_KB_DIR, load_structured_records


DEFAULT_SCENARIO_DIR = ROOT / "examples" / "retrieval"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run structured KB retrieval smoke tests.")
    parser.add_argument("--scenario-dir", default=str(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--source", choices=["local", "supabase"], default="local")
    parser.add_argument("--kb-dir", default=str(DEFAULT_KB_DIR))
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--product", default=DEFAULT_PRODUCT)
    parser.add_argument("--system", default=DEFAULT_SYSTEM)
    args = parser.parse_args()

    scenario_dir = Path(args.scenario_dir).expanduser()
    if not scenario_dir.is_absolute():
        scenario_dir = ROOT / scenario_dir
    scenario_paths = sorted(scenario_dir.glob("*.json"))
    if not scenario_paths:
        raise SystemExit(f"No scenario JSON files found in {scenario_dir}")

    kb_dir = Path(args.kb_dir).expanduser()
    if not kb_dir.is_absolute():
        kb_dir = ROOT / kb_dir

    records = load_structured_records(args.source, kb_dir=kb_dir, env_file=args.env_file)

    failures = 0
    total_rules = 0
    total_atoms = 0
    total_guardrails = 0
    category_counter: Counter[str] = Counter()

    print("Structured KB retrieval smoke suite")
    print(f"- source: {args.source}")
    print(f"- scenarios: {len(scenario_paths)}")
    print()

    for path in scenario_paths:
        scenario = read_json_object(path)
        bundle = build_structured_bundle(
            records,
            scenario,
            source=args.source,
            product=args.product,
            system=args.system,
        )
        retrieval = bundle["retrieval"]
        errors = retrieval["errors"]
        if errors:
            failures += 1
        total_rules += int(retrieval["ruleCount"])
        total_atoms += int(retrieval["atomCount"])
        total_guardrails += int(retrieval["guardrailCount"])
        category_counter.update(retrieval["requiredCategories"])

        print(path.name)
        print(
            f"  rules={retrieval['ruleCount']} "
            f"atoms={retrieval['atomCount']} "
            f"blueprints={retrieval['questionBlueprintCount']} "
            f"guardrails={retrieval['guardrailCount']}"
        )
        print(f"  required_categories={', '.join(retrieval['requiredCategories'])}")
        print(f"  errors={errors if errors else 'none'}")

    print()
    print(f"Total rules across scenarios: {total_rules}")
    print(f"Total atoms across scenarios: {total_atoms}")
    print(f"Total guardrails across scenarios: {total_guardrails}")
    print("Required category frequency:")
    for category, count in category_counter.most_common():
        print(f"- {category}: {count}/{len(scenario_paths)}")
    print(f"Scenarios with errors: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
