#!/usr/bin/env python3
"""Validate structured book digests before converting them into runtime atoms/rules."""

from __future__ import annotations

import argparse
from pathlib import Path

from book_digests import BOOK_DIGEST_DIR, digest_stats, flattened_digests, load_book_digest_files, validate_book_digest_contract
from kb_utils import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate kb/book_digests YAML files.")
    parser.add_argument("--dir", default=str(BOOK_DIGEST_DIR), help="Digest directory. Defaults to kb/book_digests.")
    args = parser.parse_args()

    digest_dir = Path(args.dir)
    if not digest_dir.is_absolute():
        digest_dir = ROOT / digest_dir

    loaded = load_book_digest_files(digest_dir)
    digests = flattened_digests(loaded)
    errors = validate_book_digest_contract(digests)
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    stats = digest_stats(digests)
    print(
        "Validated book digests: "
        f"{stats['digest_count']} digest(s), "
        f"{stats['method_claim_count']} method claim(s), "
        f"{stats['lane_counts']} lane(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
