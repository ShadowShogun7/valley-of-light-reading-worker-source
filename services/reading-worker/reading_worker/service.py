"""One-job-at-a-time worker loop plus independent email reconciliation."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Protocol

from .client import WorkerApiError


LOGGER = logging.getLogger("valley-reading-worker")


class RuntimeProtocol(Protocol):
    runtime_version: str
    source_fingerprints: dict[str, Any]


class GenerationRunnerProtocol(Protocol):
    def run(
        self,
        job: dict[str, Any],
        *,
        heartbeat: Any,
    ) -> dict[str, Any]: ...


class ClientProtocol(Protocol):
    def claim_job(self, lease_seconds: int) -> dict[str, Any]: ...

    def submit_result(
        self,
        job: dict[str, Any],
        *,
        result_payload: dict[str, Any],
        runtime_version: str,
        source_fingerprints: dict[str, Any],
    ) -> dict[str, Any]: ...

    def report_failure(
        self,
        job: dict[str, Any],
        *,
        error_code: str,
        retryable: bool,
    ) -> dict[str, Any]: ...

    def renew_lease(
        self,
        job: dict[str, Any],
        *,
        lease_seconds: int,
    ) -> dict[str, Any]: ...

    def reconcile_email(self, limit: int) -> dict[str, Any]: ...


class HealthState:
    def __init__(
        self,
        *,
        email_loop_stale_seconds: float = 180,
        email_success_stale_seconds: float = 180,
        email_success_startup_grace_seconds: float = 180,
        job_loop_stale_seconds: float = 120,
        job_timeout_seconds: float = 900,
        lease_heartbeat_stale_seconds: float = 150,
        runtime_version: str,
    ):
        self._lock = threading.Lock()
        now_monotonic = time.monotonic()
        self._base_ready = True
        self._email_loop_stale_seconds = email_loop_stale_seconds
        self._email_success_stale_seconds = email_success_stale_seconds
        self._email_success_startup_grace_seconds = (
            email_success_startup_grace_seconds
        )
        self._started_at = now_monotonic
        self._last_email_reconciliation_success = None
        self._job_loop_stale_seconds = job_loop_stale_seconds
        self._job_timeout_seconds = job_timeout_seconds
        self._last_email_loop_tick = now_monotonic
        self._last_job_loop_tick = now_monotonic
        self._lease_heartbeat_stale_seconds = lease_heartbeat_stale_seconds
        self._active_job_started = None
        self._last_lease_heartbeat = None
        self._state: dict[str, Any] = {
            "activeJob": False,
            "activeJobStartedAt": None,
            "lastEmailReconciliationAt": None,
            "lastEmailReconciliationError": None,
            "lastEmailReconciliationFailureAt": None,
            "lastJobFinishedAt": None,
            "lastJobOutcome": None,
            "lastLeaseHeartbeatAt": None,
            "ready": True,
            "runtimeVersion": runtime_version,
            "service": "valley-reading-worker",
        }

    def update(self, **values: Any) -> None:
        with self._lock:
            if "ready" in values:
                self._base_ready = bool(values["ready"])
            self._state.update(values)

    def job_loop_tick(self) -> None:
        with self._lock:
            self._last_job_loop_tick = time.monotonic()

    def email_loop_tick(self) -> None:
        with self._lock:
            self._last_email_loop_tick = time.monotonic()

    def email_reconciliation_succeeded(self) -> None:
        with self._lock:
            self._last_email_reconciliation_success = time.monotonic()
            self._state.update(
                lastEmailReconciliationAt=_now_iso(),
                lastEmailReconciliationError=None,
            )

    def email_reconciliation_failed(self, error_code: str) -> None:
        with self._lock:
            self._state.update(
                lastEmailReconciliationError=error_code,
                lastEmailReconciliationFailureAt=_now_iso(),
            )

    def job_started(self) -> None:
        with self._lock:
            now = time.monotonic()
            now_iso = _now_iso()
            self._active_job_started = now
            self._last_lease_heartbeat = now
            self._state.update(
                activeJob=True,
                activeJobStartedAt=now_iso,
                lastLeaseHeartbeatAt=now_iso,
            )

    def lease_heartbeat(self) -> None:
        with self._lock:
            self._last_lease_heartbeat = time.monotonic()
            self._state["lastLeaseHeartbeatAt"] = _now_iso()

    def job_finished(self, outcome: str) -> None:
        with self._lock:
            self._active_job_started = None
            self._last_lease_heartbeat = None
            self._state.update(
                activeJob=False,
                activeJobStartedAt=None,
                lastJobFinishedAt=_now_iso(),
                lastJobOutcome=outcome,
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            now = time.monotonic()
            ready = (
                self._base_ready
                and now - self._last_email_loop_tick
                <= self._email_loop_stale_seconds
            )
            if self._last_email_reconciliation_success is None:
                ready = (
                    ready
                    and now - self._started_at
                    <= self._email_success_startup_grace_seconds
                )
            else:
                ready = (
                    ready
                    and now - self._last_email_reconciliation_success
                    <= self._email_success_stale_seconds
                )
            if self._active_job_started is not None:
                ready = (
                    ready
                    and now - self._active_job_started <= self._job_timeout_seconds
                    and self._last_lease_heartbeat is not None
                    and now - self._last_lease_heartbeat
                    <= self._lease_heartbeat_stale_seconds
                )
            else:
                ready = (
                    ready
                    and now - self._last_job_loop_tick
                    <= self._job_loop_stale_seconds
                )
            snapshot = dict(self._state)
            snapshot["ready"] = ready
            return snapshot


class WorkerService:
    def __init__(
        self,
        *,
        client: ClientProtocol,
        email_reconciliation_limit: int,
        email_reconciliation_seconds: float,
        generation_runner: GenerationRunnerProtocol,
        health: HealthState,
        lease_seconds: int,
        poll_seconds: float,
        runtime: RuntimeProtocol,
    ):
        self._client = client
        self._email_reconciliation_limit = email_reconciliation_limit
        self._email_reconciliation_seconds = email_reconciliation_seconds
        self._generation_runner = generation_runner
        self._health = health
        self._lease_seconds = lease_seconds
        self._poll_seconds = poll_seconds
        self._runtime = runtime
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._threads:
            return
        self._threads = [
            threading.Thread(
                target=self._job_loop,
                name="reading-job-loop",
                daemon=True,
            ),
            threading.Thread(
                target=self._email_loop,
                name="email-reconciliation-loop",
                daemon=True,
            ),
        ]
        for thread in self._threads:
            thread.start()
        self._wake_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        for thread in self._threads:
            thread.join(timeout=10)
        self._threads = []

    def wake(self) -> None:
        self._wake_event.set()

    def process_one(self) -> bool:
        try:
            job = self._client.claim_job(self._lease_seconds)
        except WorkerApiError as error:
            log_event("CLAIM_FAILED", errorCode=error.code)
            return False
        except Exception:
            log_event("CLAIM_FAILED", errorCode="WORKER_API_UNAVAILABLE")
            return False
        if job.get("claimed") is not True:
            return False

        self._health.job_started()
        log_event(
            "JOB_CLAIMED",
            attemptCount=job.get("attempt_count"),
            fulfillmentId=job.get("fulfillment_id"),
        )
        outcome = "failed"
        try:
            result = self._generation_runner.run(
                job,
                heartbeat=lambda: self._renew_lease(job),
            )
            try:
                self._client.submit_result(
                    job,
                    result_payload=result,
                    runtime_version=self._runtime.runtime_version,
                    source_fingerprints=self._runtime.source_fingerprints,
                )
            except WorkerApiError as error:
                # The result endpoint may have committed before a downstream email
                # failure or transport timeout. Do not race it with a failure
                # callback; the fenced lease/idempotent result path will recover.
                log_event(
                    "RESULT_CALLBACK_UNCONFIRMED",
                    errorCode=error.code,
                    fulfillmentId=job.get("fulfillment_id"),
                )
                outcome = "callback_unconfirmed"
                return True
            outcome = "succeeded"
            log_event(
                "JOB_SUCCEEDED",
                fulfillmentId=job.get("fulfillment_id"),
            )
            return True
        except Exception as error:
            error_code = _safe_error_code(error)
            retryable = bool(getattr(error, "retryable", True))
            try:
                self._client.report_failure(
                    job,
                    error_code=error_code,
                    retryable=retryable,
                )
            except WorkerApiError as callback_error:
                log_event(
                    "FAILURE_CALLBACK_UNCONFIRMED",
                    errorCode=callback_error.code,
                    fulfillmentId=job.get("fulfillment_id"),
                )
            except Exception:
                log_event(
                    "FAILURE_CALLBACK_UNCONFIRMED",
                    errorCode="WORKER_API_UNAVAILABLE",
                    fulfillmentId=job.get("fulfillment_id"),
                )
            log_event(
                "JOB_FAILED",
                errorCode=error_code,
                fulfillmentId=job.get("fulfillment_id"),
                retryable=retryable,
            )
            return True
        finally:
            self._health.job_finished(outcome)

    def _renew_lease(self, job: dict[str, Any]) -> None:
        self._client.renew_lease(
            job,
            lease_seconds=self._lease_seconds,
        )
        self._health.lease_heartbeat()
        log_event(
            "JOB_LEASE_RENEWED",
            attemptCount=job.get("attempt_count"),
            fulfillmentId=job.get("fulfillment_id"),
        )

    def reconcile_email_once(self) -> None:
        try:
            result = self._client.reconcile_email(
                self._email_reconciliation_limit
            )
            failed = result.get("failed")
            if not isinstance(failed, int) or failed < 0:
                self._health.email_reconciliation_failed(
                    "INVALID_EMAIL_RECONCILIATION_RESPONSE"
                )
                log_event(
                    "EMAIL_RECONCILIATION_FAILED",
                    errorCode="INVALID_EMAIL_RECONCILIATION_RESPONSE",
                )
                return
            if failed > 0:
                self._health.email_reconciliation_failed(
                    "EMAIL_DELIVERY_CANDIDATES_FAILED"
                )
                log_event(
                    "EMAIL_RECONCILIATION_FAILED",
                    errorCode="EMAIL_DELIVERY_CANDIDATES_FAILED",
                    failed=failed,
                )
                return
            self._health.email_reconciliation_succeeded()
            log_event(
                "EMAIL_RECONCILIATION_COMPLETED",
                candidates=result.get("candidates"),
                providerAccepted=result.get("providerAccepted"),
                failed=result.get("failed"),
                skipped=result.get("skipped"),
            )
        except WorkerApiError as error:
            self._health.email_reconciliation_failed(error.code)
            log_event(
                "EMAIL_RECONCILIATION_FAILED",
                errorCode=error.code,
            )
        except Exception:
            self._health.email_reconciliation_failed(
                "WORKER_API_UNAVAILABLE"
            )
            log_event(
                "EMAIL_RECONCILIATION_FAILED",
                errorCode="WORKER_API_UNAVAILABLE",
            )

    def _job_loop(self) -> None:
        while not self._stop_event.is_set():
            self._health.job_loop_tick()
            self._wake_event.wait(timeout=self._poll_seconds)
            self._wake_event.clear()
            if self._stop_event.is_set():
                break
            claimed = self.process_one()
            if claimed and not self._stop_event.is_set():
                # Drain sequentially while preserving the one-job-at-a-time rule.
                self._wake_event.set()

    def _email_loop(self) -> None:
        self._health.email_loop_tick()
        initial_delay = min(5.0, self._email_reconciliation_seconds)
        if self._stop_event.wait(initial_delay):
            return
        while not self._stop_event.is_set():
            self._health.email_loop_tick()
            self.reconcile_email_once()
            if self._stop_event.wait(self._email_reconciliation_seconds):
                break


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    LOGGER.info(
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _safe_error_code(error: Exception) -> str:
    raw = getattr(error, "code", None)
    if isinstance(raw, str) and re.fullmatch(r"[A-Z0-9_]{2,80}", raw):
        return raw
    return "RUNTIME_GENERATION_FAILED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
