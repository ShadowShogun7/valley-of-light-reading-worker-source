#!/usr/bin/env python3
"""Context-combo storyline smoke for final relationship narratives."""

from __future__ import annotations

import copy
import re
import sys
from collections import Counter
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
from readable_interpretation.zh_tw import sanitize_public_answer_text  # noqa: E402
from structured_runtime import load_structured_kb  # noqa: E402


BASE_READING_PATH = ROOT / "examples" / "readings" / "cold-war-still-love-me.json"
SECTION_IDS = ("chart-positioning", "relationship-fit", "core-answer", "timing-reading", "action-direction")
CONTEXT_INDEPENDENT_SECTION_IDS = ("chart-positioning", "relationship-fit")
VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
STAGES = ("cold-war", "broke-up-recent", "broke-up-long", "crisis", "ambiguous")
QUESTIONS = ("still-love-me", "any-chance", "when-to-contact", "what-did-i-do-wrong", "stay-or-let-go")
CONTACTS = ("blocked", "no-contact", "occasional-contact", "still-in-contact", "living-or-working-together")
PUBLIC_COMPARISON_REPLACEMENTS = (
    ("通道未斷", "還有零星聯絡"),
    ("通道受阻", "聯絡被擋住"),
    ("自然互動通道", "自然互動"),
    ("自然小通道", "自然小開口"),
    ("沒有自然通道", "沒有能自然開口的位置"),
    ("正常通道", "正常聯絡"),
    ("通道", "聯絡方式"),
)

FORBIDDEN_TERMS = (
    "冷戰 / 斷聯中",
    "剛分手 / 情緒未穩",
    "分手已久 / 距離拉開",
    "關係危機 / 還在拉扯",
    "曖昧 / 尚未定義",
    "你選的是",
    "你選的聯絡是",
    "stageLabel",
    "contactLabel",
    "判讀",
    "副動力",
    "承接度",
    "承接量",
    "可觀察",
    "通道未斷",
    "通道受阻",
    "壓力測試",
    "行動速度",
    "關係答案",
    "relationshipContextStoryline",
    "relationshipThesis",
    "relationshipCaseModel",
    "dynamicInteractionPlan",
)
REPEATED_TOPIC_TERMS = (
    "延續",
    "接下去",
    "接話",
    "接住",
    "回覆",
    "回應",
    "聊天",
    "聯絡",
    "開口",
    "下一步",
    "承諾",
    "責任",
    "自責",
    "沉默",
    "界線",
    "復合",
    "等待",
)
CONTACT_PROOF_CONCEPT_TERMS: dict[str, tuple[str, ...]] = {
    "occasional-contact": (
        "回覆後有沒有下一次自然延續",
        "回覆後的延續",
        "回覆能否變連續",
        "願意把話多往前帶",
        "零星回覆後先看有沒有下一次",
    ),
    "still-in-contact": (
        "自然延續",
        "主動延續",
        "自然接下去",
        "主動多接",
        "也把話接",
        "也會自然接",
        "聊天是否由他",
        "他會不會也接話",
    ),
}
PHRASE_SPLIT_PATTERN = re.compile(r"[。！？!?；;\n]+")


