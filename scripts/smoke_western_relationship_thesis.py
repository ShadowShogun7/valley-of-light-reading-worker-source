#!/usr/bin/env python3
"""Smoke-test the paid Western relationship thesis layer."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
)
from visible_reading_depth import READING_PATHS, build_view_models  # noqa: E402


ARTICLES = load_articles(DEFAULT_ARTICLES_PATH)
CLAIMS_BY_ARTICLE = load_claims_by_article(DEFAULT_CLAIMS_PATH)

REQUIRED_THESIS_FIELDS = (
    "questionReframe",
    "centralThesis",
    "dominantTension",
    "interactionLoop",
    "currentActivation",
    "observableSigns",
    "changeCondition",
    "decisionBoundary",
    "uncertainty",
    "evidencePacket",
    "candidateDynamics",
    "selectedCandidateId",
    "evidenceMap",
    "prohibitedConclusions",
    "validation",
)

REQUIRED_LOOP_FIELDS = (
    "userTrigger",
    "userResponse",
    "partnerTrigger",
    "partnerResponse",
    "reinforcingEffect",
)

REQUIRED_TENSION_FIELDS = (
    "poleA",
    "poleB",
    "currentPattern",
    "desiredShift",
)

MIND_READING_TERMS = (
    "愛你",
    "不愛你",
    "心裡",
    "想復合",
    "想放下",
    "還在乎你",
)

INTERNAL_VISIBLE_TERMS = (
    "relationshipThesis",
    "evidencePacket",
    "candidateDynamics",
    "selectedCandidateId",
    "centralDynamicKey",
)

DYNAMIC_VISIBLE_MARKERS = {
    "emotional_safety": ("安全感", "情緒", "不安", "安心", "接住"),
    "saturn_pressure": ("承諾", "責任", "界線", "壓力", "變重"),
    "communication_repair": ("訊息", "開口", "說法", "接話", "對話"),
    "attraction_pursuit": ("吸引", "火花", "靠近", "熱絡", "延續"),
    "action_conflict": ("氣氛", "變硬", "衝突", "爭", "急"),
    "identity_rhythm": ("尊重", "台階", "自尊", "面子", "被看見"),
    "outer_intensity": ("強烈", "現實", "界線", "感覺", "行動"),
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def thesis_from_view_model(view_model: dict[str, Any]) -> dict[str, Any]:
    case_file = view_model.get("westernRelationshipCaseFile") or {}
    thesis = view_model.get("relationshipThesis") or case_file.get("relationshipThesis") or {}
    assert_true(thesis.get("version") == "relationship-thesis-v1", f"{view_model.get('id')}: thesis version missing")
    assert_true(thesis == case_file.get("relationshipThesis"), f"{view_model.get('id')}: case-file thesis mismatch")
    return thesis


def field_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def visible_final_text(final: dict[str, Any]) -> str:
    pieces: list[str] = []
    for section in (final.get("sections") or {}).values():
        if not isinstance(section, dict):
            continue
        for field in ("headline", "meaning", "body", "nextMove", "caution"):
            if section.get(field):
                pieces.append(str(section.get(field) or ""))
    return "\n".join(pieces)


def assert_evidence_packet(label: str, thesis: dict[str, Any]) -> None:
    packet = thesis.get("evidencePacket") or []
    assert_true(len(packet) >= 4, f"{label}: evidence packet too thin")
    domains = {str(item.get("domain") or "") for item in packet}
    assert_true(len(domains) >= 2, f"{label}: thesis has fewer than two evidence domains")
    assert_true("relationshipContext" in domains, f"{label}: context evidence missing")
    assert_true("synastry" in domains, f"{label}: synastry evidence missing")
    assert_true("partnerNatal" in domains, f"{label}: partner evidence missing")
    for item in packet:
        evidence_id = str(item.get("id") or "")
        assert_true(evidence_id, f"{label}: evidence id missing")
        assert_true(item.get("proposition"), f"{label}: evidence proposition missing: {evidence_id}")
        assert_true(item.get("allowedInference"), f"{label}: allowed inference missing: {evidence_id}")
        assert_true(item.get("prohibitedInference"), f"{label}: prohibited inference missing: {evidence_id}")
        assert_true(0 <= float(item.get("relevance") or -1) <= 1, f"{label}: invalid relevance: {evidence_id}")
        assert_true(0 <= float(item.get("confidence") or -1) <= 1, f"{label}: invalid confidence: {evidence_id}")


def assert_thesis_schema(view_model: dict[str, Any]) -> None:
    label = str(view_model.get("id") or "unknown")
    thesis = thesis_from_view_model(view_model)
    for field in REQUIRED_THESIS_FIELDS:
        assert_true(field in thesis, f"{label}: thesis field missing: {field}")
    tension = thesis.get("dominantTension") or {}
    for field in REQUIRED_TENSION_FIELDS:
        assert_true(tension.get(field), f"{label}: tension field missing: {field}")
    loop = thesis.get("interactionLoop") or {}
    for field in REQUIRED_LOOP_FIELDS:
        assert_true(loop.get(field), f"{label}: loop field missing: {field}")
    assert_evidence_packet(label, thesis)

    signs = thesis.get("observableSigns") or []
    assert_true(len(signs) >= 2, f"{label}: too few observable signs")
    for sign in signs:
        behavior = str(sign.get("behavior") or "")
        assert_true(behavior, f"{label}: observable sign behavior missing")
        assert_true(not any(term in behavior for term in MIND_READING_TERMS), f"{label}: observable sign is mind-reading: {behavior}")
        assert_true(sign.get("valence") in {"supportive", "caution", "ambiguous"}, f"{label}: invalid observable sign valence")

    change = thesis.get("changeCondition") or {}
    assert_true(change.get("strengthensReadingWhen"), f"{label}: confirming change condition missing")
    assert_true(change.get("weakensReadingWhen"), f"{label}: disconfirming change condition missing")
    boundary = thesis.get("decisionBoundary") or {}
    assert_true(boundary.get("continueWhen"), f"{label}: continue boundary missing")
    assert_true(boundary.get("stepBackWhen"), f"{label}: step-back boundary missing")
    validation = thesis.get("validation") or {}
    assert_true(validation.get("passed") is True, f"{label}: thesis validation failed: {validation.get('failures')}")

    final_text = visible_final_text(view_model.get("finalInterpretation") or {})
    assert_true("relationshipThesis" in field_text(view_model), f"{label}: hidden thesis absent from public payload")
    for term in INTERNAL_VISIBLE_TERMS:
        assert_true(term not in final_text, f"{label}: internal thesis term leaked into final copy: {term}")
    dynamic_key = str(thesis.get("centralDynamicKey") or "")
    dynamic_markers = DYNAMIC_VISIBLE_MARKERS.get(dynamic_key) or ()
    assert_true(
        any(marker in final_text for marker in dynamic_markers),
        f"{label}: final interpretation does not reflect central dynamic: {dynamic_key}",
    )


def build_counterfactual_view_model(reading_path: Path, contact_status: str) -> dict[str, Any]:
    reading = copy.deepcopy(read_json(reading_path))
    reading["reading_id"] = f"{reading.get('reading_id')}-contact-{contact_status}"
    reading.setdefault("context", {})["contact_status"] = contact_status
    payload = build_payload(reading, include_drafts=True, select=True)
    return build_view_model(payload, ARTICLES, CLAIMS_BY_ARTICLE)


def assert_contact_counterfactual_sensitivity() -> None:
    reading_path = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
    statuses = ["blocked", "no-contact", "still-in-contact", "living-or-working-together"]
    theses = [thesis_from_view_model(build_counterfactual_view_model(reading_path, status)) for status in statuses]
    patterns = {str((thesis.get("dominantTension") or {}).get("currentPattern") or "") for thesis in theses}
    activations = {str(thesis.get("currentActivation") or "") for thesis in theses}
    signs = {field_text([item.get("behavior") for item in thesis.get("observableSigns") or []]) for thesis in theses}
    boundaries = {field_text(thesis.get("decisionBoundary") or {}) for thesis in theses}
    assert_true(len(patterns) >= 3, f"counterfactual currentPattern variation too low: {patterns}")
    assert_true(len(activations) == len(statuses), "counterfactual currentActivation did not vary by contact status")
    assert_true(len(signs) >= 3, "counterfactual observable signs did not vary enough")
    assert_true(len(boundaries) >= 3, "counterfactual decision boundaries did not vary enough")


def thesis_fits_case(source_thesis: dict[str, Any], target_thesis: dict[str, Any]) -> bool:
    return (
        source_thesis.get("centralDynamicKey") == target_thesis.get("centralDynamicKey")
        and (source_thesis.get("dominantTension") or {}).get("currentPattern")
        == (target_thesis.get("dominantTension") or {}).get("currentPattern")
    )


def assert_thesis_swap_rejection(view_models: list[dict[str, Any]]) -> None:
    theses = [thesis_from_view_model(view_model) for view_model in view_models]
    for left in theses:
        for right in theses:
            if left is right:
                continue
            if left.get("centralDynamicKey") != right.get("centralDynamicKey"):
                assert_true(not thesis_fits_case(left, right), "thesis swap unexpectedly fit a different case")
                return
    raise AssertionError("thesis swap test could not find two distinct thesis dynamics")


def main() -> int:
    view_models = build_view_models(READING_PATHS)
    failures: list[str] = []
    for view_model in view_models:
        try:
            assert_thesis_schema(view_model)
        except AssertionError as exc:
            failures.append(str(exc))
    try:
        assert_contact_counterfactual_sensitivity()
    except AssertionError as exc:
        failures.append(str(exc))
    try:
        assert_thesis_swap_rejection(view_models)
    except AssertionError as exc:
        failures.append(str(exc))

    if failures:
        print("Western relationship thesis smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    dynamics = sorted({str(thesis_from_view_model(view_model).get("centralDynamicKey") or "") for view_model in view_models})
    print("Western relationship thesis smoke passed")
    print(f"- validated scenarios: {len(view_models)}")
    print(f"- thesis dynamics: {', '.join(dynamics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
