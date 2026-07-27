#!/usr/bin/env python3
"""Keep the frontend/API relationship-stage contract aligned with policy."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from relationship_status_answer_policy import STAGE_ORDER, STATUS_POLICIES  # noqa: E402


INTAKE_PATH = ROOT / "apps" / "web" / "src" / "components" / "IntakeFlow.tsx"
ROUTE_PATH = ROOT / "apps" / "web" / "src" / "app" / "api" / "readings" / "relationship-result" / "route.ts"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def quoted_values(source: str) -> set[str]:
    return set(re.findall(r'["\']([a-z][a-z0-9-]+)["\']', source))


def source_block(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def main() -> int:
    intake = INTAKE_PATH.read_text(encoding="utf-8")
    route = ROUTE_PATH.read_text(encoding="utf-8")
    stage_block = source_block(intake, "const stageOptions", "const questionOptions")
    api_block = source_block(route, "const validRelationshipStages", "const validMainQuestions")
    intake_stages = quoted_values(stage_block) & set(STAGE_ORDER)
    api_stages = quoted_values(api_block) & set(STAGE_ORDER)
    require(intake_stages == set(STAGE_ORDER), f"intake stage mismatch: {sorted(intake_stages)}")
    require(api_stages == set(STAGE_ORDER), f"API stage mismatch: {sorted(api_stages)}")

    for stage in STAGE_ORDER:
        policy = STATUS_POLICIES[stage]
        require(str(policy.get("readerLabel") or "") in intake, f"{stage}: reader label missing from intake")
        for question_key, question_label in (policy.get("questionRewrites") or {}).items():
            require(f'value: "{question_key}"' in intake, f"{stage}:{question_key}: question value missing")
            require(str(question_label) in intake, f"{stage}:{question_key}: policy wording missing from intake")

    print("Relationship input contract smoke passed.")
    print(f"- canonical stages: {len(STAGE_ORDER)}")
    print("- intake, API validation, and status policy are aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
