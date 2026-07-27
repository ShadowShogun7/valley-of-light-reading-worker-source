from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from book_digests import flattened_digests, load_book_digest_files
from kb_utils import ROOT, load_source_manifest, read_text


BOOK_COVERAGE_DIR = ROOT / "kb" / "book_coverage"
COVERAGE_ID_RE = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SOURCE_LOCATION_RE = re.compile(r"([^:]+):(\d+)(?:-(\d+))?")
TRACKED_SYSTEMS = {"western", "consultation", "relationship"}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CoverageSection(StrictModel):
    section_id: str
    title: str
    line_range: str = ""
    topics: list[str] = Field(default_factory=list)
    runtime_targets: list[str] = Field(default_factory=list)
    status: Literal["unread", "mapped", "extracted", "reviewed", "implemented", "blocked"]
    blocked_reason: str = ""
    digest_claim_ids: list[str] = Field(default_factory=list)

    @field_validator("section_id")
    @classmethod
    def validate_section_id(cls, value: str) -> str:
        if not re.fullmatch(COVERAGE_ID_RE, value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @model_validator(mode="after")
    def validate_status_contract(self) -> "CoverageSection":
        if self.status == "blocked" and not self.blocked_reason:
            raise ValueError("blocked sections require blocked_reason")
        if self.status in {"reviewed", "implemented"} and not self.digest_claim_ids:
            raise ValueError("reviewed/implemented sections require digest_claim_ids")
        return self


class SourceCoverage(StrictModel):
    source_id: str
    priority: Literal["P0", "P1", "P2", "reserve"]
    product_role: str
    sections: list[CoverageSection] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        if not re.fullmatch(COVERAGE_ID_RE, value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @model_validator(mode="after")
    def validate_sections(self) -> "SourceCoverage":
        if not self.sections:
            raise ValueError("source coverage requires at least one section")
        section_ids = [section.section_id for section in self.sections]
        duplicates = sorted(section_id for section_id in set(section_ids) if section_ids.count(section_id) > 1)
        if duplicates:
            raise ValueError(f"duplicate section ids: {', '.join(duplicates)}")
        return self


class BookCoverageFile(StrictModel):
    version: Literal["kb-book-coverage-v1"]
    sources: list[SourceCoverage] = Field(default_factory=list)


@dataclass(frozen=True)
class LoadedBookCoverageFile:
    path: Path
    parsed: BookCoverageFile


def coverage_yaml_files(directory: Path = BOOK_COVERAGE_DIR) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([*directory.rglob("*.yml"), *directory.rglob("*.yaml")])


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(read_text(path)) or {}
    if not isinstance(payload, dict):
        raise ValueError("YAML root must be a mapping")
    return payload


def load_book_coverage_files(directory: Path = BOOK_COVERAGE_DIR) -> list[LoadedBookCoverageFile]:
    loaded: list[LoadedBookCoverageFile] = []
    errors: list[str] = []
    for path in coverage_yaml_files(directory):
        try:
            loaded.append(LoadedBookCoverageFile(path=path, parsed=BookCoverageFile.model_validate(read_yaml_mapping(path))))
        except (ValidationError, ValueError) as error:
            errors.append(f"{path.relative_to(ROOT)}: {error}")
    if errors:
        raise ValueError("\n".join(errors))
    return loaded


def flattened_coverages(loaded_files: list[LoadedBookCoverageFile]) -> list[SourceCoverage]:
    return [source for loaded in loaded_files for source in loaded.parsed.sources]


def source_manifest_map() -> dict[str, dict[str, Any]]:
    return {
        str(source.get("id")): source
        for source in load_source_manifest().get("sources", [])
        if isinstance(source, dict) and source.get("id")
    }


def tracked_source_ids() -> set[str]:
    return {
        source_id
        for source_id, source in source_manifest_map().items()
        if str(source.get("system") or "") in TRACKED_SYSTEMS
    }


def digest_claim_source_map() -> dict[str, str]:
    claim_sources: dict[str, str] = {}
    for digest in flattened_digests(load_book_digest_files()):
        for claim in digest.method_claims:
            claim_sources[claim.id] = digest.source_id
    return claim_sources


def parse_line_range(value: str) -> tuple[Path, int, int] | None:
    if not value:
        return None
    match = SOURCE_LOCATION_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"invalid line_range {value!r}; expected raw/path.txt:start-end")
    relative_path = Path(match.group(1))
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"line_range must be a safe repo-relative path: {value!r}")
    start_line = int(match.group(2))
    end_line = int(match.group(3) or match.group(2))
    if start_line < 1 or end_line < start_line:
        raise ValueError(f"invalid line_range line numbers: {value!r}")
    return relative_path, start_line, end_line


