from __future__ import annotations

import json
from datetime import date, time, timedelta
from typing import Any


KNOWN_PLACES = {
    "taipei": {"latitude": 25.0330, "longitude": 121.5654, "label": "Taipei, Taiwan"},
    "台北": {"latitude": 25.0330, "longitude": 121.5654, "label": "Taipei, Taiwan"},
    "new taipei": {"latitude": 25.0169, "longitude": 121.4628, "label": "New Taipei, Taiwan"},
    "新北": {"latitude": 25.0169, "longitude": 121.4628, "label": "New Taipei, Taiwan"},
    "taichung": {"latitude": 24.1477, "longitude": 120.6736, "label": "Taichung, Taiwan"},
    "台中": {"latitude": 24.1477, "longitude": 120.6736, "label": "Taichung, Taiwan"},
    "tainan": {"latitude": 22.9999, "longitude": 120.2269, "label": "Tainan, Taiwan"},
    "台南": {"latitude": 22.9999, "longitude": 120.2269, "label": "Tainan, Taiwan"},
    "kaohsiung": {"latitude": 22.6273, "longitude": 120.3014, "label": "Kaohsiung, Taiwan"},
    "高雄": {"latitude": 22.6273, "longitude": 120.3014, "label": "Kaohsiung, Taiwan"},
    "hsinchu": {"latitude": 24.8138, "longitude": 120.9675, "label": "Hsinchu, Taiwan"},
    "新竹": {"latitude": 24.8138, "longitude": 120.9675, "label": "Hsinchu, Taiwan"},
    "taoyuan": {"latitude": 24.9937, "longitude": 121.3009, "label": "Taoyuan, Taiwan"},
    "桃園": {"latitude": 24.9937, "longitude": 121.3009, "label": "Taoyuan, Taiwan"},
    "hong kong": {"latitude": 22.3193, "longitude": 114.1694, "label": "Hong Kong"},
    "香港": {"latitude": 22.3193, "longitude": 114.1694, "label": "Hong Kong"},
    "singapore": {"latitude": 1.3521, "longitude": 103.8198, "label": "Singapore"},
    "新加坡": {"latitude": 1.3521, "longitude": 103.8198, "label": "Singapore"},
    "tokyo": {"latitude": 35.6762, "longitude": 139.6503, "label": "Tokyo, Japan"},
    "東京": {"latitude": 35.6762, "longitude": 139.6503, "label": "Tokyo, Japan"},
    "seoul": {"latitude": 37.5665, "longitude": 126.9780, "label": "Seoul, Korea"},
    "首爾": {"latitude": 37.5665, "longitude": 126.9780, "label": "Seoul, Korea"},
}

DEFAULT_PLACE_FALLBACK = {
    "latitude": 25.0330,
    "longitude": 121.5654,
    "label": "Taipei, Taiwan fallback",
    "precision": "fallback",
}

RELATIONSHIP_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn", "Asc", "Desc"}
TRANSIT_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"}
TRANSIT_NATAL_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"}


def parse_date(value: Any) -> date:
    if not value:
        raise ValueError("birth_date is required")
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"invalid birth_date {value!r}; expected YYYY-MM-DD with a real calendar date") from exc


def parse_time(value: Any) -> time | None:
    if value in (None, ""):
        return None
    raw = str(value)
    if len(raw.split(":")) == 2:
        raw = f"{raw}:00"
    return time.fromisoformat(raw)


