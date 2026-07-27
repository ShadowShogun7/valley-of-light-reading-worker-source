#!/usr/bin/env python3
"""Generate V2 depth fixtures for complete relationship-result scenarios.

The six seed calculation fixtures stay as the canonical examples from real
birth inputs. These V2 variants are deterministic regression fixtures derived
from those seeds so the interpretation layer is forced through broader thesis,
context, and timing branches.
"""

from __future__ import annotations

import copy
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CALCULATION_DIR = ROOT / "examples" / "calculations"
MANIFEST_PATH = CALCULATION_DIR / "relationship-depth-fixtures-v2.json"
GENERATED_PREFIX = "v2-depth-"
GENERATED_AT = "2026-06-25"


PAIR_TO_SIGNAL_ID = {
    frozenset(("Sun", "Mars")): "western-aspects-sun-mars",
    frozenset(("Venus", "Mars")): "western-aspects-venus-mars",
    frozenset(("Sun", "Venus")): "western-aspects-sun-venus",
    frozenset(("Moon", "Moon")): "western-aspects-moon-moon",
    frozenset(("Moon", "Mars")): "western-aspects-moon-mars",
    frozenset(("Venus", "Venus")): "western-aspects-venus-venus",
    frozenset(("Mars", "Mars")): "western-aspects-mars-mars",
    frozenset(("Mercury", "Sun")): "western-aspects-mercury-sun",
    frozenset(("Mercury", "Jupiter")): "western-aspects-mercury-jupiter",
    frozenset(("Mars", "Saturn")): "western-aspects-mars-saturn",
    frozenset(("Moon", "Saturn")): "western-aspects-moon-saturn",
    frozenset(("Moon", "Venus")): "western-aspects-moon-venus",
    frozenset(("Venus", "Saturn")): "western-aspects-venus-saturn",
    frozenset(("Sun", "Saturn")): "western-aspects-sun-saturn",
    frozenset(("Sun", "Moon")): "western-aspects-sun-moon",
    frozenset(("Mercury", "Mercury")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Moon")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Venus")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Mars")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Saturn")): "western-aspects-mercury-contacts",
}

OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
PERSONAL_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter"}

SIGNAL_LABELS = {
    "western-aspects-sun-mars": "Sun-Mars 強互動",
    "western-aspects-venus-mars": "Venus-Mars 吸引",
    "western-aspects-sun-venus": "Sun-Venus 欣賞好感",
    "western-aspects-moon-moon": "Moon-Moon 情緒節奏",
    "western-aspects-moon-mars": "Moon-Mars 情緒點火",
    "western-aspects-venus-venus": "Venus-Venus 喜歡語言",
    "western-aspects-mars-mars": "Mars-Mars 行動節奏",
    "western-aspects-mercury-sun": "Mercury-Sun 理解與自尊",
    "western-aspects-mercury-jupiter": "Mercury-Jupiter 開闊對話",
    "western-aspects-mars-saturn": "火星-土星壓力",
    "western-aspects-moon-saturn": "月亮-土星防衛",
    "western-aspects-moon-venus": "Moon-Venus 情緒好感",
    "western-aspects-venus-saturn": "金星-土星慢熱防衛",
    "western-aspects-sun-saturn": "太陽-土星壓力",
    "western-aspects-sun-moon": "Sun-Moon 情緒連結",
    "western-aspects-mercury-contacts": "Mercury 溝通相位",
    "western-aspects-outer-planet-intensity-families": "外行星強度相位",
}

SEED_BY_QUESTION = {
    "still-love-me": "broke-up-recent-still-love-me",
    "any-chance": "broke-up-long-any-chance",
    "when-to-contact": "cold-war-when-to-contact",
    "what-did-i-do-wrong": "broke-up-recent-what-did-i-do-wrong",
    "stay-or-let-go": "crisis-stay-or-let-go",
}

QUESTION_TO_OUTCOME = {
    "still-love-me": "reconnect",
    "any-chance": "decide",
    "when-to-contact": "reconnect",
    "what-did-i-do-wrong": "understand",
    "stay-or-let-go": "decide",
}

