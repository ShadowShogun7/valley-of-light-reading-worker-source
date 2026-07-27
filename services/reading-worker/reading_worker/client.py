"""Timestamped-HMAC client for the private app worker protocol."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from . import INTAKE_VERSION, JOB_VERSION, RESULT_CONTRACT_VERSION


CLAIM_PATH = "/api/internal/reading-worker/claim"
RESULT_PATH = "/api/internal/reading-worker/result"
FAILURE_PATH = "/api/internal/reading-worker/failure"
HEARTBEAT_PATH = "/api/internal/reading-worker/heartbeat"
EMAIL_RECONCILIATION_PATH = (
    "/api/internal/reading-worker/email-reconciliation"
)


class WorkerApiError(RuntimeError):
    def __init__(
        self,
        code: str,
        *,
        retryable: bool,
        status: int | None = None,
    ):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.status = status


def sign_body(raw_body: bytes, timestamp: str, signing_secret: str) -> str:
    digest = hmac.new(
        signing_secret.encode("utf-8"),
        timestamp.encode("ascii") + b"." + raw_body,
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_body_signature(
    raw_body: bytes,
    timestamp: str | None,
    supplied_signature: str | None,
    signing_secret: str,
    *,
    now_seconds: int | None = None,
) -> bool:
    if (
        timestamp is None
        or supplied_signature is None
        or len(timestamp) != 10
        or not timestamp.isdigit()
        or len(supplied_signature) != 43
    ):
        return False
    current = int(time.time()) if now_seconds is None else now_seconds
    if abs(current - int(timestamp)) > 300:
        return False
    expected = sign_body(raw_body, timestamp, signing_secret)
    return hmac.compare_digest(expected, supplied_signature)


@dataclass
class SignedWorkerApiClient:
    app_base_url: str
    signing_secret: str
    timeout_seconds: float
    worker_id: str
    sleep: Callable[[float], None] = time.sleep

    def claim_job(self, lease_seconds: int) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        response = self._post_json(
            CLAIM_PATH,
            {
                "leaseSeconds": lease_seconds,
                "requestId": request_id,
                "workerId": self.worker_id,
            },
            idempotency_key=request_id,
        )
        if response.get("claimed") is False:
            return {"claimed": False}
        if not _valid_claim_response(response, self.worker_id):
            raise WorkerApiError("INVALID_CLAIM_RESPONSE", retryable=False)
        return response

    def submit_result(
        self,
        job: dict[str, Any],
        *,
        result_payload: dict[str, Any],
        runtime_version: str,
        source_fingerprints: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._post_json(
            RESULT_PATH,
            {
                "attemptCount": job["attempt_count"],
                "contractVersion": RESULT_CONTRACT_VERSION,
                "fulfillmentId": job["fulfillment_id"],
                "readingId": job["reading_id"],
                "resultPayload": result_payload,
                "runtimeVersion": runtime_version,
                "sourceFingerprints": source_fingerprints,
                "workerId": self.worker_id,
            },
            idempotency_key=str(job["fulfillment_id"]),
        )
        if response.get("accepted") is not True:
            raise WorkerApiError("INVALID_RESULT_RESPONSE", retryable=False)
        return response

    def report_failure(
        self,
        job: dict[str, Any],
        *,
        error_code: str,
        retryable: bool,
    ) -> dict[str, Any]:
        response = self._post_json(
            FAILURE_PATH,
            {
                "attemptCount": job["attempt_count"],
                "errorCode": error_code,
                "fulfillmentId": job["fulfillment_id"],
                "readingId": job["reading_id"],
                "retryable": retryable,
                "workerId": self.worker_id,
            },
            idempotency_key=str(job["fulfillment_id"]),
        )
        if response.get("accepted") is not True:
            raise WorkerApiError("INVALID_FAILURE_RESPONSE", retryable=False)
        return response

    def renew_lease(
        self,
        job: dict[str, Any],
        *,
        lease_seconds: int,
    ) -> dict[str, Any]:
        response = self._post_json(
            HEARTBEAT_PATH,
            {
                "attemptCount": job["attempt_count"],
                "fulfillmentId": job["fulfillment_id"],
                "leaseSeconds": lease_seconds,
                "readingId": job["reading_id"],
                "workerId": self.worker_id,
            },
            idempotency_key=(
                f"{job['fulfillment_id']}:{job['attempt_count']}:heartbeat"
            ),
        )
        if response.get("renewed") is not True:
            raise WorkerApiError(
                "INVALID_HEARTBEAT_RESPONSE",
                retryable=False,
            )
        return response

    def reconcile_email(self, limit: int) -> dict[str, Any]:
        response = self._post_json(
            EMAIL_RECONCILIATION_PATH,
            {"limit": limit},
        )
        if response.get("accepted") is not True:
            raise WorkerApiError(
                "INVALID_EMAIL_RECONCILIATION_RESPONSE",
                retryable=False,
            )
        return response

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        raw_body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        last_error: WorkerApiError | None = None
        for attempt in range(3):
            timestamp = str(int(time.time()))
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "valley-reading-worker/1",
                "X-Valley-Worker-Signature": sign_body(
                    raw_body, timestamp, self.signing_secret
                ),
                "X-Valley-Worker-Timestamp": timestamp,
            }
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
            request = urllib.request.Request(
                f"{self.app_base_url}{path}",
                data=raw_body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    response_body = response.read(4 * 1024 * 1024 + 1)
                    if len(response_body) > 4 * 1024 * 1024:
                        raise WorkerApiError(
                            "WORKER_API_RESPONSE_TOO_LARGE",
                            retryable=False,
                            status=response.status,
                        )
                    decoded = json.loads(response_body.decode("utf-8"))
                    if not isinstance(decoded, dict):
                        raise WorkerApiError(
                            "INVALID_WORKER_API_RESPONSE",
                            retryable=False,
                            status=response.status,
                        )
                    return decoded
            except urllib.error.HTTPError as exc:
                error_code = _http_error_code(exc)
                retryable = exc.code == 429 or exc.code >= 500
                last_error = WorkerApiError(
                    error_code,
                    retryable=retryable,
                    status=exc.code,
                )
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = WorkerApiError(
                    "WORKER_API_UNAVAILABLE",
                    retryable=True,
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                last_error = WorkerApiError(
                    "INVALID_WORKER_API_RESPONSE",
                    retryable=False,
                )
            if not last_error.retryable or attempt == 2:
                raise last_error
            self.sleep(0.5 * (2**attempt))
        raise last_error or WorkerApiError(
            "WORKER_API_UNAVAILABLE",
            retryable=True,
        )


def _http_error_code(error: urllib.error.HTTPError) -> str:
    try:
        raw = error.read(16 * 1024)
        payload = json.loads(raw.decode("utf-8"))
        code = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(code, str) and 2 <= len(code) <= 120:
            return code
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        pass
    return f"WORKER_API_HTTP_{error.code}"


def _valid_claim_response(payload: dict[str, Any], worker_id: str) -> bool:
    required_strings = (
        "analysis_datetime",
        "fulfillment_id",
        "generation_consent_version",
        "intake_version",
        "lease_expires_at",
        "public_reading_id",
        "reading_id",
    )
    if (
        payload.get("claimed") is not True
        or payload.get("version") != JOB_VERSION
        or payload.get("intake_version") != INTAKE_VERSION
        or payload.get("worker_id") != worker_id
        or payload.get("analysis_timezone") != "Asia/Taipei"
        or not isinstance(payload.get("final_payload"), dict)
        or not isinstance(payload.get("precision_snapshot"), dict)
    ):
        return False
    attempt_count = payload.get("attempt_count")
    if (
        isinstance(attempt_count, bool)
        or not isinstance(attempt_count, int)
        or attempt_count <= 0
    ):
        return False
    if any(
        not isinstance(payload.get(key), str) or not payload[key]
        for key in required_strings
    ):
        return False
    for key in ("fulfillment_id", "public_reading_id", "reading_id"):
        try:
            uuid.UUID(payload[key])
        except (ValueError, TypeError, AttributeError):
            return False
    for key in ("analysis_datetime", "lease_expires_at"):
        try:
            parsed = datetime.fromisoformat(payload[key].replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            return False
    return True
