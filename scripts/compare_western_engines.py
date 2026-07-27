#!/usr/bin/env python3
"""
Compare the current immanuel Western pipeline with an optional Kerykeion probe.

This is a build-stage decision tool, not production runtime code. It answers:
- Are natal point positions aligned enough to trust both engines?
- Which synastry/transit facts does each engine expose?
- Does Kerykeion add useful structured data, such as house overlays or relationship score?

Kerykeion is intentionally optional because it is AGPL/commercial-sensitive.
Install locally for this probe only:
    .venv/bin/python -m pip install "kerykeion==5.12.8"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from calc_western_spike import build_payload, read_json
from calculation.western.immanuel_adapter import place_coordinates


DEFAULT_SCENARIOS = [
    ROOT / "examples" / "readings" / "cold-war-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-recent-still-love-me.json",
    ROOT / "examples" / "readings" / "broke-up-long-any-chance.json",
]

POINTS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn", "Asc", "Desc"]
TRANSIT_POINTS = ["Sun", "Moon", "Venus", "Mars", "Saturn"]
KERYKEION_POINTS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn", "Ascendant", "Descendant"]
KERYKEION_TRANSIT_POINTS = ["Sun", "Moon", "Venus", "Mars", "Saturn"]
ACTIVE_ASPECTS_10_DEG = [
    {"name": "conjunction", "orb": 10},
    {"name": "opposition", "orb": 10},
    {"name": "trine", "orb": 10},
    {"name": "sextile", "orb": 10},
    {"name": "square", "orb": 10},
    {"name": "quincunx", "orb": 3},
]

KERYKEION_ATTR_BY_POINT = {
    "Sun": "sun",
    "Moon": "moon",
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Saturn": "saturn",
    "Asc": "ascendant",
    "Desc": "descendant",
}

POINT_BY_KERYKEION_NAME = {
    "Sun": "Sun",
    "Moon": "Moon",
    "Mercury": "Mercury",
    "Venus": "Venus",
    "Mars": "Mars",
    "Saturn": "Saturn",
    "Ascendant": "Asc",
    "Descendant": "Desc",
}

SIGN_BY_ABBREV = {
    "Ari": "Aries",
    "Tau": "Taurus",
    "Gem": "Gemini",
    "Can": "Cancer",
    "Leo": "Leo",
    "Vir": "Virgo",
    "Lib": "Libra",
    "Sco": "Scorpio",
    "Sag": "Sagittarius",
    "Cap": "Capricorn",
    "Aqu": "Aquarius",
    "Pis": "Pisces",
}

HOUSE_BY_NAME = {
    "First_House": 1,
    "Second_House": 2,
    "Third_House": 3,
    "Fourth_House": 4,
    "Fifth_House": 5,
    "Sixth_House": 6,
    "Seventh_House": 7,
    "Eighth_House": 8,
    "Ninth_House": 9,
    "Tenth_House": 10,
    "Eleventh_House": 11,
    "Twelfth_House": 12,
}

ASPECT_TITLE = {
    "conjunction": "Conjunction",
    "opposition": "Opposition",
    "trine": "Trine",
    "sextile": "Sextile",
    "square": "Square",
    "quincunx": "Quincunx",
}


def parse_date(value: Any) -> date:
    if not value:
        raise ValueError("date value is required")
    return date.fromisoformat(str(value))


def parse_birth_time(value: Any) -> tuple[time, bool]:
    if value in (None, ""):
        return time(12, 0), False
    raw = str(value)
    if len(raw.split(":")) == 2:
        raw = f"{raw}:00"
    return time.fromisoformat(raw), True


def round_float(value: Any, digits: int = 6) -> float | None:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def angular_delta(a: Any, b: Any) -> float | None:
    a_float = round_float(a, 9)
    b_float = round_float(b, 9)
    if a_float is None or b_float is None:
        return None
    delta = abs(a_float - b_float) % 360
    return round(min(delta, 360 - delta), 6)


def load_kerykeion() -> dict[str, Any]:
    try:
        from kerykeion import (  # type: ignore
            AspectsFactory,
            AstrologicalSubject,
            CompositeSubjectFactory,
            HouseComparisonFactory,
            RelationshipScoreFactory,
        )
    except ImportError as exc:
        raise SystemExit(
            "Kerykeion is not installed in this Python environment. "
            "Install it for the local probe with: "
            '.venv/bin/python -m pip install "kerykeion==5.12.8"'
        ) from exc
    return {
        "AspectsFactory": AspectsFactory,
        "AstrologicalSubject": AstrologicalSubject,
        "CompositeSubjectFactory": CompositeSubjectFactory,
        "HouseComparisonFactory": HouseComparisonFactory,
        "RelationshipScoreFactory": RelationshipScoreFactory,
    }


def kerykeion_subject_model(person: dict[str, Any], name: str, when: date | None = None) -> tuple[Any | None, list[str], dict[str, Any]]:
    k = load_kerykeion()
    warnings: list[str] = []
    coordinates, warning = place_coordinates(person)
    if warning:
        warnings.append(warning)
    if coordinates is None:
        return None, warnings, {"status": "skipped"}

    if when is None:
        birth_date = parse_date(person.get("birth_date"))
        birth_time, time_known = parse_birth_time(person.get("birth_time"))
    else:
        birth_date = when
        birth_time = time(12, 0)
        time_known = True

    if not time_known:
        warnings.append("birth_time unknown; Kerykeion probe uses noon fallback and must block time-sensitive claims")

    subject = k["AstrologicalSubject"](
        name,
        birth_date.year,
        birth_date.month,
        birth_date.day,
        birth_time.hour,
        birth_time.minute,
        lng=coordinates["longitude"],
        lat=coordinates["latitude"],
        tz_str=str(person.get("birth_timezone") or "Asia/Taipei"),
        online=False,
    )
    return subject.model(), warnings, {
        "status": "calculated",
        "birthPrecision": "date_time" if time_known else "date_only",
        "locationPrecision": coordinates.get("precision", "known"),
    }


def kerykeion_point(model: Any, point: str) -> dict[str, Any] | None:
    attr = KERYKEION_ATTR_BY_POINT.get(point)
    if not attr:
        return None
    value = getattr(model, attr, None)
    if value is None:
        return None
    return {
        "name": point,
        "sign": SIGN_BY_ABBREV.get(str(value.sign), str(value.sign)),
        "signElement": getattr(value, "element", None),
        "longitude": round_float(getattr(value, "abs_pos", None)),
        "signDegree": round_float(getattr(value, "position", None)),
        "house": HOUSE_BY_NAME.get(str(getattr(value, "house", ""))),
    }


def immanuel_point(chart: dict[str, Any], point: str) -> dict[str, Any] | None:
    key = point.lower()
    value = (chart.get("objects") or {}).get(key)
    if not isinstance(value, dict):
        return None
    return {
        "name": point,
        "sign": value.get("sign"),
        "signElement": value.get("sign_element"),
        "longitude": round_float(value.get("longitude")),
        "signDegree": round_float(value.get("sign_degree")),
        "house": value.get("house") if isinstance(value.get("house"), int) else None,
    }


def aspect_key(item: dict[str, Any]) -> str:
    return f"{item.get('p1')}->{item.get('p2')}:{item.get('aspect')}"


def normalize_immanuel_aspects(aspects: list[dict[str, Any]], p1_owner: str = "person_a", p2_owner: str = "person_b") -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in aspects:
        p1 = str(item.get("person_a_point") or item.get("transit_point") or "")
        p2 = str(item.get("person_b_point") or item.get("natal_point") or "")
        if p1 not in POINTS and p1 not in TRANSIT_POINTS:
            continue
        if p2 not in POINTS and p2 not in TRANSIT_POINTS:
            continue
        normalized.append(
            {
                "p1": p1,
                "p2": p2,
                "p1Owner": p1_owner,
                "p2Owner": p2_owner,
                "aspect": str(item.get("aspect") or ""),
                "orb": round_float(item.get("orb"), 3),
                "applying": bool(item.get("applying")),
                "eligible": bool(item.get("eligible_for_signal", item.get("eligible_for_timing", True))),
            }
        )
    normalized.sort(key=lambda item: (aspect_key(item), item.get("orb") or 99))
    return normalized


def normalize_kerykeion_aspects(aspects: list[Any], p1_owner: str, p2_owner: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for aspect in aspects:
        p1 = POINT_BY_KERYKEION_NAME.get(str(getattr(aspect, "p1_name", "")))
        p2 = POINT_BY_KERYKEION_NAME.get(str(getattr(aspect, "p2_name", "")))
        if not p1 or not p2:
            continue
        normalized.append(
            {
                "p1": p1,
                "p2": p2,
                "p1Owner": p1_owner,
                "p2Owner": p2_owner,
                "aspect": ASPECT_TITLE.get(str(getattr(aspect, "aspect", "")), str(getattr(aspect, "aspect", ""))),
                "orb": round_float(getattr(aspect, "orbit", None), 3),
                "applying": str(getattr(aspect, "aspect_movement", "")).lower() == "applying",
                "eligible": True,
            }
        )
    normalized.sort(key=lambda item: (aspect_key(item), item.get("orb") or 99))
    return normalized


def compare_points(immanuel_chart: dict[str, Any], kerykeion_model: Any | None) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    max_delta = 0.0
    for point in POINTS:
        i_point = immanuel_point(immanuel_chart, point)
        k_point = kerykeion_point(kerykeion_model, point) if kerykeion_model is not None else None
        delta = angular_delta(i_point.get("longitude") if i_point else None, k_point.get("longitude") if k_point else None)
        if delta is not None:
            max_delta = max(max_delta, delta)
        rows[point] = {
            "immanuel": i_point,
            "kerykeion": k_point,
            "longitudeDelta": delta,
            "signMatch": bool(i_point and k_point and i_point.get("sign") == k_point.get("sign")),
            "houseMatch": bool(i_point and k_point and i_point.get("house") == k_point.get("house")),
        }
    return {"points": rows, "maxLongitudeDelta": round(max_delta, 6)}


def compare_aspect_sets(immanuel_aspects: list[dict[str, Any]], kerykeion_aspects: list[dict[str, Any]]) -> dict[str, Any]:
    i_by_key = {aspect_key(item): item for item in immanuel_aspects}
    k_by_key = {aspect_key(item): item for item in kerykeion_aspects}
    shared_keys = sorted(set(i_by_key) & set(k_by_key))
    immanuel_only = sorted(set(i_by_key) - set(k_by_key))
    kerykeion_only = sorted(set(k_by_key) - set(i_by_key))
    orb_deltas = [
        abs(float(i_by_key[key].get("orb") or 0) - float(k_by_key[key].get("orb") or 0))
        for key in shared_keys
    ]
    overlap = len(shared_keys) / max(1, len(set(i_by_key) | set(k_by_key)))
    return {
        "immanuelCount": len(i_by_key),
        "kerykeionCount": len(k_by_key),
        "sharedCount": len(shared_keys),
        "overlapRatio": round(overlap, 3),
        "maxSharedOrbDelta": round(max(orb_deltas or [0]), 3),
        "immanuelOnly": immanuel_only[:12],
        "kerykeionOnly": kerykeion_only[:12],
    }


def kerykeion_synastry(model_a: Any | None, model_b: Any | None) -> dict[str, Any]:
    if model_a is None or model_b is None:
        return {"status": "skipped", "aspects": []}
    k = load_kerykeion()
    aspects = k["AspectsFactory"]().synastry_aspects(
        model_a,
        model_b,
        active_points=KERYKEION_POINTS,
        active_aspects=ACTIVE_ASPECTS_10_DEG,
    )
    output: dict[str, Any] = {
        "status": "calculated",
        "aspects": normalize_kerykeion_aspects(aspects.aspects, "person_a", "person_b"),
    }
    try:
        score = k["RelationshipScoreFactory"](model_a, model_b).get_relationship_score()
        output["relationshipScore"] = score.model_dump(mode="json")
    except Exception as exc:  # score is debug-only; do not fail the comparison.
        output["relationshipScoreError"] = str(exc)
    try:
        house_comparison = k["HouseComparisonFactory"](
            model_a,
            model_b,
            active_points=["Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"],
        ).get_house_comparison()
        output["houseComparison"] = house_comparison.model_dump(mode="json")
    except Exception as exc:
        output["houseComparisonError"] = str(exc)
    try:
        composite = k["CompositeSubjectFactory"](model_a, model_b, "Composite").get_midpoint_composite_subject_model()
        output["compositeAvailable"] = True
        output["compositeCore"] = {
            point: kerykeion_point(composite, point)
            for point in ["Sun", "Moon", "Venus", "Mars", "Saturn", "Asc", "Desc"]
        }
    except Exception as exc:
        output["compositeAvailable"] = False
        output["compositeError"] = str(exc)
    return output


def kerykeion_transits(person: dict[str, Any], natal_model: Any | None, analysis_date: date, owner: str) -> dict[str, Any]:
    if natal_model is None:
        return {"status": "skipped", "aspects": []}
    transit_model, warnings, status = kerykeion_subject_model(person, f"{owner}_transit", when=analysis_date)
    if transit_model is None:
        return {"status": "skipped", "warnings": warnings, "aspects": []}
    k = load_kerykeion()
    aspects = k["AspectsFactory"]().dual_chart_aspects(
        transit_model,
        natal_model,
        active_points=KERYKEION_TRANSIT_POINTS,
        active_aspects=ACTIVE_ASPECTS_10_DEG,
    )
    normalized = [
        item
        for item in normalize_kerykeion_aspects(aspects.aspects, f"{owner}_transit", owner)
        if item["p1"] in TRANSIT_POINTS and item["p2"] in TRANSIT_POINTS
    ]
    return {"status": status["status"], "warnings": warnings, "aspects": normalized}


def summarize_engine_gap(comparison: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    max_delta = max(
        float(comparison["people"][person]["maxLongitudeDelta"] or 0)
        for person in ("person_a", "person_b")
    )
    if max_delta <= 0.01:
        findings.append(f"Natal longitudes align tightly between engines (max delta {max_delta:.6f}°).")
    else:
        findings.append(f"Natal longitude gap needs review (max delta {max_delta:.6f}°).")

    syn = comparison["synastryComparison"]
    if syn["kerykeionOnly"]:
        mercury_related = [key for key in syn["kerykeionOnly"] if "Mercury" in key]
        if mercury_related:
            findings.append("Kerykeion exposes Mercury synastry aspects missing from the current immanuel adapter.")
    if syn["immanuelOnly"]:
        quincunx_related = [key for key in syn["immanuelOnly"] if "Quincunx" in key]
        if quincunx_related:
            findings.append("Current immanuel output includes quincunx contacts that Kerykeion only returns with narrow minor-aspect settings.")

    statuses = [
        comparison["kerykeion"].get("personAStatus", {}),
        comparison["kerykeion"].get("personBStatus", {}),
    ]
    precise_for_houses = all(
        status.get("birthPrecision") == "date_time" and status.get("locationPrecision") == "known"
        for status in statuses
    )
    if comparison["kerykeion"].get("synastry", {}).get("houseComparison"):
        if precise_for_houses:
            findings.append("Kerykeion exposes structured house overlay comparison that our current runtime only blocks/reserves.")
        else:
            findings.append("Kerykeion emits house overlays even with fallback/date-only inputs; product output must keep our precision gates.")
    if comparison["kerykeion"].get("synastry", {}).get("compositeAvailable"):
        findings.append("Kerykeion can produce midpoint composite core points for paid-depth exploration.")
    if comparison["kerykeion"].get("synastry", {}).get("relationshipScore"):
        findings.append("Kerykeion relationship score is available but should stay debug-only, not product truth.")
    return findings


def compare_scenario(path: Path) -> dict[str, Any]:
    reading = read_json(path)
    immanuel_payload = build_payload(reading, include_drafts=True, select=True)
    analysis_date = parse_date(
        (reading.get("context") or {}).get("analysis_date")
        or reading.get("analysis_date")
        or date.today().isoformat()
    )

    model_a, warnings_a, status_a = kerykeion_subject_model(reading.get("person_a") or {}, "person_a")
    model_b, warnings_b, status_b = kerykeion_subject_model(reading.get("person_b") or {}, "person_b")
    k_synastry = kerykeion_synastry(model_a, model_b)

    im_synastry = normalize_immanuel_aspects(
        immanuel_payload.get("western", {}).get("synastry", {}).get("inter_aspects") or []
    )
    k_synastry_aspects = k_synastry.get("aspects") or []

    im_transits: dict[str, Any] = {}
    k_transits: dict[str, Any] = {}
    transit_comparison: dict[str, Any] = {}
    for owner, model in (("person_a", model_a), ("person_b", model_b)):
        im_items = normalize_immanuel_aspects(
            (
                immanuel_payload.get("western", {})
                .get("transits", {})
                .get(owner, {})
                .get("transit_aspects")
                or []
            ),
            f"{owner}_transit",
            owner,
        )
        k_items_payload = kerykeion_transits(reading.get(owner) or {}, model, analysis_date, owner)
        im_transits[owner] = im_items
        k_transits[owner] = k_items_payload
        transit_comparison[owner] = compare_aspect_sets(im_items, k_items_payload.get("aspects") or [])

    comparison = {
        "scenario": str(path.relative_to(ROOT)),
        "readingId": reading.get("reading_id"),
        "context": reading.get("context"),
        "immanuel": {
            "engineVersions": immanuel_payload.get("debug", {}).get("engine_versions"),
            "warnings": immanuel_payload.get("debug", {}).get("calculation_warnings") or [],
            "candidateSignalIds": [
                item.get("id")
                for item in (immanuel_payload.get("candidate_signals", {}).get("western_signals") or [])[:8]
            ],
            "synastryAspects": im_synastry,
            "transits": im_transits,
        },
        "kerykeion": {
            "personAStatus": status_a,
            "personBStatus": status_b,
            "warnings": [*warnings_a, *warnings_b],
            "synastry": k_synastry,
            "transits": k_transits,
        },
        "people": {
            "person_a": compare_points(
                immanuel_payload.get("western", {}).get("people", {}).get("person_a", {}),
                model_a,
            ),
            "person_b": compare_points(
                immanuel_payload.get("western", {}).get("people", {}).get("person_b", {}),
                model_b,
            ),
        },
        "synastryComparison": compare_aspect_sets(im_synastry, k_synastry_aspects),
        "transitComparison": transit_comparison,
    }
    comparison["findings"] = summarize_engine_gap(comparison)
    return comparison


def compact_report(comparisons: list[dict[str, Any]]) -> str:
    lines = ["Western Engine Comparison", ""]
    for item in comparisons:
        lines.append(f"- {item['readingId']} ({item['scenario']})")
        lines.append(
            "  "
            f"natal max delta: "
            f"{max(float(item['people'][person]['maxLongitudeDelta'] or 0) for person in ('person_a', 'person_b')):.6f}°; "
            f"synastry overlap: {item['synastryComparison']['overlapRatio']} "
            f"({item['synastryComparison']['sharedCount']} shared / "
            f"{item['synastryComparison']['immanuelCount']} immanuel / "
            f"{item['synastryComparison']['kerykeionCount']} kerykeion)"
        )
        for finding in item["findings"]:
            lines.append(f"  - {finding}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare immanuel and optional Kerykeion Western astrology outputs.")
    parser.add_argument(
        "--scenario",
        action="append",
        type=Path,
        help="ReadingInput JSON path. Can be repeated. Defaults to three representative example readings.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON instead of compact text.")
    parser.add_argument("--write", type=Path, help="Optional path to write full JSON comparison.")
    args = parser.parse_args()

    scenarios = args.scenario or DEFAULT_SCENARIOS
    comparisons = [compare_scenario(path if path.is_absolute() else ROOT / path) for path in scenarios]
    payload = {
        "version": "western-engine-comparison-v1",
        "purpose": "Build-stage comparison of immanuel runtime output vs optional Kerykeion probe.",
        "scenarios": comparisons,
    }

    if args.write:
        out_path = args.write if args.write.is_absolute() else ROOT / args.write
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(compact_report(comparisons))
        if args.write:
            print(f"Wrote full comparison JSON: {out_path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
