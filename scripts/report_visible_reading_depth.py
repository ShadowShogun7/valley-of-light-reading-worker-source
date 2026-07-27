#!/usr/bin/env python3
"""Generate the paid V1 visible reading depth audit report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from visible_reading_depth import analyze_view_models, build_view_models, render_markdown_report  # noqa: E402


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "24-paid-v1-visible-reading-depth-audit.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report paid V1 visible reading depth and repetition risk.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output report path.")
    parser.add_argument("--check", action="store_true", help="Fail if the committed report is stale.")
    args = parser.parse_args()

    report = render_markdown_report(analyze_view_models(build_view_models()))
    out_path = Path(args.out)
    if args.check:
        current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if current != report:
            print(f"{out_path.relative_to(ROOT)} is stale. Run `scripts/report_visible_reading_depth.py`.")
            return 1
        print(f"{out_path.relative_to(ROOT)} is current")
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
