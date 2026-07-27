from __future__ import annotations

import unittest
import time

from reading_worker.service import HealthState, WorkerService


class FakeRuntime:
    runtime_version = "valley-paid-reading-runtime-v1"
    source_fingerprints = {"kbManifestSha256": "a" * 64}

    def __init__(self, error: Exception | None = None):
        self.error = error


class FakeGenerationRunner:
    def __init__(self, runtime: FakeRuntime, *, heartbeat: bool = False):
        self.runtime = runtime
        self.should_heartbeat = heartbeat

    def run(self, job: dict, *, heartbeat: object) -> dict:
        if self.should_heartbeat:
            heartbeat()
        if self.runtime.error:
            raise self.runtime.error
        return {"contractVersion": "complete-relationship-result-v1"}


class FakeGenerationError(RuntimeError):
    code = "UNSUPPORTED_BIRTH_PLACE"
    retryable = False


class FakeClient:
    def __init__(self, job: dict):
        self.job = job
        self.results: list[dict] = []
        self.failures: list[dict] = []
        self.heartbeats: list[dict] = []
        self.email_calls = 0

    def claim_job(self, lease_seconds: int) -> dict:
        return self.job

    def submit_result(self, job: dict, **payload: object) -> dict:
        self.results.append({"job": job, **payload})
        return {"accepted": True}

    def report_failure(self, job: dict, **payload: object) -> dict:
        self.failures.append({"job": job, **payload})
        return {"accepted": True}

    def renew_lease(self, job: dict, **payload: object) -> dict:
        self.heartbeats.append({"job": job, **payload})
        return {"renewed": True}

    def reconcile_email(self, limit: int) -> dict:
        self.email_calls += 1
        return {
            "accepted": True,
            "candidates": 0,
            "providerAccepted": 0,
            "failed": 0,
            "skipped": 0,
        }


def claimed_job() -> dict:
    return {
        "attempt_count": 1,
        "claimed": True,
        "fulfillment_id": "0ac33044-0ba1-49cb-ad7d-4f5f4fd05c02",
        "reading_id": "936c0fbc-6a0c-4511-ab44-10f9859e6847",
    }


def build_service(client: FakeClient, runtime: FakeRuntime) -> WorkerService:
    return WorkerService(
        client=client,
        email_reconciliation_limit=5,
        email_reconciliation_seconds=60,
        generation_runner=FakeGenerationRunner(runtime),
        health=HealthState(
            runtime_version=runtime.runtime_version,
        ),
        lease_seconds=300,
        poll_seconds=15,
        runtime=runtime,
    )


class ServiceTests(unittest.TestCase):
    def test_active_job_health_uses_lease_heartbeat_not_idle_loop_tick(self) -> None:
        health = HealthState(
            email_loop_stale_seconds=1,
            job_loop_stale_seconds=0.01,
            job_timeout_seconds=1,
            lease_heartbeat_stale_seconds=0.05,
            runtime_version="valley-paid-reading-runtime-v1",
        )
        health.job_started()
        time.sleep(0.02)
        health.lease_heartbeat()
        self.assertTrue(health.snapshot()["ready"])
        time.sleep(0.06)
        self.assertFalse(health.snapshot()["ready"])

    def test_submits_successful_result(self) -> None:
        client = FakeClient(claimed_job())
        service = build_service(client, FakeRuntime())
        self.assertTrue(service.process_one())
        self.assertEqual(len(client.results), 1)
        self.assertEqual(client.failures, [])
        self.assertEqual(
            client.results[0]["runtime_version"],
            "valley-paid-reading-runtime-v1",
        )

    def test_reports_stable_nonretryable_failure(self) -> None:
        client = FakeClient(claimed_job())
        service = build_service(client, FakeRuntime(FakeGenerationError()))
        self.assertTrue(service.process_one())
        self.assertEqual(client.results, [])
        self.assertEqual(
            client.failures[0]["error_code"],
            "UNSUPPORTED_BIRTH_PLACE",
        )
        self.assertFalse(client.failures[0]["retryable"])

    def test_email_reconciliation_is_independently_callable(self) -> None:
        client = FakeClient({"claimed": False})
        service = build_service(client, FakeRuntime())
        service.reconcile_email_once()
        self.assertEqual(client.email_calls, 1)

    def test_email_health_requires_a_recent_success_after_startup_grace(self) -> None:
        health = HealthState(
            email_loop_stale_seconds=1,
            email_success_stale_seconds=0.05,
            email_success_startup_grace_seconds=0.01,
            runtime_version="valley-paid-reading-runtime-v1",
        )
        time.sleep(0.02)
        self.assertFalse(health.snapshot()["ready"])
        health.email_reconciliation_succeeded()
        self.assertTrue(health.snapshot()["ready"])
        health.email_reconciliation_failed("WORKER_API_UNAVAILABLE")
        time.sleep(0.06)
        self.assertFalse(health.snapshot()["ready"])

    def test_renews_lease_when_generation_runner_heartbeats(self) -> None:
        client = FakeClient(claimed_job())
        runtime = FakeRuntime()
        service = WorkerService(
            client=client,
            email_reconciliation_limit=5,
            email_reconciliation_seconds=60,
            generation_runner=FakeGenerationRunner(runtime, heartbeat=True),
            health=HealthState(runtime_version=runtime.runtime_version),
            lease_seconds=300,
            poll_seconds=15,
            runtime=runtime,
        )
        self.assertTrue(service.process_one())
        self.assertEqual(len(client.heartbeats), 1)
        self.assertEqual(client.heartbeats[0]["lease_seconds"], 300)


if __name__ == "__main__":
    unittest.main()
