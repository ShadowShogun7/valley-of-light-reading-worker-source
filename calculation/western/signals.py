from __future__ import annotations

from typing import Any


PAIR_ARTICLES = {
    frozenset(("Venus", "Saturn")): "western-aspects-venus-saturn",
    frozenset(("Moon", "Saturn")): "western-aspects-moon-saturn",
    frozenset(("Moon", "Venus")): "western-aspects-moon-venus",
    frozenset(("Venus", "Mars")): "western-aspects-venus-mars",
    frozenset(("Sun", "Venus")): "western-aspects-sun-venus",
    frozenset(("Moon", "Moon")): "western-aspects-moon-moon",
    frozenset(("Moon", "Mars")): "western-aspects-moon-mars",
    frozenset(("Venus", "Venus")): "western-aspects-venus-venus",
    frozenset(("Mars", "Mars")): "western-aspects-mars-mars",
    frozenset(("Mercury", "Sun")): "western-aspects-mercury-sun",
    frozenset(("Mercury", "Jupiter")): "western-aspects-mercury-jupiter",
    frozenset(("Sun", "Moon")): "western-aspects-sun-moon",
    frozenset(("Sun", "Mars")): "western-aspects-sun-mars",
    frozenset(("Sun", "Saturn")): "western-aspects-sun-saturn",
    frozenset(("Mars", "Saturn")): "western-aspects-mars-saturn",
    frozenset(("Mercury", "Mercury")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Moon")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Venus")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Mars")): "western-aspects-mercury-contacts",
    frozenset(("Mercury", "Saturn")): "western-aspects-mercury-contacts",
}

ASPECT_WEIGHT = {
    "Conjunction": 1.0,
    "Opposition": 0.96,
    "Square": 0.92,
    "Trine": 0.86,
    "Sextile": 0.82,
}

SATURN_PERSONAL_POINTS = {"Sun", "Moon", "Venus", "Mars"}
OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
PERSONAL_RELATIONSHIP_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter"}
TRANSIT_POINT_WEIGHT = {
    "Saturn": 1.0,
    "Mercury": 0.74,
    "Venus": 0.82,
    "Mars": 0.78,
    "Moon": 0.56,
    "Sun": 0.5,
}
TRANSIT_NATAL_WEIGHT = {
    "Moon": 1.0,
    "Venus": 0.96,
    "Mars": 0.88,
    "Mercury": 0.86,
    "Sun": 0.84,
    "Saturn": 0.72,
}
POINT_LABELS = {
    "Sun": "太陽",
    "Moon": "月亮",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
    "Uranus": "天王星",
    "Neptune": "海王星",
    "Pluto": "冥王星",
}
ASPECT_LABELS = {
    "Conjunction": "合相",
    "Opposition": "對分相",
    "Square": "四分相",
    "Trine": "三分相",
    "Sextile": "六分相",
}


def strength_for_aspect(aspect: dict[str, Any]) -> float:
    max_orb = float(aspect.get("max_orb") or 8.0)
    orb = float(aspect.get("orb") or max_orb)
    closeness = max(0.0, 1.0 - min(1.0, orb / max_orb))
    aspect_weight = ASPECT_WEIGHT.get(str(aspect.get("aspect")), 0.75)
    return round(max(0.35, min(0.99, 0.45 + (0.54 * closeness * aspect_weight))), 3)


def strength_for_transit(aspect: dict[str, Any]) -> float:
    base = strength_for_aspect(aspect)
    transit_weight = TRANSIT_POINT_WEIGHT.get(str(aspect.get("transit_point")), 0.5)
    natal_weight = TRANSIT_NATAL_WEIGHT.get(str(aspect.get("natal_point")), 0.7)
    score = base * transit_weight * natal_weight
    if aspect.get("time_sensitive"):
        score *= 0.86
    return round(max(0.24, min(0.94, score)), 3)


def add_signal(
    signals: dict[str, dict[str, Any]],
    article_id: str,
    strength: float,
    reason: str,
    evidence: dict[str, Any],
) -> None:
    current = signals.get(article_id)
    if current is None:
        signals[article_id] = {
            "id": article_id,
            "strength": strength,
            "reason": reason,
            "evidence": [evidence],
        }
        return
    current["strength"] = max(current["strength"], strength)
    current.setdefault("evidence", []).append(evidence)


