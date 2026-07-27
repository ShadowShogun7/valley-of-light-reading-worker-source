#!/usr/bin/env python3
"""Verify Phase 1 section narrative ownership contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    build_view_model,
    load_articles,
    load_claims_by_article,
    read_json,
)
from readable_interpretation.section_narrative_spec import (  # noqa: E402
    SECTION_NARRATIVE_IDS,
    SECTION_NARRATIVE_POLICIES,
    SECTION_NARRATIVE_RENDERER_VERSION,
    SECTION_NARRATIVE_SPEC_VERSION,
    validate_section_narrative_specs,
)
from relationship_status_answer_policy import STAGE_ORDER, STATUS_POLICIES  # noqa: E402
from structured_runtime import load_structured_kb  # noqa: E402
from visible_reading_depth import READING_PATHS, build_view_models  # noqa: E402


BASE_READING_PATH = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
QUESTIONS = tuple((STATUS_POLICIES[STAGE_ORDER[0]].get("questionRewrites") or {}).keys())
CONTACTS = ("blocked", "no-contact", "occasional-contact", "still-in-contact", "living-or-working-together")
VISIBLE_COPY_FIELDS = {"headline", "meaning", "body", "nextMove", "caution", "stuckPattern"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def section_specs(view_model: dict[str, Any]) -> dict[str, Any]:
    bundle = view_model.get("sectionNarrativeSpecs") if isinstance(view_model.get("sectionNarrativeSpecs"), dict) else {}
    require(bundle.get("version") == SECTION_NARRATIVE_SPEC_VERSION, "section spec version missing")
    require(bundle.get("rendererConsumesSpecs") is True, "Phase 2 renderer must consume section specs")
    require(bundle.get("rendererVersion") == SECTION_NARRATIVE_RENDERER_VERSION, "section renderer version missing")
    require((bundle.get("validation") or {}).get("status") == "valid", f"section bundle invalid: {bundle.get('validation')}")
    specs = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    require(set(specs) == set(SECTION_NARRATIVE_IDS), f"section set mismatch: {sorted(specs)}")
    return specs


def ownership_fingerprint(spec: dict[str, Any]) -> str:
    evidence = [
        {
            "id": item.get("id"),
            "domain": item.get("domain"),
            "conceptKey": item.get("conceptKey"),
            "source": item.get("source"),
            "sourceClaimIds": item.get("sourceClaimIds") or [],
            "methodClaimIds": item.get("methodClaimIds") or [],
            "evidenceClusterKeys": item.get("evidenceClusterKeys") or [],
        }
        for item in spec.get("evidence") or []
        if isinstance(item, dict)
    ]
    return stable_hash(
        {
            "sectionId": spec.get("sectionId"),
            "context": spec.get("context") or {},
            "semanticSlots": spec.get("semanticSlots") or {},
            "conceptKeys": spec.get("conceptKeys") or [],
            "evidence": evidence,
        }
    )


def visible_section_fingerprint(view_model: dict[str, Any], section_id: str) -> str:
    section = (((view_model.get("finalInterpretation") or {}).get("sections") or {}).get(section_id) or {})
    return stable_hash({key: str(section.get(key) or "") for key in VISIBLE_COPY_FIELDS})


def assert_bundle_contract(view_model: dict[str, Any]) -> None:
    specs = section_specs(view_model)
    aggregate = validate_section_narrative_specs(specs)
    require(aggregate.get("status") == "valid", f"aggregate validation failed: {aggregate}")
    for section_id, spec in specs.items():
        require(not (VISIBLE_COPY_FIELDS & set(spec)), f"{section_id}: visible copy fields leaked into semantic contract")
        require((spec.get("validation") or {}).get("status") == "valid", f"{section_id}: invalid contract")
        policy = SECTION_NARRATIVE_POLICIES[section_id]
        allowed_domains = set(policy.get("allowedEvidenceDomains") or ())
        actual_domains = {str(item.get("domain") or "") for item in spec.get("evidence") or [] if isinstance(item, dict)}
        require(actual_domains <= allowed_domains, f"{section_id}: evidence domains escaped ownership: {actual_domains - allowed_domains}")
    require(not (specs["chart-positioning"].get("context") or {}), "chart-positioning must be context-free")
    require(not (specs["relationship-fit"].get("context") or {}), "relationship-fit must be context-free")


def assert_existing_readings() -> None:
    view_models = build_view_models(READING_PATHS)
    require(len(view_models) >= 10, "expected representative reading fixtures")
    for view_model in view_models:
        assert_bundle_contract(view_model)


def assert_context_ownership_matrix() -> None:
    base_fixture = read_json(BASE_READING_PATH)
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    chart_fingerprints: set[str] = set()
    fit_fingerprints: set[str] = set()
    chart_visible_fingerprints: set[str] = set()
    fit_visible_fingerprints: set[str] = set()
    generated = 0

    for stage in STAGE_ORDER:
        for question in QUESTIONS:
            for contact in CONTACTS:
                fixture = copy.deepcopy(base_fixture)
                fixture["reading_id"] = f"section-spec-{stage}-{question}-{contact}"
                context = fixture.setdefault("context", {})
                context["relationship_stage"] = stage
                context["main_question"] = question
                context["contact_status"] = contact
                context["emotional_risk"] = "calm"
                view_model = build_view_model(fixture, articles, claims, structured_kb)
                assert_bundle_contract(view_model)
                specs = section_specs(view_model)
                chart_fingerprints.add(ownership_fingerprint(specs["chart-positioning"]))
                fit_fingerprints.add(ownership_fingerprint(specs["relationship-fit"]))
                chart_visible_fingerprints.add(visible_section_fingerprint(view_model, "chart-positioning"))
                fit_visible_fingerprints.add(visible_section_fingerprint(view_model, "relationship-fit"))
                for section_id in ("core-answer", "timing-reading", "action-direction"):
                    spec_context = specs[section_id].get("context") or {}
                    require(spec_context.get("stageKey") == stage, f"{section_id}: stage context mismatch")
                    require(spec_context.get("questionKey") == question, f"{section_id}: question context mismatch")
                    require(spec_context.get("contactKey") == contact, f"{section_id}: contact context mismatch")
                generated += 1

    require(generated == len(STAGE_ORDER) * len(QUESTIONS) * len(CONTACTS), "context matrix count mismatch")
    require(len(chart_fingerprints) == 1, f"chart-positioning changed across context: {len(chart_fingerprints)} specs")
    require(len(fit_fingerprints) == 1, f"relationship-fit changed across context: {len(fit_fingerprints)} specs")
    require(len(chart_visible_fingerprints) == 1, f"chart-positioning visible copy changed across context: {len(chart_visible_fingerprints)}")
    require(len(fit_visible_fingerprints) == 1, f"relationship-fit visible copy changed across context: {len(fit_visible_fingerprints)}")


def main() -> int:
    assert_existing_readings()
    assert_context_ownership_matrix()
    print("Section narrative spec smoke passed.")
    print(f"- existing readings: {len(READING_PATHS)}")
    print(f"- ownership matrix: {len(STAGE_ORDER) * len(QUESTIONS) * len(CONTACTS)} combinations")
    print("- chart-positioning and relationship-fit specs and visible copy are context-invariant")
    print("- visible renderer consumes validated section-owned specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