def place_coordinates(person: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if person.get("latitude") is not None and person.get("longitude") is not None:
        return (
            {
                "latitude": float(person["latitude"]),
                "longitude": float(person["longitude"]),
                "label": person.get("birth_place") or "provided coordinates",
                "precision": "known",
            },
            None,
        )
    place = str(person.get("birth_place") or "").lower()
    if not place.strip():
        return dict(DEFAULT_PLACE_FALLBACK), "birth_place missing; using Taipei fallback and disabling house/angle claims"
    for key, coordinates in KNOWN_PLACES.items():
        if key in place:
            return {**coordinates, "precision": "known"}, None
    return None, f"Unknown birth_place coordinates: {person.get('birth_place')!r}"


def object_to_dict(value: Any, encoder: type[Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, cls=encoder))


def simplify_object(value: dict[str, Any]) -> dict[str, Any]:
    sign = value.get("sign") or {}
    longitude = value.get("longitude") or {}
    sign_longitude = value.get("sign_longitude") or {}
    house = value.get("house") or {}
    return {
        "name": value.get("name"),
        "sign": sign.get("name"),
        "sign_element": sign.get("element"),
        "longitude": longitude.get("raw"),
        "sign_degree": sign_longitude.get("raw"),
        "house": house.get("number") or house.get("name"),
    }


def calculate_person(person: dict[str, Any]) -> tuple[dict[str, Any], list[str], Any | None, Any | None]:
    try:
        from immanuel import charts
        from immanuel.classes.serialize import ToJSON
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `immanuel`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    warnings: list[str] = []
    coordinates, warning = place_coordinates(person)
    if warning:
        warnings.append(warning)
    if coordinates is None:
        return {"engine": "immanuel", "status": "skipped", "warnings": warnings}, warnings, None, None

    birth_date = parse_date(person.get("birth_date"))
    birth_time = parse_time(person.get("birth_time"))
    time_known = birth_time is not None
    if birth_time is None:
        birth_time = time(12, 0)
        warnings.append("birth_time unknown; Western chart uses noon fallback and disables time-sensitive signals")

    timezone = str(person.get("birth_timezone") or "Asia/Taipei")
    date_time = f"{birth_date.isoformat()} {birth_time.strftime('%H:%M')}"
    subject = charts.Subject(
        date_time,
        coordinates["latitude"],
        coordinates["longitude"],
        timezone=timezone,
    )
    natal = charts.Natal(subject)

    object_map: dict[str, dict[str, Any]] = {}
    for raw_object in natal.objects.values():
        data = object_to_dict(raw_object, ToJSON)
        name = data.get("name")
        if name in RELATIONSHIP_POINTS or name in {"Mercury", "Jupiter"}:
            object_map[name.lower().replace(" ", "_")] = simplify_object(data)

    return (
        {
            "engine": "immanuel",
            "status": "calculated",
            "birth_precision": "date_time" if time_known else "date_only",
            "location_precision": coordinates.get("precision", "known"),
            "coordinate_source": coordinates["label"],
            "objects": object_map,
            "natal_aspect_count": len(natal.aspects),
            "warnings": warnings,
        },
        warnings,
        subject,
        natal,
    )


def calculate_synastry(
    subject_a: Any,
    natal_a: Any,
    natal_b: Any,
    birth_precision_a: str,
    birth_precision_b: str,
) -> tuple[dict[str, Any], list[str]]:
    try:
        from immanuel import charts
        from immanuel.classes.serialize import ToJSON
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `immanuel`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    if subject_a is None or natal_a is None or natal_b is None:
        return {"engine": "immanuel", "status": "skipped", "inter_aspects": []}, [
            "synastry skipped because one Western chart was unavailable"
        ]

    synastry = charts.Natal(subject_a, aspects_to=natal_b)
    a_names = {int(index): obj.name for index, obj in natal_a.objects.items()}
    b_names = {int(index): obj.name for index, obj in natal_b.objects.items()}
    a_time_known = birth_precision_a == "date_time"
    b_time_known = birth_precision_b == "date_time"

    inter_aspects: list[dict[str, Any]] = []
    for active_id, passive_aspects in synastry.aspects.items():
        active_name = a_names.get(int(active_id))
        if active_name not in RELATIONSHIP_POINTS:
            continue
        for passive_id, aspect in passive_aspects.items():
            passive_name = b_names.get(int(passive_id))
            if passive_name not in RELATIONSHIP_POINTS:
                continue
            data = object_to_dict(aspect, ToJSON)
            difference = data.get("difference") or {}
            distance = abs(float(difference.get("raw") or 0))
            max_orb = float(data.get("orb") or 0)
            involves_moon = active_name == "Moon" or passive_name == "Moon"
            time_sensitive = active_name in {"Moon", "Asc", "Desc"} or passive_name in {"Moon", "Asc", "Desc"}
            eligible = not ((involves_moon and not (a_time_known and b_time_known)) or active_name in {"Asc", "Desc"} or passive_name in {"Asc", "Desc"})
            inter_aspects.append(
                {
                    "person_a_point": active_name,
                    "person_b_point": passive_name,
                    "aspect": data.get("type"),
                    "orb": round(distance, 3),
                    "max_orb": max_orb,
                    "applying": bool((data.get("movement") or {}).get("applicative")),
                    "time_sensitive": time_sensitive,
                    "eligible_for_signal": eligible,
                }
            )

    inter_aspects.sort(key=lambda item: (not item["eligible_for_signal"], item["orb"]))
    return (
        {
            "engine": "immanuel",
            "status": "calculated",
            "inter_aspect_count": len(inter_aspects),
            "inter_aspects": inter_aspects[:24],
        },
        [],
    )


def calculate_transits_for_person(
    person: dict[str, Any],
    natal: Any | None,
    birth_precision: str,
    target_date: date,
    target_time: time | None = None,
    target_timezone: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    try:
        from immanuel import charts
        from immanuel.classes.serialize import ToJSON
    except ImportError as exc:
        raise RuntimeError(
            "Missing calculation dependency `immanuel`. Install with "
            "`python3 -m pip install -r requirements-calculation.txt`."
        ) from exc

    warnings: list[str] = []
    if natal is None:
        return {"engine": "immanuel", "status": "skipped", "transit_aspects": []}, [
            "transits skipped because natal chart was unavailable"
        ]

    coordinates, warning = place_coordinates(person)
    if warning:
        warnings.append(warning)
    if coordinates is None:
        return {"engine": "immanuel", "status": "skipped", "transit_aspects": []}, warnings

    timezone = str(target_timezone or person.get("birth_timezone") or "Asia/Taipei")
    normalized_target_time = target_time or time(12, 0)
    date_time = f"{target_date.isoformat()} {normalized_target_time.strftime('%H:%M')}"
    transit_subject = charts.Subject(
        date_time,
        coordinates["latitude"],
        coordinates["longitude"],
        timezone=timezone,
    )
    transit_chart = charts.Natal(transit_subject, aspects_to=natal)
    transit_names = {int(index): obj.name for index, obj in transit_chart.objects.items()}
    natal_names = {int(index): obj.name for index, obj in natal.objects.items()}
    time_known = birth_precision == "date_time"

    transit_objects: dict[str, dict[str, Any]] = {}
    for raw_object in transit_chart.objects.values():
        data = object_to_dict(raw_object, ToJSON)
        name = data.get("name")
        if name in TRANSIT_POINTS:
            transit_objects[name.lower()] = simplify_object(data)

    transit_aspects: list[dict[str, Any]] = []
    for active_id, passive_aspects in transit_chart.aspects.items():
        transit_name = transit_names.get(int(active_id))
        if transit_name not in TRANSIT_POINTS:
            continue
        for passive_id, aspect in passive_aspects.items():
            natal_name = natal_names.get(int(passive_id))
            if natal_name not in TRANSIT_NATAL_POINTS:
                continue
            data = object_to_dict(aspect, ToJSON)
            difference = data.get("difference") or {}
            distance = abs(float(difference.get("raw") or 0))
            time_sensitive = transit_name == "Moon" or natal_name == "Moon"
            eligible = not (natal_name == "Moon" and not time_known)
            transit_aspects.append(
                {
                    "transit_point": transit_name,
                    "natal_point": natal_name,
                    "aspect": data.get("type"),
                    "orb": round(distance, 3),
                    "max_orb": float(data.get("orb") or 0),
                    "applying": bool((data.get("movement") or {}).get("applicative")),
                    "time_sensitive": time_sensitive,
                    "eligible_for_timing": eligible,
                }
            )

    transit_aspects.sort(key=lambda item: (not item["eligible_for_timing"], item["orb"]))
    if not time_known:
        warnings.append("birth_time unknown; transit Moon-to-natal-Moon timing is disabled")

    return (
        {
            "engine": "immanuel",
            "status": "calculated",
            "target_date": target_date.isoformat(),
            "target_time": normalized_target_time.strftime("%H:%M"),
            "timezone": timezone,
            "location_precision": coordinates.get("precision", "known"),
            "coordinate_source": coordinates["label"],
            "objects": transit_objects,
            "transit_aspect_count": len(transit_aspects),
            "transit_aspects": transit_aspects[:30],
            "warnings": warnings,
        },
        warnings,
    )


def calculate_transit_window_samples(
    source_people: dict[str, dict[str, Any]],
    raw_natal_a: Any | None,
    raw_natal_b: Any | None,
    birth_precision_a: str,
    birth_precision_b: str,
    target_date: date,
    *,
    scan_days: int = 90,
    step_days: int = 2,
) -> tuple[list[dict[str, Any]], list[str]]:
    if scan_days <= 0:
        return [], []

    normalized_days = max(1, min(scan_days, 90))
    normalized_step = max(1, min(step_days, 7))
    samples: list[dict[str, Any]] = []
    warnings: list[str] = []

    for day_offset in range(0, normalized_days + 1, normalized_step):
        sample_date = target_date + timedelta(days=day_offset)
        transits_a, transit_warnings_a = calculate_transits_for_person(
            source_people.get("person_a") or {},
            raw_natal_a,
            birth_precision_a,
            sample_date,
            time(12, 0),
        )
        transits_b, transit_warnings_b = calculate_transits_for_person(
            source_people.get("person_b") or {},
            raw_natal_b,
            birth_precision_b,
            sample_date,
            time(12, 0),
        )
        warnings.extend(f"{sample_date.isoformat()} person_a transit: {warning}" for warning in transit_warnings_a)
        warnings.extend(f"{sample_date.isoformat()} person_b transit: {warning}" for warning in transit_warnings_b)
        samples.append(
            {
                "date": sample_date.isoformat(),
                "person_a": transits_a,
                "person_b": transits_b,
            }
        )

    return samples, warnings