def validate_line_range(value: str) -> str | None:
    parsed = parse_line_range(value)
    if parsed is None:
        return None
    relative_path, _start_line, end_line = parsed
    source_file = ROOT / relative_path
    if not source_file.exists():
        return f"line_range file does not exist: {value}"
    line_count = read_text(source_file).count("\n") + 1
    if end_line > line_count:
        return f"line_range exceeds file length: {value}"
    return None


def validate_book_coverage_contract(coverages: list[SourceCoverage]) -> list[str]:
    errors: list[str] = []
    known_sources = source_manifest_map()
    expected_sources = tracked_source_ids()
    known_claim_sources = digest_claim_source_map()

    source_ids = [coverage.source_id for coverage in coverages]
    duplicate_sources = sorted(source_id for source_id in set(source_ids) if source_ids.count(source_id) > 1)
    for source_id in duplicate_sources:
        errors.append(f"duplicate source coverage: {source_id}")

    missing_sources = sorted(expected_sources - set(source_ids))
    for source_id in missing_sources:
        errors.append(f"missing coverage for tracked source: {source_id}")

    unknown_sources = sorted(set(source_ids) - set(known_sources))
    for source_id in unknown_sources:
        errors.append(f"unknown source_id in coverage: {source_id}")

    section_ids = [
        f"{coverage.source_id}:{section.section_id}"
        for coverage in coverages
        for section in coverage.sections
    ]
    duplicate_sections = sorted(section_id for section_id in set(section_ids) if section_ids.count(section_id) > 1)
    for section_id in duplicate_sections:
        errors.append(f"duplicate coverage section: {section_id}")

    for coverage in coverages:
        manifest_source = known_sources.get(coverage.source_id) or {}
        manifest_raw_path = str(manifest_source.get("raw_path") or "")
        for section in coverage.sections:
            if section.line_range:
                line_error = validate_line_range(section.line_range)
                if line_error:
                    errors.append(f"{coverage.source_id}:{section.section_id}: {line_error}")
                parsed = parse_line_range(section.line_range)
                if parsed and manifest_raw_path and str(parsed[0]) != manifest_raw_path:
                    errors.append(
                        f"{coverage.source_id}:{section.section_id}: line_range path {parsed[0]} "
                        f"does not match source raw_path {manifest_raw_path}"
                    )
            for claim_id in section.digest_claim_ids:
                claim_source = known_claim_sources.get(claim_id)
                if not claim_source:
                    errors.append(f"{coverage.source_id}:{section.section_id}: unknown digest claim id {claim_id}")
                elif claim_source != coverage.source_id:
                    errors.append(
                        f"{coverage.source_id}:{section.section_id}: claim {claim_id} belongs to {claim_source}"
                    )
    return errors


def coverage_stats(coverages: list[SourceCoverage]) -> dict[str, Any]:
    source_statuses: dict[str, Counter[str]] = {}
    status_counts: Counter[str] = Counter()
    target_counts: Counter[str] = Counter()
    claim_ids: set[str] = set()
    for coverage in coverages:
        source_counter: Counter[str] = Counter()
        for section in coverage.sections:
            status_counts[section.status] += 1
            source_counter[section.status] += 1
            target_counts.update(section.runtime_targets)
            claim_ids.update(section.digest_claim_ids)
        source_statuses[coverage.source_id] = source_counter
    return {
        "source_count": len(coverages),
        "section_count": sum(len(coverage.sections) for coverage in coverages),
        "status_counts": dict(status_counts),
        "runtime_target_counts": dict(sorted(target_counts.items())),
        "digest_claim_count": len(claim_ids),
        "source_statuses": {source_id: dict(counter) for source_id, counter in sorted(source_statuses.items())},
    }
