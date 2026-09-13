#!/usr/bin/env python3
"""Fresh-chart regression gate for evidence, decision collapse, and contact safety."""

from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path

from build_reading_production_baseline import build_runtime_case, deterministic_pairs, reading_for_pair, stable_hash, visible_sections
from complete_relationship_result_runtime import DEFAULT_ARTICLES_PATH, DEFAULT_CLAIMS_PATH, load_articles, load_claims_by_article, relationship_case_model_repair_lever
from readable_interpretation.decision_zh_tw_catalog import action_decision, decision_catalog_errors
from readable_interpretation.final_narrative_chinese_quality import validate_hard_native_zh_tw_section
from readable_interpretation.final_narrative_fact_contract import bind_facts_to_source, source_spec_fingerprint, validate_fact_section
from readable_interpretation.final_narrative_semantic_domains import QUESTION_KEYS, RELATIONSHIP_DYNAMIC_KEYS
from readable_interpretation.final_narrative_pages.action_direction_renderer import ACTION_MODE_FORMS
from readable_interpretation.section_narrative_spec import timing_window_fact_key
from structured_runtime import load_structured_kb
from test_reading_phase5_calibration import semantic_correspondence_errors
from verify_final_narrative_phase4_semantic_coverage import exhaustive_value_domain_check, render_synthetic


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def decision_checks() -> int:
    require(not decision_catalog_errors(), "decision catalog coverage incomplete")
    count = 0
    for question, mode in ((question, mode) for question in QUESTION_KEYS for mode in ACTION_MODE_FORMS):
        outputs = set()
        for repair in (*RELATIONSHIP_DYNAMIC_KEYS, "unknown"):
            values = {
                "question": [question], "contact-status": ["blocked" if mode == "boundary-only" else "occasional-contact"],
                "action-purpose": [mode], "action-mode": [mode], "completion-boundary": [mode],
                "repair-lever": [repair], "stop-condition": ["standard"],
                "contact-posture": ["boundary-first" if mode == "boundary-only" else "test-low-pressure"],
                "blocked-action": ["repeated-messages"],
            }
            rendered, _ = render_synthetic("action-direction", values)
            validate_hard_native_zh_tw_section("action-direction", rendered)
            outputs.add(stable_hash(rendered))
            count += 1
        expected = 1 if mode in {"boundary-only", "shared-space-boundary"} else len(RELATIONSHIP_DYNAMIC_KEYS) + 1
        require(len(outputs) == expected, f"repair meanings collapsed in {mode}: {len(outputs)} != {expected}")
    for values in (("unsupported", "saturn-pressure", "stay-or-let-go"), ("boundary-only", "unknown", "unsupported"), ("small-bid-response-led", "unsupported", "any-chance")):
        try:
            action_decision(*values)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsupported decision accepted: {values}")
    for repair in (*RELATIONSHIP_DYNAMIC_KEYS, "unknown"):
        open_decision = action_decision("small-bid-response-led", repair)
        tone_decision = action_decision("tone-repair-in-existing-channel", repair)
        require(open_decision[0] != tone_decision[0], "tone repair lost its distinct purpose")
        for question in ("stay-or-let-go", "what-did-i-do-wrong"):
            require(action_decision("small-bid-response-led", repair, question) == action_decision("tone-repair-in-existing-channel", repair, question), "private reflection incorrectly encourages tone-repair contact")
    primary = {"key": "saturn_pressure", "score": 0.9, "evidenceIds": ["saturn"]}
    secondary = {"key": "communication_repair", "score": 0.3, "role": "repairLever", "evidenceIds": ["mercury"]}
    selected = relationship_case_model_repair_lever(primary_dynamic=primary, secondary_dynamics=[secondary], thesis={})
    require(selected["key"] == "saturn_pressure", "communication role overrode stronger evidence")
    secondary["score"] = 1.1
    selected = relationship_case_model_repair_lever(primary_dynamic=primary, secondary_dynamics=[secondary], thesis={})
    require(selected["key"] == "communication_repair", "repair ranking ignores evidence score")
    return count


def exact_evidence_checks(vm: dict) -> int:
    bundle = vm["sectionNarrativeSpecs"]
    failures = 0
    for section_id in ("relationship-fit", "core-answer"):
        spec = copy.deepcopy(bundle["sections"][section_id])
        section = copy.deepcopy(bundle["finalNarrativeFacts"]["sections"][section_id])
        facts = section["facts"]
        fact = next(item for item in facts if item["role"] in {"attraction-signal", "evidence-signal"})
        selected = next(item for item in spec["evidence"] if item["id"] in fact["evidenceIds"])
        require(selected.get("signalKey") == fact["valueKey"], "selected aspect lacks exact binding")
        original_identity = selected["calculationIdentity"]
        selected["calculationIdentity"] = {**original_identity, "orb": 99}
        require(validate_fact_section(section, spec)["status"] == "invalid", "stale calculation fingerprint accepted")
        failures += 1
        selected["calculationIdentity"] = original_identity
        selected["calculationIdentity"] = {**original_identity, "personAPoint": "unsupported"}
        bind_facts_to_source(facts, spec)
        section["sourceSpecFingerprint"] = source_spec_fingerprint(spec)
        require(validate_fact_section(section, spec)["status"] == "invalid", "rehashed wrong planet accepted")
        failures += 1
        selected["calculationIdentity"] = original_identity
        selected["signalKey"] = "unrelated-aspect"
        # Recomputing hashes must not make a semantically unrelated record valid.
        bind_facts_to_source(facts, spec)
        section["sourceSpecFingerprint"] = source_spec_fingerprint(spec)
        require(validate_fact_section(section, spec)["status"] == "invalid", "rehashed unrelated aspect evidence accepted")
        failures += 1
        selected.pop("signalKey")
        bind_facts_to_source(facts, spec)
        section["sourceSpecFingerprint"] = source_spec_fingerprint(spec)
        require(validate_fact_section(section, spec)["status"] == "invalid", "aggregate-only aspect evidence accepted")
        failures += 1
    return failures


