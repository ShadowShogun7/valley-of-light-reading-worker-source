#!/usr/bin/env python3
"""Smoke-test deterministic when-to-contact answer rule priority."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from structured_runtime import load_structured_kb  # noqa: E402
from complete_relationship_result_runtime import western_select_answer_rule  # noqa: E402


FIXTURES_PATH = ROOT / "examples" / "timing" / "when-to-contact-rule-scenarios.json"
QUESTION = "when-to-contact"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert_true(isinstance(payload, dict), f"expected JSON object: {path}")
    return payload


def scenario_clusters(scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
    clusters = scenario.get("clusters") or {}
    assert_true(isinstance(clusters, dict), f"{scenario.get('id')}: clusters must be an object")
    return {
        str(key): value
        for key, value in clusters.items()
        if isinstance(value, dict)
    }


def assert_rule_matches_fixture(
    structured_kb: dict[str, Any],
    scenario: dict[str, Any],
) -> str:
    scenario_id = str(scenario.get("id") or "unnamed")
    expected_rule_id = str(scenario.get("expectedRuleId") or "")
    assert_true(expected_rule_id, f"{scenario_id}: expectedRuleId missing")

    rule = western_select_answer_rule(
        {"main_question": QUESTION},
        scenario_clusters(scenario),
        structured_kb,
    )
    assert_true(rule is not None, f"{scenario_id}: no rule selected")
    rule_id = str(rule.get("id") or "")
    assert_true(rule_id == expected_rule_id, f"{scenario_id}: expected {expected_rule_id}, got {rule_id}")

    output = rule.get("output") or {}
    assert_true(output.get("short_answer"), f"{scenario_id}: selected rule short_answer missing")
    assert_true(output.get("therefore"), f"{scenario_id}: selected rule therefore missing")
    because_clusters = {str(item) for item in output.get("because_clusters") or []}
    for expected_cluster in scenario.get("expectedBecauseIncludes") or []:
        assert_true(
            str(expected_cluster) in because_clusters,
            f"{scenario_id}: selected rule missing because cluster {expected_cluster}",
        )
    return rule_id


def assert_all_when_to_contact_rules_covered(
    structured_kb: dict[str, Any],
    selected_rule_ids: set[str],
) -> None:
    rule_ids = {
        str(rule.get("id") or "")
        for rule in (structured_kb.get("rulesByQuestion") or {}).get(QUESTION, [])
        if rule.get("id")
    }
    missing = sorted(rule_ids - selected_rule_ids)
    extra = sorted(selected_rule_ids - rule_ids)
    assert_true(not missing, f"when-to-contact rule fixtures missing coverage: {missing}")
    assert_true(not extra, f"when-to-contact fixtures reference unknown rules: {extra}")


def main() -> int:
    fixture_payload = read_json(FIXTURES_PATH)
    assert_true(fixture_payload.get("question") == QUESTION, "fixture question mismatch")
    scenarios = [item for item in fixture_payload.get("scenarios") or [] if isinstance(item, dict)]
    assert_true(scenarios, "when-to-contact rule scenarios missing")

    structured_kb = load_structured_kb()
    selected_rule_ids: set[str] = set()
    for scenario in scenarios:
        selected_rule_ids.add(assert_rule_matches_fixture(structured_kb, scenario))
    assert_all_when_to_contact_rules_covered(structured_kb, selected_rule_ids)

    print("Western when-to-contact rule matrix passed")
    print(f"- scenarios: {len(scenarios)}")
    print("- covered rules:")
    for rule_id in sorted(selected_rule_ids):
        print(f"  - {rule_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
