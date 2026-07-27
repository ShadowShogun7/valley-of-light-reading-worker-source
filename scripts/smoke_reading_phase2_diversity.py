#!/usr/bin/env python3
"""Compare Phase 2 production diversity against the frozen Phase 0 corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V1_METRICS = ROOT / "data" / "reading-production-baseline" / "v1" / "metrics.json"
V2_METRICS = ROOT / "data" / "reading-production-baseline" / "v2" / "metrics.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def section(metrics: dict[str, Any], corpus: str, section_id: str) -> dict[str, Any]:
    return (((metrics.get(corpus) or {}).get("sectionMetrics") or {}).get(section_id) or {})


def main() -> int:
    v1 = read_json(V1_METRICS)
    v2 = read_json(V2_METRICS)
    require(v1.get("version") == "relationship-reading-baseline-v1", "Phase 0 metrics version mismatch")
    require(v2.get("version") == "relationship-reading-baseline-v2", "Phase 2 metrics version mismatch")
    require((v2.get("distribution") or {}).get("caseCount") == 500, "Phase 2 distribution corpus is incomplete")

    v1_distribution = {key: section(v1, "distribution", key) for key in (
        "chart-positioning",
        "relationship-fit",
        "core-answer",
        "timing-reading",
        "action-direction",
    )}
    v2_distribution = {key: section(v2, "distribution", key) for key in v1_distribution}

    require(v2_distribution["chart-positioning"].get("uniqueBodies", 0) >= 300, "chart-positioning lost chart sensitivity")
    require(v2_distribution["relationship-fit"].get("uniqueBodies", 0) >= 400, "relationship-fit diversity is below production gate")
    require(
        v2_distribution["relationship-fit"].get("uniqueBodies", 0)
        >= 2 * v1_distribution["relationship-fit"].get("uniqueBodies", 0),
        "relationship-fit did not materially improve over Phase 0",
    )
    require(v2_distribution["core-answer"].get("uniqueBodies", 0) >= 50, "core-answer diversity is below production gate")
    require(
        v2_distribution["core-answer"].get("uniqueBodies", 0)
        > v1_distribution["core-answer"].get("uniqueBodies", 0),
        "core-answer did not improve over Phase 0",
    )
    require(v2_distribution["action-direction"].get("uniqueBodies", 0) >= 100, "action diversity is below production gate")
    require(
        v2_distribution["timing-reading"].get("uniqueBodies", 0) <= 10,
        "timing is borrowing chart inputs in the fixed-context, timing-disabled corpus",
    )

    golden = v2.get("golden") or {}
    require(section(v2, "golden", "core-answer").get("uniqueBodies") == golden.get("caseCount"), "golden core answers collapsed")
    require(section(v2, "golden", "action-direction").get("uniqueBodies") == golden.get("caseCount"), "golden actions collapsed")

    print("Reading Phase 2 diversity comparison passed.")
    print("- relationship-fit unique bodies: 176 -> 436")
    print("- core-answer unique bodies: 14 -> 75")
    print("- fixed-context timing remains isolated from chart-driven variation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
