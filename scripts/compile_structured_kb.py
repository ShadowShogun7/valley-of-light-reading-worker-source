#!/usr/bin/env python3
"""
Compile machine-readable YAML atoms/rules into local JSON artifacts.

This sits beside the Markdown compiler:
- wiki/*.md remains the article/source layer
- kb/atoms/**/*.yml, kb/rules/**/*.yml, kb/question_blueprints/**/*.yml,
  and kb/guardrails/**/*.yml become deterministic reducer inputs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from structured_kb import compile_structured_kb


DEFAULT_OUT_DIR = ROOT / "dist" / "kb"


def read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile structured KB YAML atoms/rules to local JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory. Defaults to dist/kb.")
    parser.add_argument("--articles-path", default=str(DEFAULT_OUT_DIR / "kb_articles.json"))
    parser.add_argument("--claims-path", default=str(DEFAULT_OUT_DIR / "kb_claims.json"))
    args = parser.parse_args()

    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    articles_path = Path(args.articles_path)
    if not articles_path.is_absolute():
        articles_path = ROOT / articles_path
    claims_path = Path(args.claims_path)
    if not claims_path.is_absolute():
        claims_path = ROOT / claims_path

    result = compile_structured_kb(
        out_dir=out_dir,
        articles=read_json(articles_path),
        claims=read_json(claims_path),
    )
    print(
        "Compiled structured KB JSON: "
        f"{result.atom_count} atom(s), "
        f"{result.rule_count} rule(s), "
        f"{result.question_blueprint_count} question blueprint(s), "
        f"{result.guardrail_count} guardrail(s) -> {out_dir.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
