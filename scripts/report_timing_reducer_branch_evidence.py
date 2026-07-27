#!/usr/bin/env python3
"""Generate an audit report for Western timing reducer branches."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json  # noqa: E402
from complete_relationship_result_runtime import build_view_model, western_select_answer_rule  # noqa: E402
from smoke_western_timing_window_matrix import (  # noqa: E402
    ARTICLES,
    CLAIMS_BY_ARTICLE,
    CONTACT_REDUCER_FIXTURES_PATH,
    TIMING_ACTION_HEADLINE_NEEDLES,
    read_fixture_scenarios,
    synthetic_timing_scan,
    timing_reading_without_scan,
)
from structured_runtime import load_structured_kb  # noqa: E402


DEFAULT_REPORT_PATH = ROOT / "docs" / "research" / "19-western-timing-reducer-branch-evidence.md"
WHEN_TO_CONTACT_FIXTURES_PATH = ROOT / "examples" / "timing" / "when-to-contact-rule-scenarios.json"
TIMING_SELECTOR_KEYS = (
    "timingMercuryCommunication",
    "timingVenusSoftening",
    "timingMarsActivation",
    "timingSaturnPressure",
    "timingMoonWeather",
)
FORBIDDEN_PUBLIC_TIMING_KEYS = {"date", "start_date", "end_date", "startDate", "endDate", "daySummaries", "day_summaries", "windows"}
VISIBLE_INTERNAL_TERMS = ("avoid_push", "low_pressure", "not_calculated", "reducer", "selector", "精準成功日期")


@dataclass
class TimingBranchAudit:
    scenario_id: str
    description: str
    expected: dict[str, Any]
    view_model: dict[str, Any]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class RuleAudit:
    scenario_id: str
    description: str
    expected_rule_id: str
    actual_rule_id: str
    expected_because: tuple[str, ...]
    actual_because: tuple[str, ...]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


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


def compact(values: Iterable[Any], *, limit: int = 8) -> str:
    items = unique(values)
    if len(items) > limit:
        return ", ".join(items[:limit]) + f", +{len(items) - limit} more"
    return ", ".join(items)


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def collect_claim_ids(value: Any) -> list[str]:
    claim_ids: list[str] = []
    for item in walk(value):
        if not isinstance(item, dict):
            continue
        for key in ("claimIds", "sourceClaimIds", "methodClaimIds", "sourceClaimId"):
            raw = item.get(key)
            if isinstance(raw, list):
                claim_ids.extend(str(claim_id) for claim_id in raw if claim_id)
            elif raw:
                claim_ids.append(str(raw))
    return unique(claim_ids)


def exact_timing_public_only(view_model: dict[str, Any]) -> bool:
    case = view_model.get("westernRelationshipCaseFile") or {}
    clusters = case.get("evidenceClusters") or {}
    public_scan = (case.get("timingLayer") or {}).get("windowScan") or {}
    contact = clusters.get("timingContactReducer") or {}
    timing_guidance = view_model.get("timingGuidance") or {}
    selected_reducers = contact.get("selectedTimingReducers") or []
    public_payload = {
        "publicScan": public_scan,
        "contact": contact,
        "timingGuidance": timing_guidance,
        "selectedReducers": selected_reducers,
    }
    rendered = json.dumps(public_payload, ensure_ascii=False)
    return (
        public_scan.get("preciseDatesAvailable") is False
        and contact.get("preciseDatesAvailable") is False
        and timing_guidance.get("preciseDatesAvailable") is False
        and not FORBIDDEN_PUBLIC_TIMING_KEYS.intersection(public_scan)
        and all(not FORBIDDEN_PUBLIC_TIMING_KEYS.intersection(item) for item in selected_reducers if isinstance(item, dict))
        and "start_date" not in rendered
        and "end_date" not in rendered
    )


def timing_readable_text(view_model: dict[str, Any]) -> str:
    readable = ((view_model.get("timingGuidance") or {}).get("readableInterpretation") or {})
    return "\n".join(str(readable.get(key) or "") for key in ("headline", "meaning", "body", "nextMove", "caution"))


def timing_guidance_headline(view_model: dict[str, Any]) -> str:
    return str(((view_model.get("timingGuidance") or {}).get("readableInterpretation") or {}).get("headline") or "")


def donts_text(view_model: dict[str, Any]) -> str:
    donts = (((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("donts") or [])
    return "\n".join(str(item.get("body") or "") for item in donts if isinstance(item, dict))


def selected_categories(contact: dict[str, Any]) -> set[str]:
    return {
        str(item.get("category") or "")
        for item in contact.get("selectedTimingReducers") or []
        if isinstance(item, dict) and item.get("category")
    }


def selector_summary(view_model: dict[str, Any]) -> list[str]:
    clusters = ((view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {})
    rows: list[str] = []
    for key in TIMING_SELECTOR_KEYS:
        cluster = clusters.get(key) or {}
        state = str(cluster.get("dominantContactType") or "none")
        count = int(cluster.get("windowCount") or 0)
        rows.append(f"{key}:{state}/{count}")
    return rows


def build_branch_view_model(base_payload: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    scenario_id = str(scenario.get("id") or "unnamed")
    payload = copy.deepcopy(base_payload)
    payload["reading_id"] = f"timing-contact-reducer-{scenario_id}"
    analysis = (payload.get("western") or {}).setdefault("analysis", {})
    analysis["timing_window_scan"] = synthetic_timing_scan(scenario)
    payload.setdefault("debug", {})["western_analysis"] = analysis
    return build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)


def audit_timing_branch(base_payload: dict[str, Any], scenario: dict[str, Any]) -> TimingBranchAudit:
    scenario_id = str(scenario.get("id") or "unnamed")
    expected = scenario.get("expected") or {}
    view_model = build_branch_view_model(base_payload, scenario)
    case = view_model.get("westernRelationshipCaseFile") or {}
    clusters = case.get("evidenceClusters") or {}
    contact = clusters.get("timingContactReducer") or {}
    band = clusters.get("timingWindowBand") or {}
    timing_guidance = view_model.get("timingGuidance") or {}
    errors: list[str] = []

    comparisons = {
        "recommendedAction": contact.get("recommendedAction"),
        "contactMode": contact.get("contactMode"),
        "topBand": contact.get("topBand"),
        "supportSignalCount": contact.get("supportSignalCount"),
        "cautionSignalCount": contact.get("cautionSignalCount"),
        "hasLowPressureContactWindow": contact.get("hasLowPressureContactWindow"),
        "hasAvoidPressureWindow": contact.get("hasAvoidPressureWindow"),
        "hasMercuryCommunicationWindow": contact.get("hasMercuryCommunicationWindow"),
        "hasVenusSofteningWindow": contact.get("hasVenusSofteningWindow"),
        "hasMarsActivationRisk": contact.get("hasMarsActivationRisk"),
        "hasSaturnBoundaryRisk": contact.get("hasSaturnBoundaryRisk"),
    }
    for key, actual in comparisons.items():
        if actual != expected.get(key):
            errors.append(f"{scenario_id}: {key} expected {expected.get(key)!r}, got {actual!r}")

    expected_categories = {str(item) for item in expected.get("selectedCategories") or []}
    actual_categories = selected_categories(contact)
    if actual_categories != expected_categories:
        errors.append(f"{scenario_id}: selected categories expected {sorted(expected_categories)}, got {sorted(actual_categories)}")
    if band.get("topBand") != expected.get("topBand"):
        errors.append(f"{scenario_id}: timingWindowBand expected {expected.get('topBand')}, got {band.get('topBand')}")
    if timing_guidance.get("recommendedAction") != expected.get("recommendedAction"):
        errors.append(f"{scenario_id}: visible timing guidance action mismatch")
    if timing_guidance.get("topBand") != expected.get("topBand"):
        errors.append(f"{scenario_id}: visible timing guidance band mismatch")
    instruction_needle = str(expected.get("instructionContains") or "")
    if instruction_needle and instruction_needle not in str(contact.get("contactInstruction") or ""):
        errors.append(f"{scenario_id}: contact instruction missing {instruction_needle!r}")
    headline_needle = TIMING_ACTION_HEADLINE_NEEDLES.get(scenario_id)
    if headline_needle and headline_needle not in timing_guidance_headline(view_model):
        errors.append(f"{scenario_id}: timing headline missing {headline_needle!r}")
    visible_text = timing_readable_text(view_model).lower()
    for term in VISIBLE_INTERNAL_TERMS:
        if term.lower() in visible_text:
            errors.append(f"{scenario_id}: timing readable leaked internal term {term!r}")
    if not exact_timing_public_only(view_model):
        errors.append(f"{scenario_id}: public timing payload leaked precise timing/date fields")
    if "western-contact-timing-action-reducers-007" not in set(collect_claim_ids((((view_model.get("readableQuestionAnswer") or {}).get("sections") or {}).get("donts") or []))):
        errors.append(f"{scenario_id}: boundary donts missing repair-tone source claim")
    if not any(needle in donts_text(view_model) for needle in ("長訊息", "補訊息", "連續傳訊息", "長文")):
        errors.append(f"{scenario_id}: boundary donts missing visible message-pressure warning")

    return TimingBranchAudit(
        scenario_id=scenario_id,
        description=str(scenario.get("description") or ""),
        expected=expected,
        view_model=view_model,
        errors=errors,
    )


def audit_timing_branches() -> list[TimingBranchAudit]:
    base_payload = build_payload(timing_reading_without_scan(), include_drafts=True, select=True)
    return [audit_timing_branch(base_payload, scenario) for scenario in read_fixture_scenarios()]


def scenario_clusters(scenario: dict[str, Any]) -> dict[str, dict[str, Any]]:
    clusters = scenario.get("clusters") or {}
    return {str(key): value for key, value in clusters.items() if isinstance(value, dict)}


def audit_when_to_contact_rules() -> list[RuleAudit]:
    payload = read_json(WHEN_TO_CONTACT_FIXTURES_PATH)
    scenarios = [item for item in payload.get("scenarios") or [] if isinstance(item, dict)]
    structured_kb = load_structured_kb()
    audits: list[RuleAudit] = []
    selected_rule_ids: set[str] = set()
    for scenario in scenarios:
        scenario_id = str(scenario.get("id") or "unnamed")
        expected_rule_id = str(scenario.get("expectedRuleId") or "")
        rule = western_select_answer_rule({"main_question": "when-to-contact"}, scenario_clusters(scenario), structured_kb) or {}
        actual_rule_id = str(rule.get("id") or "")
        output = rule.get("output") or {}
        actual_because = tuple(str(item) for item in output.get("because_clusters") or [])
        expected_because = tuple(str(item) for item in scenario.get("expectedBecauseIncludes") or [])
        selected_rule_ids.add(actual_rule_id)
        errors: list[str] = []
        if actual_rule_id != expected_rule_id:
            errors.append(f"{scenario_id}: expected {expected_rule_id}, got {actual_rule_id}")
        missing_because = sorted(set(expected_because) - set(actual_because))
        if missing_because:
            errors.append(f"{scenario_id}: selected rule missing because clusters {missing_because}")
        if not output.get("short_answer") or not output.get("therefore"):
            errors.append(f"{scenario_id}: selected rule missing answer output")
        audits.append(
            RuleAudit(
                scenario_id=scenario_id,
                description=str(scenario.get("description") or ""),
                expected_rule_id=expected_rule_id,
                actual_rule_id=actual_rule_id,
                expected_because=expected_because,
                actual_because=actual_because,
                errors=errors,
            )
        )

    compiled_rule_ids = {
        str(rule.get("id") or "")
        for rule in (structured_kb.get("rulesByQuestion") or {}).get("when-to-contact", [])
        if isinstance(rule, dict) and rule.get("id")
    }
    missing_rules = sorted(compiled_rule_ids - selected_rule_ids)
    extra_rules = sorted(selected_rule_ids - compiled_rule_ids)
    if missing_rules or extra_rules:
        audits.append(
            RuleAudit(
                scenario_id="compiled-rule-coverage",
                description="Every compiled when-to-contact rule should have a deterministic fixture.",
                expected_rule_id=f"{len(compiled_rule_ids)} compiled rule(s)",
                actual_rule_id=f"{len(selected_rule_ids)} selected rule(s)",
                expected_because=(),
                actual_because=(),
                errors=[
                    *([f"missing rules: {', '.join(missing_rules)}"] if missing_rules else []),
                    *([f"extra rules: {', '.join(extra_rules)}"] if extra_rules else []),
                ],
            )
        )
    return audits


def branch_rows(audits: list[TimingBranchAudit]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for audit in audits:
        view_model = audit.view_model
        clusters = ((view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {})
        contact = clusters.get("timingContactReducer") or {}
        selected = contact.get("selectedTimingReducers") or []
        rows.append(
            [
                audit.scenario_id,
                "ok" if audit.ok else f"{len(audit.errors)} error(s)",
                audit.description,
                f"{contact.get('recommendedAction')} / {contact.get('contactMode')} / {contact.get('topBand')}",
                compact(str(item.get("category") or "") for item in selected if isinstance(item, dict)),
                f"support={contact.get('supportSignalCount')}, caution={contact.get('cautionSignalCount')}",
                compact(selector_summary(view_model), limit=5),
                timing_guidance_headline(view_model),
                compact(collect_claim_ids(contact), limit=5),
            ]
        )
    return rows


def rule_rows(audits: list[RuleAudit]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for audit in audits:
        rows.append(
            [
                audit.scenario_id,
                "ok" if audit.ok else f"{len(audit.errors)} error(s)",
                audit.description,
                audit.expected_rule_id,
                audit.actual_rule_id,
                compact(audit.expected_because, limit=5),
                compact(audit.actual_because, limit=6),
            ]
        )
    return rows


def build_report(branch_audits: list[TimingBranchAudit], rule_audits: list[RuleAudit]) -> str:
    errors = [error for audit in branch_audits for error in audit.errors]
    errors.extend(error for audit in rule_audits for error in audit.errors)
    branch_actions = sorted({str(((audit.view_model.get("westernRelationshipCaseFile") or {}).get("evidenceClusters") or {}).get("timingContactReducer", {}).get("recommendedAction") or "") for audit in branch_audits})
    lines = [
        "# Western Timing Reducer Branch Evidence",
        "",
        "Generated from `examples/timing/contact-reducer-action-scenarios.json`, `examples/timing/when-to-contact-rule-scenarios.json`, and the live Western result runtime.",
        "",
        "## Purpose",
        "",
        "This report proves the timing layer has branch-level coverage beyond the six paid examples, which currently skew Saturn-heavy. It locks the reducer behavior for missing scans, Mercury low-pressure message windows, Venus softening, mixed neutral observe windows, Mars activation caution, Saturn boundary pressure, and background observe-only scans.",
        "",
        "## Gate Result",
        "",
        "Status: " + ("PASS" if not errors else "FAIL"),
        "",
        md_table(
            ["Check", "Result"],
            [
                ["Timing reducer branch fixtures", f"{sum(1 for audit in branch_audits if audit.ok)}/{len(branch_audits)} passing"],
                ["Observed reducer actions", ", ".join(branch_actions)],
                ["When-to-contact rule fixtures", f"{sum(1 for audit in rule_audits if audit.ok)}/{len(rule_audits)} passing"],
                ["Precise timing policy", "public payload blocks exact dates and date ranges"],
            ],
        ),
        "",
        "## Timing Reducer Branch Matrix",
        "",
        md_table(
            [
                "Scenario",
                "Status",
                "Purpose",
                "Action / mode / band",
                "Selected categories",
                "Signal counts",
                "Selector states",
                "Visible timing headline",
                "Contact reducer claim ids",
            ],
            branch_rows(branch_audits),
        ),
        "",
        "## When-To-Contact Rule Priority Matrix",
        "",
        md_table(
            [
                "Scenario",
                "Status",
                "Purpose",
                "Expected rule",
                "Actual rule",
                "Expected because",
                "Actual because",
            ],
            rule_rows(rule_audits),
        ),
        "",
        "## Runtime Rule",
        "",
        "A timing branch is not allowed to become visible copy unless it passes three gates: the contact reducer state matches the fixture, `timingGuidance` mirrors that state in readable Traditional Chinese, and the public payload keeps precise dates unavailable. The when-to-contact answer rule matrix then decides whether timing is allowed to shape the final answer or is overridden by contact boundaries, emotional safety, pressure, or precision limits.",
        "",
    ]
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Western timing reducer branch evidence report.")
    parser.add_argument("--out", default=str(DEFAULT_REPORT_PATH), help="Output markdown path.")
    parser.add_argument("--check", action="store_true", help="Validate without writing and fail if the report is stale.")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    branch_audits = audit_timing_branches()
    rule_audits = audit_when_to_contact_rules()
    report = build_report(branch_audits, rule_audits)
    errors_present = "Status: FAIL" in report
    if args.check:
        if errors_present:
            print(report)
            return 1
        if not out_path.exists():
            print(f"Missing timing reducer branch evidence report: {out_path.relative_to(ROOT)}")
            return 1
        if out_path.read_text(encoding="utf-8") != report:
            print(f"Timing reducer branch evidence report is stale: {out_path.relative_to(ROOT)}")
            return 1
        print("Western timing reducer branch evidence report passed")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    if errors_present:
        print(f"Wrote failing timing reducer branch evidence report -> {out_path.relative_to(ROOT)}")
        return 1
    print(f"Wrote timing reducer branch evidence report -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
