#!/usr/bin/env python3
"""Smoke-test visible paid-result depth, variation, and anti-repetition."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from visible_reading_depth import analyze_view_models, build_view_models  # noqa: E402


def main() -> int:
    audit = analyze_view_models(build_view_models())
    if audit.failures:
        print("Western visible reading depth smoke failed")
        for failure in audit.failures:
            print(f"- {failure}")
        return 1
    print("Western visible reading depth smoke passed")
    print(f"- validated scenarios: {len(audit.scenarios)}")
    print(f"- variation metrics: {audit.variation_metrics}")
    print("- repeated generic visible copy: within contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