ASPECT_PROFILES: dict[str, list[tuple[str, str, str, float, bool]]] = {
    "emotional_safety": [
        ("Moon", "Venus", "Trine", 0.65, True),
        ("Sun", "Moon", "Sextile", 0.9, True),
        ("Moon", "Moon", "Conjunction", 1.1, False),
        ("Mercury", "Moon", "Sextile", 2.0, True),
        ("Venus", "Venus", "Trine", 4.8, False),
    ],
    "saturn_pressure": [
        ("Venus", "Saturn", "Square", 0.55, True),
        ("Moon", "Saturn", "Opposition", 0.8, True),
        ("Sun", "Saturn", "Conjunction", 1.0, False),
        ("Mars", "Saturn", "Square", 1.3, True),
        ("Mercury", "Saturn", "Opposition", 1.7, False),
    ],
    "communication_repair": [
        ("Mercury", "Mercury", "Trine", 0.45, True),
        ("Mercury", "Sun", "Sextile", 0.8, True),
        ("Mercury", "Venus", "Trine", 1.1, False),
        ("Mercury", "Moon", "Sextile", 1.6, True),
        ("Mercury", "Mars", "Square", 2.2, False),
    ],
    "attraction_pursuit": [
        ("Venus", "Mars", "Trine", 0.5, True),
        ("Sun", "Venus", "Conjunction", 0.75, True),
        ("Moon", "Venus", "Sextile", 1.2, False),
        ("Venus", "Venus", "Trine", 1.5, True),
        ("Sun", "Mars", "Trine", 2.0, False),
    ],
    "action_conflict": [
        ("Mars", "Mars", "Square", 0.5, True),
        ("Moon", "Mars", "Opposition", 0.75, True),
        ("Sun", "Mars", "Square", 1.0, False),
        ("Mercury", "Mars", "Square", 1.3, True),
        ("Mars", "Saturn", "Square", 2.0, False),
    ],
    "identity_rhythm": [
        ("Mercury", "Sun", "Trine", 0.4, True),
        ("Sun", "Moon", "Trine", 0.75, True),
        ("Sun", "Venus", "Sextile", 1.1, False),
        ("Sun", "Mars", "Trine", 1.5, True),
        ("Sun", "Saturn", "Trine", 2.0, False),
    ],
    "outer_intensity": [
        ("Pluto", "Moon", "Square", 0.5, True),
        ("Neptune", "Venus", "Opposition", 0.75, True),
        ("Uranus", "Mars", "Conjunction", 0.95, False),
        ("Pluto", "Sun", "Square", 1.3, True),
        ("Neptune", "Mercury", "Trine", 1.8, False),
    ],
}

TIMING_PROFILES = {
    "avoid_push": {
        "sample_count": 12,
        "better_count": 2,
        "neutral_count": 2,
        "avoid_count": 8,
        "top_band": "avoid",
        "category_counts": {
            "pressure": 5,
            "activation_pressure": 3,
            "communication_pressure": 2,
            "background": 2,
        },
    },
    "low_pressure_message": {
        "sample_count": 12,
        "better_count": 7,
        "neutral_count": 3,
        "avoid_count": 2,
        "top_band": "better",
        "category_counts": {
            "communication_window": 5,
            "softening": 4,
            "relationship_focus": 2,
            "background": 1,
        },
    },
    "observe_for_soft_window": {
        "sample_count": 12,
        "better_count": 0,
        "neutral_count": 8,
        "avoid_count": 4,
        "top_band": "neutral",
        "category_counts": {
            "communication_window": 2,
            "softening": 2,
            "background": 8,
        },
    },
    "observe_only": {
        "sample_count": 12,
        "better_count": 0,
        "neutral_count": 10,
        "avoid_count": 2,
        "top_band": "neutral",
        "category_counts": {
            "background": 12,
        },
    },
    "not_calculated": {
        "sample_count": 0,
        "better_count": 0,
        "neutral_count": 0,
        "avoid_count": 0,
        "top_band": "neutral",
        "category_counts": {},
    },
}

