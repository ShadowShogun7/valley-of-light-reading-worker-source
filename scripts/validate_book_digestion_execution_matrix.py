#!/usr/bin/env python3
"""Validate that the generated book digestion matrix is current."""

from __future__ import annotations

from book_coverage import flattened_coverages, load_book_coverage_files
from book_digests import flattened_digests, load_book_digest_files
from kb_utils import read_text
from method_claim_usage import build_method_claim_usage_records
from report_book_digestion_execution_matrix import DEFAULT_REPORT_PATH, build_report


def main() -> int:
    expected = build_report(
        flattened_coverages(load_book_coverage_files()),
        flattened_digests(load_book_digest_files()),
        build_method_claim_usage_records(),
    )
    actual = read_text(DEFAULT_REPORT_PATH) if DEFAULT_REPORT_PATH.exists() else ""
    if actual != expected:
        print(
            "Book digestion execution matrix is stale. "
            "Run `.venv/bin/python scripts/report_book_digestion_execution_matrix.py`."
        )
        return 1
    print("Book digestion execution matrix is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
