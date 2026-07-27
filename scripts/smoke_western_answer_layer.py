#!/usr/bin/env python3
"""Smoke-test fixture coverage for every deterministic Western answer rule."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from structured_runtime import load_structured_kb  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    question_selector_method_claim_ids,
    western_answer_contract_from_evidence,
    western_select_answer_rule,
)


ANSWER_FIXTURES_PATH = ROOT / "examples" / "rules" / "free-relationship-answer-rule-scenarios.json"
WHEN_TO_CONTACT_FIXTURES_PATH = ROOT / "examples" / "timing" / "when-to-contact-rule-scenarios.json"

QUESTION_SELECTOR_METHOD_CLAIMS = {
    "still-love-me": "valley-question-still-love-evidence-selector",
    "any-chance": "valley-question-any-chance-conditional-selector",
    "when-to-contact": "valley-question-when-to-contact-timing-selector",
    "what-did-i-do-wrong": "valley-question-self-blame-interaction-cycle-selector",
    "stay-or-let-go": "valley-question-stay-let-go-boundary-selector",
}


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


def load_fixture_scenarios() -> list[dict[str, Any]]:
    answer_payload = read_json(ANSWER_FIXTURES_PATH)
    target_questions = {str(question) for question in answer_payload.get("targetQuestions") or []}
    assert_true(target_questions, "answer fixture targetQuestions missing")

    scenarios: list[dict[str, Any]] = []
    for item in answer_payload.get("scenarios") or []:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "")
        assert_true(question in target_questions, f"{item.get('id')}: unsupported answer fixture question {question}")
        scenarios.append(item)

    when_payload = read_json(WHEN_TO_CONTACT_FIXTURES_PATH)
    when_question = str(when_payload.get("question") or "")
    assert_true(when_question == "when-to-contact", "when-to-contact fixture question mismatch")
    for item in when_payload.get("scenarios") or []:
        if not isinstance(item, dict):
            continue
        scenario = dict(item)
        scenario["question"] = when_question
        scenarios.append(scenario)

    assert_true(scenarios, "answer layer scenarios missing")
    return scenarios


def assert_rule_matches_fixture(
    structured_kb: dict[str, Any],
    scenario: dict[str, Any],
) -> tuple[str, str]:
    scenario_id = str(scenario.get("id") or "unnamed")
    question = str(scenario.get("question") or "")
    expected_rule_id = str(scenario.get("expectedRuleId") or "")
    assert_true(question, f"{scenario_id}: question missing")
    assert_true(expected_rule_id, f"{scenario_id}: expectedRuleId missing")

    rule = western_select_answer_rule(
        {"main_question": question},
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

    expected_selector_claim = QUESTION_SELECTOR_METHOD_CLAIMS.get(question)
    assert_true(expected_selector_claim is not None, f"{scenario_id}: no selector claim mapped for question {question}")
    selector_method_claim_ids = set(question_selector_method_claim_ids(question))
    assert_true(
        expected_selector_claim in selector_method_claim_ids,
        f"{scenario_id}: selector map missing {expected_selector_claim}",
    )
    evidence_contract = western_answer_contract_from_evidence(
        {"main_question": question},
        scenario_clusters(scenario),
        [],
        {"overall": "high"},
    )
    question_selector = evidence_contract.get("questionSelector") or {}
    assert_true(
        question_selector.get("role") == "evidence_weighting_policy",
        f"{scenario_id}: question selector role missing",
    )
    assert_true(
        expected_selector_claim in set(question_selector.get("methodClaimIds") or []),
        f"{scenario_id}: evidence contract missing selector claim {expected_selector_claim}",
    )

    return question, rule_id


def assert_all_compiled_rules_covered(
    structured_kb: dict[str, Any],
    selected_by_question: dict[str, set[str]],
) -> None:
    rules_by_question = structured_kb.get("rulesByQuestion") or {}
    assert_true(isinstance(rules_by_question, dict), "rulesByQuestion missing")

    for question, rules in sorted(rules_by_question.items()):
        rule_ids = {
            str(rule.get("id") or "")
            for rule in rules
            if isinstance(rule, dict) and rule.get("id")
        }
        assert_true(rule_ids, f"{question}: no compiled rules")
        selected_rule_ids = selected_by_question.get(str(question), set())
        missing = sorted(rule_ids - selected_rule_ids)
        extra = sorted(selected_rule_ids - rule_ids)
        assert_true(not missing, f"{question} answer layer fixtures missing coverage: {missing}")
        assert_true(not extra, f"{question} answer layer fixtures reference unknown rules: {extra}")

    unexpected_questions = sorted(set(selected_by_question) - {str(question) for question in rules_by_question})
    assert_true(not unexpected_questions, f"answer layer fixtures reference unknown questions: {unexpected_questions}")


def main() -> int:
    scenarios = load_fixture_scenarios()
    structured_kb = load_structured_kb()

    selected_by_question: dict[str, set[str]] = defaultdict(set)
    scenario_ids: set[str] = set()
    for scenario in scenarios:
        scenario_id = str(scenario.get("id") or "unnamed")
        assert_true(scenario_id not in scenario_ids, f"duplicate scenario id: {scenario_id}")
        scenario_ids.add(scenario_id)
        question, rule_id = assert_rule_matches_fixture(structured_kb, scenario)
        selected_by_question[question].add(rule_id)

    assert_all_compiled_rules_covered(structured_kb, selected_by_question)

    total_rules = sum(len(rule_ids) for rule_ids in selected_by_question.values())
    print("Western answer layer smoke passed")
    print(f"- scenarios: {len(scenarios)}")
    print(f"- compiled rules covered: {total_rules}")
    for question in sorted(selected_by_question):
        print(f"- {question}: {len(selected_by_question[question])} rule(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