CASE_SPECS: list[dict[str, str]] = [
    {"slug": "emotional-cold-war-still-love-no-contact", "dynamic": "emotional_safety", "timing": "low_pressure_message", "stage": "cold-war", "question": "still-love-me", "contact": "no-contact", "risk": "anxious"},
    {"slug": "emotional-recent-still-love-occasional", "dynamic": "emotional_safety", "timing": "observe_for_soft_window", "stage": "broke-up-recent", "question": "still-love-me", "contact": "occasional-contact", "risk": "self-blaming"},
    {"slug": "emotional-recent-what-wrong-blocked", "dynamic": "emotional_safety", "timing": "not_calculated", "stage": "broke-up-recent", "question": "what-did-i-do-wrong", "contact": "blocked", "risk": "self-blaming"},
    {"slug": "emotional-crisis-stay-shared-space", "dynamic": "emotional_safety", "timing": "observe_only", "stage": "crisis", "question": "stay-or-let-go", "contact": "living-or-working-together", "risk": "desperate"},
    {"slug": "emotional-long-any-chance-no-contact", "dynamic": "emotional_safety", "timing": "low_pressure_message", "stage": "broke-up-long", "question": "any-chance", "contact": "no-contact", "risk": "calm"},
    {"slug": "saturn-crisis-stay-shared-space", "dynamic": "saturn_pressure", "timing": "avoid_push", "stage": "crisis", "question": "stay-or-let-go", "contact": "living-or-working-together", "risk": "desperate"},
    {"slug": "saturn-long-any-chance-blocked", "dynamic": "saturn_pressure", "timing": "observe_only", "stage": "broke-up-long", "question": "any-chance", "contact": "blocked", "risk": "calm"},
    {"slug": "saturn-cold-war-still-love-no-contact", "dynamic": "saturn_pressure", "timing": "avoid_push", "stage": "cold-war", "question": "still-love-me", "contact": "no-contact", "risk": "anxious"},
    {"slug": "saturn-cold-war-when-contact-blocked", "dynamic": "saturn_pressure", "timing": "observe_for_soft_window", "stage": "cold-war", "question": "when-to-contact", "contact": "blocked", "risk": "calm"},
    {"slug": "saturn-recent-what-wrong-still-contact", "dynamic": "saturn_pressure", "timing": "avoid_push", "stage": "broke-up-recent", "question": "what-did-i-do-wrong", "contact": "still-in-contact", "risk": "self-blaming"},
    {"slug": "communication-cold-war-when-contact-still-contact", "dynamic": "communication_repair", "timing": "low_pressure_message", "stage": "cold-war", "question": "when-to-contact", "contact": "still-in-contact", "risk": "calm"},
    {"slug": "communication-recent-what-wrong-occasional", "dynamic": "communication_repair", "timing": "low_pressure_message", "stage": "broke-up-recent", "question": "what-did-i-do-wrong", "contact": "occasional-contact", "risk": "self-blaming"},
    {"slug": "communication-long-any-chance-blocked", "dynamic": "communication_repair", "timing": "observe_for_soft_window", "stage": "broke-up-long", "question": "any-chance", "contact": "blocked", "risk": "calm"},
    {"slug": "communication-recent-still-love-still-contact", "dynamic": "communication_repair", "timing": "low_pressure_message", "stage": "broke-up-recent", "question": "still-love-me", "contact": "still-in-contact", "risk": "anxious"},
    {"slug": "communication-crisis-when-contact-shared-space", "dynamic": "communication_repair", "timing": "observe_only", "stage": "crisis", "question": "when-to-contact", "contact": "living-or-working-together", "risk": "desperate"},
    {"slug": "attraction-long-any-chance-occasional", "dynamic": "attraction_pursuit", "timing": "low_pressure_message", "stage": "broke-up-long", "question": "any-chance", "contact": "occasional-contact", "risk": "calm"},
    {"slug": "attraction-cold-war-still-love-still-contact", "dynamic": "attraction_pursuit", "timing": "low_pressure_message", "stage": "cold-war", "question": "still-love-me", "contact": "still-in-contact", "risk": "anxious"},
    {"slug": "attraction-recent-stay-no-contact", "dynamic": "attraction_pursuit", "timing": "observe_for_soft_window", "stage": "broke-up-recent", "question": "stay-or-let-go", "contact": "no-contact", "risk": "desperate"},
    {"slug": "attraction-cold-war-when-contact-occasional", "dynamic": "attraction_pursuit", "timing": "low_pressure_message", "stage": "cold-war", "question": "when-to-contact", "contact": "occasional-contact", "risk": "calm"},
    {"slug": "attraction-crisis-what-wrong-blocked", "dynamic": "attraction_pursuit", "timing": "observe_only", "stage": "crisis", "question": "what-did-i-do-wrong", "contact": "blocked", "risk": "self-blaming"},
    {"slug": "action-recent-what-wrong-occasional", "dynamic": "action_conflict", "timing": "avoid_push", "stage": "broke-up-recent", "question": "what-did-i-do-wrong", "contact": "occasional-contact", "risk": "self-blaming"},
    {"slug": "action-cold-war-when-contact-blocked", "dynamic": "action_conflict", "timing": "avoid_push", "stage": "cold-war", "question": "when-to-contact", "contact": "blocked", "risk": "anxious"},
    {"slug": "action-crisis-any-chance-shared-space", "dynamic": "action_conflict", "timing": "observe_only", "stage": "crisis", "question": "any-chance", "contact": "living-or-working-together", "risk": "desperate"},
    {"slug": "action-long-still-love-no-contact", "dynamic": "action_conflict", "timing": "observe_for_soft_window", "stage": "broke-up-long", "question": "still-love-me", "contact": "no-contact", "risk": "anxious"},
    {"slug": "action-crisis-stay-still-contact", "dynamic": "action_conflict", "timing": "avoid_push", "stage": "crisis", "question": "stay-or-let-go", "contact": "still-in-contact", "risk": "desperate"},
    {"slug": "identity-recent-what-wrong-still-contact", "dynamic": "identity_rhythm", "timing": "observe_only", "stage": "broke-up-recent", "question": "what-did-i-do-wrong", "contact": "still-in-contact", "risk": "self-blaming"},
    {"slug": "identity-long-any-chance-no-contact", "dynamic": "identity_rhythm", "timing": "low_pressure_message", "stage": "broke-up-long", "question": "any-chance", "contact": "no-contact", "risk": "calm"},
    {"slug": "identity-cold-war-still-love-blocked", "dynamic": "identity_rhythm", "timing": "not_calculated", "stage": "cold-war", "question": "still-love-me", "contact": "blocked", "risk": "anxious"},
    {"slug": "identity-crisis-when-contact-shared-space", "dynamic": "identity_rhythm", "timing": "observe_for_soft_window", "stage": "crisis", "question": "when-to-contact", "contact": "living-or-working-together", "risk": "desperate"},
    {"slug": "outer-crisis-stay-blocked", "dynamic": "outer_intensity", "timing": "not_calculated", "stage": "crisis", "question": "stay-or-let-go", "contact": "blocked", "risk": "calm"},
    {"slug": "outer-long-any-chance-occasional", "dynamic": "outer_intensity", "timing": "not_calculated", "stage": "broke-up-long", "question": "any-chance", "contact": "occasional-contact", "risk": "anxious"},
    {"slug": "outer-cold-war-what-wrong-shared-space", "dynamic": "outer_intensity", "timing": "not_calculated", "stage": "cold-war", "question": "what-did-i-do-wrong", "contact": "living-or-working-together", "risk": "self-blaming"},
    {"slug": "ambiguous-attraction-still-love-still-contact", "dynamic": "attraction_pursuit", "timing": "low_pressure_message", "stage": "ambiguous", "question": "still-love-me", "contact": "still-in-contact", "risk": "calm"},
    {"slug": "ambiguous-communication-any-chance-occasional", "dynamic": "communication_repair", "timing": "observe_for_soft_window", "stage": "ambiguous", "question": "any-chance", "contact": "occasional-contact", "risk": "anxious"},
    {"slug": "ambiguous-emotional-when-contact-no-contact", "dynamic": "emotional_safety", "timing": "observe_only", "stage": "ambiguous", "question": "when-to-contact", "contact": "no-contact", "risk": "calm"},
    {"slug": "ambiguous-action-what-wrong-blocked", "dynamic": "action_conflict", "timing": "avoid_push", "stage": "ambiguous", "question": "what-did-i-do-wrong", "contact": "blocked", "risk": "self-blaming"},
    {"slug": "ambiguous-saturn-stay-shared-space", "dynamic": "saturn_pressure", "timing": "observe_only", "stage": "ambiguous", "question": "stay-or-let-go", "contact": "living-or-working-together", "risk": "anxious"},
    {"slug": "ambiguous-identity-any-chance-still-contact", "dynamic": "identity_rhythm", "timing": "low_pressure_message", "stage": "ambiguous", "question": "any-chance", "contact": "still-in-contact", "risk": "calm"},
    {"slug": "ambiguous-outer-still-love-occasional", "dynamic": "outer_intensity", "timing": "not_calculated", "stage": "ambiguous", "question": "still-love-me", "contact": "occasional-contact", "risk": "anxious"},
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def aspect_strength(aspect: dict[str, Any]) -> float:
    max_orb = float(aspect.get("max_orb") or 10)
    orb = float(aspect.get("orb") or 0)
    exactness = max(0.0, min(1.0, 1 - orb / max_orb))
    if aspect.get("applying"):
        exactness += 0.04
    return round(max(0.0, min(1.0, exactness)), 3)


def signal_id_for_aspect(aspect: dict[str, Any]) -> str:
    points = {str(aspect.get("person_a_point") or ""), str(aspect.get("person_b_point") or "")}
    pair_id = PAIR_TO_SIGNAL_ID.get(frozenset(points))
    if pair_id:
        return pair_id
    if points.intersection(OUTER_PLANETS) and points.intersection(PERSONAL_POINTS):
        return "western-aspects-outer-planet-intensity-families"
    if "Saturn" in points:
        return "western-aspects-saturn-pressure"
    return "western-synastry"


def build_aspects(dynamic: str) -> list[dict[str, Any]]:
    aspects = []
    for point_a, point_b, aspect_name, orb, applying in ASPECT_PROFILES[dynamic]:
        aspects.append(
            {
                "applying": applying,
                "aspect": aspect_name,
                "eligible_for_signal": True,
                "max_orb": 10.0,
                "orb": orb,
                "person_a_point": point_a,
                "person_b_point": point_b,
                "time_sensitive": point_a in {"Moon", "Asc", "Desc"} or point_b in {"Moon", "Asc", "Desc"},
            }
        )
    return aspects


def build_candidate_signals(aspects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strongest_by_id: dict[str, float] = {}
    evidence_by_id: dict[str, list[dict[str, Any]]] = {}
    for aspect in aspects:
        signal_id = signal_id_for_aspect(aspect)
        if signal_id == "western-synastry":
            continue
        strength = aspect_strength(aspect)
        strongest_by_id[signal_id] = max(strongest_by_id.get(signal_id, 0.0), strength)
        evidence_by_id.setdefault(signal_id, []).append(
            {
                "aspect": aspect["aspect"],
                "orb": aspect["orb"],
                "person_a_point": aspect["person_a_point"],
                "person_b_point": aspect["person_b_point"],
            }
        )
    return [
        {
            "id": signal_id,
            "label": SIGNAL_LABELS.get(signal_id, signal_id),
            "strength": strength,
            "evidence": evidence_by_id.get(signal_id, []),
        }
        for signal_id, strength in sorted(strongest_by_id.items(), key=lambda item: item[1], reverse=True)
    ]


def expand_counts(counts: dict[str, int]) -> list[str]:
    items: list[str] = []
    for key, count in counts.items():
        items.extend([key] * int(count))
    return items


def timing_profile_label(category: str) -> str:
    return {
        "communication_window": "水星溝通窗口",
        "communication_pressure": "水星溝通壓力",
        "softening": "金星緩和窗口",
        "relationship_focus": "關係感受被帶到前台",
        "activation_pressure": "火星啟動刺激",
        "pressure": "土星壓力觸發",
        "background": "背景行運",
    }.get(category, "背景行運")


def timing_relationship_meaning(band: str, category: str) -> str:
    if category in {"communication_window", "softening", "relationship_focus"} and band != "avoid":
        return "這段氣候比較適合短、輕、可退場的互動；重點是測試對話能不能自然接住。"
    if category in {"pressure", "activation_pressure", "communication_pressure"}:
        return "這段氣候容易放大壓力、急迫或防衛；先降低刺激，不把焦急當成行動指令。"
    return "這段氣候適合觀察關係是否自然恢復流動，不適合把單次互動直接當成結論。"


def build_day_summaries(profile_key: str, analysis_date: str) -> list[dict[str, Any]]:
    profile = TIMING_PROFILES[profile_key]
    sample_count = int(profile["sample_count"])
    if not sample_count:
        return []
    categories = expand_counts(profile["category_counts"])
    bands = (
        ["better"] * int(profile["better_count"])
        + ["neutral"] * int(profile["neutral_count"])
        + ["avoid"] * int(profile["avoid_count"])
    )
    if len(categories) != sample_count or len(bands) != sample_count:
        raise ValueError(f"Timing profile {profile_key} has inconsistent counts.")
    start = date.fromisoformat(analysis_date)
    rows = []
    for index, (category, band) in enumerate(zip(categories, bands)):
        day = start + timedelta(days=index * 4)
        better_score = 1.3 if band == "better" else 0.8 if band == "neutral" else 0.35
        avoid_score = 1.35 if band == "avoid" else 0.7 if band == "neutral" else 0.3
        rows.append(
            {
                "band": band,
                "date": day.isoformat(),
                "profile": {
                    "confidence": "medium",
                    "relationship_meaning": timing_relationship_meaning(band, category),
                    "strongest_aspect": "Trine" if band == "better" else "Square" if band == "avoid" else "Sextile",
                    "strongest_category": category,
                    "strongest_label": timing_profile_label(category),
                    "strongest_natal_point": "Mercury" if "communication" in category else "Venus" if category in {"softening", "relationship_focus"} else "Mars" if category == "activation_pressure" else "Saturn" if category == "pressure" else "Moon",
                    "strongest_transit_point": "Mercury" if "communication" in category else "Venus" if category in {"softening", "relationship_focus"} else "Mars" if category == "activation_pressure" else "Saturn" if category == "pressure" else "Jupiter",
                    "window_label": "有低壓靠近窗口" if band == "better" else "先降速，不急著推進" if band == "avoid" else "觀察為主",
                },
                "score": round(better_score - avoid_score, 3),
                "score_components": {"avoid": avoid_score, "better": better_score},
                "strongest_category": category,
            }
        )
    return rows


def build_windows(day_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not day_summaries:
        return []
    windows: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for row in day_summaries:
        if current and row["band"] != current[-1]["band"]:
            windows.append(window_from_rows(current))
            current = []
        current.append(row)
    if current:
        windows.append(window_from_rows(current))
    return windows


def window_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "band": rows[0]["band"],
        "dominant_categories": [str(row.get("strongest_category") or "background") for row in rows],
        "end_date": rows[-1]["date"],
        "max_score": max(float(row.get("score") or 0) for row in rows),
        "sample_count": len(rows),
        "start_date": rows[0]["date"],
    }


def build_timing_scan(profile_key: str, analysis_date: str) -> dict[str, Any]:
    profile = TIMING_PROFILES[profile_key]
    day_summaries = build_day_summaries(profile_key, analysis_date)
    top_band = str(profile["top_band"])
    if int(profile["sample_count"]):
        free_summary = f"未來掃描偏向{top_band}；better={profile['better_count']}、avoid={profile['avoid_count']}、neutral={profile['neutral_count']}，fixture 不提供精準日期。"
    else:
        free_summary = "本次 V2 fixture 不提供未來三個月 timing scan；改用當下行運氣候與合盤壓力回答。"
    return {
        "avoid_count": int(profile["avoid_count"]),
        "avoid_window_count": sum(1 for window in build_windows(day_summaries) if window["band"] == "avoid"),
        "better_count": int(profile["better_count"]),
        "better_window_count": sum(1 for window in build_windows(day_summaries) if window["band"] == "better"),
        "category_counts": dict(profile["category_counts"]),
        "day_summaries": day_summaries,
        "free_summary": free_summary,
        "granularity_days": 4,
        "method": "western-transit-window-scan-v1-v2-depth-fixture",
        "neutral_count": int(profile["neutral_count"]),
        "paid_detail_locked": True,
        "sample_count": int(profile["sample_count"]),
        "scan_days": 60 if int(profile["sample_count"]) else 0,
        "top_band": top_band,
        "windows": build_windows(day_summaries),
    }


def build_context(spec: dict[str, str], index: int) -> dict[str, str]:
    analysis_date = (date(2026, 6, 25) + timedelta(days=index * 3)).isoformat()
    return {
        "analysis_date": analysis_date,
        "analysis_timezone": "Asia/Taipei",
        "contact_status": spec["contact"],
        "desired_outcome": QUESTION_TO_OUTCOME[spec["question"]],
        "emotional_risk": spec["risk"],
        "main_question": spec["question"],
        "relationship_length": "1-3y" if spec["stage"] in {"cold-war", "crisis"} else "6-12m",
        "relationship_stage": spec["stage"],
        "who_initiated": "them" if spec["contact"] in {"blocked", "no-contact"} else "unclear",
    }


def update_selection(fixture: dict[str, Any], context: dict[str, str], signals: list[dict[str, Any]]) -> None:
    selected_ids = [
        f"context-stage-{context['relationship_stage']}",
        f"context-question-{context['main_question']}",
    ]
    if signals:
        selected_ids.append(str(signals[0]["id"]))
    fixture["selection"] = {
        "budget": {
            "max_claims_warn": 20,
            "max_expanded_recommended": 3,
            "max_primary": 4,
        },
        "dropped_candidates": [],
        "input": {
            "main_question": context["main_question"],
            "mode": "western-only",
            "product_surface": "paid-v2-depth-fixture",
            "stage": context["relationship_stage"],
        },
        "missing_slots": [],
        "selected_primary_ids": selected_ids,
        "slot_assignments": [
            {
                "article_id": f"context-stage-{context['relationship_stage']}",
                "cluster": "western_astrology",
                "components": {"signal_strength": 1.0},
                "rank_reason": ["relationship_stage_context"],
                "slot": "stage",
            },
            {
                "article_id": f"context-question-{context['main_question']}",
                "cluster": "western_astrology",
                "components": {"signal_strength": 1.0},
                "rank_reason": ["main_question_context"],
                "slot": "question",
            },
        ],
    }
    if signals:
        fixture["selection"]["slot_assignments"].append(
            {
                "article_id": str(signals[0]["id"]),
                "cluster": "western_astrology",
                "components": {"signal_strength": float(signals[0]["strength"])},
                "rank_reason": ["v2_depth_target_dynamic", "relationship_relevant_inter_aspect"],
                "slot": "western_core",
            }
        )


def build_fixture(seed: dict[str, Any], spec: dict[str, str], index: int) -> dict[str, Any]:
    fixture = copy.deepcopy(seed)
    fixture_id = f"{GENERATED_PREFIX}{index:02d}-{spec['slug']}"
    context = build_context(spec, index)
    aspects = build_aspects(spec["dynamic"])
    signals = build_candidate_signals(aspects)
    timing_scan = build_timing_scan(spec["timing"], context["analysis_date"])

    fixture["reading_id"] = fixture_id
    fixture["context"] = context
    fixture["runtime_context"] = {
        "analysis_date": context["analysis_date"],
        "analysis_datetime": "",
        "analysis_timezone": context["analysis_timezone"],
        "contact_status": context["contact_status"],
        "desired_outcome": context["desired_outcome"],
        "emotional_risk": context["emotional_risk"],
        "main_question": context["main_question"],
        "relationship_stage": context["relationship_stage"],
    }
    fixture.setdefault("candidate_signals", {})["western_signals"] = signals
    fixture.setdefault("western", {}).setdefault("synastry", {})["inter_aspects"] = aspects
    fixture["western"]["synastry"]["inter_aspect_count"] = len(aspects)
    fixture.setdefault("western", {}).setdefault("analysis", {})["timing_window_scan"] = timing_scan
    fixture.setdefault("western", {}).setdefault("transits", {})["target_date"] = context["analysis_date"]
    fixture["western"]["transits"]["timezone"] = context["analysis_timezone"]
    fixture.setdefault("debug", {}).setdefault("western_analysis", {})["timing_window_scan"] = timing_scan
    fixture["debug"]["v2_depth_fixture"] = {
        "version": "relationship-depth-fixtures-v2",
        "generated_at": GENERATED_AT,
        "source_seed": SEED_BY_QUESTION[spec["question"]],
        "target_dynamic": spec["dynamic"],
        "target_timing_action": spec["timing"],
        "synthetic_scope": "synastry_aspect_profile_and_timing_scan_for_interpretation_depth_coverage",
    }
    update_selection(fixture, context, signals)
    return fixture


def manifest_entry(fixture: dict[str, Any], spec: dict[str, str], index: int) -> dict[str, Any]:
    context = fixture["context"]
    signals = fixture.get("candidate_signals", {}).get("western_signals") or []
    return {
        "id": fixture["reading_id"],
        "file": f"{fixture['reading_id']}.json",
        "seed": f"{SEED_BY_QUESTION[spec['question']]}.json",
        "stage": context["relationship_stage"],
        "question": context["main_question"],
        "contact_status": context["contact_status"],
        "emotional_risk": context["emotional_risk"],
        "desired_outcome": context["desired_outcome"],
        "intended_dynamic": spec["dynamic"],
        "timing_profile": spec["timing"],
        "dominant_signal_ids": [str(signal.get("id") or "") for signal in signals[:4]],
        "notes": "Synthetic V2 depth fixture derived from a seed calculation; use for interpretation and frontend regression coverage, not as a new birth-data calculation.",
        "order": index,
    }


def validate_case_matrix(cases: list[dict[str, Any]]) -> None:
    if not 25 <= len(cases) <= 40:
        raise ValueError(f"Expected 25-40 V2 fixtures, got {len(cases)}")
    for key, minimum in (
        ("stage", 4),
        ("question", 5),
        ("contact_status", 5),
        ("intended_dynamic", 7),
        ("timing_profile", 5),
    ):
        counts = Counter(str(case[key]) for case in cases)
        if len(counts) < minimum:
            raise ValueError(f"{key} coverage too narrow: {counts}")


def main() -> int:
    seeds = {
        seed_name: read_json(CALCULATION_DIR / f"{seed_name}.json")
        for seed_name in sorted(set(SEED_BY_QUESTION.values()))
    }
    cases = []
    for index, spec in enumerate(CASE_SPECS, start=1):
        seed_name = SEED_BY_QUESTION[spec["question"]]
        fixture = build_fixture(seeds[seed_name], spec, index)
        output_path = CALCULATION_DIR / f"{fixture['reading_id']}.json"
        write_json(output_path, fixture)
        cases.append(manifest_entry(fixture, spec, index))

    validate_case_matrix(cases)
    manifest = {
        "version": "relationship-depth-fixtures-v2",
        "generated_at": GENERATED_AT,
        "target_case_count": len(CASE_SPECS),
        "generated_case_count": len(cases),
        "source": "six seed calculation fixtures plus deterministic synthetic V2 depth variants",
        "coverage": {
            "stages": dict(Counter(case["stage"] for case in cases)),
            "questions": dict(Counter(case["question"] for case in cases)),
            "contact_statuses": dict(Counter(case["contact_status"] for case in cases)),
            "intended_dynamics": dict(Counter(case["intended_dynamic"] for case in cases)),
            "timing_profiles": dict(Counter(case["timing_profile"] for case in cases)),
        },
        "cases": cases,
    }
    write_json(MANIFEST_PATH, manifest)
    print(f"Wrote {len(cases)} V2 relationship depth fixtures -> {CALCULATION_DIR.relative_to(ROOT)}")
    print(f"Wrote manifest -> {MANIFEST_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
