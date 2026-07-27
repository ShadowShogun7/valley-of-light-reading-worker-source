"""Direct in-process bridge to the audited deterministic result runtime."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any

from . import RESULT_CONTRACT_VERSION, RUNTIME_VERSION
from .bundle import source_fingerprints, validate_bundle
from .intake import IntakeMappingError, build_reading_input


EXPECTED_DEPENDENCIES = {
    "immanuel": "1.5.4",
    "pyswisseph": "2.10.3.2",
}


class ReadingGenerationError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class ReadingRuntime:
    def __init__(
        self,
        *,
        expected_intake_version: str,
        expected_job_version: str,
        expected_result_contract_version: str,
        expected_runtime_version: str,
        kb_dir: Path,
        max_result_bytes: int,
        repo_root: Path,
    ):
        self._kb_dir = kb_dir.resolve()
        self._max_result_bytes = max_result_bytes
        self._repo_root = repo_root.resolve()
        self._ensure_import_paths()
        self._dependency_versions = _validate_dependency_versions()
        self._bundle = validate_bundle(
            self._kb_dir,
            expected_intake_version=expected_intake_version,
            expected_job_version=expected_job_version,
            expected_result_contract_version=expected_result_contract_version,
            expected_runtime_version=expected_runtime_version,
        )
        self.source_fingerprints = {
            **source_fingerprints(self._bundle),
            "engineVersions": dict(self._dependency_versions),
        }
        self.runtime_version = RUNTIME_VERSION
        self._load_runtime()

    def generate(self, job: dict[str, Any]) -> dict[str, Any]:
        try:
            reading_input = build_reading_input(job)
            _validate_supported_locations(reading_input)
            calculation_payload = self._build_payload(
                reading_input,
                include_drafts=False,
                select=True,
            )
            result: dict[str, Any] = self._build_view_model(
                calculation_payload,
                self._articles,
                self._claims_by_article,
                self._structured_kb,
            )
            if result.get("contractVersion") != RESULT_CONTRACT_VERSION:
                raise ReadingGenerationError(
                    "RESULT_CONTRACT_MISMATCH",
                    retryable=False,
                )
            result.setdefault("debug", {})["calculationWarnings"] = [
                str(warning)
                for warning in calculation_payload.get("debug", {}).get(
                    "calculation_warnings", []
                )
            ]
            result["debug"]["engineVersions"] = dict(self._dependency_versions)
            result["debug"]["kbSupportSource"] = "local-published-bundle"
            result["debug"]["kbSupportCounts"] = {
                "articles": len(self._articles),
                "claims": sum(
                    len(claims)
                    for claims in self._claims_by_article.values()
                ),
            }
            encoded_size = len(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            if encoded_size > self._max_result_bytes:
                raise ReadingGenerationError(
                    "RESULT_PAYLOAD_TOO_LARGE",
                    retryable=False,
                )
            return result
        except (IntakeMappingError, ReadingGenerationError):
            raise
        except (ValueError, KeyError, TypeError) as exc:
            raise ReadingGenerationError(
                "INVALID_READING_INPUT",
                retryable=False,
            ) from exc
        except Exception as exc:
            raise ReadingGenerationError(
                "RUNTIME_GENERATION_FAILED",
                retryable=True,
            ) from exc

    def _ensure_import_paths(self) -> None:
        scripts_dir = self._repo_root / "scripts"
        if not scripts_dir.is_dir() or not (self._repo_root / "calculation").is_dir():
            raise ReadingGenerationError(
                "RUNTIME_SOURCE_NOT_FOUND",
                retryable=False,
            )
        for path in (self._repo_root, scripts_dir):
            value = str(path)
            if value not in sys.path:
                sys.path.insert(0, value)

    def _load_runtime(self) -> None:
        try:
            from calc_western_spike import build_payload
            from complete_relationship_result_runtime import build_view_model
            from structured_runtime import load_kb_support, load_structured_kb
        except ImportError as exc:
            raise ReadingGenerationError(
                "RUNTIME_IMPORT_FAILED",
                retryable=False,
            ) from exc

        support = load_kb_support(
            "local",
            articles_path=self._kb_dir / "kb_articles.json",
            claims_path=self._kb_dir / "kb_claims.json",
        )
        if support.get("articleCount", 0) <= 0 or support.get("claimCount", 0) <= 0:
            raise ReadingGenerationError(
                "KB_SUPPORT_EMPTY",
                retryable=False,
            )
        self._articles = support["articles"]
        self._claims_by_article = support["claimsByArticle"]
        self._structured_kb = load_structured_kb(
            "local",
            atoms_path=self._kb_dir / "kb_atoms.json",
            rules_path=self._kb_dir / "kb_rules.json",
            question_blueprints_path=self._kb_dir
            / "kb_question_blueprints.json",
            guardrails_path=self._kb_dir / "kb_guardrails.json",
        )
        self._build_payload = build_payload
        self._build_view_model = build_view_model


def _validate_dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package, expected in EXPECTED_DEPENDENCIES.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError as exc:
            raise ReadingGenerationError(
                "CALCULATION_DEPENDENCY_MISSING",
                retryable=False,
            ) from exc
        if actual != expected:
            raise ReadingGenerationError(
                "CALCULATION_DEPENDENCY_VERSION_MISMATCH",
                retryable=False,
            )
        versions[package] = actual
    return versions


def _validate_supported_locations(reading_input: dict[str, Any]) -> None:
    from calculation.western.immanuel_adapter import KNOWN_PLACES, place_coordinates

    for key in ("person_a", "person_b"):
        person = reading_input[key]
        _pin_longest_known_place_coordinates(person, KNOWN_PLACES)
        coordinates, _warning = place_coordinates(person)
        if coordinates is None:
            raise ReadingGenerationError(
                "UNSUPPORTED_BIRTH_PLACE",
                retryable=False,
            )


def _pin_longest_known_place_coordinates(
    person: dict[str, Any],
    known_places: dict[str, dict[str, Any]],
) -> None:
    """Avoid substring-order ambiguity in the legacy place adapter."""

    if person.get("latitude") is not None and person.get("longitude") is not None:
        return
    normalized_place = str(person.get("birth_place") or "").strip().lower()
    if not normalized_place:
        return
    exact = known_places.get(normalized_place)
    if exact is not None:
        selected = exact
    else:
        matches = [
            (len(alias), alias, coordinates)
            for alias, coordinates in known_places.items()
            if alias in normalized_place
        ]
        if not matches:
            return
        _length, _alias, selected = max(
            matches,
            key=lambda item: (item[0], item[1]),
        )
    person["latitude"] = float(selected["latitude"])
    person["longitude"] = float(selected["longitude"])
