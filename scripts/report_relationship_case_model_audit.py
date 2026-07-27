#!/usr/bin/env python3
"""Generate the Phase 4 RelationshipCaseModel provenance and grammar gate."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from kb_utils import ROOT


SCENARIOS_PATH = ROOT / "apps" / "web" / "src" / "data" / "generated" / "relationship-result-scenarios.json"
DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "25-paid-v3-relationship-case-model-audit.md"
SECTION_IDS = ("core-answer", "timing-reading", "action-direction")

REQUIRED_GRAMMAR_PAIRS = {
    ("saturn_pressure", "attraction_pursuit"),
    ("action_conflict", "attraction_pursuit"),
    ("emotional_safety", "attraction_pursuit"),
    ("attraction_pursuit", "action_conflict"),
    ("identity_rhythm", "emotional_safety"),
    ("communication_repair", "saturn_pressure"),
    ("communication_repair", "action_conflict"),
    ("emotional_safety", "saturn_pressure"),
    ("action_conflict", "communication_repair"),
    ("outer_intensity", "saturn_pressure"),
}

DYNAMIC_INTERACTION_PLAN_FIELDS = (
    "dynamicInteraction",
    "whatThisMeans",
    "whatItDoesNotMean",
    "repairImplication",
    "actionBoundary",
    "timingModifier",
    "contactModifier",
)


@dataclass(frozen=True)
class CaseModelScenario:
    scenario_id: str
    question: str
    stage: str
    contact_status: str
    primary: str
    primary_label: str
    secondary_summary: tuple[str, ...]
    top_secondary: str
    top_secondary_role: str
    grammar_id: str
    grammar_mode: str
    matched_grammar: bool
    timing: str
    contact: str
    risk: str
    interaction_excerpt: str
    meaning_excerpt: str
    core_excerpt: str
    timing_excerpt: str
    action_excerpt: str
    issues: tuple[str, ...]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def md_escape(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(md_escape(header) for header in headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(cell) for cell in row) + " |")
    return "\n".join(lines)


def unique(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "")
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output


def clip_text(value: Any, limit: int = 150) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def final_section(view_model: dict[str, Any], section_id: str) -> dict[str, Any]:
    return ((view_model.get("finalInterpretation") or {}).get("sections") or {}).get(section_id) or {}


def section_excerpt(view_model: dict[str, Any], section_id: str, *, limit: int = 150) -> str:
    section = final_section(view_model, section_id)
    if section_id == "action-direction":
        source = section.get("nextMove") or section.get("body") or ""
    else:
        source = section.get("body") or section.get("nextMove") or ""
    return clip_text(source, limit)


def scenario_issues(view_model: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    model = view_model.get("relationshipCaseModel") or {}
    final = view_model.get("finalInterpretation") or {}
    if model.get("version") != "relationship-case-model-v1":
        issues.append("missing case model")
    if not (model.get("validation") or {}).get("passed"):
        issues.append("case model validation failed")
    secondaries = model.get("secondaryDynamics") or []
    if not secondaries:
        issues.append("missing secondary dynamics")
    primary = model.get("primaryDynamic") or {}
    if not primary.get("evidenceIds"):
        issues.append("primary lacks evidence ids")
    for secondary in secondaries:
        if not secondary.get("evidenceIds"):
            issues.append(f"secondary lacks evidence: {secondary.get('key')}")
        if not secondary.get("interactionEffect"):
            issues.append(f"secondary lacks interaction effect: {secondary.get('key')}")
    interaction_plan = model.get("dynamicInteractionPlan") if isinstance(model.get("dynamicInteractionPlan"), dict) else {}
    if interaction_plan.get("version") != "dynamic-interaction-plan-v1":
        issues.append("missing dynamic interaction plan")
    for field in DYNAMIC_INTERACTION_PLAN_FIELDS:
        if not interaction_plan.get(field):
            issues.append(f"dynamic interaction plan lacks {field}")
    if not interaction_plan.get("evidenceIds"):
        issues.append("dynamic interaction plan lacks evidence ids")
    if interaction_plan.get("grammarMode") not in {"explicit", "composed"}:
        issues.append("dynamic interaction plan has invalid grammar mode")
    if interaction_plan.get("matchedGrammar") is not True:
        issues.append("dynamic interaction plan is unmatched")
    if "fallback" in str(interaction_plan.get("grammarId") or ""):
        issues.append("fallback grammar remains")
    top_secondary = secondaries[0] if secondaries else {}
    if interaction_plan:
        if interaction_plan.get("primaryKey") != primary.get("key"):
            issues.append("dynamic interaction primary mismatch")
        if interaction_plan.get("secondaryKey") != top_secondary.get("key"):
            issues.append("dynamic interaction secondary mismatch")
        pair = (str(interaction_plan.get("primaryKey") or ""), str(interaction_plan.get("secondaryKey") or ""))
        if pair in REQUIRED_GRAMMAR_PAIRS and interaction_plan.get("grammarMode") != "explicit":
            issues.append("required pair did not use explicit grammar")
    if "relationshipCaseModel" in (final.get("evidenceClusterKeys") or []):
        issues.append("global case model incorrectly owns final evidence")
    bundle = view_model.get("sectionNarrativeSpecs") or final.get("sectionSpecs") or {}
    specs = bundle.get("sections") or {}
    for section_id in ("chart-positioning", "relationship-fit"):
        if (specs.get(section_id) or {}).get("caseModelTrace"):
            issues.append(f"{section_id} spec has forbidden case trace")
        if final_section(view_model, section_id).get("caseModelTrace"):
            issues.append(f"{section_id} final has forbidden case trace")
    for section_id in SECTION_IDS:
        section = final_section(view_model, section_id)
        spec_trace = (specs.get(section_id) or {}).get("caseModelTrace") or {}
        final_trace = section.get("caseModelTrace") or {}
        expected_trace = {
            "version": "relationship-case-model-trace-v1",
            "caseModelVersion": model.get("version"),
            "sectionId": section_id,
            "primaryDynamicKey": interaction_plan.get("primaryKey") or primary.get("key"),
            "secondaryDynamicKey": interaction_plan.get("secondaryKey") or top_secondary.get("key"),
            "secondaryRole": interaction_plan.get("secondaryRole") or top_secondary.get("role"),
            "grammarId": interaction_plan.get("grammarId"),
            "grammarMode": interaction_plan.get("grammarMode"),
            "caseEvidenceIds": interaction_plan.get("evidenceIds") or [],
        }
        if spec_trace != expected_trace:
            issues.append(f"{section_id} spec case trace mismatch")
        if final_trace != spec_trace:
            issues.append(f"{section_id} final case trace mismatch")
    expected_final_trace = {
        **((specs.get("core-answer") or {}).get("caseModelTrace") or {}),
        "sectionId": "final-reading",
    }
    if final.get("caseModelTrace") != expected_final_trace:
        issues.append("top-level final case trace mismatch")
    return unique(issues)


def analyze_scenario(view_model: dict[str, Any]) -> CaseModelScenario:
    context = view_model.get("context") or {}
    model = view_model.get("relationshipCaseModel") or {}
    primary = model.get("primaryDynamic") or {}
    secondaries = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    top_secondary = secondaries[0] if secondaries else {}
    timing = model.get("timingPosture") or {}
    contact = model.get("contactPosture") or {}
    risk = model.get("riskPosture") or {}
    interaction_plan = model.get("dynamicInteractionPlan") or {}
    secondary_summary = tuple(
        f"{item.get('key')} ({item.get('role')})"
        for item in secondaries[:3]
        if item.get("key") and item.get("role")
    )
    return CaseModelScenario(
        scenario_id=str(view_model.get("id") or ""),
        question=str(context.get("main_question") or model.get("questionKey") or ""),
        stage=str(context.get("relationship_stage") or model.get("stageKey") or ""),
        contact_status=str(context.get("contact_status") or ""),
        primary=str(primary.get("key") or ""),
        primary_label=str(primary.get("label") or ""),
        secondary_summary=secondary_summary,
        top_secondary=str(top_secondary.get("key") or ""),
        top_secondary_role=str(top_secondary.get("role") or ""),
        grammar_id=str(interaction_plan.get("grammarId") or ""),
        grammar_mode=str(interaction_plan.get("grammarMode") or ""),
        matched_grammar=bool(interaction_plan.get("matchedGrammar")),
        timing=str(timing.get("key") or ""),
        contact=str(contact.get("key") or ""),
        risk=str(risk.get("key") or ""),
        interaction_excerpt=clip_text(interaction_plan.get("dynamicInteraction") or ""),
        meaning_excerpt=clip_text(interaction_plan.get("whatThisMeans") or ""),
        core_excerpt=section_excerpt(view_model, "core-answer"),
        timing_excerpt=section_excerpt(view_model, "timing-reading"),
        action_excerpt=section_excerpt(view_model, "action-direction"),
        issues=tuple(scenario_issues(view_model)),
    )


def count_rows(counter: Counter[str], *, limit: int | None = None) -> list[list[Any]]:
    rows = [[key, count] for key, count in counter.most_common(limit)]
    return rows or [["-", 0]]


def pair_counts(scenarios: list[CaseModelScenario]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for scenario in scenarios:
        if scenario.primary and scenario.top_secondary:
            counts[f"{scenario.primary} + {scenario.top_secondary} ({scenario.top_secondary_role})"] += 1
    return counts


def grammar_counts(scenarios: list[CaseModelScenario]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for scenario in scenarios:
        counts[scenario.grammar_id or "-"] += 1
    return counts


def required_pair_coverage_rows(scenarios: list[CaseModelScenario]) -> list[list[Any]]:
    counts: Counter[tuple[str, str]] = Counter()
    matched: dict[tuple[str, str], bool] = {}
    for scenario in scenarios:
        pair = (scenario.primary, scenario.top_secondary)
        if pair not in REQUIRED_GRAMMAR_PAIRS:
            continue
        counts[pair] += 1
        matched[pair] = matched.get(pair, False) or (
            scenario.matched_grammar and scenario.grammar_mode == "explicit"
        )

    rows: list[list[Any]] = []
    for pair in sorted(REQUIRED_GRAMMAR_PAIRS):
        rows.append(
            [
                f"{pair[0]} + {pair[1]}",
                counts[pair],
                "yes" if matched.get(pair) else "no",
            ]
        )
    return rows


def secondary_coverage_by_primary(scenarios: list[CaseModelScenario]) -> dict[str, dict[str, set[str]]]:
    coverage: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"secondary": set(), "role": set()})
    for scenario in scenarios:
        if not scenario.primary:
            continue
        for item in scenario.secondary_summary:
            key = item.split(" (", 1)[0]
            role = item.rsplit("(", 1)[-1].rstrip(")")
            coverage[scenario.primary]["secondary"].add(key)
            coverage[scenario.primary]["role"].add(role)
    return coverage


def coverage_table(scenarios: list[CaseModelScenario]) -> list[list[Any]]:
    coverage = secondary_coverage_by_primary(scenarios)
    rows: list[list[Any]] = []
    for primary in sorted(coverage):
        rows.append(
            [
                primary,
                len(coverage[primary]["secondary"]),
                ", ".join(sorted(coverage[primary]["secondary"])),
                len(coverage[primary]["role"]),
                ", ".join(sorted(coverage[primary]["role"])),
            ]
        )
    return rows


def notable_samples(scenarios: list[CaseModelScenario]) -> list[CaseModelScenario]:
    wanted_pairs = (
        ("emotional_safety", "attraction_pursuit"),
        ("emotional_safety", "saturn_pressure"),
        ("communication_repair", "saturn_pressure"),
        ("communication_repair", "action_conflict"),
        ("attraction_pursuit", "action_conflict"),
        ("saturn_pressure", "attraction_pursuit"),
        ("outer_intensity", "saturn_pressure"),
        ("identity_rhythm", "emotional_safety"),
    )
    output: list[CaseModelScenario] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_scenarios: set[str] = set()
    for primary, secondary in wanted_pairs:
        match = next(
            (
                scenario
                for scenario in scenarios
                if scenario.primary == primary
                and scenario.scenario_id not in seen_scenarios
                and any(item.startswith(f"{secondary} (") for item in scenario.secondary_summary)
            ),
            None,
        )
        if match:
            output.append(match)
            seen_pairs.add((primary, secondary))
            seen_scenarios.add(match.scenario_id)
    for scenario in scenarios:
        if len(output) >= 12:
            break
        pair = (scenario.primary, scenario.top_secondary)
        if pair not in seen_pairs and scenario.scenario_id not in seen_scenarios:
            output.append(scenario)
            seen_pairs.add(pair)
            seen_scenarios.add(scenario.scenario_id)
    return output


def audit_summary(scenarios: list[CaseModelScenario]) -> list[str]:
    issue_count = sum(1 for scenario in scenarios if scenario.issues)
    pair_counter = pair_counts(scenarios)
    coverage = secondary_coverage_by_primary(scenarios)
    explicit_grammar = sum(1 for scenario in scenarios if scenario.grammar_mode == "explicit")
    composed_grammar = sum(1 for scenario in scenarios if scenario.grammar_mode == "composed")
    fallback_grammar = sum(
        1
        for scenario in scenarios
        if not scenario.matched_grammar
        or scenario.grammar_mode not in {"explicit", "composed"}
        or "fallback" in scenario.grammar_id
    )
    required_covered = {
        (scenario.primary, scenario.top_secondary)
        for scenario in scenarios
        if (scenario.primary, scenario.top_secondary) in REQUIRED_GRAMMAR_PAIRS
    }
    missing_required = REQUIRED_GRAMMAR_PAIRS - required_covered
    thin_primary = [
        primary
        for primary, values in coverage.items()
        if len(values["secondary"]) < 3 or len(values["role"]) < 2
    ]
    lines = [
        f"- Status: {'PASS' if issue_count == 0 and not thin_primary and not missing_required and fallback_grammar == 0 else 'REVIEW'}",
        f"- Scenarios checked: {len(scenarios)}",
        f"- Scenarios with structural issues: {issue_count}",
        f"- Primary dynamics covered: {len({scenario.primary for scenario in scenarios if scenario.primary})}",
        f"- Top primary + secondary-role combinations: {len(pair_counter)}",
        f"- Explicit pair grammar scenarios: {explicit_grammar}",
        f"- Compositional pair grammar scenarios: {composed_grammar}",
        f"- Pair grammar fallback scenarios: {fallback_grammar}",
        f"- Required pair grammars covered: {len(required_covered)} / {len(REQUIRED_GRAMMAR_PAIRS)}",
        f"- Missing required pair grammars: {', '.join(f'{a}+{b}' for a, b in sorted(missing_required)) if missing_required else 'none'}",
        f"- Primary dynamics needing more pair variety: {', '.join(sorted(thin_primary)) if thin_primary else 'none'}",
    ]
    return lines


def render_report(view_models: list[dict[str, Any]]) -> str:
    scenarios = [analyze_scenario(view_model) for view_model in view_models]
    primary_counter = Counter(scenario.primary for scenario in scenarios)
    role_counter = Counter(
        role
        for scenario in scenarios
        for role in [item.rsplit("(", 1)[-1].rstrip(")") for item in scenario.secondary_summary]
        if role
    )
    timing_counter = Counter(scenario.timing for scenario in scenarios)
    contact_counter = Counter(scenario.contact for scenario in scenarios)
    grammar_counter = grammar_counts(scenarios)
    issue_rows = [
        [scenario.scenario_id, ", ".join(scenario.issues)]
        for scenario in scenarios
        if scenario.issues
    ]
    lines = [
        "# Phase 4 Relationship Case Model Provenance And Pair-Grammar Audit",
        "",
        "> Generated by `scripts/report_relationship_case_model_audit.py`. This release gate audits distinct primary/secondary combinations, explicit or compositional pair grammar, and hidden case-model provenance from section specs to final output.",
        "",
        "## Summary",
        "",
        *audit_summary(scenarios),
        "",
        "## Distribution",
        "",
        "### Primary Dynamics",
        "",
        md_table(["Primary dynamic", "Count"], count_rows(primary_counter)),
        "",
        "### Secondary Roles",
        "",
        md_table(["Secondary role", "Count"], count_rows(role_counter)),
        "",
        "### Timing Posture",
        "",
        md_table(["Timing posture", "Count"], count_rows(timing_counter)),
        "",
        "### Contact Posture",
        "",
        md_table(["Contact posture", "Count"], count_rows(contact_counter)),
        "",
        "### Pair Grammar",
        "",
        md_table(["Grammar id", "Count"], count_rows(grammar_counter)),
        "",
        "## Primary To Secondary Coverage",
        "",
        md_table(
            ["Primary", "Secondary count", "Secondary dynamics", "Role count", "Roles"],
            coverage_table(scenarios),
        ),
        "",
        "## Most Common Top Combinations",
        "",
        md_table(["Primary + top secondary role", "Count"], count_rows(pair_counts(scenarios), limit=20)),
        "",
        "## Required Pair Grammar Coverage",
        "",
        md_table(["Required pair", "Scenario count", "Matched grammar"], required_pair_coverage_rows(scenarios)),
        "",
        "## Representative Reading Samples",
        "",
        md_table(
            [
                "Scenario",
                "Question",
                "Primary",
                "Secondary dynamics",
                "Grammar",
                "Pair meaning",
                "Timing/contact",
                "Core excerpt",
                "Timing excerpt",
                "Action excerpt",
            ],
            [
                [
                    scenario.scenario_id,
                    scenario.question,
                    scenario.primary,
                    "<br>".join(scenario.secondary_summary),
                    scenario.grammar_id,
                    scenario.meaning_excerpt,
                    f"{scenario.timing} / {scenario.contact}",
                    scenario.core_excerpt,
                    scenario.timing_excerpt,
                    scenario.action_excerpt,
                ]
                for scenario in notable_samples(scenarios)
            ],
        ),
        "",
        "## Scenario Matrix",
        "",
        md_table(
            [
                "Scenario",
                "Stage/contact",
                "Question",
                "Primary",
                "Secondary dynamics",
                "Grammar",
                "Timing",
                "Risk",
                "Issues",
            ],
            [
                [
                    scenario.scenario_id,
                    f"{scenario.stage} / {scenario.contact_status}",
                    scenario.question,
                    scenario.primary,
                    "<br>".join(scenario.secondary_summary),
                    f"{scenario.grammar_id} / {scenario.grammar_mode}",
                    scenario.timing,
                    scenario.risk,
                    ", ".join(scenario.issues) or "-",
                ]
                for scenario in scenarios
            ],
        ),
        "",
        "## Interpretation Notes",
        "",
        "- This audit checks structure and surface consumption; it does not replace human reading QA.",
        "- Phase 4 quality depends on pair-specific grammar: explicit high-value pairs and composed long-tail pairs must both preserve the selected primary, secondary, and role.",
        "- Case-model provenance is metadata, not evidence ownership. It is required on core, timing, and action specs/final sections, and forbidden on chart-positioning and relationship-fit.",
        "",
    ]
    if issue_rows:
        lines.extend(
            [
                "## Structural Issues",
                "",
                md_table(["Scenario", "Issues"], issue_rows),
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Report V4 RelationshipCaseModel pair-grammar coverage and visible use.")
    parser.add_argument("--scenarios", default=str(SCENARIOS_PATH), help="Generated relationship scenarios JSON.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output report path.")
    parser.add_argument("--check", action="store_true", help="Fail if the committed report is stale.")
    args = parser.parse_args()

    view_models = read_json(Path(args.scenarios))
    analyzed = [analyze_scenario(view_model) for view_model in view_models]
    passed = any(line == "- Status: PASS" for line in audit_summary(analyzed))
    report = render_report(view_models)
    out_path = Path(args.out)
    if args.check:
        current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if current != report:
            print(f"{out_path.relative_to(ROOT)} is stale. Run `scripts/report_relationship_case_model_audit.py`.")
            return 1
        if not passed:
            print(f"{out_path.relative_to(ROOT)} is current but the Phase 4 gate is REVIEW")
            return 1
        print(f"{out_path.relative_to(ROOT)} is current")
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)} ({'PASS' if passed else 'REVIEW'})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
