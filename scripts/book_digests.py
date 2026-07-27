from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from kb_utils import ROOT, load_source_manifest, read_text


BOOK_DIGEST_DIR = ROOT / "kb" / "book_digests"
DIGEST_ID_RE = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SOURCE_GUIDED_POLICY_TYPES = {
    "product_rule",
    "question_selector",
    "advanced_layer_guardrail",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MethodClaim(StrictModel):
    id: str
    claim_type: str
    summary: str
    use_for: list[str] = Field(default_factory=list)
    runtime_targets: list[str] = Field(default_factory=list)
    implementation_status: Literal["implemented", "partial", "not_started", "blocked"]
    evidence_level: Literal["source_backed", "source_guided", "product_hypothesis"]
    source_basis: list[str] = Field(default_factory=list)
    source_locations: list[str] = Field(default_factory=list)
    review_notes: list[str] = Field(default_factory=list)
    must_not_claim: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        import re

        if not re.fullmatch(DIGEST_ID_RE, value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @model_validator(mode="after")
    def validate_source_contract(self) -> "MethodClaim":
        if self.evidence_level != "product_hypothesis" and not self.source_basis:
            raise ValueError("source_guided/source_backed claims require source_basis")
        if self.evidence_level == "source_backed" and not self.source_locations:
            raise ValueError("source_backed claims require source_locations")
        for location in self.source_locations:
            match = re.fullmatch(r"([^:]+):(\d+)(?:-(\d+))?", location)
            if not match:
                raise ValueError(f"invalid source location {location!r}; expected relative/path.txt:line or :start-end")
            relative_path = Path(match.group(1))
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise ValueError(f"source location must be a safe repo-relative path: {location!r}")
            source_file = ROOT / relative_path
            if not source_file.exists():
                raise ValueError(f"source location file does not exist: {location!r}")
            start_line = int(match.group(2))
            end_line = int(match.group(3) or match.group(2))
            if start_line < 1 or end_line < start_line:
                raise ValueError(f"invalid source location line range: {location!r}")
            line_count = read_text(source_file).count("\n") + 1
            if end_line > line_count:
                raise ValueError(f"source location exceeds file length: {location!r}")
        return self


class BookDigest(StrictModel):
    id: str
    source_id: str
    lane: Literal["astrology_method", "situation_handling"]
    status: Literal["seed", "reviewed", "approved"]
    priority: Literal["P0", "P1", "P2", "reserve"]
    product_role: str
    method_scope: list[str] = Field(default_factory=list)
    extraction_goal: str
    method_claims: list[MethodClaim] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("id", "source_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        import re

        if not re.fullmatch(DIGEST_ID_RE, value):
            raise ValueError("must be kebab-case ASCII")
        return value

    @model_validator(mode="after")
    def validate_claim_ids_unique(self) -> "BookDigest":
        ids = [claim.id for claim in self.method_claims]
        duplicates = sorted(claim_id for claim_id in set(ids) if ids.count(claim_id) > 1)
        if duplicates:
            raise ValueError(f"duplicate method claim ids: {', '.join(duplicates)}")
        return self


class BookDigestFile(StrictModel):
    version: Literal["kb-book-digests-v1"]
    digests: list[BookDigest] = Field(default_factory=list)


@dataclass(frozen=True)
class LoadedDigestFile:
    path: Path
    parsed: BookDigestFile


def digest_yaml_files(directory: Path = BOOK_DIGEST_DIR) -> list[Path]:
    if not directory.exists():
        return []
    return sorted([*directory.rglob("*.yml"), *directory.rglob("*.yaml")])


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(read_text(path)) or {}
    if not isinstance(payload, dict):
        raise ValueError("YAML root must be a mapping")
    return payload


def load_book_digest_files(directory: Path = BOOK_DIGEST_DIR) -> list[LoadedDigestFile]:
    loaded: list[LoadedDigestFile] = []
    errors: list[str] = []
    for path in digest_yaml_files(directory):
        try:
            loaded.append(LoadedDigestFile(path=path, parsed=BookDigestFile.model_validate(read_yaml_mapping(path))))
        except (ValidationError, ValueError) as error:
            errors.append(f"{path.relative_to(ROOT)}: {error}")
    if errors:
        raise ValueError("\n".join(errors))
    return loaded


def flattened_digests(loaded_files: list[LoadedDigestFile]) -> list[BookDigest]:
    return [digest for loaded in loaded_files for digest in loaded.parsed.digests]


def source_ids() -> set[str]:
    return {
        str(source.get("id"))
        for source in load_source_manifest().get("sources", [])
        if isinstance(source, dict) and source.get("id")
    }


def validate_book_digest_contract(digests: list[BookDigest]) -> list[str]:
    errors: list[str] = []
    known_source_ids = source_ids()

    digest_ids = [digest.id for digest in digests]
    duplicate_digests = sorted(digest_id for digest_id in set(digest_ids) if digest_ids.count(digest_id) > 1)
    for digest_id in duplicate_digests:
        errors.append(f"duplicate digest id: {digest_id}")

    claim_ids = [claim.id for digest in digests for claim in digest.method_claims]
    duplicate_claims = sorted(claim_id for claim_id in set(claim_ids) if claim_ids.count(claim_id) > 1)
    for claim_id in duplicate_claims:
        errors.append(f"duplicate method claim id across files: {claim_id}")

    for digest in digests:
        if digest.source_id not in known_source_ids:
            errors.append(f"{digest.id}: unknown source_id {digest.source_id}")
        if not digest.method_claims:
            errors.append(f"{digest.id}: no method_claims")
        if digest.status in {"reviewed", "approved"}:
            source_backed_count = sum(1 for claim in digest.method_claims if claim.evidence_level == "source_backed")
            if source_backed_count == 0:
                errors.append(f"{digest.id}: reviewed/approved digest has no source-backed claims")
        if digest.priority == "P0" and digest.status == "seed":
            source_guided_count = sum(
                1
                for claim in digest.method_claims
                if claim.evidence_level in {"source_backed", "source_guided"}
            )
            if source_guided_count == 0:
                errors.append(f"{digest.id}: P0 digest has no source-guided/source-backed claims")
        for claim in digest.method_claims:
            if claim.evidence_level != "source_guided" or claim.implementation_status == "blocked":
                continue
            prefix = f"{digest.id}/{claim.id}"
            if claim.claim_type not in SOURCE_GUIDED_POLICY_TYPES:
                errors.append(
                    f"{prefix}: source_guided implemented claims must be explicit product-policy or guardrail types"
                )
            if not claim.source_locations:
                errors.append(f"{prefix}: source_guided implemented claims require source_locations")
            if not claim.review_notes:
                errors.append(f"{prefix}: source_guided implemented claims require review_notes explaining policy status")
            if not claim.must_not_claim:
                errors.append(f"{prefix}: source_guided implemented claims require must_not_claim boundaries")

    return errors


def digest_stats(digests: list[BookDigest]) -> dict[str, Any]:
    status_counts = Counter(digest.status for digest in digests)
    lane_counts = Counter(digest.lane for digest in digests)
    priority_counts = Counter(digest.priority for digest in digests)
    implementation_counts = Counter(
        claim.implementation_status
        for digest in digests
        for claim in digest.method_claims
    )
    evidence_counts = Counter(
        claim.evidence_level
        for digest in digests
        for claim in digest.method_claims
    )
    target_counts: dict[str, int] = defaultdict(int)
    for digest in digests:
        for claim in digest.method_claims:
            for target in claim.runtime_targets:
                target_counts[target] += 1
    return {
        "digest_count": len(digests),
        "method_claim_count": sum(len(digest.method_claims) for digest in digests),
        "status_counts": dict(status_counts),
        "lane_counts": dict(lane_counts),
        "priority_counts": dict(priority_counts),
        "implementation_counts": dict(implementation_counts),
        "evidence_counts": dict(evidence_counts),
        "target_counts": dict(sorted(target_counts.items())),
    }
