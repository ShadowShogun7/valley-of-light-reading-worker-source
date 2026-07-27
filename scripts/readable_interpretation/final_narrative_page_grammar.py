"""Executable content grammars for the five final narrative pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


VISIBLE_FIELDS = ("headline", "meaning", "body", "nextMove", "caution")
SENTENCE_FIELDS = ("meaning", "body", "nextMove", "caution")


class FinalNarrativePageGrammarError(ValueError):
    """Raised when a page renderer crosses its owned content grammar."""


@dataclass(frozen=True)
class PageGrammar:
    required_content: tuple[str, ...]
    sentence_limits: Mapping[str, tuple[int, int]]
    forbidden_phrases: tuple[str, ...]


PAGE_GRAMMARS: dict[str, PageGrammar] = {
    "chart-positioning": PageGrammar(
        required_content=("your emotional need", "your communication habit", "his pressure response"),
        sentence_limits={"meaning": (2, 2), "body": (1, 1), "nextMove": (1, 1), "caution": (1, 1)},
        forbidden_phrases=("復合", "聯絡時機", "傳訊息", "幾月", "日期"),
    ),
    "relationship-fit": PageGrammar(
        required_content=("attraction mechanism", "friction mechanism", "repair potential"),
        sentence_limits={"meaning": (1, 2), "body": (2, 3), "nextMove": (1, 1), "caution": (1, 1)},
        forbidden_phrases=("現在適合聯絡", "傳訊息", "幾月", "日期", "他還愛不愛"),
    ),
    "core-answer": PageGrammar(
        required_content=("direct answer", "strongest evidence", "change condition"),
        sentence_limits={"meaning": (1, 1), "body": (1, 1), "nextMove": (1, 1), "caution": (1, 1)},
        forbidden_phrases=("上旬", "中旬", "下旬", "這次先避開這幾件事"),
    ),
    "timing-reading": PageGrammar(
        required_content=("contact permission", "suitable window", "uncertainty"),
        sentence_limits={"meaning": (1, 1), "body": (1, 2), "nextMove": (1, 1), "caution": (1, 2)},
        forbidden_phrases=("型：", "關係類型", "靈魂伴侶", "歡喜冤家", "高吸引高摩擦"),
    ),
    "action-direction": PageGrammar(
        required_content=("action purpose", "one action", "completion boundary", "one stopping condition"),
        sentence_limits={"meaning": (1, 1), "body": (1, 1), "nextMove": (1, 1), "caution": (1, 1)},
        forbidden_phrases=(
            "這次先避開這幾件事",
            "型：",
            "關係類型",
            "上旬",
            "中旬",
            "下旬",
            "月亮",
            "水星",
            "金星",
            "火星",
            "土星",
        ),
    ),
}


def sentence_count(text: str) -> int:
    return len([item for item in re.split(r"[。！？]+", str(text or "")) if item.strip()])


def validate_page_grammar(section_id: str, rendered: Mapping[str, str]) -> None:
    grammar = PAGE_GRAMMARS.get(section_id)
    if grammar is None:
        raise FinalNarrativePageGrammarError(f"unknown page grammar: {section_id}")
    if set(rendered) != set(VISIBLE_FIELDS):
        raise FinalNarrativePageGrammarError(
            f"{section_id}: visible field mismatch: {sorted(rendered)}"
        )
    for field in VISIBLE_FIELDS:
        if not str(rendered.get(field) or "").strip():
            raise FinalNarrativePageGrammarError(f"{section_id}:{field}: empty visible copy")
    for field in SENTENCE_FIELDS:
        minimum, maximum = grammar.sentence_limits[field]
        count = sentence_count(rendered[field])
        if not minimum <= count <= maximum:
            raise FinalNarrativePageGrammarError(
                f"{section_id}:{field}: sentence count {count} outside {minimum}-{maximum}"
            )
    visible = "".join(str(rendered[field]) for field in VISIBLE_FIELDS)
    hits = [phrase for phrase in grammar.forbidden_phrases if phrase in visible]
    if hits:
        raise FinalNarrativePageGrammarError(
            f"{section_id}: crossed page grammar with forbidden phrases: {hits}"
        )


__all__ = [
    "FinalNarrativePageGrammarError",
    "PAGE_GRAMMARS",
    "PageGrammar",
    "VISIBLE_FIELDS",
    "sentence_count",
    "validate_page_grammar",
]
