#!/usr/bin/env python3
"""
Build one frontend CompleteRelationshipResultViewModel from one runtime reading input.

This is the local prototype bridge:
ReadingInput -> Western-only calculation spike -> WesternRelationshipCaseFile
-> CompleteRelationshipResultViewModel.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from complete_relationship_result_runtime import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
)
from calc_western_spike import build_payload, read_json
from structured_runtime import (
    DEFAULT_ATOMS_PATH,
    DEFAULT_ARTICLES_PATH as STRUCTURED_DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH as STRUCTURED_DEFAULT_CLAIMS_PATH,
    DEFAULT_GUARDRAILS_PATH,
    DEFAULT_QUESTION_BLUEPRINTS_PATH,
    DEFAULT_RULES_PATH,
    load_kb_support,
    load_structured_kb,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one complete relationship result view model from one reading JSON.")
    parser.add_argument("--reading", required=True, type=Path, help="Path to one ReadingInput JSON.")
    parser.add_argument("--articles-path", default=str(DEFAULT_ARTICLES_PATH))
    parser.add_argument("--claims-path", default=str(DEFAULT_CLAIMS_PATH))
    parser.add_argument("--atoms-path", default=str(DEFAULT_ATOMS_PATH))
    parser.add_argument("--rules-path", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--question-blueprints-path", default=str(DEFAULT_QUESTION_BLUEPRINTS_PATH))
    parser.add_argument("--guardrails-path", default=str(DEFAULT_GUARDRAILS_PATH))
    parser.add_argument("--structured-kb-source", choices=["local", "supabase"], default="local")
    parser.add_argument("--structured-kb-env-file", default=None)
    parser.add_argument("--include-drafts", action="store_true", help="Allow draft KB articles during local build.")
    parser.add_argument("--json", action="store_true", help="Print the CompleteRelationshipResultViewModel JSON.")
    parser.add_argument("--write", type=Path, help="Optional path to write the CompleteRelationshipResultViewModel JSON.")
    args = parser.parse_args()

    reading = read_json(args.reading)
    try:
        calculation_payload = build_payload(reading, include_drafts=args.include_drafts, select=True)
    except ValueError as exc:
        print(f"Invalid reading input: {exc}", file=sys.stderr)
        return 2
    support = load_kb_support(
        args.structured_kb_source,
        articles_path=Path(args.articles_path or STRUCTURED_DEFAULT_ARTICLES_PATH),
        claims_path=Path(args.claims_path or STRUCTURED_DEFAULT_CLAIMS_PATH),
        env_file=args.structured_kb_env_file,
    )
    articles = support["articles"]
    claims_by_article = support["claimsByArticle"]
    structured_kb = load_structured_kb(
        args.structured_kb_source,
        atoms_path=Path(args.atoms_path),
        rules_path=Path(args.rules_path),
        question_blueprints_path=Path(args.question_blueprints_path),
        guardrails_path=Path(args.guardrails_path),
        env_file=args.structured_kb_env_file,
    )
    view_model: dict[str, Any] = build_view_model(calculation_payload, articles, claims_by_article, structured_kb)
    warnings = [
        str(warning)
        for warning in calculation_payload.get("debug", {}).get("calculation_warnings", [])
    ]
    engine_versions = calculation_payload.get("debug", {}).get("engine_versions", {})
    view_model["debug"]["calculationWarnings"] = warnings
    view_model["debug"]["engineVersions"] = {
        "immanuel": engine_versions.get("immanuel"),
        "pyswisseph": engine_versions.get("pyswisseph"),
    }
    view_model["debug"]["kbSupportSource"] = args.structured_kb_source
    view_model["debug"]["kbSupportCounts"] = {
        "articles": support["articleCount"],
        "claims": support["claimCount"],
    }

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(view_model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(view_model, ensure_ascii=False, sort_keys=True))
    elif not args.write:
        print(f"Built complete relationship result view model: {view_model.get('id')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