def calibration_checks(vm: dict) -> None:
    facts = vm["sectionNarrativeSpecs"]["finalNarrativeFacts"]["sections"]
    case = {"sections": visible_sections(vm), "finalFactContract": {"sections": {}}}
    for section_id, section in facts.items():
        values = defaultdict(list)
        for fact in section["facts"]:
            values[fact["role"]].append(fact["valueKey"])
        case["finalFactContract"]["sections"][section_id] = {
            "roleValues": dict(values), "sourceSpecFingerprint": section["sourceSpecFingerprint"],
        }
        errors = semantic_correspondence_errors(case, section_id)
        require(not errors, f"valid paragraph rejected by correspondence check: {section_id}: {errors}")
    poisoned = copy.deepcopy(case)
    poisoned["sections"]["core-answer"]["body"] = "安全感、安心、表達、壓力、需要、回應、反應、互動、行動。"
    require(bool(semantic_correspondence_errors(poisoned, "core-answer")), "keyword stuffing passes semantic correspondence")
    poisoned = copy.deepcopy(case)
    current = poisoned["finalFactContract"]["sections"]["action-direction"]["roleValues"]["repair-lever"][0]
    replacement = next(value for value in RELATIONSHIP_DYNAMIC_KEYS if value != current)
    poisoned["finalFactContract"]["sections"]["action-direction"]["roleValues"]["repair-lever"] = [replacement]
    require(bool(semantic_correspondence_errors(poisoned, "action-direction")), "approved action for another repair target accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=40)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--audit-baseline-context", action="store_true", help="Use the exact September audit context for before/after comparison.")
    args = parser.parse_args()
    require(args.pairs >= 12, "use at least 12 independent chart pairs")
    checked = exhaustive_value_domain_check()
    action_combinations = decision_checks()
    articles, claims, kb = load_articles(DEFAULT_ARTICLES_PATH), load_claims_by_article(DEFAULT_CLAIMS_PATH), load_structured_kb()
    context = {
        "relationship_stage": "broke-up-recent", "main_question": "any-chance",
        "contact_status": "occasional-contact", "emotional_risk": "not-collected",
        "desired_outcome": "decide", "analysis_datetime": "2026-09-13T12:00:00+08:00",
        "analysis_timezone": "Asia/Taipei", "timing_scan_days": 56, "timing_scan_step_days": 7,
    }
    if args.audit_baseline_context:
        context.pop("analysis_datetime")
        context.pop("analysis_timezone")
        context.update(emotional_risk="calm", analysis_date="2026-09-13")
    records, action_groups = [], defaultdict(set)
    baseline, baseline_input = None, None
    for index, pair in enumerate(deterministic_pairs(args.pairs)):
        reading = reading_for_pair(reading_id=f"architecture-{index + 1}", pair=pair, context=copy.deepcopy(context), mix_unknown_times=False, record_index=index)
        _, vm = build_runtime_case(reading, articles=articles, claims=claims, structured_kb=kb)
        if baseline is None:
            baseline, baseline_input = vm, reading
        sections = visible_sections(vm)
        repair = vm["relationshipCaseModel"]["repairLever"]["key"]
        action_groups[stable_hash(sections["action-direction"])].add(repair)
        records.append({"id": reading["reading_id"], "repair": repair, "sections": sections})
        if (index + 1) % 10 == 0:
            print(f"Verified {index + 1}/{args.pairs} fresh chart pairs", flush=True)
    require(len(action_groups) > 1, "all fresh charts still have one action")
    require(all(len(keys) == 1 for keys in action_groups.values()), "different repair targets collapse into the same action")
    rejected = exact_evidence_checks(baseline)
    calibration_checks(baseline)
    blocked_input = copy.deepcopy(baseline_input)
    blocked_input["context"]["contact_status"] = "blocked"
    _, blocked = build_runtime_case(blocked_input, articles=articles, claims=claims, structured_kb=kb)
    timing = visible_sections(blocked)["timing-reading"]
    require("若他主動恢復聯絡" in timing["body"] or "沒有足夠資料" in timing["body"], "blocked window suggests unpermitted contact")
    require("不要" in timing["body"] and "不主動聯絡" in timing["nextMove"], "blocked timing boundary incomplete")
    windows = baseline["relationshipTurningWindows"]["items"]
    for window in windows:
        poisoned = {**window, "title": "隨便改寫的標題", "periodLabel": "不是日期"}
        require(timing_window_fact_key(window) == timing_window_fact_key(poisoned), "timing meaning depends on Chinese labels")
    report = {
        "status": "pass", "freshChartPairs": args.pairs, "actionCombinations": action_combinations,
        "rejectedInvalidEvidenceCases": rejected, "testedRoles": checked["testedRoleCount"],
        "testedValues": checked["testedValueCount"], "distinctActionDecisions": len(action_groups),
        "distinctPages": {key: len({stable_hash(record["sections"][key]) for record in records}) for key in records[0]["sections"]},
        "humanAcceptance": "pending", "records": records,
        "contextProfile": "september-audit" if args.audit_baseline_context else "production-shaped-reduced-scan",
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
