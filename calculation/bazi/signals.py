from __future__ import annotations

from typing import Any


STEM_ELEMENT = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}

ELEMENT_GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}

ELEMENT_CONTROLS = {
    "木": "土",
    "土": "水",
    "水": "火",
    "火": "金",
    "金": "木",
}

BRANCH_ELEMENTS = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}

CLASH_PAIRS = {frozenset(pair) for pair in ("子午", "丑未", "寅申", "卯酉", "辰戌", "巳亥")}
COMBINATION_PAIRS = {frozenset(pair) for pair in ("子丑", "寅亥", "卯戌", "辰酉", "巳申", "午未")}
HARM_PAIRS = {frozenset(pair) for pair in ("子未", "丑午", "寅巳", "卯辰", "申亥", "酉戌")}
TRIAD_GROUPS = {
    "水": ("申", "子", "辰"),
    "木": ("亥", "卯", "未"),
    "火": ("寅", "午", "戌"),
    "金": ("巳", "酉", "丑"),
}
PILLAR_LABELS = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "時柱"}
VISIBLE_STEM_WEIGHTS = {"year": 0.8, "month": 1.2, "day": 1.0, "hour": 0.9}
BRANCH_MAIN_WEIGHTS = {"year": 0.55, "month": 2.6, "day": 1.1, "hour": 0.7}
HIDDEN_STEM_WEIGHTS = {"year": 0.25, "month": 0.6, "day": 0.45, "hour": 0.35}
TRADITIONAL_TEN_GODS = {
    "七杀": "七殺",
    "正财": "正財",
    "偏财": "偏財",
    "伤官": "傷官",
    "劫财": "劫財",
}

DAY_MASTER_ARTICLES = {
    "甲": "bazi-tiangan-jia-mu",
    "乙": "bazi-tiangan-yi-mu",
    "丙": "bazi-tiangan-bing-huo",
    "丁": "bazi-tiangan-ding-huo",
    "己": "bazi-tiangan-ji-tu",
    "辛": "bazi-tiangan-xin-jin",
}


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
            "strength": round(max(0.2, min(1.0, strength)), 3),
            "reason": reason,
            "evidence": [evidence],
        }
        return
    current["strength"] = max(current["strength"], round(max(0.2, min(1.0, strength)), 3))
    current.setdefault("evidence", []).append(evidence)


def traditional_ten_god(value: Any) -> str:
    text = str(value)
    return TRADITIONAL_TEN_GODS.get(text, text)


def spouse_star_targets(gender: str | None) -> set[str]:
    gender = str(gender or "").lower()
    if gender in {"female", "woman", "女"}:
        return {"正官", "七殺"}
    if gender in {"male", "man", "男"}:
        return {"正財", "偏財"}
    return {"正官", "七殺", "正財", "偏財"}


def spouse_role_targets(gender: str | None) -> set[str]:
    gender = str(gender or "").lower()
    if gender in {"female", "woman", "女"}:
        return {"officer"}
    if gender in {"male", "man", "男"}:
        return {"wealth"}
    return {"officer", "wealth"}


