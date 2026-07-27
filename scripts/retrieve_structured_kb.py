#!/usr/bin/env python3
"""
Build a structured KB runtime bundle for deterministic readings.

This is the companion to retrieve_kb.py:
- retrieve_kb.py selects article/claim evidence for prompt grounding
- retrieve_structured_kb.py selects atoms/rules/blueprints/guardrails for
  deterministic reading logic

Default mode reads local compiled JSON so the contract can be tested without a
live Supabase instance. Supabase mode reads the same records from the runtime
tables created by the structured KB migration.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from kb_utils import ROOT
from structured_runtime import DEFAULT_KB_DIR, load_structured_records


DEFAULT_PRODUCT = "relationship_compatibility"
DEFAULT_SYSTEM = "western"

EVIDENCE_SOURCE_CATEGORY_ALIASES = {
    "partnerIdentity": "identityNeeds",
    "userIdentity": "identityNeeds",
    "identity": "identityNeeds",
    "identityNeeds": "identityNeeds",
    "birthDataQuality": "birthDataQuality",
    "currentTransits": "currentTransits",
    "timing": "currentTransits",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_object(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return payload


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def normalize_stage(stage: str) -> str:
    return stage.removeprefix("context-stage-").strip()


def normalize_question(question: str) -> str:
    return question.removeprefix("context-question-").strip()


def applies_to_matches(
    applies_to: dict[str, Any],
    *,
    product: str,
    stage: str,
    question: str,
) -> bool:
    def matches(values: list[str], value: str) -> bool:
        return not values or "all" in values or value in values

    return (
        matches(as_list(applies_to.get("products")), product)
        and matches(as_list(applies_to.get("stages")), stage)
        and matches(as_list(applies_to.get("questions")), question)
    )


def rule_clusters(rule: dict[str, Any]) -> list[str]:
    clusters: list[str] = []
    output = rule.get("output") or {}
    clusters.extend(as_list(output.get("because_clusters")))

    when = rule.get("when") or {}
    for group_name in ("all", "any"):
        for condition in when.get(group_name) or []:
            if isinstance(condition, dict) and condition.get("cluster"):
                clusters.append(str(condition["cluster"]))
    return stable_unique(clusters)


def chapter_evidence_categories(blueprint: dict[str, Any]) -> list[str]:
    categories: list[str] = []
    for chapter in blueprint.get("chapters") or []:
        if not isinstance(chapter, dict):
            continue
        for evidence in chapter.get("evidence") or []:
            if not isinstance(evidence, dict):
                continue
            source = str(evidence.get("source") or "")
            categories.append(EVIDENCE_SOURCE_CATEGORY_ALIASES.get(source, source))
    return stable_unique(categories)


def question_contract(blueprint: dict[str, Any], question: str) -> dict[str, Any]:
    for item in blueprint.get("questions") or []:
        if isinstance(item, dict) and item.get("question") == question:
            return item
    return {}


def selected_blueprint(
    blueprints: list[dict[str, Any]],
    *,
    product: str,
    stage: str,
    question: str,
) -> dict[str, Any]:
    matching = [
        blueprint
        for blueprint in blueprints
        if applies_to_matches(blueprint.get("applies_to") or {}, product=product, stage=stage, question=question)
        and question_contract(blueprint, question)
    ]
    matching.sort(key=lambda item: str(item.get("blueprint_id") or ""))
    return matching[0] if matching else {}


def required_categories(rules: list[dict[str, Any]], blueprint: dict[str, Any], question: str) -> list[str]:
    categories: list[str] = []
    for rule in rules:
        categories.extend(rule_clusters(rule))

    contract = question_contract(blueprint, question)
    categories.extend(as_list(contract.get("because_clusters")))
    categories.extend(chapter_evidence_categories(blueprint))
    return stable_unique([category for category in categories if category])


def western_signal_ids(scenario: dict[str, Any]) -> list[str]:
    return stable_unique([*as_list(scenario.get("western_signals")), *as_list(scenario.get("article_ids"))])


def compact_atom(atom: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": atom.get("id"),
        "category": atom.get("category"),
        "layer": atom.get("layer"),
        "label": atom.get("label"),
        "sourceArticleId": atom.get("source_article_id"),
        "claimIds": atom.get("claim_ids") or [],
        "selectors": atom.get("selectors") or {},
        "interpretation": atom.get("interpretation") or {},
    }


def compact_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rule.get("id"),
        "rulesetId": rule.get("ruleset_id"),
        "question": rule.get("question"),
        "priority": rule.get("priority"),
        "when": rule.get("when") or {},
        "output": rule.get("output") or {},
    }


def compact_guardrail(guardrail: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": guardrail.get("id"),
        "guardrailId": guardrail.get("guardrail_id"),
        "category": guardrail.get("category"),
        "display": guardrail.get("display"),
        "appliesTo": guardrail.get("applies_to") or [],
        "pointsAny": guardrail.get("points_any") or [],
        "precisionAny": guardrail.get("precision_any") or [],
        "blocks": guardrail.get("blocks") or [],
        "lowersConfidence": guardrail.get("lowers_confidence") or [],
        "sourceArticleId": guardrail.get("source_article_id"),
        "claimIds": guardrail.get("claim_ids") or [],
        "reason": guardrail.get("reason"),
    }


def build_prompt_context(bundle: dict[str, Any]) -> str:
    lines = [
        "Valley of Light structured KB bundle",
        "Use these deterministic records as the interpretation contract. LLM wording must not add unsupported astrology claims.",
        "",
        f"Question: {bundle['input']['question']}",
        f"Stage: {bundle['input']['stage']}",
        "",
        "## Required Evidence Categories",
        "- " + ", ".join(bundle["retrieval"]["requiredCategories"]),
        "",
        "## Rules",
    ]
    for rule in bundle["rules"]:
        output = rule.get("output") or {}
        lines.append(
            f"- {rule.get('id')} priority={rule.get('priority')} confidence={output.get('confidence')} "
            f"because={', '.join(output.get('because_clusters') or [])}"
        )
        if output.get("short_answer"):
            lines.append(f"  short_answer: {output['short_answer']}")

    lines.extend(["", "## Atoms"])
    for atom in bundle["atoms"]:
        interpretation = atom.get("interpretation") or {}
        lines.append(
            f"- {atom.get('id')} category={atom.get('category')} source={atom.get('sourceArticleId')} "
            f"claims={', '.join(atom.get('claimIds') or [])}"
        )
        if interpretation.get("interpretation"):
            lines.append(f"  meaning: {interpretation['interpretation']}")
        if interpretation.get("does_not_prove"):
            lines.append(f"  does_not_prove: {interpretation['does_not_prove']}")

    blueprint = bundle.get("questionBlueprint") or {}
    if blueprint:
        lines.extend(["", "## Question Blueprint"])
        lines.append(f"- blueprint_id: {blueprint.get('blueprint_id')}")
        lines.append(f"- chapter_order: {', '.join(blueprint.get('chapter_order') or [])}")
        contract = bundle.get("questionContract") or {}
        if contract:
            lines.append(f"- answer_contract: {contract.get('answer_contract')}")

    lines.extend(["", "## Guardrails"])
    for guardrail in bundle["guardrails"]:
        lines.append(
            f"- {guardrail.get('id')} display={guardrail.get('display')} "
            f"blocks={', '.join(guardrail.get('blocks') or [])}"
        )
        if guardrail.get("reason"):
            lines.append(f"  reason: {guardrail['reason']}")

    return "\n".join(lines).strip()


def build_structured_bundle(
    records: dict[str, list[dict[str, Any]]],
    scenario: dict[str, Any],
    *,
    source: str,
    product: str,
    system: str,
) -> dict[str, Any]:
    stage = normalize_stage(str(scenario.get("stage") or ""))
    question = normalize_question(str(scenario.get("main_question") or ""))
    if not stage:
        raise SystemExit("Scenario is missing `stage`.")
    if not question:
        raise SystemExit("Scenario is missing `main_question`.")

    rules = sorted(
        [rule for rule in records["rules"] if rule.get("question") == question],
        key=lambda rule: int(rule.get("priority") or 0),
        reverse=True,
    )
    blueprint = selected_blueprint(
        records["question_blueprints"],
        product=product,
        stage=stage,
        question=question,
    )
    contract = question_contract(blueprint, question) if blueprint else {}
    categories = required_categories(rules, blueprint, question)
    signal_ids = western_signal_ids(scenario)

    atoms = [
        atom
        for atom in records["atoms"]
        if atom.get("system") == system
        and applies_to_matches(atom.get("applies_to") or {}, product=product, stage=stage, question=question)
        and (
            not categories
            or atom.get("category") in categories
            or atom.get("source_article_id") in signal_ids
        )
    ]
    atoms.sort(key=lambda atom: (str(atom.get("category") or ""), str(atom.get("id") or "")))

    rule_ids = {str(rule.get("id")) for rule in rules if rule.get("id")}
    rulesets = [
        ruleset
        for ruleset in records["rulesets"]
        if applies_to_matches(ruleset.get("applies_to") or {}, product=product, stage=stage, question=question)
        and (not rule_ids or set(as_list(ruleset.get("rule_ids"))).intersection(rule_ids))
    ]
    rulesets.sort(key=lambda ruleset: str(ruleset.get("ruleset_id") or ""))

    guardrail_sets = [
        guardrail_set
        for guardrail_set in records["guardrail_sets"]
        if applies_to_matches(guardrail_set.get("applies_to") or {}, product=product, stage=stage, question=question)
    ]
    guardrail_set_ids = {str(item.get("guardrail_id")) for item in guardrail_sets if item.get("guardrail_id")}
    guardrails = [
        guardrail
        for guardrail in records["guardrails"]
        if guardrail.get("system") == system and guardrail.get("guardrail_id") in guardrail_set_ids
    ]
    guardrails.sort(key=lambda guardrail: (str(guardrail.get("category") or ""), str(guardrail.get("id") or "")))

    available_categories = {str(atom.get("category")) for atom in atoms if atom.get("category")}
    missing_categories = [category for category in categories if category not in available_categories]
    errors: list[str] = []
    if not rules:
        errors.append(f"missing rules for {question}")
    if rules and not any(int(rule.get("priority") or 0) == 0 for rule in rules):
        errors.append(f"missing fallback rule for {question}")
    if not blueprint:
        errors.append(f"missing question blueprint for {question}")
    if blueprint and not contract:
        errors.append(f"missing question contract for {question}")
    if missing_categories:
        errors.append("missing atom categories: " + ", ".join(missing_categories))
    if not guardrails:
        errors.append(f"missing guardrails for {question}")

    bundle = {
        "input": {
            "source": source,
            "scenario": scenario,
            "product": product,
            "system": system,
            "stage": stage,
            "question": question,
        },
        "retrieval": {
            "rulesetCount": len(rulesets),
            "ruleCount": len(rules),
            "atomCount": len(atoms),
            "questionBlueprintCount": 1 if blueprint else 0,
            "guardrailSetCount": len(guardrail_sets),
            "guardrailCount": len(guardrails),
            "requiredCategories": categories,
            "missingCategories": missing_categories,
            "errors": errors,
        },
        "rulesets": rulesets,
        "rules": [compact_rule(rule) for rule in rules],
        "atoms": [compact_atom(atom) for atom in atoms],
        "questionBlueprint": blueprint,
        "questionContract": contract,
        "guardrailSets": guardrail_sets,
        "guardrails": [compact_guardrail(guardrail) for guardrail in guardrails],
    }
    bundle["promptContext"] = build_prompt_context(bundle)
    return bundle


def print_summary(bundle: dict[str, Any]) -> None:
    retrieval = bundle["retrieval"]
    print("Structured KB bundle")
    print(f"- source: {bundle['input']['source']}")
    print(f"- question: {bundle['input']['question']}")
    print(f"- stage: {bundle['input']['stage']}")
    print(f"- rulesets: {retrieval['rulesetCount']}")
    print(f"- rules: {retrieval['ruleCount']}")
    print(f"- atoms: {retrieval['atomCount']}")
    print(f"- question blueprints: {retrieval['questionBlueprintCount']}")
    print(f"- guardrail sets: {retrieval['guardrailSetCount']}")
    print(f"- guardrails: {retrieval['guardrailCount']}")
    print(f"- required categories: {', '.join(retrieval['requiredCategories'])}")
    if retrieval["missingCategories"]:
        print(f"- missing categories: {', '.join(retrieval['missingCategories'])}")
    if retrieval["errors"]:
        print(f"- errors: {retrieval['errors']}")
    print()
    print("Rules:")
    for rule in bundle["rules"]:
        output = rule.get("output") or {}
        print(f"- {rule['id']} priority={rule['priority']} confidence={output.get('confidence')}")
    print()
    print("Atoms:")
    for atom in bundle["atoms"]:
        print(f"- {atom['id']} | {atom['category']} | {atom['sourceArticleId']}")
    print()
    print("Guardrails:")
    for guardrail in bundle["guardrails"]:
        print(f"- {guardrail['id']} | {guardrail['category']} | {guardrail['display']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve structured KB runtime records.")
    parser.add_argument("--scenario", required=True, help="Path to scenario JSON.")
    parser.add_argument(
        "--source",
        choices=["local", "supabase"],
        default="local",
        help="Read from local compiled JSON or Supabase runtime tables.",
    )
    parser.add_argument("--kb-dir", default=str(DEFAULT_KB_DIR), help="Compiled KB directory for local mode.")
    parser.add_argument("--env-file", default=None, help="Optional env file for Supabase mode.")
    parser.add_argument("--product", default=DEFAULT_PRODUCT)
    parser.add_argument("--system", default=DEFAULT_SYSTEM)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when required records are missing.")
    parser.add_argument("--json", action="store_true", help="Print full JSON bundle.")
    args = parser.parse_args()

    scenario_path = Path(args.scenario).expanduser()
    if not scenario_path.is_absolute():
        scenario_path = ROOT / scenario_path
    scenario = read_json_object(scenario_path)

    kb_dir = Path(args.kb_dir).expanduser()
    if not kb_dir.is_absolute():
        kb_dir = ROOT / kb_dir

    records = load_structured_records(args.source, kb_dir=kb_dir, env_file=args.env_file)
    bundle = build_structured_bundle(
        records,
        scenario,
        source=args.source,
        product=args.product,
        system=args.system,
    )

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print_summary(bundle)

    return 1 if args.strict and bundle["retrieval"]["errors"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