def transit_category(aspect: dict[str, Any]) -> str:
    transit_point = str(aspect.get("transit_point") or "")
    natal_point = str(aspect.get("natal_point") or "")
    aspect_type = str(aspect.get("aspect") or "")
    hard = aspect_type in {"Conjunction", "Opposition", "Square"}
    soft = aspect_type in {"Trine", "Sextile"}
    if transit_point == "Mercury" and natal_point in {"Sun", "Moon", "Mercury", "Venus"}:
        return "communication_pressure" if aspect_type in {"Opposition", "Square"} else "communication_window"
    if transit_point == "Mercury" and natal_point in {"Mars", "Saturn"}:
        return "communication_pressure" if hard else "communication_window"
    if transit_point == "Saturn" and natal_point in SATURN_PERSONAL_POINTS:
        return "pressure"
    if transit_point == "Mars" and hard:
        return "activation_pressure"
    if transit_point == "Venus" and soft:
        return "softening"
    if transit_point == "Venus" and natal_point in {"Moon", "Venus", "Mars", "Sun"}:
        return "relationship_focus"
    if transit_point == "Moon":
        return "emotional_weather"
    return "background"


def transit_category_label(category: str) -> str:
    return {
        "communication_window": "水星溝通窗口",
        "communication_pressure": "水星溝通壓力",
        "pressure": "土星壓力觸發",
        "activation_pressure": "火星行動壓力",
        "softening": "金星緩和窗口",
        "relationship_focus": "關係感受被帶到前台",
        "emotional_weather": "短期情緒天氣",
        "background": "背景行運",
    }.get(category, category)


def transit_emotional_meaning(category: str) -> str:
    if category == "communication_window":
        return "行運水星提供比較清楚的訊息與對話節奏，適合低壓說明，但不保證對方一定回覆。"
    if category == "communication_pressure":
        return "行運水星觸發溝通壓力時，訊息容易變成辯論、誤解或防衛，適合先修語氣再行動。"
    if category == "pressure":
        return "行運土星觸發個人關係點時，責任、距離和界線會讓回應變得比較保守；有在意也可能先退回安全距離。"
    if category == "activation_pressure":
        return "行運火星會把衝動、焦急或想立刻得到答案的感覺放大，適合控速，不適合硬碰硬。"
    if category == "softening":
        return "行運金星提供比較柔和的靠近氣候，適合低壓釋放善意，但仍不代表對方一定回頭。"
    if category == "relationship_focus":
        return "關係感受被帶到前台，容易重新在意彼此的吸引、好感或被看見需求。"
    if category == "emotional_weather":
        return "這是短期情緒天氣，能描述當天感受被觸動，但不適合當成長期結論。"
    return "目前行運提供背景線索，需與本命需求、合盤相位和當下關係階段一起看。"


def transit_aspect_sentence(aspect: dict[str, Any]) -> str:
    transit_point = str(aspect.get("transit_point") or "")
    natal_point = str(aspect.get("natal_point") or "")
    aspect_type = str(aspect.get("aspect") or "")
    transit_label = POINT_LABELS.get(transit_point, transit_point)
    natal_label = POINT_LABELS.get(natal_point, natal_point)
    aspect_label = ASPECT_LABELS.get(aspect_type, aspect_type or "相位")
    orb = aspect.get("orb")
    person_label = "你" if aspect.get("person") == "person_a" else "對方"
    return f"行運{transit_label}與{person_label}本命{natal_label}形成{aspect_label}，orb 約 {orb}°。"


def western_timing_profile(transits: dict[str, Any] | None) -> dict[str, Any] | None:
    if not transits:
        return None

    all_aspects: list[dict[str, Any]] = []
    for person_key in ("person_a", "person_b"):
        chart = transits.get(person_key) or {}
        for aspect in chart.get("transit_aspects") or []:
            if not aspect.get("eligible_for_timing"):
                continue
            category = transit_category(aspect)
            score = strength_for_transit(aspect)
            if category == "background" and score < 0.5:
                continue
            all_aspects.append(
                {
                    **aspect,
                    "person": person_key,
                    "category": category,
                    "category_label": transit_category_label(category),
                    "timing_strength": score,
                    "technical_summary": transit_aspect_sentence({**aspect, "person": person_key}),
                    "emotional_meaning": transit_emotional_meaning(category),
                }
            )

    triggers = sorted(all_aspects, key=lambda item: (-float(item.get("timing_strength", 0)), float(item.get("orb", 99))))[:8]
    strongest = triggers[0] if triggers else None
    pressure_count = sum(1 for item in triggers if item.get("category") in {"pressure", "activation_pressure", "communication_pressure"})
    softening_count = sum(1 for item in triggers if item.get("category") in {"softening", "relationship_focus"})
    communication_count = sum(1 for item in triggers if item.get("category") == "communication_window")

    if not strongest:
        window_label = "西洋行運偏背景"
        relationship_meaning = "目前西洋行運沒有讀到強觸發，先以本命需求與合盤主訊號作主判斷。"
        confidence = "low"
    elif pressure_count and pressure_count >= softening_count:
        window_label = "先降速，不急著推進"
        relationship_meaning = "西洋行運正在觸發壓力、責任或界線感，短期更適合降低壓迫感，觀察對方是否能自然回應。"
        confidence = "medium"
    elif communication_count and communication_count >= softening_count:
        window_label = "有溝通整理窗口"
        relationship_meaning = "西洋行運帶出較清楚的溝通節奏，適合低壓整理訊息，但不適合要求對方立刻表態。"
        confidence = "medium"
    elif softening_count:
        window_label = "有低壓靠近窗口"
        relationship_meaning = "西洋行運帶出較柔和的關係觸發，適合低壓釋放善意，但不適合一次要求明確承諾。"
        confidence = "medium"
    else:
        window_label = "短期情緒被觸動"
        relationship_meaning = "西洋行運有短期情緒觸發，可以說明為什麼近期比較在意，但不宜直接當成復合保證。"
        confidence = "low"

    return {
        "method": "western_current_transits_v1",
        "confidence": confidence,
        "target_date": transits.get("target_date"),
        "transits": transits,
        "relationship_triggers": triggers,
        "strongest_trigger": strongest,
        "window_label": window_label,
        "relationship_meaning": relationship_meaning,
        "technical_summary": western_timing_summary(transits, strongest, window_label),
        "limits": [
            "目前使用分析日中午行運盤與本命個人點相位。",
            "尚未接入 composite、Davison、secondary progressions 或精準月內窗口搜尋。",
        ],
    }


