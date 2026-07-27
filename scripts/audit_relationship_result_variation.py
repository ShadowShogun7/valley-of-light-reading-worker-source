#!/usr/bin/env python3
"""Audit whether different relationship-result inputs collapse into same readings."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json  # noqa: E402
from complete_relationship_result_runtime import (  # noqa: E402
    DEFAULT_ARTICLES_PATH,
    DEFAULT_CLAIMS_PATH,
    DEFAULT_OUTPUT_PATH,
    build_view_model,
)
from structured_runtime import (  # noqa: E402
    DEFAULT_ATOMS_PATH,
    DEFAULT_GUARDRAILS_PATH,
    DEFAULT_QUESTION_BLUEPRINTS_PATH,
    DEFAULT_RULES_PATH,
    load_kb_support,
    load_structured_kb,
)


RAW_READING_DIR = ROOT / "examples" / "readings"
GENERATED_SCENARIOS_PATH = DEFAULT_OUTPUT_PATH
REPORT_PATH = ROOT / "docs" / "research" / "26-real-input-variation-audit.md"
VISIBLE_SECTION_IDS = ("relationship-fit", "core-answer", "timing-reading", "action-direction")
RELATIONSHIP_FIT_SLOT_PATTERNS = {
    "archetype": re.compile(r"你們比較像「([^」]+)」"),
    "attraction": re.compile(r"吸引的地方在於([^。！？!?]+)"),
    "friction": re.compile(r"卡住的地方在於([^。！？!?]+)"),
}
GENERIC_COPY_PHRASES = (
    "你們不是只有想像中的好感",
    "談責任、承諾或結果時，關係容易變重、變慢或有人先防衛",
    "關係有機會透過耐心、規則和實際行動慢慢穩住",
    "所以這頁的重點不是誰先低頭",
)


@dataclass(frozen=True)
class AuditRecord:
    source: str
    id: str
    question: str
    stage: str
    contact: str
    chart_signature: str
    chart_summary: str
    hidden_signature: str
    hidden_summary: str
    fit_model_signature: str
    fit_model_summary: str
    relationship_fit_signature: str
    visible_signature: str
    relationship_fit_body: str
    visible_summary: str
    slots: dict[str, str]


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def short_hash(value: Any) -> str:
    return hashlib.sha1(compact_json(value).encode("utf-8")).hexdigest()[:10]


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def markdown_cell(value: Any, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    text = text.replace("|", "\\|")
    return text[:limit]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def visible_text_from_section(section: dict[str, Any]) -> str:
    return "\n".join(
        str(section.get(field) or "")
        for field in ("headline", "meaning", "body", "nextMove", "caution")
        if section.get(field)
    )


def section_text(view_model: dict[str, Any], section_id: str) -> str:
    section = (((view_model.get("finalInterpretation") or {}).get("sections") or {}).get(section_id) or {})
    return visible_text_from_section(section) if isinstance(section, dict) else ""


def relationship_fit_body(view_model: dict[str, Any]) -> str:
    section = (((view_model.get("finalInterpretation") or {}).get("sections") or {}).get("relationship-fit") or {})
    return str(section.get("body") or "") if isinstance(section, dict) else ""


def relationship_fit_slots(body: str) -> dict[str, str]:
    slots: dict[str, str] = {}
    for slot, pattern in RELATIONSHIP_FIT_SLOT_PATTERNS.items():
        match = pattern.search(body)
        if match:
            slots[slot] = match.group(1)
    return slots


def top_synastry_aspects(payload: dict[str, Any], limit: int = 8) -> list[str]:
    aspects = (((payload.get("western") or {}).get("synastry") or {}).get("inter_aspects") or [])
    eligible = [item for item in aspects if isinstance(item, dict) and item.get("eligible_for_signal")]
    eligible = sorted(eligible, key=lambda item: float(item.get("orb") or 99))
    output: list[str] = []
    for item in eligible[:limit]:
        output.append(
            f"{item.get('person_a_point')}-{item.get('person_b_point')}:{item.get('aspect')}:{float(item.get('orb') or 0):.2f}"
        )
    return output


def natal_signs_from_payload(payload: dict[str, Any], person_key: str) -> dict[str, str]:
    objects = (((payload.get("western") or {}).get("people") or {}).get(person_key) or {}).get("objects") or {}
    points = ("sun", "moon", "mercury", "venus", "mars", "saturn", "asc")
    return {
        point: str((objects.get(point) or {}).get("sign") or "")
        for point in points
        if isinstance(objects.get(point), dict)
    }


def chart_fingerprint_from_payload(payload: dict[str, Any]) -> tuple[str, str]:
    chart = {
        "person_a": natal_signs_from_payload(payload, "person_a"),
        "person_b": natal_signs_from_payload(payload, "person_b"),
        "top_synastry": top_synastry_aspects(payload),
    }
    summary = (
        f"A {chart['person_a'].get('sun', '?')}/{chart['person_a'].get('moon', '?')} "
        f"B {chart['person_b'].get('sun', '?')}/{chart['person_b'].get('moon', '?')} "
        f"aspects {', '.join(chart['top_synastry'][:3])}"
    )
    return short_hash(chart), summary


def dynamic_item_summary(view_model: dict[str, Any], key: str) -> str:
    block = view_model.get(key) if isinstance(view_model.get(key), dict) else {}
    item = ((block.get("items") or [{}])[0]) if isinstance(block, dict) else {}
    if not isinstance(item, dict):
        return ""
    pair = str(item.get("pairKey") or "")
    aspect = str(item.get("aspectLabel") or item.get("aspect") or "")
    points = "-".join(part for part in (str(item.get("personAPoint") or ""), str(item.get("personBPoint") or "")) if part)
    return ":".join(part for part in (pair, aspect, points) if part)


def chart_fingerprint_from_view_model(view_model: dict[str, Any]) -> tuple[str, str]:
    profiles = view_model.get("relationshipProfiles") if isinstance(view_model.get("relationshipProfiles"), dict) else {}
    baseline = profiles.get("translationBaseline") if isinstance(profiles.get("translationBaseline"), dict) else {}
    chart = {
        "person_a": {
            "emotionalNeed": str(((baseline.get("personA") or {}).get("emotionalNeed")) or ""),
            "communicationStyle": str(((baseline.get("personA") or {}).get("communicationStyle")) or ""),
        },
        "person_b": {
            "emotionalNeed": str(((baseline.get("personB") or {}).get("emotionalNeed")) or ""),
            "conflictResponse": str(((baseline.get("personB") or {}).get("conflictResponse")) or ""),
        },
        "dynamics": {
            "attraction": dynamic_item_summary(view_model, "attractionDynamics"),
            "conflict": dynamic_item_summary(view_model, "conflictDynamics"),
            "growth": dynamic_item_summary(view_model, "growthDynamics"),
        },
    }
    summary = " | ".join(value for value in chart["dynamics"].values() if value) or "profile-derived chart signal"
    return short_hash(chart), summary


def hidden_fingerprint(view_model: dict[str, Any]) -> tuple[str, str]:
    thesis = view_model.get("relationshipThesis") if isinstance(view_model.get("relationshipThesis"), dict) else {}
    model = view_model.get("relationshipCaseModel") if isinstance(view_model.get("relationshipCaseModel"), dict) else {}
    primary = model.get("primaryDynamic") if isinstance(model.get("primaryDynamic"), dict) else {}
    secondaries = [item for item in model.get("secondaryDynamics") or [] if isinstance(item, dict)]
    interaction = model.get("dynamicInteractionPlan") if isinstance(model.get("dynamicInteractionPlan"), dict) else {}
    timing = view_model.get("timingGuidance") if isinstance(view_model.get("timingGuidance"), dict) else {}
    hidden = {
        "centralDynamicKey": str(thesis.get("centralDynamicKey") or ""),
        "primary": str(primary.get("key") or ""),
        "secondaries": [(str(item.get("key") or ""), str(item.get("role") or "")) for item in secondaries],
        "grammarId": str(interaction.get("grammarId") or ""),
        "timingAction": str(timing.get("recommendedAction") or ""),
        "contactPosture": str(((model.get("contactPosture") or {}).get("key")) or ""),
        "archetype": str(((view_model.get("relationshipArchetype") or {}).get("title")) or ""),
    }
    summary = (
        f"{hidden['primary']} + "
        f"{', '.join(f'{key}:{role}' for key, role in hidden['secondaries'][:3])} | "
        f"{hidden['grammarId']} | {hidden['timingAction']}"
    )
    return short_hash(hidden), summary


def fit_model_fingerprint(view_model: dict[str, Any]) -> tuple[str, str]:
    bundle = view_model.get("sectionNarrativeSpecs") if isinstance(view_model.get("sectionNarrativeSpecs"), dict) else {}
    specs = bundle.get("sections") if isinstance(bundle.get("sections"), dict) else {}
    fit_spec = specs.get("relationship-fit") if isinstance(specs.get("relationship-fit"), dict) else {}
    slots = fit_spec.get("semanticSlots") if isinstance(fit_spec.get("semanticSlots"), dict) else {}
    fit_model = {
        "archetypeTitle": str(slots.get("archetypeTitle") or ""),
        "primaryDynamicKey": str(slots.get("primaryDynamicKey") or ""),
        "secondaryDynamicKeys": [str(item) for item in slots.get("secondaryDynamicKeys") or [] if item],
        "fitSignature": str(slots.get("fitSignature") or ""),
        "attractionSignalKeys": [str(item.get("key") or "") for item in slots.get("attractionSignals") or [] if isinstance(item, dict)],
        "frictionSignalKeys": [str(item.get("key") or "") for item in slots.get("frictionSignals") or [] if isinstance(item, dict)],
        "growthSignalKeys": [str(item.get("key") or "") for item in slots.get("growthSignals") or [] if isinstance(item, dict)],
    }
    summary = (
        f"{fit_model['primaryDynamicKey']} + {', '.join(fit_model['secondaryDynamicKeys'][:3])} | "
        f"{fit_model['fitSignature'][:48]} | {fit_model['archetypeTitle']}"
    )
    return short_hash(fit_model), summary


def visible_fingerprint(view_model: dict[str, Any]) -> tuple[str, str, str]:
    sections = {section_id: clean_text(section_text(view_model, section_id)) for section_id in VISIBLE_SECTION_IDS}
    fit_body = relationship_fit_body(view_model)
    summary = " | ".join(f"{section_id}:{short_hash(text)}" for section_id, text in sections.items())
    return short_hash(sections), short_hash(clean_text(fit_body)), summary


def context_from_view_model(view_model: dict[str, Any]) -> tuple[str, str, str]:
    context = view_model.get("context") if isinstance(view_model.get("context"), dict) else {}
    return (
        str(context.get("main_question") or ""),
        str(context.get("relationship_stage") or ""),
        str(context.get("contact_status") or ""),
    )


def record_from_view_model(
    *,
    source: str,
    view_model: dict[str, Any],
    chart_signature: str | None = None,
    chart_summary: str | None = None,
) -> AuditRecord:
    question, stage, contact = context_from_view_model(view_model)
    if not chart_signature or not chart_summary:
        chart_signature, chart_summary = chart_fingerprint_from_view_model(view_model)
    hidden_signature, hidden_summary = hidden_fingerprint(view_model)
    fit_model_signature, fit_model_summary = fit_model_fingerprint(view_model)
    visible_signature, fit_signature, visible_summary = visible_fingerprint(view_model)
    fit_body = relationship_fit_body(view_model)
    return AuditRecord(
        source=source,
        id=str(view_model.get("id") or "unknown"),
        question=question,
        stage=stage,
        contact=contact,
        chart_signature=chart_signature,
        chart_summary=chart_summary,
        hidden_signature=hidden_signature,
        hidden_summary=hidden_summary,
        fit_model_signature=fit_model_signature,
        fit_model_summary=fit_model_summary,
        relationship_fit_signature=fit_signature,
        visible_signature=visible_signature,
        relationship_fit_body=fit_body,
        visible_summary=visible_summary,
        slots=relationship_fit_slots(fit_body),
    )


def raw_reading_paths(reading_dir: Path) -> list[Path]:
    return sorted(path for path in reading_dir.glob("*.json") if path.is_file())


def build_raw_reading_records(reading_dir: Path) -> list[AuditRecord]:
    support = load_kb_support("local", articles_path=DEFAULT_ARTICLES_PATH, claims_path=DEFAULT_CLAIMS_PATH)
    structured_kb = load_structured_kb(
        "local",
        atoms_path=DEFAULT_ATOMS_PATH,
        rules_path=DEFAULT_RULES_PATH,
        question_blueprints_path=DEFAULT_QUESTION_BLUEPRINTS_PATH,
        guardrails_path=DEFAULT_GUARDRAILS_PATH,
    )
    records: list[AuditRecord] = []
    for path in raw_reading_paths(reading_dir):
        reading = read_json(path)
        payload = build_payload(reading, include_drafts=True, select=True)
        view_model = build_view_model(payload, support["articles"], support["claimsByArticle"], structured_kb)
        chart_signature, chart_summary = chart_fingerprint_from_payload(payload)
        records.append(
            record_from_view_model(
                source="raw-reading",
                view_model=view_model,
                chart_signature=chart_signature,
                chart_summary=chart_summary,
            )
        )
    return records


def load_generated_fixture_records(path: Path) -> list[AuditRecord]:
    scenarios = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(scenarios, list):
        raise ValueError(f"{path} must contain a list of generated scenarios")
    return [
        record_from_view_model(source="generated-fixture", view_model=scenario)
        for scenario in scenarios
        if isinstance(scenario, dict)
    ]


def group_records(records: Iterable[AuditRecord], key: str) -> dict[str, list[AuditRecord]]:
    grouped: dict[str, list[AuditRecord]] = defaultdict(list)
    for record in records:
        grouped[getattr(record, key)].append(record)
    return dict(grouped)


def collapse_groups(records: list[AuditRecord], group_key: str, distinct_key: str) -> list[list[AuditRecord]]:
    groups = group_records(records, group_key)
    output = []
    for group in groups.values():
        distinct_values = {getattr(record, distinct_key) for record in group}
        if len(group) > 1 and len(distinct_values) > 1:
            output.append(group)
    return sorted(output, key=lambda group: (-len(group), group[0].id))


def slot_variation(records: list[AuditRecord]) -> dict[str, int]:
    slots: dict[str, set[str]] = {slot: set() for slot in RELATIONSHIP_FIT_SLOT_PATTERNS}
    for record in records:
        for slot, value in record.slots.items():
            if value:
                slots[slot].add(value)
    return {slot: len(values) for slot, values in slots.items()}


def slot_counts(records: list[AuditRecord], slot: str) -> Counter[str]:
    values = [record.slots.get(slot, "") for record in records if record.slots.get(slot)]
    return Counter(values)


def generic_phrase_counts(records: list[AuditRecord]) -> dict[str, int]:
    return {
        phrase: sum(1 for record in records if phrase in record.relationship_fit_body)
        for phrase in GENERIC_COPY_PHRASES
    }


def max_duplicate_count(records: list[AuditRecord], key: str) -> int:
    counts = Counter(getattr(record, key) for record in records)
    return counts.most_common(1)[0][1] if counts else 0


def render_record_table(records: list[AuditRecord], limit: int | None = None) -> list[str]:
    rows = [
        "| ID | Question | Stage | Contact | Chart | Hidden model | Fit model | Fit copy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records[:limit]:
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{record.id}`",
                    record.question,
                    record.stage,
                    record.contact,
                    f"`{record.chart_signature}` {markdown_cell(record.chart_summary, 80)}",
                    f"`{record.hidden_signature}` {markdown_cell(record.hidden_summary)}",
                    f"`{record.fit_model_signature}` {markdown_cell(record.fit_model_summary)}",
                    f"`{record.relationship_fit_signature}`",
                ]
            )
            + " |"
        )
    return rows


def render_collapse_section(title: str, groups: list[list[AuditRecord]], reason: str) -> list[str]:
    lines = [f"### {title}", ""]
    if not groups:
        lines.append(f"- None found. {reason}")
        return lines
    lines.append(f"- Found {len(groups)} group(s). {reason}")
    lines.append("")
    for index, group in enumerate(groups[:8], start=1):
        lines.append(f"**Group {index}:**")
        for record in group:
            lines.append(
                f"- `{record.id}` chart `{record.chart_signature}`, hidden `{record.hidden_signature}`, "
                f"fit-model `{record.fit_model_signature}`, fit `{record.relationship_fit_signature}`"
            )
        lines.append("")
    return lines


def render_generic_phrase_section(records: list[AuditRecord]) -> list[str]:
    lines = ["### Exact Old Generic Phrase Check", ""]
    counts = generic_phrase_counts(records)
    found = {phrase: count for phrase, count in counts.items() if count}
    if not found:
        lines.append("- None found.")
        return lines
    for phrase, count in found.items():
        lines.append(f"- `{phrase}` appears {count} time(s).")
    return lines


def render_slot_repetition_section(records: list[AuditRecord]) -> list[str]:
    lines = ["### Relationship-Fit Slot Repetition", ""]
    if not records:
        lines.append("- No records.")
        return lines
    for slot in RELATIONSHIP_FIT_SLOT_PATTERNS:
        counts = slot_counts(records, slot)
        if not counts:
            lines.append(f"- `{slot}`: no extractable values.")
            continue
        repeated = [(value, count) for value, count in counts.most_common(3) if count > 1]
        summary = f"- `{slot}`: {len(counts)} unique of {len(records)} cases; max repeat {counts.most_common(1)[0][1]}"
        if repeated:
            detail = "; ".join(f"`{value}` x{count}" for value, count in repeated)
            summary = f"{summary}; top repeats: {detail}"
        lines.append(summary)
    return lines


def render_audit_verdict(raw_records: list[AuditRecord], fixture_records: list[AuditRecord]) -> list[str]:
    fixture_slot_counts = {slot: slot_counts(fixture_records, slot) for slot in RELATIONSHIP_FIT_SLOT_PATTERNS}
    repeated_slots = []
    max_repeat_summary = []
    for slot, counts in fixture_slot_counts.items():
        if not counts:
            continue
        max_repeat = counts.most_common(1)[0][1]
        max_repeat_summary.append(f"`{slot}` {max_repeat}")
        if max_repeat >= 5:
            repeated_slots.append(f"`{slot}` max repeat {max_repeat}")
    if repeated_slots:
        slot_verdict = (
            "- The remaining weakness is slot-level repetition, not full-result duplication. In generated fixtures, "
            "the most repeated slots are: "
            + ", ".join(repeated_slots)
            + "."
        )
        next_target = "- Next implementation target should be phrase-family depth and repetition guards for the repeated slots above."
    else:
        slot_verdict = (
            "- The previous slot-level repetition issue is now below the guard threshold. Generated fixture max repeats are: "
            + ", ".join(max_repeat_summary)
            + "."
        )
        next_target = "- Next work should focus on subjective copy QA with real user inputs, while keeping these repetition gates in place."
    return [
        "## Audit Verdict",
        "",
        f"- Strict fixture status: {'PASS' if not audit_failures(fixture_records) else 'FAIL'}",
        f"- Full visible collapse groups across different fixture charts: {len(collapse_groups(fixture_records, 'visible_signature', 'chart_signature'))}.",
        f"- Relationship-fit collapse groups across different fixture models: {len(collapse_groups(fixture_records, 'relationship_fit_signature', 'fit_model_signature'))}.",
        slot_verdict,
        next_target,
        "",
    ]


def audit_failures(fixture_records: list[AuditRecord]) -> list[str]:
    failures: list[str] = []
    if len(fixture_records) < 45:
        failures.append(f"fixture corpus too small: {len(fixture_records)}")
    generic_hits = sum(generic_phrase_counts(fixture_records).values())
    if generic_hits:
        failures.append(f"old generic phrases remain: {generic_hits}")
    visible_collapses = collapse_groups(fixture_records, "visible_signature", "chart_signature")
    if visible_collapses:
        failures.append(f"full visible output collapse groups: {len(visible_collapses)}")
    fit_collapses = collapse_groups(fixture_records, "relationship_fit_signature", "fit_model_signature")
    if fit_collapses:
        failures.append(f"relationship-fit collapse groups: {len(fit_collapses)}")
    return failures


def render_report(raw_records: list[AuditRecord], fixture_records: list[AuditRecord]) -> str:
    all_sets = (("Raw Reading Inputs", raw_records), ("Generated Scenario Fixtures", fixture_records))
    lines = [
        "# Real Input Variation Audit",
        "",
        "> Generated by `scripts/audit_relationship_result_variation.py`. This checks whether different relationship-result inputs collapse at the chart-signal, hidden-model, or visible-final-copy layer.",
        "",
        "## Summary",
        "",
        f"- Strict generated-fixture status: {'PASS' if not audit_failures(fixture_records) else 'FAIL'}",
        "",
    ]
    for label, records in all_sets:
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Cases: {len(records)}",
                f"- Unique chart fingerprints: {len({record.chart_signature for record in records})}",
                f"- Unique hidden-model fingerprints: {len({record.hidden_signature for record in records})}",
                f"- Unique fit-model fingerprints: {len({record.fit_model_signature for record in records})}",
                f"- Unique relationship-fit bodies: {len({record.relationship_fit_signature for record in records})}",
                f"- Unique full visible fingerprints: {len({record.visible_signature for record in records})}",
                f"- Max duplicate relationship-fit body count: {max_duplicate_count(records, 'relationship_fit_signature')}",
                f"- Relationship-fit slot variation: {slot_variation(records)}",
                "",
            ]
        )
    lines.extend(render_audit_verdict(raw_records, fixture_records))
    lines.extend(
        [
            "## Collapse Diagnosis",
            "",
            "These checks separate likely causes:",
            "",
            "- Same chart fingerprint and same output: expected if the same case is duplicated.",
            "- Different chart fingerprints but same hidden model: selector/thesis may be too coarse.",
            "- Different fit-relevant hidden models but same relationship-fit copy: final relationship-fit rendering is collapsing detail.",
            "- Different chart and hidden model but same full visible output: severe visible-layer collapse.",
            "",
        ]
    )
    for label, records in all_sets:
        lines.extend([f"## {label}", ""])
        lines.extend(render_generic_phrase_section(records))
        lines.extend([""])
        lines.extend(render_slot_repetition_section(records))
        lines.extend([""])
        lines.extend(
            render_collapse_section(
                "Visible full-output collapse across different charts",
                collapse_groups(records, "visible_signature", "chart_signature"),
                "This should normally be zero.",
            )
        )
        lines.extend([""])
        lines.extend(
            render_collapse_section(
                "Relationship-fit copy collapse across different fit models",
                collapse_groups(records, "relationship_fit_signature", "fit_model_signature"),
                "This should be zero after the phrase-bank layer. Timing-only or risk-only differences are intentionally excluded.",
            )
        )
        lines.extend([""])
        lines.extend(
            render_collapse_section(
                "Hidden-model reuse across different charts",
                collapse_groups(records, "hidden_signature", "chart_signature"),
                "Some reuse is acceptable when relationship dynamics are genuinely similar; review large groups.",
            )
        )
        lines.extend(["", "### Case Matrix", ""])
        lines.extend(render_record_table(records, limit=50))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit relationship-result variation across input sets.")
    parser.add_argument("--reading-dir", default=str(RAW_READING_DIR))
    parser.add_argument("--generated-scenarios", default=str(GENERATED_SCENARIOS_PATH))
    parser.add_argument("--report", "--out", dest="report", default=str(REPORT_PATH))
    args = parser.parse_args()

    raw_records = build_raw_reading_records(Path(args.reading_dir))
    fixture_records = load_generated_fixture_records(Path(args.generated_scenarios))
    report = render_report(raw_records, fixture_records)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {display_path(report_path)}")
    print(f"Raw readings: {len(raw_records)} cases, {len({record.relationship_fit_signature for record in raw_records})} unique fit bodies")
    print(f"Generated fixtures: {len(fixture_records)} cases, {len({record.relationship_fit_signature for record in fixture_records})} unique fit bodies")
    print(f"Raw visible collapse groups: {len(collapse_groups(raw_records, 'visible_signature', 'chart_signature'))}")
    print(f"Fixture visible collapse groups: {len(collapse_groups(fixture_records, 'visible_signature', 'chart_signature'))}")
    failures = audit_failures(fixture_records)
    for failure in failures:
        print(f"- {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
