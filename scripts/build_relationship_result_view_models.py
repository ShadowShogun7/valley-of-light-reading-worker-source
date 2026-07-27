#!/usr/bin/env python3
"""Build complete relationship result fixture scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from complete_relationship_result_runtime import (
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CALCULATION_DIR,
    DEFAULT_CLAIMS_PATH,
    DEFAULT_OUTPUT_PATH,
    SCENARIO_ORDER,
    build_complete_relationship_result_view_model,
    load_articles,
    load_claims_by_article,
    read_json,
)
from kb_utils import ROOT
from structured_runtime import (
    DEFAULT_ATOMS_PATH,
    DEFAULT_GUARDRAILS_PATH,
    DEFAULT_QUESTION_BLUEPRINTS_PATH,
    DEFAULT_RULES_PATH,
    load_structured_kb,
)

CALCULATION_METADATA_STEMS = {"relationship-depth-fixtures-v2"}


def build_view_model(
    fixture: dict[str, Any],
    articles: dict[str, dict[str, Any]],
    claims_by_article: dict[str, list[dict[str, Any]]] | None = None,
    structured_kb: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_complete_relationship_result_view_model(fixture, articles, claims_by_article, structured_kb)


def ordered_calculation_paths(calculation_dir: Path) -> list[Path]:
    available_paths = {
        path.stem: path
        for path in calculation_dir.glob("*.json")
        if path.stem not in CALCULATION_METADATA_STEMS
    }
    ordered_paths = [available_paths[name] for name in SCENARIO_ORDER if name in available_paths]
    extra_paths = sorted(path for stem, path in available_paths.items() if stem not in set(SCENARIO_ORDER))
    return [*ordered_paths, *extra_paths]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build frontend complete relationship result scenarios.")
    parser.add_argument("--calculation-dir", default=str(DEFAULT_CALCULATION_DIR))
    parser.add_argument("--articles-path", default=str(DEFAULT_ARTICLES_PATH))
    parser.add_argument("--claims-path", default=str(DEFAULT_CLAIMS_PATH))
    parser.add_argument("--atoms-path", default=str(DEFAULT_ATOMS_PATH))
    parser.add_argument("--rules-path", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--question-blueprints-path", default=str(DEFAULT_QUESTION_BLUEPRINTS_PATH))
    parser.add_argument("--guardrails-path", default=str(DEFAULT_GUARDRAILS_PATH))
    parser.add_argument("--structured-kb-source", choices=["local", "supabase"], default="local")
    parser.add_argument("--structured-kb-env-file", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    calculation_dir = Path(args.calculation_dir)
    articles = load_articles(Path(args.articles_path))
    claims_by_article = load_claims_by_article(Path(args.claims_path))
    structured_kb = load_structured_kb(
        args.structured_kb_source,
        atoms_path=Path(args.atoms_path),
        rules_path=Path(args.rules_path),
        question_blueprints_path=Path(args.question_blueprints_path),
        guardrails_path=Path(args.guardrails_path),
        env_file=args.structured_kb_env_file,
    )
    scenarios = [
        build_view_model(read_json(path), articles, claims_by_article, structured_kb)
        for path in ordered_calculation_paths(calculation_dir)
    ]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        display_path = output_path.relative_to(ROOT)
    except ValueError:
        display_path = output_path
    print(f"Wrote {len(scenarios)} complete relationship result scenario(s) -> {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