TIMING_BAND_SCORES = {
    "communication_window": 0.72,
    "softening": 0.82,
    "relationship_focus": 0.64,
    "emotional_weather": 0.22,
    "communication_pressure": -0.58,
    "activation_pressure": -0.78,
    "pressure": -0.9,
}


def timing_band_for_profile(profile: dict[str, Any] | None) -> tuple[str, float, dict[str, float]]:
    if not profile:
        return "neutral", 0.0, {"better": 0.0, "avoid": 0.0}

    better = 0.0
    avoid = 0.0
    for trigger in profile.get("relationship_triggers") or []:
        if not isinstance(trigger, dict):
            continue
        category = str(trigger.get("category") or "background")
        strength = float(trigger.get("timing_strength") or 0)
        score = TIMING_BAND_SCORES.get(category, 0.0) * strength
        if score >= 0:
            better += score
        else:
            avoid += abs(score)

    net = better - avoid
    if better >= 0.45 and net >= 0.18:
        return "better", round(net, 3), {"better": round(better, 3), "avoid": round(avoid, 3)}
    if avoid >= 0.45 and net <= -0.18:
        return "avoid", round(net, 3), {"better": round(better, 3), "avoid": round(avoid, 3)}
    return "neutral", round(net, 3), {"better": round(better, 3), "avoid": round(avoid, 3)}


def strongest_category(profile: dict[str, Any] | None) -> str:
    if not profile:
        return "background"
    trigger = profile.get("strongest_trigger") or {}
    return str(trigger.get("category") or "background")


def compact_timing_profile(profile: dict[str, Any] | None) -> dict[str, Any]:
    if not profile:
        return {
            "confidence": "low",
            "window_label": "西洋行運偏背景",
            "relationship_meaning": "目前沒有讀到強 timing 觸發。",
            "strongest_category": "background",
        }
    strongest = profile.get("strongest_trigger") or {}
    return {
        "confidence": profile.get("confidence") or "low",
        "window_label": profile.get("window_label") or "",
        "relationship_meaning": profile.get("relationship_meaning") or "",
        "strongest_category": strongest_category(profile),
        "strongest_label": strongest.get("category_label"),
        "strongest_transit_point": strongest.get("transit_point"),
        "strongest_natal_point": strongest.get("natal_point"),
        "strongest_aspect": strongest.get("aspect"),
    }


