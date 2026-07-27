"""Fail-closed environment configuration for the reading worker."""

from __future__ import annotations

import os
import re
import socket
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from . import INTAKE_VERSION, JOB_VERSION, RESULT_CONTRACT_VERSION, RUNTIME_VERSION


LICENSE_DECISION_ENV = "VALLEY_ASTROLOGY_LICENSE_DECISION"
LICENSE_DECISION_VALUE = "agpl-3.0"
SOURCE_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
WORKER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")


class ConfigurationError(RuntimeError):
    """Raised when the worker must not start with the supplied configuration."""


@dataclass(frozen=True)
class WorkerConfig:
    app_base_url: str
    email_reconciliation_limit: int
    email_reconciliation_seconds: float
    expected_intake_version: str
    expected_job_version: str
    expected_result_contract_version: str
    expected_runtime_version: str
    http_timeout_seconds: float
    kb_dir: Path
    job_timeout_seconds: float
    lease_heartbeat_seconds: float
    lease_seconds: int
    license_decision: str
    max_result_bytes: int
    poll_seconds: float
    port: int
    repo_root: Path
    signing_secret: str
    source_code_sha256: str
    source_code_url: str
    worker_id: str

    @classmethod
    def from_environment(cls) -> "WorkerConfig":
        app_base_url = _required_first(
            "VALLEY_APP_API_BASE_URL",
            "VALEOFLIGHT_APP_BASE_URL",
        ).rstrip("/")
        parsed_url = urlparse(app_base_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc or parsed_url.path not in {"", "/"}:
            raise ConfigurationError(
                "VALLEY_APP_API_BASE_URL must be an HTTPS origin without a path"
            )

        signing_secret = _required("VALLEY_WORKER_SIGNING_SECRET")
        if len(signing_secret.encode("utf-8")) < 32:
            raise ConfigurationError(
                "VALLEY_WORKER_SIGNING_SECRET must contain at least 32 UTF-8 bytes"
            )

        license_decision = _required(LICENSE_DECISION_ENV)
        if license_decision != LICENSE_DECISION_VALUE:
            raise ConfigurationError(
                f"{LICENSE_DECISION_ENV} must equal {LICENSE_DECISION_VALUE!r} "
                "only for an AGPL source-published deployment"
            )

        source_code_url = _required("VALLEY_AGPL_SOURCE_URL")
        parsed_source_url = urlparse(source_code_url)
        if (
            parsed_source_url.scheme != "https"
            or not parsed_source_url.netloc
            or parsed_source_url.username
            or parsed_source_url.password
            or parsed_source_url.fragment
        ):
            raise ConfigurationError(
                "VALLEY_AGPL_SOURCE_URL must be a public HTTPS URL without "
                "credentials or a fragment"
            )
        source_code_sha256 = _required("VALLEY_AGPL_SOURCE_SHA256").lower()
        if not SOURCE_SHA256_PATTERN.fullmatch(source_code_sha256):
            raise ConfigurationError(
                "VALLEY_AGPL_SOURCE_SHA256 must be a lowercase SHA-256 digest"
            )

        worker_id = os.environ.get("VALLEY_WORKER_ID", "").strip() or _default_worker_id()
        if not WORKER_ID_PATTERN.fullmatch(worker_id):
            raise ConfigurationError(
                "VALLEY_WORKER_ID must match [A-Za-z0-9._:-]{1,120}"
            )

        expected_job_version = os.environ.get(
            "VALLEY_EXPECTED_JOB_VERSION", JOB_VERSION
        ).strip()
        expected_intake_version = os.environ.get(
            "VALLEY_EXPECTED_INTAKE_VERSION", INTAKE_VERSION
        ).strip()
        expected_result_contract_version = os.environ.get(
            "VALLEY_EXPECTED_RESULT_CONTRACT_VERSION",
            RESULT_CONTRACT_VERSION,
        ).strip()
        expected_runtime_version = os.environ.get(
            "VALLEY_EXPECTED_RUNTIME_VERSION", RUNTIME_VERSION
        ).strip()
        if expected_job_version != JOB_VERSION:
            raise ConfigurationError(
                f"Unsupported VALLEY_EXPECTED_JOB_VERSION: {expected_job_version!r}"
            )
        if expected_intake_version != INTAKE_VERSION:
            raise ConfigurationError(
                "Unsupported VALLEY_EXPECTED_INTAKE_VERSION: "
                f"{expected_intake_version!r}"
            )
        if expected_result_contract_version != RESULT_CONTRACT_VERSION:
            raise ConfigurationError(
                "Unsupported VALLEY_EXPECTED_RESULT_CONTRACT_VERSION: "
                f"{expected_result_contract_version!r}"
            )
        if expected_runtime_version != RUNTIME_VERSION:
            raise ConfigurationError(
                f"Unsupported VALLEY_EXPECTED_RUNTIME_VERSION: {expected_runtime_version!r}"
            )

        lease_seconds = _integer(
            "VALLEY_WORKER_LEASE_SECONDS", 300, minimum=60, maximum=1800
        )
        lease_heartbeat_seconds = _number(
            "VALLEY_WORKER_LEASE_HEARTBEAT_SECONDS",
            60,
            minimum=10,
            maximum=300,
        )
        if lease_heartbeat_seconds >= lease_seconds / 2:
            raise ConfigurationError(
                "VALLEY_WORKER_LEASE_HEARTBEAT_SECONDS must be less than "
                "half of VALLEY_WORKER_LEASE_SECONDS"
            )

        job_timeout_seconds = _number(
            "VALLEY_WORKER_JOB_TIMEOUT_SECONDS",
            900,
            minimum=60,
            maximum=3600,
        )
        if job_timeout_seconds <= lease_heartbeat_seconds:
            raise ConfigurationError(
                "VALLEY_WORKER_JOB_TIMEOUT_SECONDS must exceed "
                "VALLEY_WORKER_LEASE_HEARTBEAT_SECONDS"
            )

        return cls(
            app_base_url=app_base_url,
            email_reconciliation_limit=_integer(
                "VALLEY_EMAIL_RECONCILIATION_LIMIT", 5, minimum=1, maximum=20
            ),
            email_reconciliation_seconds=_number(
                "VALLEY_EMAIL_RECONCILIATION_SECONDS",
                60,
                minimum=30,
                maximum=3600,
            ),
            expected_job_version=expected_job_version,
            expected_intake_version=expected_intake_version,
            expected_result_contract_version=expected_result_contract_version,
            expected_runtime_version=expected_runtime_version,
            http_timeout_seconds=_number(
                "VALLEY_WORKER_HTTP_TIMEOUT_SECONDS",
                20,
                minimum=2,
                maximum=120,
            ),
            kb_dir=Path(
                os.environ.get("VALLEY_KB_DIR", "/opt/valley/dist/kb")
            ).resolve(),
            job_timeout_seconds=job_timeout_seconds,
            lease_heartbeat_seconds=lease_heartbeat_seconds,
            lease_seconds=lease_seconds,
            license_decision=license_decision,
            max_result_bytes=_integer(
                "VALLEY_WORKER_MAX_RESULT_BYTES",
                3_500_000,
                minimum=100_000,
                maximum=3_800_000,
            ),
            poll_seconds=_number(
                "VALLEY_WORKER_POLL_SECONDS", 15, minimum=1, maximum=300
            ),
            port=_integer("PORT", 8080, minimum=1, maximum=65535),
            repo_root=Path(
                os.environ.get("VALLEY_REPO_ROOT", "/opt/valley")
            ).resolve(),
            signing_secret=signing_secret,
            source_code_sha256=source_code_sha256,
            source_code_url=source_code_url,
            worker_id=worker_id,
        )


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _required_first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise ConfigurationError(
        f"Missing required environment variable: {' or '.join(names)}"
    )


def _integer(
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def _number(
    name: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if value < minimum or value > maximum:
        raise ConfigurationError(
            f"{name} must be between {minimum:g} and {maximum:g}"
        )
    return value


def _default_worker_id() -> str:
    raw_host = socket.gethostname().lower()
    host = re.sub(r"[^a-z0-9.-]+", "-", raw_host).strip(".-") or "host"
    suffix = uuid.uuid4().hex[:12]
    return f"reading-worker:{host[:80]}:{suffix}"
