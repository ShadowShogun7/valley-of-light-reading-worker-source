#!/usr/bin/env python3
"""Validate Western book coverage maps."""

from __future__ import annotations

import argparse
from pathlib import Path

from book_coverage import BOOK_COVERAGE_DIR, coverage_stats, flattened_coverages, load_book_coverage_files, validate_book_coverage_contract
from kb_utils import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate kb/book_coverage YAML files.")
    parser.add_argument("--dir", default=str(BOOK_COVERAGE_DIR), help="Coverage directory. Defaults to kb/book_coverage.")
    args = parser.parse_args()

    coverage_dir = Path(args.dir)
    if not coverage_dir.is_absolute():
        coverage_dir = ROOT / coverage_dir

    loaded = load_book_coverage_files(coverage_dir)
    coverages = flattened_coverages(loaded)
    errors = validate_book_coverage_contract(coverages)
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    stats = coverage_stats(coverages)
    print(
        "Validated book coverage: "
        f"{stats['source_count']} source(s), "
        f"{stats['section_count']} section(s), "
        f"{stats['digest_claim_count']} linked digest claim(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