def compress_timing_bands(day_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for summary in day_summaries:
        band = str(summary.get("band") or "neutral")
        if current is None or current.get("band") != band:
            if current:
                windows.append(current)
            current = {
                "band": band,
                "start_date": summary.get("date"),
                "end_date": summary.get("date"),
                "sample_count": 1,
                "max_score": float(summary.get("score") or 0),
                "dominant_categories": [summary.get("strongest_category") or "background"],
            }
            continue
        current["end_date"] = summary.get("date")
        current["sample_count"] = int(current.get("sample_count") or 0) + 1
        current["max_score"] = max(float(current.get("max_score") or 0), float(summary.get("score") or 0))
        current.setdefault("dominant_categories", []).append(summary.get("strongest_category") or "background")
    if current:
        windows.append(current)
    return windows


def timing_scan_public_summary(scan: dict[str, Any]) -> str:
    band = str(scan.get("top_band") or "neutral")
    better = int(scan.get("better_count") or 0)
    avoid = int(scan.get("avoid_count") or 0)
    communication = int((scan.get("category_counts") or {}).get("communication_window") or 0)
    if band == "better":
        return f"未來掃描偏向有低壓窗口；better 樣本 {better} 個，其中 Mercury 溝通訊號 {communication} 個。"
    if band == "avoid":
        return f"未來掃描偏向先避開高壓推進；avoid 樣本 {avoid} 個，免費頁不提供精準日期。"
    return "未來掃描偏中性；可觀察低壓窗口，但免費頁不提供精準日期。"


def build_timing_window_scan(samples: list[dict[str, Any]], scan_days: int, step_days: int) -> dict[str, Any]:
    day_summaries: list[dict[str, Any]] = []
    category_counts: dict[str, int] = {}
    for sample in samples:
        transits = {
            "engine": "immanuel",
            "target_date": sample.get("date"),
            "person_a": sample.get("person_a") or {},
            "person_b": sample.get("person_b") or {},
        }
        profile = western_timing_profile(transits)
        band, score, components = timing_band_for_profile(profile)
        category = strongest_category(profile)
        category_counts[category] = category_counts.get(category, 0) + 1
        day_summaries.append(
            {
                "date": sample.get("date"),
                "band": band,
                "score": score,
                "score_components": components,
                "strongest_category": category,
                "profile": compact_timing_profile(profile),
            }
        )

    band_counts = {
        "better": sum(1 for item in day_summaries if item.get("band") == "better"),
        "neutral": sum(1 for item in day_summaries if item.get("band") == "neutral"),
        "avoid": sum(1 for item in day_summaries if item.get("band") == "avoid"),
    }
    top_band = max(band_counts, key=lambda band: band_counts[band]) if day_summaries else "neutral"
    windows = compress_timing_bands(day_summaries)
    better_windows = [window for window in windows if window.get("band") == "better"]
    avoid_windows = [window for window in windows if window.get("band") == "avoid"]

    return {
        "method": "western-transit-window-scan-v1",
        "scan_days": scan_days,
        "granularity_days": step_days,
        "sample_count": len(day_summaries),
        "top_band": top_band,
        "better_count": band_counts["better"],
        "neutral_count": band_counts["neutral"],
        "avoid_count": band_counts["avoid"],
        "category_counts": dict(sorted(category_counts.items())),
        "better_window_count": len(better_windows),
        "avoid_window_count": len(avoid_windows),
        "windows": windows,
        "day_summaries": day_summaries,
        "free_summary": timing_scan_public_summary(
            {
                "top_band": top_band,
                "better_count": band_counts["better"],
                "avoid_count": band_counts["avoid"],
                "category_counts": category_counts,
            }
        ),
        "paid_detail_locked": True,
    }


def western_timing_summary(transits: dict[str, Any], strongest: dict[str, Any] | None, window_label: str) -> str:
    target_date = transits.get("target_date") or "分析日"
    if not strongest:
        return f"西洋行運以{target_date}中午盤檢查；未讀到強觸發，時間層暫作背景。"
    return f"西洋行運以{target_date}中午盤檢查；最明顯是{strongest.get('technical_summary')} 屬於「{strongest.get('category_label')}」，時間判斷暫定為「{window_label}」。"


def build_candidate_signals(
    synastry: dict[str, Any],
    transits: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signals: dict[str, dict[str, Any]] = {}
    considered = 0
    skipped_time_sensitive = 0

    for aspect in synastry.get("inter_aspects") or []:
        if not aspect.get("eligible_for_signal"):
            if aspect.get("time_sensitive"):
                skipped_time_sensitive += 1
            continue
        considered += 1
        pair = frozenset((aspect.get("person_a_point"), aspect.get("person_b_point")))
        strength = strength_for_aspect(aspect)
        article_id = PAIR_ARTICLES.get(pair)
        if article_id:
            add_signal(
                signals,
                article_id,
                strength,
                "relationship_relevant_inter_aspect",
                aspect,
            )
        elif pair.intersection(OUTER_PLANETS) and pair.intersection(PERSONAL_RELATIONSHIP_POINTS):
            add_signal(
                signals,
                "western-aspects-outer-planet-intensity-families",
                max(0.5, strength - 0.05),
                "guarded_outer_planet_intensity",
                aspect,
            )
        if "Saturn" in pair and pair.intersection(SATURN_PERSONAL_POINTS):
            add_signal(
                signals,
                "western-aspects-saturn-pressure",
                max(0.55, strength - 0.08),
                "saturn_contacts_personal_point",
                aspect,
            )

    analysis = {
        "eligible_inter_aspects_considered": considered,
        "time_sensitive_aspects_skipped": skipped_time_sensitive,
        "timing_profile": western_timing_profile(transits),
    }
    return sorted(signals.values(), key=lambda item: (-item["strength"], item["id"])), analysis
