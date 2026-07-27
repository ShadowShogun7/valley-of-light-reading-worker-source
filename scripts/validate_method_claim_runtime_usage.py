#!/usr/bin/env python3
"""Validate that every book-digest method claim maps to runtime artifacts."""

from __future__ import annotations

from method_claim_usage import build_method_claim_usage_records, usage_stats, validate_method_claim_usage


def main() -> int:
    records = build_method_claim_usage_records()
    errors = validate_method_claim_usage(records)
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    stats = usage_stats(records)
    print(
        "Validated method claim runtime usage: "
        f"{stats['claim_count']} claim(s), "
        f"{stats['artifact_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
