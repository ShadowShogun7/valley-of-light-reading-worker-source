#!/usr/bin/env python3
"""Audit near-duplicate relationship-fit copy beyond exact string matching."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_relationship_result_variation import (  # noqa: E402
    GENERATED_SCENARIOS_PATH,
    RAW_READING_DIR,
    RELATIONSHIP_FIT_SLOT_PATTERNS,
    build_raw_reading_records,
    load_generated_fixture_records,
)


REPORT_PATH = ROOT / "docs" / "research" / "27-relationship-fit-semantic-similarity-audit.md"
NEAR_DUPLICATE_THRESHOLD = 0.72
GENERATED_MAX_EXACT_REPEATS = {
    "archetype": 4,
    "attraction": 4,
    "friction": 4,
    "viability": 3,
    "repair": 3,
    "observable": 3,
    "boundary": 4,
}
SEMANTIC_FAMILIES = {
    "pressure_or_definition": re.compile(r"壓力|逼|追問|表態|定義|承諾|責任"),
    "natural_continuation": re.compile(r"自然|延續|接續|接住|主動"),
    "boundary_or_channel": re.compile(r"界線|通道|繞路|停點|承受"),
    "small_specific_action": re.compile(r"具體|小|一步|一件|短|輕"),
    "emotion_or_safety": re.compile(r"安全感|情緒|安定|穩|溫柔"),
    "speed_or_action": re.compile(r"推進|速度|急|降速|升溫|行動"),
}


@dataclass(frozen=True)
class TextItem:
    id: str
    text: str
    semantic_identity: str


@dataclass(frozen=True)
class SimilarityPair:
    score: float
    left_id: str
    right_id: str
    left_text: str
    right_text: str


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def char_ngrams(value: str, size: int = 3) -> set[str]:
    text = normalize_text(value)
    if not text:
        return set()
    if len(text) <= size:
        return {text}
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def jaccard_similarity(left: str, right: str, size: int = 3) -> float:
    left_grams = char_ngrams(left, size)
    right_grams = char_ngrams(right, size)
    if not left_grams and not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def truncate_cell(value: str, limit: int = 96) -> str:
    text = re.sub(r"\s+", " ", value or "").strip().replace("|", "\\|")
    return text[:limit]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def top_similarity_pairs(
    items: list[TextItem],
    threshold: float | None = None,
    *,
    include_exact: bool = True,
) -> list[SimilarityPair]:
    pairs: list[SimilarityPair] = []
    for left_index, left in enumerate(items):
        for right in items[left_index + 1 :]:
            if not left.text or not right.text:
                continue
            if left.semantic_identity == right.semantic_identity:
                continue
            if not include_exact and normalize_text(left.text) == normalize_text(right.text):
                continue
            score = jaccard_similarity(left.text, right.text)
            if threshold is None or score >= threshold:
                pairs.append(
                    SimilarityPair(
                        score=score,
                        left_id=left.id,
                        right_id=right.id,
                        left_text=left.text,
                        right_text=right.text,
                    )
                )
    return sorted(pairs, key=lambda item: item.score, reverse=True)


def exact_max_repeat(items: Iterable[TextItem]) -> int:
    identities_by_text: dict[str, set[str]] = {}
    for item in items:
        if item.text:
            identities_by_text.setdefault(item.text, set()).add(item.semantic_identity)
    return max((len(identities) for identities in identities_by_text.values()), default=0)


def slot_items(records: list[object], slot: str) -> list[TextItem]:
    output: list[TextItem] = []
    for record in records:
        slots = getattr(record, "slots")
        value = slots.get(slot, "")
        if value:
            output.append(
                TextItem(
                    id=getattr(record, "id"),
                    text=value,
                    semantic_identity=getattr(record, "fit_model_signature"),
                )
            )
    return output


def body_items(records: list[object]) -> list[TextItem]:
    return [
        TextItem(
            id=getattr(record, "id"),
            text=getattr(record, "relationship_fit_body"),
            semantic_identity=getattr(record, "fit_model_signature"),
        )
        for record in records
    ]


def semantic_family_counts(items: list[TextItem]) -> dict[str, int]:
    return {
        family: sum(1 for item in items if pattern.search(item.text))
        for family, pattern in SEMANTIC_FAMILIES.items()
    }


def render_pair_table(pairs: list[SimilarityPair], limit: int = 6) -> list[str]:
    lines = [
        "| Score | Left | Right | Left text | Right text |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not pairs:
        lines.append("| - | - | - | No pairs above threshold. | - |")
        return lines
    for pair in pairs[:limit]:
        lines.append(
            f"| {pair.score:.3f} | `{pair.left_id}` | `{pair.right_id}` | "
            f"{truncate_cell(pair.left_text)} | {truncate_cell(pair.right_text)} |"
        )
    return lines


def render_dataset(label: str, records: list[object], strict: bool) -> tuple[list[str], bool]:
    lines = [f"## {label}", ""]
    passed = True
    bodies = body_items(records)
    body_pairs = top_similarity_pairs(bodies)
    near_body_pairs = [pair for pair in body_pairs if pair.score >= NEAR_DUPLICATE_THRESHOLD]
    exact_body_max = exact_max_repeat(bodies)
    max_body_similarity = body_pairs[0].score if body_pairs else 0.0
    if strict and near_body_pairs:
        passed = False
    lines.extend(
        [
            "### Full Relationship-Fit Body Similarity",
            "",
            f"- Cases: {len(bodies)}",
            f"- Unique bodies: {len({item.text for item in bodies})}",
            f"- Max exact body repeat across different fit semantic models: {exact_body_max}",
            f"- Highest full-body similarity: {max_body_similarity:.3f}",
            f"- Near-duplicate body pairs at `{NEAR_DUPLICATE_THRESHOLD}`: {len(near_body_pairs)}",
            "",
        ]
    )
    lines.extend(render_pair_table(body_pairs))
    lines.append("")
    lines.extend(["### Slot Similarity", ""])
    lines.append("| Slot | Unique | Max exact repeat | Highest non-exact similarity | Non-exact near-duplicate pairs | Strict status |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    slot_pair_details: dict[str, list[SimilarityPair]] = {}
    for slot in RELATIONSHIP_FIT_SLOT_PATTERNS:
        items = slot_items(records, slot)
        pairs = top_similarity_pairs(items, include_exact=False)
        near_pairs = [pair for pair in pairs if pair.score >= NEAR_DUPLICATE_THRESHOLD]
        max_repeat = exact_max_repeat(items)
        max_similarity = pairs[0].score if pairs else 0.0
        strict_ok = True
        if strict:
            strict_ok = not near_pairs and max_repeat <= GENERATED_MAX_EXACT_REPEATS.get(slot, 4)
            if not strict_ok:
                passed = False
        lines.append(
            f"| `{slot}` | {len({item.text for item in items})} | {max_repeat} | "
            f"{max_similarity:.3f} | {len(near_pairs)} | {'pass' if strict_ok else 'fail'} |"
        )
        slot_pair_details[slot] = pairs
    lines.append("")
    lines.extend(["### Top Slot Similarity Pairs", ""])
    for slot, pairs in slot_pair_details.items():
        lines.extend([f"#### `{slot}`", ""])
        lines.extend(render_pair_table(pairs[:4], limit=4))
        lines.append("")
    lines.extend(["### Semantic Family Presence", ""])
    family_counts = semantic_family_counts(bodies)
    lines.append("| Family | Count | Share |")
    lines.append("| --- | --- | --- |")
    for family, count in family_counts.items():
        share = count / len(bodies) if bodies else 0
        lines.append(f"| `{family}` | {count} | {share:.0%} |")
    lines.append("")
    return lines, passed


def render_report(raw_records: list[object], fixture_records: list[object]) -> tuple[str, bool]:
    raw_lines, _ = render_dataset("Raw Reading Inputs", raw_records, strict=False)
    fixture_lines, fixture_passed = render_dataset("Generated Scenario Fixtures", fixture_records, strict=True)
    lines = [
        "# Relationship-Fit Semantic Similarity Audit",
        "",
        "> Generated by `scripts/audit_relationship_fit_semantic_similarity.py`. This audit checks whether the post-V5 copy is merely unique by hash or also free of near-duplicate sentence-slot meaning.",
        "",
        "## Verdict",
        "",
        f"- Strict generated-fixture semantic audit: {'PASS' if fixture_passed else 'FAIL'}",
        f"- Near-duplicate threshold: `{NEAR_DUPLICATE_THRESHOLD}` using Chinese character trigram Jaccard similarity.",
        "- Raw readings are review-only because the sample intentionally contains repeated chart/fit-model cases; generated fixtures are strict because they cover the regression matrix.",
        "",
    ]
    lines.extend(fixture_lines)
    lines.extend(raw_lines)
    return "\n".join(lines).rstrip() + "\n", fixture_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit relationship-fit semantic near-duplicates.")
    parser.add_argument("--reading-dir", default=str(RAW_READING_DIR))
    parser.add_argument("--generated-scenarios", default=str(GENERATED_SCENARIOS_PATH))
    parser.add_argument("--report", "--out", dest="report", default=str(REPORT_PATH))
    args = parser.parse_args()

    raw_records = build_raw_reading_records(Path(args.reading_dir))
    fixture_records = load_generated_fixture_records(Path(args.generated_scenarios))
    report, passed = render_report(raw_records, fixture_records)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Wrote {display_path(report_path)}")
    print(f"Generated fixture semantic audit: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