def normalize(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def normalize_public(value: Any) -> str:
    text = sanitize_public_answer_text(value)
    for old, new in PUBLIC_COMPARISON_REPLACEMENTS:
        text = text.replace(old, new)
    return normalize(text)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def final_sections(view_model: dict[str, Any]) -> dict[str, dict[str, str]]:
    sections = ((view_model.get("finalInterpretation") or {}).get("sections") or {})
    return {
        section_id: {
            field: str((sections.get(section_id) or {}).get(field) or "")
            for field in VISIBLE_FIELDS
        }
        for section_id in SECTION_IDS
    }


def section_text(view_model: dict[str, Any], section_id: str) -> str:
    fields = final_sections(view_model).get(section_id) or {}
    return "\n".join(str(fields.get(field) or "") for field in VISIBLE_FIELDS)


def section_fingerprint(view_model: dict[str, Any], section_id: str) -> str:
    return normalize(section_text(view_model, section_id))


def full_fingerprint(view_model: dict[str, Any]) -> str:
    return normalize("\n".join(section_text(view_model, section_id) for section_id in SECTION_IDS))


def topic_phrases(text: str) -> set[str]:
    phrases: set[str] = set()
    for sentence in PHRASE_SPLIT_PATTERN.split(text):
        normalized = normalize_public(sentence).strip("，,：:")
        if len(normalized) < 12:
            continue
        if any(term in normalized for term in REPEATED_TOPIC_TERMS):
            phrases.add(normalized)
    return phrases


def repeated_body_clauses(text: str) -> list[tuple[str, int]]:
    clauses = [
        normalize_public(item).strip("，,：:")
        for item in re.split(r"[。！？!?；;，,\n]+", text)
    ]
    counts = Counter(item for item in clauses if len(item) >= 10)
    return [(clause, count) for clause, count in counts.items() if count > 1]


def directive_values(storyline: dict[str, Any], section_id: str) -> list[str]:
    section = ((storyline.get("sectionDirectives") or {}).get(section_id) or {})
    values: list[str] = []
    for field in ("headline", "meaning", "bridge", "nextMove", "caution"):
        raw = sanitize_public_answer_text(section.get(field))
        for old, new in PUBLIC_COMPARISON_REPLACEMENTS:
            raw = raw.replace(old, new)
        fragments = re.split(r"[；;。！？!?，,：:]", raw)
        for fragment in fragments:
            normalized = normalize(fragment)
            if len(normalized) >= 8:
                values.append(normalized)
    return values


def build_matrix() -> dict[tuple[str, str, str], dict[str, Any]]:
    base_fixture = read_json(BASE_READING_PATH)
    articles = load_articles(DEFAULT_ARTICLES_PATH)
    claims = load_claims_by_article(DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb()
    output: dict[tuple[str, str, str], dict[str, Any]] = {}
    for stage in STAGES:
        for question in QUESTIONS:
            for contact in CONTACTS:
                fixture = copy.deepcopy(base_fixture)
                fixture["reading_id"] = f"context-story-{stage}-{question}-{contact}"
                context = fixture.setdefault("context", {})
                context["relationship_stage"] = stage
                context["main_question"] = question
                context["contact_status"] = contact
                context["emotional_risk"] = "calm"
                output[(stage, question, contact)] = build_view_model(fixture, articles, claims, structured_kb)
    return output


def assert_storyline_contract(matrix: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    failures: list[str] = []
    for (stage, question, contact), view_model in matrix.items():
        label = f"{stage}|{question}|{contact}"
        storyline = view_model.get("relationshipContextStoryline") or {}
        final = view_model.get("finalInterpretation") or {}
        final_storyline = final.get("contextStoryline") or {}
        case_storyline = ((view_model.get("westernRelationshipCaseFile") or {}).get("relationshipContextStoryline") or {})
        if storyline.get("version") != "relationship-context-storyline-v1":
            failures.append(f"{label}: storyline version missing")
        if storyline.get("comboKey") != label:
            failures.append(f"{label}: comboKey mismatch: {storyline.get('comboKey')}")
        if final_storyline.get("comboKey") != label:
            failures.append(f"{label}: final interpretation missing context storyline")
        if case_storyline.get("comboKey") != label:
            failures.append(f"{label}: case file missing context storyline")
        if "relationshipContextStoryline" in set(final.get("evidenceClusterKeys") or []):
            failures.append(f"{label}: final sections still cite the global storyline as paragraph evidence")
        for section_id, section in ((final.get("sections") or {}).items()):
            section_keys = set(section.get("evidenceClusterKeys") or [])
            if "relationshipContextStoryline" in section_keys:
                failures.append(f"{label}:{section_id}: global storyline leaked into section evidence")
        for section_id in SECTION_IDS:
            text = normalize_public(section_text(view_model, section_id))
            body = ((final_sections(view_model).get(section_id) or {}).get("body") or "")
            if len(body) > 320:
                failures.append(f"{label}:{section_id}: body too long after storyline layer: {len(body)}")
        visible_text = "\n".join(section_text(view_model, section_id) for section_id in SECTION_IDS)
        for term in FORBIDDEN_TERMS:
            if term in visible_text:
                failures.append(f"{label}: forbidden visible term leaked: {term}")
    require(not failures, "context storyline contract failed:\n- " + "\n- ".join(failures[:25]))


def assert_section_topic_ownership(matrix: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    failures: list[str] = []
    for (stage, question, contact), view_model in matrix.items():
        label = f"{stage}|{question}|{contact}"
        phrase_sections: dict[str, set[str]] = {}
        for section_id in SECTION_IDS:
            for phrase in topic_phrases(section_text(view_model, section_id)):
                phrase_sections.setdefault(phrase, set()).add(section_id)
            body = (final_sections(view_model).get(section_id) or {}).get("body") or ""
            repeated_clauses = repeated_body_clauses(body)
            if repeated_clauses:
                clause, count = sorted(repeated_clauses, key=lambda item: (-item[1], item[0]))[0]
                failures.append(f"{label}:{section_id}: repeated body clause {count}x: {clause[:36]}")
        repeated = [
            (phrase, sections)
            for phrase, sections in phrase_sections.items()
            if len(sections) >= 3
        ]
        if repeated:
            phrase, sections = sorted(repeated, key=lambda item: (-len(item[1]), item[0]))[0]
            failures.append(f"{label}: topic phrase dominates {len(sections)} sections: {phrase[:42]}")
        concept_terms = CONTACT_PROOF_CONCEPT_TERMS.get(contact) or ()
        if concept_terms:
            concept_sections = {
                section_id
                for section_id in SECTION_IDS
                if section_id not in CONTEXT_INDEPENDENT_SECTION_IDS
                if any(term in normalize_public(section_text(view_model, section_id)) for term in concept_terms)
            }
            if len(concept_sections) >= 3:
                failures.append(
                    f"{label}: contact proof concept leaked into {len(concept_sections)} sections: {','.join(sorted(concept_sections))}"
                )
    require(not failures, "context storyline section-topic ownership failed:\n- " + "\n- ".join(failures[:25]))


def assert_axis_diversity(matrix: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    failures: list[str] = []
    require(len(matrix) == len(STAGES) * len(QUESTIONS) * len(CONTACTS), "context matrix size mismatch")
    full_unique = len({full_fingerprint(view_model) for view_model in matrix.values()})
    if full_unique < 25:
        failures.append(f"full final narratives collapsed: {full_unique} unique for {len(matrix)} combos")
    for section_id in SECTION_IDS:
        section_unique = len({section_fingerprint(view_model, section_id) for view_model in matrix.values()})
        if section_id in CONTEXT_INDEPENDENT_SECTION_IDS:
            if section_unique != 1:
                failures.append(f"{section_id}: context-independent section changed across context-only matrix: {section_unique} variants")
        elif section_unique < 5:
            failures.append(f"{section_id}: section narratives collapsed: {section_unique} unique for {len(matrix)} combos")
    base = matrix[("cold-war", "still-love-me", "no-contact")]
    question_variant = matrix[("cold-war", "any-chance", "no-contact")]
    contact_variant = matrix[("cold-war", "still-love-me", "blocked")]
    stage_variant = matrix[("broke-up-long", "still-love-me", "no-contact")]
    if section_fingerprint(base, "core-answer") == section_fingerprint(question_variant, "core-answer"):
        failures.append("core-answer did not react to a question-only change")
    for section_id in ("timing-reading", "action-direction"):
        if section_fingerprint(base, section_id) == section_fingerprint(contact_variant, section_id):
            failures.append(f"{section_id} did not react to a contact-only change")
    if not any(
        section_fingerprint(base, section_id) != section_fingerprint(stage_variant, section_id)
        for section_id in ("core-answer", "timing-reading", "action-direction")
    ):
        failures.append("no context-owned section reacted to a stage-only change")
    require(not failures, "context storyline axis diversity failed:\n- " + "\n- ".join(failures[:25]))


def main() -> int:
    failures: list[str] = []
    try:
        matrix = build_matrix()
        assert_storyline_contract(matrix)
        assert_section_topic_ownership(matrix)
        assert_axis_diversity(matrix)
    except AssertionError as exc:
        failures.append(str(exc))
    if failures:
        print("Final narrative context storyline smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Final narrative context storyline smoke passed")
    print(f"- context combinations checked: {len(STAGES) * len(QUESTIONS) * len(CONTACTS)}")
    print("- storyline remains routing metadata and does not write final paragraphs")
    print("- chart-positioning and relationship-fit remain context-independent")
    print("- storyline topic phrases do not dominate across final sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
