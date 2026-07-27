"""Map the locked paid intake contract to the deterministic ReadingInput."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import INTAKE_VERSION


RELATIONSHIP_STAGES = {
    "ambiguous",
    "cold-war",
    "broke-up-recent",
    "broke-up-long",
    "crisis",
}
MAIN_QUESTIONS = {
    "still-love-me",
    "any-chance",
    "when-to-contact",
    "what-did-i-do-wrong",
    "stay-or-let-go",
}
CONTACT_STATUSES = {
    "none",
    "occasional",
    "cold-chat",
    "awkward-meeting",
    "blocked",
    "no-contact",
    "occasional-contact",
    "still-in-contact",
    "living-or-working-together",
}
GENDERS = {"female", "male", "other"}


class IntakeMappingError(ValueError):
    """A stable, non-sensitive error that can be reported to the app."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
        self.retryable = False


def build_reading_input(job: dict[str, Any]) -> dict[str, Any]:
    if job.get("version") != "paid-reading-job-v1":
        raise IntakeMappingError("UNSUPPORTED_JOB_VERSION")
    if job.get("intake_version") != INTAKE_VERSION:
        raise IntakeMappingError("UNSUPPORTED_INTAKE_VERSION")

    final_payload = job.get("final_payload")
    if not isinstance(final_payload, dict):
        raise IntakeMappingError("INVALID_FINAL_INTAKE")
    consent_version = job.get("generation_consent_version")
    if (
        final_payload.get("generationConsentAccepted") is not True
        or not isinstance(consent_version, str)
        or not consent_version
        or final_payload.get("generationConsentVersion") != consent_version
    ):
        raise IntakeMappingError("GENERATION_CONSENT_MISMATCH")
    relationship_stage = _choice(
        final_payload.get("relationshipStage"),
        RELATIONSHIP_STAGES,
        "INVALID_RELATIONSHIP_STAGE",
    )
    main_question = _choice(
        final_payload.get("mainQuestion"),
        MAIN_QUESTIONS,
        "INVALID_MAIN_QUESTION",
    )
    contact_status = _choice(
        final_payload.get("contactStatus"),
        CONTACT_STATUSES,
        "INVALID_CONTACT_STATUS",
    )
    person_a = _person(final_payload.get("user"))
    person_b = _person(final_payload.get("partner"))

    analysis_timezone = job.get("analysis_timezone")
    if analysis_timezone != "Asia/Taipei":
        raise IntakeMappingError("UNSUPPORTED_ANALYSIS_TIMEZONE")
    analysis_datetime = _analysis_datetime(
        job.get("analysis_datetime"),
        analysis_timezone,
    )

    public_reading_id = str(job.get("public_reading_id") or "")
    if not public_reading_id:
        raise IntakeMappingError("MISSING_PUBLIC_READING_ID")
    return {
        "reading_id": public_reading_id,
        "person_a": person_a,
        "person_b": person_b,
        "context": {
            "relationship_stage": relationship_stage,
            "main_question": main_question,
            "contact_status": _normalize_contact_status(contact_status),
            "desired_outcome": _desired_outcome(main_question),
            "emotional_risk": "not-collected",
            "analysis_date": analysis_datetime.date().isoformat(),
            "analysis_datetime": analysis_datetime.isoformat(),
            "analysis_timezone": analysis_timezone,
        },
    }


def _person(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntakeMappingError("INVALID_BIRTH_PROFILE")
    birth_date = _birth_date(value.get("birthDate"))
    unknown_time = value.get("unknownTime")
    if not isinstance(unknown_time, bool):
        raise IntakeMappingError("INVALID_BIRTH_TIME_PRECISION")
    birth_time = "" if unknown_time else _birth_time(value.get("birthTime"))
    birth_place = value.get("birthPlace")
    if not isinstance(birth_place, str) or len(birth_place.strip()) > 120:
        raise IntakeMappingError("INVALID_BIRTH_PLACE")
    normalized_birth_place = birth_place.strip().replace("臺", "台")
    if not normalized_birth_place:
        # A clock time without a place/timezone cannot be converted to a
        # trustworthy instant. Force date-only calculation so Moon and other
        # time-sensitive evidence are conservatively disabled.
        birth_time = ""
    gender = value.get("gender")
    if gender not in GENDERS:
        raise IntakeMappingError("INVALID_GENDER")
    return {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_timezone": _timezone_for_place(normalized_birth_place),
        "birth_place": normalized_birth_place,
        "gender": gender,
    }


def _birth_date(value: Any) -> str:
    if not isinstance(value, str):
        raise IntakeMappingError("INVALID_BIRTH_DATE")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise IntakeMappingError("INVALID_BIRTH_DATE") from exc
    if parsed.year < 1900 or parsed > date.today():
        raise IntakeMappingError("INVALID_BIRTH_DATE")
    return parsed.isoformat()


def _birth_time(value: Any) -> str:
    if not isinstance(value, str):
        raise IntakeMappingError("INVALID_BIRTH_TIME")
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise IntakeMappingError("INVALID_BIRTH_TIME") from exc
    return parsed.strftime("%H:%M")


def _analysis_datetime(value: Any, timezone_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise IntakeMappingError("INVALID_ANALYSIS_DATETIME")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntakeMappingError("INVALID_ANALYSIS_DATETIME") from exc
    if parsed.tzinfo is None:
        raise IntakeMappingError("INVALID_ANALYSIS_DATETIME")
    try:
        target_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise IntakeMappingError("ANALYSIS_TIMEZONE_UNAVAILABLE") from exc
    return parsed.astimezone(target_timezone)


def _choice(value: Any, allowed: set[str], code: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise IntakeMappingError(code)
    return value


def _normalize_contact_status(value: str) -> str:
    return {
        "none": "no-contact",
        "occasional": "occasional-contact",
        "cold-chat": "still-in-contact",
        "awkward-meeting": "living-or-working-together",
        "blocked": "blocked",
    }.get(value, value)


def _desired_outcome(question: str) -> str:
    return {
        "still-love-me": "reconnect",
        "any-chance": "reconnect",
        "when-to-contact": "reconnect",
        "what-did-i-do-wrong": "understand",
        "stay-or-let-go": "decide",
    }[question]


def _timezone_for_place(place: str) -> str:
    normalized = place.strip().lower()
    if "東京" in place or "tokyo" in normalized:
        return "Asia/Tokyo"
    if "首爾" in place or "seoul" in normalized:
        return "Asia/Seoul"
    if "香港" in place or "hong kong" in normalized:
        return "Asia/Hong_Kong"
    if "新加坡" in place or "singapore" in normalized:
        return "Asia/Singapore"
    return "Asia/Taipei"
