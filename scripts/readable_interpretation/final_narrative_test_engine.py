"""Semantic test-engine primitives for the final narrative layer."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Iterable, Mapping

from .final_narrative_composition import SECTION_COMPOSITION_RULES
from .final_narrative_fact_contract import FINAL_NARRATIVE_FACT_POLICIES
from .final_narrative_page_grammar import PAGE_GRAMMARS, VISIBLE_FIELDS
from .final_narrative_paragraph_plan import (
    FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
    PAGE_BLUEPRINTS,
)
from .final_narrative_semantic_coverage import FINAL_NARRATIVE_ROLE_DISPOSITIONS
from .final_narrative_story_arc import (
    FINAL_NARRATIVE_ROLE_PRESENTATIONS,
    FINAL_NARRATIVE_STORY_ARC_VERSION,
    STORY_CHAPTERS,
    visible_roles,
)
from .final_narrative_semantic_domains import is_unknown_signal, parse_relationship_signal
from .section_narrative_spec import SECTION_NARRATIVE_IDS


FINAL_NARRATIVE_TEST_ENGINE_VERSION = "final-narrative-test-engine-v4"
FINAL_NARRATIVE_CANONICAL_RECORD_VERSION = "final-narrative-canonical-record-v1"
SIGNAL_ROLES = {"attraction-signal", "friction-signal", "growth-signal", "evidence-signal"}
CONTEXT_ROLES = {"question", "relationship-stage", "contact-status"}


def stable_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def visible_sections(view_model: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    final = view_model.get("finalInterpretation") if isinstance(view_model.get("finalInterpretation"), dict) else {}
    sections = final.get("sections") if isinstance(final.get("sections"), dict) else {}
    return {
        section_id: {
            field: str((sections.get(section_id) or {}).get(field) or "")
            for field in VISIBLE_FIELDS
        }
        for section_id in SECTION_NARRATIVE_IDS
    }


def chart_evidence(calculation_payload: Mapping[str, Any]) -> dict[str, Any]:
    western = calculation_payload.get("western") if isinstance(calculation_payload.get("western"), dict) else {}
    people = western.get("people") if isinstance(western.get("people"), dict) else {}
    synastry = western.get("synastry") if isinstance(western.get("synastry"), dict) else {}
    return {
        "people": {
            person_id: {
                "objects": copy.deepcopy((people.get(person_id) or {}).get("objects") or {}),
                "birthPrecision": str((people.get(person_id) or {}).get("birth_precision") or ""),
            }
            for person_id in ("person_a", "person_b")
        },
        "interAspects": copy.deepcopy(synastry.get("inter_aspects") or []),
    }


def contract_registry_payload() -> dict[str, Any]:
    return {
        "paragraphPlanVersion": FINAL_NARRATIVE_PARAGRAPH_PLAN_VERSION,
        "paragraphBlueprints": copy.deepcopy(PAGE_BLUEPRINTS),
        "factPolicies": copy.deepcopy(FINAL_NARRATIVE_FACT_POLICIES),
        "roleDispositions": copy.deepcopy(FINAL_NARRATIVE_ROLE_DISPOSITIONS),
        "storyArcVersion": FINAL_NARRATIVE_STORY_ARC_VERSION,
        "storyChapters": {
            section_id: asdict(chapter)
            for section_id, chapter in STORY_CHAPTERS.items()
        },
        "rolePresentations": copy.deepcopy(FINAL_NARRATIVE_ROLE_PRESENTATIONS),
        "compositionRules": {
            section_id: asdict(rule)
            for section_id, rule in SECTION_COMPOSITION_RULES.items()
        },
        "pageGrammars": {
            section_id: asdict(grammar)
            for section_id, grammar in PAGE_GRAMMARS.items()
        },
    }


def role_values_from_facts(facts: Iterable[Mapping[str, Any]]) -> dict[str, list[str]]:
    values: dict[str, set[str]] = defaultdict(set)
    for fact in facts:
        role = str(fact.get("role") or "")
        value = str(fact.get("valueKey") or "")
        if role and value:
            values[role].add(value)
    return {role: sorted(items) for role, items in sorted(values.items())}


def visible_value_projection(role: str, value: str) -> str:
    if role not in SIGNAL_ROLES or is_unknown_signal(value):
        return value
    try:
        signal = parse_relationship_signal(value)
    except ValueError:
        return value
    if role == "evidence-signal":
        return (
            f"{signal.kind}:{signal.actor_person}:{signal.actor_planet}>"
            f"{signal.receiver_person}:{signal.receiver_planet}"
        )
    if role == "growth-signal":
        # Growth copy intentionally owns the pair and acting person. Aspect and
        # planet order remain evidence details unless a future renderer exposes them.
        return f"{signal.kind}:{signal.pair_key}:{signal.actor_person}"
    return signal.raw


def role_projection(
    section_id: str,
    role_values: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    return {
        "sectionId": section_id,
        "roles": {
            role: sorted({visible_value_projection(role, str(value)) for value in values})
            for role, values in sorted(role_values.items())
        },
    }


def visible_role_projection(
    section_id: str,
    role_values: Mapping[str, Iterable[str]],
) -> dict[str, Any]:
    presentations = FINAL_NARRATIVE_ROLE_PRESENTATIONS.get(section_id) or {}
    owned = {
        role
        for role, presentation in presentations.items()
        if presentation != "hidden-support"
    }
    return role_projection(
        section_id,
        {role: values for role, values in role_values.items() if role in owned},
    )


def concept_projection(section_contract: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        "conceptKeys": sorted(
            {str(value) for value in section_contract.get("conceptKeys") or [] if str(value or "").strip()}
        ),
        "evidenceConceptKeys": sorted(
            {
                str(value)
                for value in section_contract.get("evidenceConceptKeys") or []
                if str(value or "").strip()
            }
        ),
    }


def canonical_fingerprints(record: Mapping[str, Any]) -> dict[str, Any]:
    evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
    evidence_sections = evidence.get("sections") if isinstance(evidence.get("sections"), dict) else {}
    facts = record.get("facts") if isinstance(record.get("facts"), dict) else {}
    fact_sections = facts.get("sections") if isinstance(facts.get("sections"), dict) else {}
    outputs = record.get("outputs") if isinstance(record.get("outputs"), dict) else {}
    output_sections = outputs.get("sections") if isinstance(outputs.get("sections"), dict) else {}
    section_fingerprints: dict[str, Any] = {}
    for section_id in SECTION_NARRATIVE_IDS:
        evidence_section = evidence_sections.get(section_id) or {}
        fact_section = fact_sections.get(section_id) or {}
        output_section = output_sections.get(section_id) or {}
        role_values = role_values_from_facts(
            item for item in fact_section.get("facts") or [] if isinstance(item, dict)
        )
        concepts = {
            "conceptKeys": evidence_section.get("conceptKeys") or [],
            "evidenceConceptKeys": evidence_section.get("evidenceConceptKeys") or [],
        }
        section_fingerprints[section_id] = {
            "evidence": stable_hash(evidence_section),
            "facts": stable_hash(fact_section.get("facts") or []),
            "roleProjection": stable_hash(role_projection(section_id, role_values)),
            "conceptProjection": stable_hash(concept_projection(concepts)),
            "semanticMeaning": stable_hash(
                {
                    "roles": visible_role_projection(section_id, role_values),
                    "chapterProposition": STORY_CHAPTERS[section_id].proposition_key,
                }
            ),
            "output": stable_hash(output_section),
        }
    return {
        "inputs": stable_hash(record.get("inputs") or {}),
        "chart": stable_hash(evidence.get("chart") or {}),
        "evidence": stable_hash(evidence),
        "facts": stable_hash(facts),
        "outputs": stable_hash(output_sections),
        "contracts": stable_hash(contract_registry_payload()),
        "sections": section_fingerprints,
    }


def build_canonical_record(
    reading: Mapping[str, Any],
    calculation_payload: Mapping[str, Any],
    view_model: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = view_model.get("sectionNarrativeSpecs") if isinstance(view_model.get("sectionNarrativeSpecs"), dict) else {}
    specs = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    facts = bundle.get("finalNarrativeFacts") if isinstance(bundle.get("finalNarrativeFacts"), dict) else {}
    outputs = visible_sections(view_model)
    record: dict[str, Any] = {
        "version": FINAL_NARRATIVE_CANONICAL_RECORD_VERSION,
        "testEngineVersion": FINAL_NARRATIVE_TEST_ENGINE_VERSION,
        "id": str(reading.get("reading_id") or ""),
        "inputs": {
            "personA": copy.deepcopy(reading.get("person_a") or {}),
            "personB": copy.deepcopy(reading.get("person_b") or {}),
            "context": copy.deepcopy(reading.get("context") or {}),
        },
        "evidence": {
            "chart": chart_evidence(calculation_payload),
            "sections": {
                section_id: {
                    "context": copy.deepcopy((specs.get(section_id) or {}).get("context") or {}),
                    "semanticSlots": copy.deepcopy((specs.get(section_id) or {}).get("semanticSlots") or {}),
                    "conceptKeys": copy.deepcopy((specs.get(section_id) or {}).get("conceptKeys") or []),
                    "evidence": copy.deepcopy((specs.get(section_id) or {}).get("evidence") or []),
                    "evidenceConceptKeys": sorted(
                        {
                            str(item.get("conceptKey") or "")
                            for item in (specs.get(section_id) or {}).get("evidence") or []
                            if isinstance(item, dict) and item.get("conceptKey")
                        }
                    ),
                }
                for section_id in SECTION_NARRATIVE_IDS
            },
        },
        "facts": copy.deepcopy(facts),
        "outputs": {
            "version": str((view_model.get("finalInterpretation") or {}).get("version") or ""),
            "sections": outputs,
        },
    }
    record["fingerprints"] = canonical_fingerprints(record)
    return record


def validate_canonical_record(record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("version") != FINAL_NARRATIVE_CANONICAL_RECORD_VERSION:
        errors.append("canonical record version is stale")
    if record.get("testEngineVersion") != FINAL_NARRATIVE_TEST_ENGINE_VERSION:
        errors.append("canonical test-engine version is stale")
    facts = record.get("facts") if isinstance(record.get("facts"), dict) else {}
    outputs = record.get("outputs") if isinstance(record.get("outputs"), dict) else {}
    evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
    for label, sections in (
        ("fact", facts.get("sections") if isinstance(facts.get("sections"), dict) else {}),
        ("evidence", evidence.get("sections") if isinstance(evidence.get("sections"), dict) else {}),
        ("output", outputs.get("sections") if isinstance(outputs.get("sections"), dict) else {}),
    ):
        if set(sections) != set(SECTION_NARRATIVE_IDS):
            errors.append(f"canonical {label} section set is incomplete")
    expected = canonical_fingerprints(record)
    if record.get("fingerprints") != expected:
        errors.append("canonical fingerprints are stale")
    return errors


def compact_role_values(case: Mapping[str, Any], section_id: str) -> dict[str, list[str]]:
    fact_contract = case.get("finalFactContract") if isinstance(case.get("finalFactContract"), dict) else {}
    sections = fact_contract.get("sections") if isinstance(fact_contract.get("sections"), dict) else {}
    section = sections.get(section_id) if isinstance(sections.get(section_id), dict) else {}
    role_values = section.get("roleValues") if isinstance(section.get("roleValues"), dict) else {}
    return {
        str(role): sorted(str(value) for value in values)
        for role, values in role_values.items()
        if isinstance(values, list)
    }


def compact_semantic_projection(case: Mapping[str, Any], section_id: str) -> dict[str, Any]:
    role_values = compact_role_values(case, section_id)
    return {
        "roles": visible_role_projection(section_id, role_values),
        "chapterProposition": STORY_CHAPTERS[section_id].proposition_key,
    }


def analyze_output_collapses(cases: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    case_list = [case for case in cases if isinstance(case, Mapping)]
    unexplained: list[dict[str, Any]] = []
    explained: list[dict[str, Any]] = []
    unique_role_concept_signatures: dict[str, set[str]] = defaultdict(set)
    for section_id in SECTION_NARRATIVE_IDS:
        output_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for case in case_list:
            outputs = case.get("sections") if isinstance(case.get("sections"), dict) else {}
            section_output = outputs.get(section_id) or {}
            role_values = compact_role_values(case, section_id)
            raw_fact_identity = str(
                ((((case.get("finalFactContract") or {}).get("sections") or {}).get(section_id) or {}).get("factIdentity") or "")
            )
            role_identity = stable_hash(role_projection(section_id, role_values))
            semantic_projection = compact_semantic_projection(case, section_id)
            concept_identity = stable_hash(
                semantic_projection["chapterProposition"]
            )
            semantic_identity = stable_hash(semantic_projection)
            unique_role_concept_signatures[section_id].add(semantic_identity)
            output_groups[stable_hash(section_output)].append(
                {
                    "id": str(case.get("id") or ""),
                    "factIdentity": raw_fact_identity,
                    "roleProjection": role_identity,
                    "conceptProjection": concept_identity,
                    "semanticMeaning": semantic_identity,
                }
            )
        for output_identity, records in output_groups.items():
            raw_facts = {record["factIdentity"] for record in records}
            if len(records) <= 1:
                continue
            role_projections = {record["roleProjection"] for record in records}
            semantic_meanings = {record["semanticMeaning"] for record in records}
            collision = {
                "sectionId": section_id,
                "outputFingerprint": output_identity,
                "caseIds": [record["id"] for record in records],
                "rawFactCount": len(raw_facts),
                "roleProjectionCount": len(role_projections),
                "semanticMeaningCount": len(semantic_meanings),
            }
            if len(semantic_meanings) > 1:
                unexplained.append(collision)
            elif len(raw_facts) > 1:
                collision["reason"] = "raw evidence differences share one declared role-and-concept projection"
                explained.append(collision)

    full_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for case in case_list:
        full_groups[stable_hash(case.get("sections") or {})].append(case)
    full_unexplained = [
        [str(case.get("id") or "") for case in group]
        for group in full_groups.values()
        if len(group) > 1
        and len(
            {
                stable_hash(
                    {
                        section_id: compact_semantic_projection(case, section_id)
                        for section_id in SECTION_NARRATIVE_IDS
                    }
                )
                for case in group
            }
        ) > 1
    ]
    return {
        "caseCount": len(case_list),
        "unexplainedCollapses": unexplained,
        "explainedCollapses": explained,
        "fullReadingUnexplainedCollapses": full_unexplained,
        "uniqueRoleConceptSignatures": {
            section_id: len(values)
            for section_id, values in sorted(unique_role_concept_signatures.items())
        },
    }


def changed_sections(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    fingerprint_key: str,
) -> set[str]:
    left_sections = ((left.get("fingerprints") or {}).get("sections") or {})
    right_sections = ((right.get("fingerprints") or {}).get("sections") or {})
    return {
        section_id
        for section_id in SECTION_NARRATIVE_IDS
        if (left_sections.get(section_id) or {}).get(fingerprint_key)
        != (right_sections.get(section_id) or {}).get(fingerprint_key)
    }


__all__ = [
    "CONTEXT_ROLES",
    "FINAL_NARRATIVE_CANONICAL_RECORD_VERSION",
    "FINAL_NARRATIVE_TEST_ENGINE_VERSION",
    "analyze_output_collapses",
    "build_canonical_record",
    "canonical_fingerprints",
    "changed_sections",
    "compact_role_values",
    "compact_semantic_projection",
    "contract_registry_payload",
    "role_projection",
    "stable_hash",
    "validate_canonical_record",
    "visible_sections",
]
