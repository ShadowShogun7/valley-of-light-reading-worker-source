"""Reader-facing copy constraints shared by narrative release gates."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


READER_META_NARRATION_PATTERNS = (
    re.compile(r"(?:^|[。！？!?；;\n])\s*(?:這裡|本頁|這頁|這一頁)"),
    re.compile(r"下一頁|往下讀|讀後面的頁面"),
    re.compile(r"(?:前面|後面)(?:的)?(?:判斷|解讀|內容|結果|頁面)"),
    re.compile(r"不重新分析(?:整段關係|整張星盤)"),
    re.compile(r"暫時不(?:談合不合|加入目前的關係狀態)"),
)


def reader_meta_narration_hits(text: str) -> list[str]:
    """Return visible UI/page narration that should stay internal."""

    hits: list[str] = []
    for pattern in READER_META_NARRATION_PATTERNS:
        match = pattern.search(text or "")
        if match:
            hits.append(match.group(0).strip())
    return hits


INTRA_PAGE_CONTENT_FIELDS = ("meaning", "body", "nextMove", "caution")
INTRA_PAGE_NORMALIZE_PATTERN = re.compile(r"[\s，。；：！？!?「」『』（）()、]+")


def intra_page_overlap_hits(section: dict[str, Any]) -> list[dict[str, Any]]:
    """Find long verbatim thoughts repeated across fields on one result page."""

    values = {
        field: INTRA_PAGE_NORMALIZE_PATTERN.sub("", str(section.get(field) or ""))
        for field in INTRA_PAGE_CONTENT_FIELDS
    }
    hits: list[dict[str, Any]] = []
    for index, left_field in enumerate(INTRA_PAGE_CONTENT_FIELDS):
        left = values[left_field]
        for right_field in INTRA_PAGE_CONTENT_FIELDS[index + 1 :]:
            right = values[right_field]
            if min(len(left), len(right)) < 16:
                continue
            match = SequenceMatcher(None, left, right, autojunk=False).find_longest_match()
            ratio = match.size / min(len(left), len(right))
            if match.size < 16 or ratio < 0.42:
                continue
            hits.append(
                {
                    "leftField": left_field,
                    "rightField": right_field,
                    "matchingChars": match.size,
                    "shorterFieldCoverage": round(ratio, 3),
                    "phrase": left[match.a : match.a + match.size],
                }
            )
    return hits