def flatten_ten_gods(lunar_chart: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for group_name in ("ten_gods_stems", "ten_gods_hidden"):
        group = lunar_chart.get(group_name) or {}
        for value in group.values():
            if isinstance(value, list):
                values.extend(traditional_ten_god(item) for item in value if item)
            elif value:
                values.append(traditional_ten_god(value))
    return values


def spouse_star_positions(person_key: str, chart: dict[str, Any], gender: str | None) -> dict[str, Any]:
    lunar_chart = chart.get("lunar_python") or {}
    wanted = spouse_star_targets(gender)
    stem_gods = lunar_chart.get("ten_gods_stems") or {}
    hidden_gods = lunar_chart.get("ten_gods_hidden") or {}
    hidden_stems = lunar_chart.get("hidden_stems") or {}
    pillars = lunar_chart.get("pillars") or {}
    visible: list[dict[str, Any]] = []
    hidden: list[dict[str, Any]] = []

    for pillar, value in stem_gods.items():
        god = traditional_ten_god(value)
        if god not in wanted:
            continue
        pillar_value = str(pillars.get(pillar) or "")
        visible.append(
            {
                "pillar": pillar,
                "pillar_label": PILLAR_LABELS.get(pillar, pillar),
                "god": god,
                "layer": "stem",
                "stem": pillar_value[0] if pillar_value else None,
            }
        )

    for pillar, values in hidden_gods.items():
        if not isinstance(values, list):
            continue
        stems = hidden_stems.get(pillar) if isinstance(hidden_stems.get(pillar), list) else []
        for index, value in enumerate(values):
            god = traditional_ten_god(value)
            if god not in wanted:
                continue
            hidden.append(
                {
                    "pillar": pillar,
                    "pillar_label": PILLAR_LABELS.get(pillar, pillar),
                    "god": god,
                    "layer": "hidden",
                    "stem": stems[index] if index < len(stems) else None,
                }
            )

    gods = sorted({item["god"] for item in [*visible, *hidden]})
    return {
        "person": person_key,
        "gender": str(gender or "").lower() or None,
        "wanted": sorted(wanted),
        "present": bool(visible or hidden),
        "visible": visible,
        "hidden": hidden,
        "matches": [item["god"] for item in [*visible, *hidden]],
        "gods": gods,
        "has_visible": bool(visible),
        "has_hidden": bool(hidden),
        "hidden_only": bool(hidden) and not visible,
        "mixed": len(gods) > 1,
    }


def spouse_star_present(person_key: str, chart: dict[str, Any], gender: str | None) -> dict[str, Any]:
    profile = spouse_star_positions(person_key, chart, gender)
    return {key: profile[key] for key in ("person", "gender", "present", "matches")}


def day_branch_interaction(branch_a: str | None, branch_b: str | None) -> dict[str, Any] | None:
    if not branch_a or not branch_b:
        return None
    pair = frozenset((branch_a, branch_b))
    if pair in CLASH_PAIRS:
        return {"type": "clash", "branches": [branch_a, branch_b], "strength": 0.92}
    if pair in COMBINATION_PAIRS:
        return {"type": "combination", "branches": [branch_a, branch_b], "strength": 0.86}
    if pair in HARM_PAIRS:
        return {"type": "harm", "branches": [branch_a, branch_b], "strength": 0.78}
    return {"type": "none", "branches": [branch_a, branch_b], "strength": 0.45}


def relation_for_branches(branch_a: str | None, branch_b: str | None) -> dict[str, Any] | None:
    if not branch_a or not branch_b:
        return None
    pair = frozenset((branch_a, branch_b))
    if pair in CLASH_PAIRS:
        return {"type": "clash", "type_label": "沖", "strength": 0.92}
    if pair in HARM_PAIRS:
        return {"type": "harm", "type_label": "害", "strength": 0.78}
    if pair in COMBINATION_PAIRS:
        return {"type": "combination", "type_label": "合", "strength": 0.72}
    return None


def branch_positions(chart: dict[str, Any]) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for pillar, data in (chart.get("sxtwl", {}).get("pillars") or {}).items():
        if not data:
            continue
        branch = data.get("zhi")
        if branch:
            positions.append({"pillar": pillar, "pillar_label": PILLAR_LABELS.get(pillar, pillar), "branch": branch})
    return positions


def cross_branch_interactions(a: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    interactions: list[dict[str, Any]] = []
    for pos_a in branch_positions(a):
        for pos_b in branch_positions(b):
            relation = relation_for_branches(pos_a["branch"], pos_b["branch"])
            if not relation:
                continue
            proximity = 0.0
            if pos_a["pillar"] == "day" and pos_b["pillar"] == "day":
                proximity = 0.18
            elif "day" in {pos_a["pillar"], pos_b["pillar"]}:
                proximity = 0.1
            interactions.append(
                {
                    **relation,
                    "person_a_pillar": pos_a["pillar"],
                    "person_a_pillar_label": pos_a["pillar_label"],
                    "person_a_branch": pos_a["branch"],
                    "person_b_pillar": pos_b["pillar"],
                    "person_b_pillar_label": pos_b["pillar_label"],
                    "person_b_branch": pos_b["branch"],
                    "strength": round(min(1.0, relation["strength"] + proximity), 3),
                }
            )
    priority = {"clash": 0, "harm": 1, "combination": 2}
    return sorted(interactions, key=lambda item: (priority.get(item["type"], 9), -float(item["strength"])))


def self_branch_patterns(chart: dict[str, Any]) -> list[dict[str, Any]]:
    branches = [item["branch"] for item in branch_positions(chart)]
    branch_set = set(branches)
    patterns: list[dict[str, Any]] = []
    for element, group in TRIAD_GROUPS.items():
        matched = [branch for branch in group if branch in branch_set]
        if len(matched) >= 3:
            patterns.append({"type": "full_triad", "element": element, "branches": matched, "strength": 0.9})
        elif len(matched) == 2:
            patterns.append({"type": "half_triad", "element": element, "branches": matched, "strength": 0.68})
    return sorted(patterns, key=lambda item: -float(item["strength"]))


def element_tally(chart: dict[str, Any]) -> dict[str, Any]:
    visible = {element: 0 for element in STEM_ELEMENT.values()}
    hidden = {element: 0 for element in STEM_ELEMENT.values()}
    for pillar in (chart.get("sxtwl", {}).get("pillars") or {}).values():
        if pillar and pillar.get("gan_element"):
            visible[pillar["gan_element"]] += 1
    for stems in (chart.get("lunar_python", {}).get("hidden_stems") or {}).values():
        if not isinstance(stems, list):
            continue
        for stem in stems:
            element = STEM_ELEMENT.get(str(stem))
            if element:
                hidden[element] += 1
    total = {element: visible[element] + hidden[element] for element in visible}
    return {"visible": visible, "hidden": hidden, "total": total}


def element_role_for_day_master(day_element: str | None, element: str | None) -> str:
    if not day_element or not element:
        return "unknown"
    if element == day_element:
        return "self"
    if ELEMENT_GENERATES.get(element) == day_element:
        return "resource"
    if ELEMENT_GENERATES.get(day_element) == element:
        return "output"
    if ELEMENT_CONTROLS.get(day_element) == element:
        return "wealth"
    if ELEMENT_CONTROLS.get(element) == day_element:
        return "officer"
    return "unknown"


def role_label(role: str) -> str:
    return {
        "self": "比劫",
        "resource": "印星",
        "output": "食傷",
        "wealth": "財星",
        "officer": "官殺",
    }.get(role, role)


def add_weight(
    roles: dict[str, float],
    elements: dict[str, float],
    sources: list[dict[str, Any]],
    day_element: str | None,
    element: str | None,
    weight: float,
    source: str,
) -> None:
    if not element:
        return
    role = element_role_for_day_master(day_element, element)
    roles[role] = roles.get(role, 0.0) + weight
    elements[element] = elements.get(element, 0.0) + weight
    sources.append({"source": source, "element": element, "role": role, "weight": round(weight, 2)})


def strength_label(score: int) -> str:
    if score >= 72:
        return "過旺"
    if score >= 60:
        return "偏旺"
    if score >= 48:
        return "中和"
    if score >= 38:
        return "稍弱"
    return "偏弱"


def supporting_element_for(day_element: str | None) -> str | None:
    if not day_element:
        return None
    for element, generated in ELEMENT_GENERATES.items():
        if generated == day_element:
            return element
    return None


def balance_elements_for(day_element: str | None, label: str) -> list[str]:
    if not day_element:
        return []
    resource = supporting_element_for(day_element)
    output = ELEMENT_GENERATES.get(day_element)
    wealth = ELEMENT_CONTROLS.get(day_element)
    officer = next((element for element, controlled in ELEMENT_CONTROLS.items() if controlled == day_element), None)
    if label in {"偏弱", "稍弱"}:
        return [element for element in (resource, day_element) if element]
    if label in {"偏旺", "過旺"}:
        return [element for element in (output, wealth, officer) if element]
    return [element for element in (output, resource) if element]


def day_master_strength_profile(person_key: str, chart: dict[str, Any]) -> dict[str, Any]:
    sxtwl_chart = chart.get("sxtwl") or {}
    lunar_chart = chart.get("lunar_python") or {}
    pillars = sxtwl_chart.get("pillars") or {}
    hidden_stems = lunar_chart.get("hidden_stems") or {}
    day_master = sxtwl_chart.get("day_master")
    day_element = sxtwl_chart.get("day_master_element")
    roles: dict[str, float] = {role: 0.0 for role in ("self", "resource", "output", "wealth", "officer")}
    elements: dict[str, float] = {element: 0.0 for element in STEM_ELEMENT.values()}
    sources: list[dict[str, Any]] = []

    for pillar_key, pillar in pillars.items():
        if not isinstance(pillar, dict):
            continue
        stem_element = pillar.get("gan_element")
        add_weight(
            roles,
            elements,
            sources,
            day_element,
            stem_element,
            VISIBLE_STEM_WEIGHTS.get(pillar_key, 0.8),
            f"{PILLAR_LABELS.get(pillar_key, pillar_key)}天干",
        )
        branch = pillar.get("zhi")
        branch_element = BRANCH_ELEMENTS.get(str(branch))
        add_weight(
            roles,
            elements,
            sources,
            day_element,
            branch_element,
            BRANCH_MAIN_WEIGHTS.get(pillar_key, 0.6),
            f"{PILLAR_LABELS.get(pillar_key, pillar_key)}地支主氣",
        )

    for pillar_key, stems in hidden_stems.items():
        if not isinstance(stems, list):
            continue
        for stem in stems:
            add_weight(
                roles,
                elements,
                sources,
                day_element,
                STEM_ELEMENT.get(str(stem)),
                HIDDEN_STEM_WEIGHTS.get(pillar_key, 0.3),
                f"{PILLAR_LABELS.get(pillar_key, pillar_key)}藏干{stem}",
            )

    support = roles.get("self", 0.0) + roles.get("resource", 0.0)
    pressure = roles.get("officer", 0.0) + (roles.get("wealth", 0.0) * 0.85) + (roles.get("output", 0.0) * 0.65)
    raw_score = round(50 + ((support - pressure) * 7.5))
    score = max(18, min(86, raw_score))
    label = strength_label(score)
    balance_elements = balance_elements_for(day_element, label)
    month_pillar = pillars.get("month") if isinstance(pillars.get("month"), dict) else {}
    month_branch = month_pillar.get("zhi") if isinstance(month_pillar, dict) else None
    month_element = BRANCH_ELEMENTS.get(str(month_branch))
    dominant_roles = sorted(
        [{"role": role, "label": role_label(role), "weight": round(weight, 2)} for role, weight in roles.items()],
        key=lambda item: -float(item["weight"]),
    )
    dominant_elements = sorted(
        [{"element": element, "weight": round(weight, 2)} for element, weight in elements.items()],
        key=lambda item: -float(item["weight"]),
    )

    return {
        "person": person_key,
        "method": "v1_weighted_month_branch_visible_hidden",
        "confidence": "medium" if sxtwl_chart.get("birth_precision") == "date_time" else "low",
        "day_master": day_master,
        "day_master_element": day_element,
        "month_branch": month_branch,
        "month_element": month_element,
        "support_score": round(support, 2),
        "pressure_score": round(pressure, 2),
        "strength_score": score,
        "strength_label": label,
        "balance_elements": balance_elements,
        "dominant_roles": dominant_roles,
        "dominant_elements": dominant_elements,
        "source_weights": sorted(sources, key=lambda item: -float(item["weight"]))[:10],
        "technical_summary": (
            f"{day_master}{day_element}日主生於{month_branch or '未知'}月，"
            f"扶身比印約{support:.2f}，洩耗剋約{pressure:.2f}，日主強弱暫判為{label}。"
        ),
        "relationship_meaning": strength_relationship_meaning(label, balance_elements),
    }


def strength_relationship_meaning(label: str, balance_elements: list[str]) -> str:
    elements = "、".join(balance_elements) if balance_elements else "平衡元素"
    if label in {"偏弱", "稍弱"}:
        return f"感情壓力下較需要{elements}來補足承接感，否則容易被對方反應牽著走。"
    if label in {"偏旺", "過旺"}:
        return f"感情壓力下需要{elements}來流通與降硬度，否則容易用控制或防衛維持安全感。"
    return f"日主接近中和，關係判斷更要看互動訊號是否能流通到{elements}。"


def flow_period_profile(
    period: str,
    pillar: dict[str, Any],
    person_key: str,
    chart: dict[str, Any],
    source_person: dict[str, Any],
    strength_profile: dict[str, Any],
) -> dict[str, Any]:
    sxtwl_chart = chart.get("sxtwl") or {}
    day_element = sxtwl_chart.get("day_master_element")
    day_branch = sxtwl_chart.get("day_branch")
    stem = pillar.get("gan")
    branch = pillar.get("zhi")
    stem_element = pillar.get("gan_element")
    branch_element = BRANCH_ELEMENTS.get(str(branch))
    stem_role = element_role_for_day_master(day_element, stem_element)
    branch_role = element_role_for_day_master(day_element, branch_element)
    interaction = relation_for_branches(day_branch, branch)
    balance_elements = set(str(item) for item in strength_profile.get("balance_elements") or [])
    spouse_roles = spouse_role_targets(source_person.get("gender"))
    activates_spouse_role = stem_role in spouse_roles or branch_role in spouse_roles
    supports_balance = bool(balance_elements.intersection({str(stem_element), str(branch_element)}))
    pressure_trigger = bool(interaction and interaction.get("type") in {"clash", "harm"})
    easing_trigger = bool(interaction and interaction.get("type") == "combination")
    score = 0.0
    if activates_spouse_role:
        score += 0.36
    if supports_balance:
        score += 0.24
    if pressure_trigger:
        score += 0.32
    if easing_trigger:
        score += 0.18
    period_weight = {
        "da_yun": 1.15,
        "year": 0.95,
        "month": 1.0,
        "day": 0.56,
    }.get(period, 1.0)
    score *= period_weight

    if pressure_trigger:
        headline = "關係宮位被壓力觸發"
    elif activates_spouse_role and supports_balance:
        headline = "關係星與平衡元素同時被觸發"
    elif activates_spouse_role:
        headline = "關係星被觸發"
    elif supports_balance:
        headline = "平衡元素被帶入"
    elif easing_trigger:
        headline = "關係宮位出現緩和線索"
    else:
        headline = "時間層作背景參考"

    return {
        "period": period,
        "pillar": pillar,
        "person": person_key,
        "stem_role": stem_role,
        "stem_role_label": role_label(stem_role),
        "branch_role": branch_role,
        "branch_role_label": role_label(branch_role),
        "day_branch_interaction": interaction,
        "activates_spouse_role": activates_spouse_role,
        "supports_balance": supports_balance,
        "pressure_trigger": pressure_trigger,
        "easing_trigger": easing_trigger,
        "trigger_score": round(score, 2),
        "headline": headline,
    }


def bazi_timing_profile(
    bazi_people: dict[str, dict[str, Any]],
    source_people: dict[str, dict[str, Any]],
    transits: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not transits:
        return None

    strength_profiles = {
        "person_a": day_master_strength_profile("person_a", bazi_people["person_a"]),
        "person_b": day_master_strength_profile("person_b", bazi_people["person_b"]),
    }
    period_profiles: list[dict[str, Any]] = []
    for period in ("year", "month"):
        pillar = transits.get(period) or {}
        if not pillar:
            continue
        for person_key in ("person_a", "person_b"):
            period_profiles.append(
                flow_period_profile(
                    period,
                    pillar,
                    person_key,
                    bazi_people[person_key],
                    source_people.get(person_key, {}),
                    strength_profiles[person_key],
                )
            )

    relationship_triggers = sorted(
        [profile for profile in period_profiles if profile.get("trigger_score", 0) > 0],
        key=lambda item: -float(item.get("trigger_score", 0)),
    )
    strongest = relationship_triggers[0] if relationship_triggers else None
    pressure_count = sum(1 for item in relationship_triggers if item.get("pressure_trigger"))
    spouse_count = sum(1 for item in relationship_triggers if item.get("activates_spouse_role"))
    balance_count = sum(1 for item in relationship_triggers if item.get("supports_balance"))
    if pressure_count:
        window_label = "先降壓再靠近"
        relationship_meaning = "流年 / 流月已觸發關係壓力點，短期更適合降低刺激與觀察自然回應。"
    elif spouse_count and balance_count:
        window_label = "有條件的低壓窗口"
        relationship_meaning = "流年 / 流月同時帶出關係星與平衡元素，可以作為低壓靠近的背景，但仍不代表保證結果。"
    elif spouse_count:
        window_label = "關係議題被帶到前台"
        relationship_meaning = "流年 / 流月帶出配偶星角色，容易讓關係議題被重新感受到，但是否行動仍要看壓力層。"
    else:
        window_label = "時間層偏背景"
        relationship_meaning = "目前流年 / 流月沒有讀到強觸發，時間層只作背景參考。"

    return {
        "method": "bazi_current_year_month_v1",
        "confidence": "medium",
        "target_date": transits.get("target_date"),
        "transits": transits,
        "period_profiles": period_profiles,
        "relationship_triggers": relationship_triggers[:6],
        "strongest_trigger": strongest,
        "window_label": window_label,
        "relationship_meaning": relationship_meaning,
        "technical_summary": timing_technical_summary(transits, strongest, window_label),
        "limits": [
            "目前只看流年、流月對日主、日支與平衡元素的觸發。",
            "大運、起運與流日另由 bazi_da_yun_liu_ri_v1 補充；本卡不作正式喜忌判定。",
        ],
    }


def bazi_luck_timing_profile(
    bazi_people: dict[str, dict[str, Any]],
    source_people: dict[str, dict[str, Any]],
    transits: dict[str, Any] | None,
) -> dict[str, Any] | None:
    strength_profiles = {
        "person_a": day_master_strength_profile("person_a", bazi_people["person_a"]),
        "person_b": day_master_strength_profile("person_b", bazi_people["person_b"]),
    }
    period_profiles: list[dict[str, Any]] = []
    cycle_summaries: list[dict[str, Any]] = []

    for person_key in ("person_a", "person_b"):
        luck = bazi_people.get(person_key, {}).get("luck_timing") or {}
        if luck.get("status") != "calculated":
            continue
        current_da_yun = luck.get("current_da_yun") or {}
        da_yun_pillar = current_da_yun.get("pillar") or {}
        if da_yun_pillar:
            profile = flow_period_profile(
                "da_yun",
                da_yun_pillar,
                person_key,
                bazi_people[person_key],
                source_people.get(person_key, {}),
                strength_profiles[person_key],
            )
            profile["cycle"] = current_da_yun
            period_profiles.append(profile)
        cycle_summaries.append(
            {
                "person": person_key,
                "direction": luck.get("direction"),
                "start": luck.get("start"),
                "current_da_yun": current_da_yun,
                "current_liu_nian": luck.get("current_liu_nian"),
            }
        )

        day_pillar = (transits or {}).get("day") or {}
        if day_pillar:
            period_profiles.append(
                flow_period_profile(
                    "day",
                    day_pillar,
                    person_key,
                    bazi_people[person_key],
                    source_people.get(person_key, {}),
                    strength_profiles[person_key],
                )
            )

    if not period_profiles and not cycle_summaries:
        return None

    relationship_triggers = sorted(
        [profile for profile in period_profiles if profile.get("trigger_score", 0) > 0],
        key=lambda item: -float(item.get("trigger_score", 0)),
    )
    strongest = relationship_triggers[0] if relationship_triggers else None
    da_yun_trigger = next((item for item in relationship_triggers if item.get("period") == "da_yun"), None)
    day_trigger = next((item for item in relationship_triggers if item.get("period") == "day"), None)
    pressure_count = sum(1 for item in relationship_triggers if item.get("pressure_trigger"))
    spouse_count = sum(1 for item in relationship_triggers if item.get("activates_spouse_role"))
    balance_count = sum(1 for item in relationship_triggers if item.get("supports_balance"))

    if da_yun_trigger and da_yun_trigger.get("pressure_trigger"):
        window_label = "大運背景先降壓"
        relationship_meaning = "目前大運先讀到較長期的關係壓力背景，短期行動要更保守，不能只看一兩天的情緒起伏。"
        confidence = "medium"
    elif da_yun_trigger and da_yun_trigger.get("activates_spouse_role"):
        window_label = "大運帶出關係主題"
        relationship_meaning = "目前大運把關係角色帶到生命主題裡，代表這段關係容易被反覆感受到，但仍要看互動壓力能否下降。"
        confidence = "medium"
    elif da_yun_trigger and da_yun_trigger.get("supports_balance"):
        window_label = "大運帶入平衡元素"
        relationship_meaning = "目前大運帶入命盤較需要的平衡元素，代表長期背景有調整空間，但仍不能直接當成復合時間保證。"
        confidence = "medium"
    elif day_trigger and pressure_count:
        window_label = "流日短期觸動"
        relationship_meaning = "流日有短期壓力觸發，適合把它當作當日情緒天氣，不適合用來做重大關係決定。"
        confidence = "low"
    elif spouse_count:
        window_label = "關係星短期被帶動"
        relationship_meaning = "大運或流日帶出關係星線索，近期容易重新在意關係，但仍不是復合保證。"
        confidence = "medium" if da_yun_trigger else "low"
    elif balance_count:
        window_label = "流日帶入平衡元素"
        relationship_meaning = "流日帶入平衡元素，短期比較適合作為調整狀態的提示，不適合當成精準聯絡日。"
        confidence = "low"
    else:
        window_label = "大運流日偏背景"
        relationship_meaning = "目前大運與流日先作背景參考，還不能單獨推斷適合聯絡的精準時間。"
        confidence = "low"

    return {
        "method": "bazi_da_yun_liu_ri_v1",
        "confidence": confidence,
        "target_date": (transits or {}).get("target_date"),
        "transits": transits,
        "cycle_summaries": cycle_summaries,
        "period_profiles": period_profiles,
        "relationship_triggers": relationship_triggers[:6],
        "strongest_trigger": strongest,
        "window_label": window_label,
        "relationship_meaning": relationship_meaning,
        "technical_summary": luck_timing_technical_summary(transits or {}, cycle_summaries, strongest, window_label),
        "limits": [
            "目前使用 lunar_python getYun 計算起運與大運，並用分析日流日作短期觸發。",
            "尚未完成正式喜忌、格局成敗、流月內精準擇日或神煞級細節。",
        ],
    }


def luck_timing_technical_summary(
    transits: dict[str, Any],
    cycle_summaries: list[dict[str, Any]],
    strongest: dict[str, Any] | None,
    window_label: str,
) -> str:
    parts: list[str] = []
    for summary in cycle_summaries[:2]:
        role = "你" if summary.get("person") == "person_a" else "對方"
        current = summary.get("current_da_yun") or {}
        start = summary.get("start") or {}
        start_solar = (start.get("solar") or {}).get("ymd")
        if current.get("ganzhi"):
            parts.append(
                f"{role}起運約{start.get('year')}年{start.get('month')}月{start.get('day')}日，"
                f"起運日約{start_solar or '未明'}；目前大運{current.get('ganzhi')}({current.get('start_year')}-{current.get('end_year')})。"
            )
    day = (transits.get("day") or {}).get("ganzhi") or "流日未明"
    if not strongest:
        return f"{''.join(parts)} 分析日流日{day}；大運/流日暫作背景。"
    role = "你" if strongest.get("person") == "person_a" else "對方"
    period_label = "大運" if strongest.get("period") == "da_yun" else "流日"
    pillar = (strongest.get("pillar") or {}).get("ganzhi") or ""
    return f"{''.join(parts)} 分析日流日{day}；最明顯是{role}的{period_label}{pillar}呈現「{strongest.get('headline')}」，時間判斷暫定為「{window_label}」。"


def timing_technical_summary(
    transits: dict[str, Any],
    strongest: dict[str, Any] | None,
    window_label: str,
) -> str:
    year = (transits.get("year") or {}).get("ganzhi") or "流年未明"
    month = (transits.get("month") or {}).get("ganzhi") or "流月未明"
    if not strongest:
        return f"目前流年{year}、流月{month}；未讀到強烈關係觸發，時間層暫作背景。"
    role = "你" if strongest.get("person") == "person_a" else "對方"
    period_label = "流年" if strongest.get("period") == "year" else "流月"
    pillar = (strongest.get("pillar") or {}).get("ganzhi") or ""
    return f"目前流年{year}、流月{month}；最明顯是{role}的{period_label}{pillar}呈現「{strongest.get('headline')}」，時間判斷暫定為「{window_label}」。"


def build_candidate_signals(
    bazi_people: dict[str, dict[str, Any]],
    source_people: dict[str, dict[str, Any]],
    transits: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    signals: dict[str, dict[str, Any]] = {}
    a = bazi_people["person_a"]["sxtwl"]
    b = bazi_people["person_b"]["sxtwl"]

    for person_key, chart in (("person_a", a), ("person_b", b)):
        day_master = chart.get("day_master")
        article_id = DAY_MASTER_ARTICLES.get(day_master)
        if article_id:
            add_signal(
                signals,
                article_id,
                0.72,
                "day_master_article_available",
                {"person": person_key, "day_master": day_master},
            )

    element_a = a.get("day_master_element")
    element_b = b.get("day_master_element")
    if {element_a, element_b} == {"木", "火"}:
        direction = (
            "person_a_generates_person_b"
            if ELEMENT_GENERATES.get(element_a) == element_b
            else "person_b_generates_person_a"
        )
        add_signal(
            signals,
            "bazi-wuxing-mu-sheng-huo",
            0.9,
            "day_master_elements_form_wood_generates_fire",
            {"person_a_element": element_a, "person_b_element": element_b, "direction": direction},
        )

    interaction = day_branch_interaction(a.get("day_branch"), b.get("day_branch"))
    if interaction:
        add_signal(
            signals,
            "bazi-hehun-marriage-palace",
            0.66 if interaction["type"] == "none" else 0.82,
            "both_day_branches_available",
            interaction,
        )
        if interaction["type"] in {"clash", "combination", "harm"}:
            add_signal(
                signals,
                "bazi-hehun-day-branch-conflict-combination",
                interaction["strength"],
                f"day_branches_have_{interaction['type']}",
                interaction,
            )

    spouse_hits = []
    spouse_profiles = []
    for person_key in ("person_a", "person_b"):
        profile = spouse_star_positions(
            person_key,
            bazi_people[person_key],
            source_people.get(person_key, {}).get("gender"),
        )
        spouse_profiles.append(profile)
        spouse_hits.append({key: profile[key] for key in ("person", "gender", "present", "matches")})
    present_count = sum(1 for hit in spouse_hits if hit["present"])
    if present_count:
        add_signal(
            signals,
            "bazi-hehun-spouse-star",
            0.68 + (0.1 * present_count),
            "spouse_star_visible_in_ten_gods",
            {"hits": spouse_hits, "profiles": spouse_profiles},
        )

    cross_interactions = cross_branch_interactions(bazi_people["person_a"], bazi_people["person_b"])
    pressure_interactions = [item for item in cross_interactions if item["type"] in {"clash", "harm"}]
    if pressure_interactions:
        strongest = pressure_interactions[0]
        add_signal(
            signals,
            "bazi-hehun-day-branch-conflict-combination",
            max(0.78, float(strongest["strength"])),
            "four_pillar_branch_pressure_detected",
            {"interactions": pressure_interactions[:4]},
        )

    if any(bazi_people[key]["sxtwl"].get("birth_precision") == "date_only" for key in ("person_a", "person_b")):
        add_signal(
            signals,
            "bazi-hehun-year-only-matching-is-insufficient",
            0.76,
            "one_birth_time_unknown",
            {"birth_precision": {key: bazi_people[key]["sxtwl"].get("birth_precision") for key in ("person_a", "person_b")}},
        )

    analysis = {
        "day_master_elements": {"person_a": element_a, "person_b": element_b},
        "day_branch_interaction": interaction,
        "spouse_star_hits": spouse_hits,
        "spouse_star_profiles": spouse_profiles,
        "cross_branch_interactions": cross_interactions,
        "self_branch_patterns": {
            "person_a": self_branch_patterns(bazi_people["person_a"]),
            "person_b": self_branch_patterns(bazi_people["person_b"]),
        },
        "day_master_strength_profiles": {
            "person_a": day_master_strength_profile("person_a", bazi_people["person_a"]),
            "person_b": day_master_strength_profile("person_b", bazi_people["person_b"]),
        },
        "element_tallies": {
            "person_a": element_tally(bazi_people["person_a"]),
            "person_b": element_tally(bazi_people["person_b"]),
        },
        "timing_profile": bazi_timing_profile(bazi_people, source_people, transits),
        "luck_timing_profile": bazi_luck_timing_profile(bazi_people, source_people, transits),
    }
    return sorted(signals.values(), key=lambda item: (-item["strength"], item["id"])), analysis
