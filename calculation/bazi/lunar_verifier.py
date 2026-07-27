from __future__ import annotations

from datetime import date, time
from typing import Any

from calculation.bazi.sxtwl_adapter import split_ganzhi


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


def safe_call(target: Any, method: str) -> Any:
    try:
        return getattr(target, method)()
    except Exception:
        return None


def lunar_gender(value: Any) -> int | None:
    gender = str(value or "").lower()
    if gender in {"male", "man", "男", "1"}:
        return 1
    if gender in {"female", "woman", "女", "0"}:
        return 0
    return None


def solar_to_dict(solar: Any) -> dict[str, Any] | None:
    if solar is None:
        return None
    return {
        "ymd": safe_call(solar, "toYmd"),
        "ymdhms": safe_call(solar, "toYmdHms"),
        "year": safe_call(solar, "getYear"),
        "month": safe_call(solar, "getMonth"),
        "day": safe_call(solar, "getDay"),
        "hour": safe_call(solar, "getHour"),
        "minute": safe_call(solar, "getMinute"),
    }


def da_yun_to_dict(da_yun: Any) -> dict[str, Any]:
    ganzhi = safe_call(da_yun, "getGanZhi")
    item = {
        "index": safe_call(da_yun, "getIndex"),
        "start_year": safe_call(da_yun, "getStartYear"),
        "end_year": safe_call(da_yun, "getEndYear"),
        "start_age": safe_call(da_yun, "getStartAge"),
        "end_age": safe_call(da_yun, "getEndAge"),
        "ganzhi": ganzhi,
        "pillar": split_ganzhi(ganzhi),
    }
    return item


def liu_nian_to_dict(liu_nian: Any) -> dict[str, Any]:
    ganzhi = safe_call(liu_nian, "getGanZhi")
    return {
        "year": safe_call(liu_nian, "getYear"),
        "age": safe_call(liu_nian, "getAge"),
        "ganzhi": ganzhi,
        "pillar": split_ganzhi(ganzhi),
    }


def calculate_person(person: dict[str, Any]) -> dict[str, Any]:
    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `lunar_python`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    birth_date = parse_date(person.get("birth_date"))
    birth_time = parse_time(person.get("birth_time")) or time(12, 0)

    solar = Solar.fromYmdHms(
        birth_date.year,
        birth_date.month,
        birth_date.day,
        birth_time.hour,
        birth_time.minute,
        birth_time.second,
    )
    lunar = solar.getLunar()
    eight = lunar.getEightChar()

    return {
        "engine": "lunar_python",
        "birth_precision": "date_time" if person.get("birth_time") else "date_only",
        "lunar_date": lunar.toString(),
        "pillars": {
            "year": safe_call(eight, "getYear"),
            "month": safe_call(eight, "getMonth"),
            "day": safe_call(eight, "getDay"),
            "hour": safe_call(eight, "getTime") if person.get("birth_time") else None,
        },
        "hidden_stems": {
            "year": safe_call(eight, "getYearHideGan"),
            "month": safe_call(eight, "getMonthHideGan"),
            "day": safe_call(eight, "getDayHideGan"),
            "hour": safe_call(eight, "getTimeHideGan") if person.get("birth_time") else None,
        },
        "ten_gods_stems": {
            "year": safe_call(eight, "getYearShiShenGan"),
            "month": safe_call(eight, "getMonthShiShenGan"),
            "day": safe_call(eight, "getDayShiShenGan"),
            "hour": safe_call(eight, "getTimeShiShenGan") if person.get("birth_time") else None,
        },
        "ten_gods_hidden": {
            "year": safe_call(eight, "getYearShiShenZhi"),
            "month": safe_call(eight, "getMonthShiShenZhi"),
            "day": safe_call(eight, "getDayShiShenZhi"),
            "hour": safe_call(eight, "getTimeShiShenZhi") if person.get("birth_time") else None,
        },
    }


def calculate_luck_timing(person: dict[str, Any], target_date: date) -> dict[str, Any]:
    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `lunar_python`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    gender = lunar_gender(person.get("gender"))
    if gender is None:
        return {
            "engine": "lunar_python",
            "status": "skipped",
            "method": "lunar_python_get_yun_v1",
            "reason": "gender is required for Da Yun direction",
        }

    birth_date = parse_date(person.get("birth_date"))
    birth_time = parse_time(person.get("birth_time")) or time(12, 0)
    solar = Solar.fromYmdHms(
        birth_date.year,
        birth_date.month,
        birth_date.day,
        birth_time.hour,
        birth_time.minute,
        birth_time.second,
    )
    eight = solar.getLunar().getEightChar()
    yun = eight.getYun(gender)
    da_yun_items = [da_yun_to_dict(item) for item in yun.getDaYun(10)]
    current_da_yun = next(
        (
            item
            for item in da_yun_items
            if item.get("start_year") is not None
            and item.get("end_year") is not None
            and int(item["start_year"]) <= target_date.year <= int(item["end_year"])
            and item.get("ganzhi")
        ),
        None,
    )
    current_liu_nian = None
    if current_da_yun:
        raw_da_yun = yun.getDaYun(10)[int(current_da_yun["index"])]
        current_liu_nian = next(
            (
                liu_nian_to_dict(item)
                for item in raw_da_yun.getLiuNian(10)
                if int(safe_call(item, "getYear") or -1) == target_date.year
            ),
            None,
        )

    return {
        "engine": "lunar_python",
        "status": "calculated",
        "method": "lunar_python_get_yun_v1",
        "target_date": target_date.isoformat(),
        "gender": gender,
        "gender_label": "男" if gender == 1 else "女",
        "direction": "forward" if yun.isForward() else "backward",
        "start": {
            "year": yun.getStartYear(),
            "month": yun.getStartMonth(),
            "day": yun.getStartDay(),
            "hour": yun.getStartHour(),
            "solar": solar_to_dict(yun.getStartSolar()),
        },
        "da_yun": da_yun_items,
        "current_da_yun": current_da_yun,
        "current_liu_nian": current_liu_nian,
    }
