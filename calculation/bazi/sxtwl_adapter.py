from __future__ import annotations

from datetime import date, time
from typing import Any


GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"

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

STEM_YIN_YANG = {
    "甲": "陽",
    "乙": "陰",
    "丙": "陽",
    "丁": "陰",
    "戊": "陽",
    "己": "陰",
    "庚": "陽",
    "辛": "陰",
    "壬": "陽",
    "癸": "陰",
}


def parse_date(value: Any) -> date:
    if not value:
        raise ValueError("birth_date is required")
    return date.fromisoformat(str(value))


def parse_time(value: Any) -> time | None:
    if value in (None, ""):
        return None
    raw = str(value)
    if len(raw.split(":")) == 2:
        raw = f"{raw}:00"
    return time.fromisoformat(raw)


def gz_label(value: Any) -> str:
    return f"{GAN[value.tg]}{ZHI[value.dz]}"


def split_ganzhi(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    gan = value[0]
    zhi = value[1]
    return {
        "gan": gan,
        "zhi": zhi,
        "ganzhi": value,
        "gan_element": STEM_ELEMENT.get(gan),
        "gan_yin_yang": STEM_YIN_YANG.get(gan),
    }


def calculate_person(person: dict[str, Any]) -> dict[str, Any]:
    try:
        import sxtwl
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `sxtwl`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    birth_date = parse_date(person.get("birth_date"))
    birth_time = parse_time(person.get("birth_time"))
    day = sxtwl.fromSolar(birth_date.year, birth_date.month, birth_date.day)

    year = gz_label(day.getYearGZ())
    month = gz_label(day.getMonthGZ())
    day_pillar = gz_label(day.getDayGZ())
    hour = gz_label(day.getHourGZ(birth_time.hour)) if birth_time else None

    pillars = {
        "year": split_ganzhi(year),
        "month": split_ganzhi(month),
        "day": split_ganzhi(day_pillar),
        "hour": split_ganzhi(hour),
    }
    day_master = pillars["day"]["gan"] if pillars["day"] else None
    day_branch = pillars["day"]["zhi"] if pillars["day"] else None

    return {
        "engine": "sxtwl",
        "birth_precision": "date_time" if birth_time else "date_only",
        "pillars": pillars,
        "day_master": day_master,
        "day_master_element": STEM_ELEMENT.get(day_master),
        "day_master_yin_yang": STEM_YIN_YANG.get(day_master),
        "day_branch": day_branch,
    }


def calculate_transits(target_date: date) -> dict[str, Any]:
    try:
        import sxtwl
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `sxtwl`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    day = sxtwl.fromSolar(target_date.year, target_date.month, target_date.day)
    year = gz_label(day.getYearGZ())
    month = gz_label(day.getMonthGZ())
    day_pillar = gz_label(day.getDayGZ())

    return {
        "engine": "sxtwl",
        "target_date": target_date.isoformat(),
        "year": split_ganzhi(year),
        "month": split_ganzhi(month),
        "day": split_ganzhi(day_pillar),
    }
