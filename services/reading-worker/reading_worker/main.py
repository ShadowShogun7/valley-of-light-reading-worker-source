"""Process entrypoint for the paid-reading worker."""

from __future__ import annotations

import logging
import signal
import threading

from .client import SignedWorkerApiClient
from .config import WorkerConfig
from .generation import SubprocessGenerationRunner
from .http_server import WorkerHttpServer
from .runtime import ReadingRuntime
from .service import HealthState, WorkerService, log_event


def main() -> int:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=logging.INFO,
    )
    config = WorkerConfig.from_environment()
    runtime = ReadingRuntime(
        expected_intake_version=config.expected_intake_version,
        expected_job_version=config.expected_job_version,
        expected_result_contract_version=config.expected_result_contract_version,
        expected_runtime_version=config.expected_runtime_version,
        kb_dir=config.kb_dir,
        max_result_bytes=config.max_result_bytes,
        repo_root=config.repo_root,
    )
    client = SignedWorkerApiClient(
        app_base_url=config.app_base_url,
        signing_secret=config.signing_secret,
        timeout_seconds=config.http_timeout_seconds,
        worker_id=config.worker_id,
    )
    health = HealthState(
        email_loop_stale_seconds=(
            config.email_reconciliation_seconds * 2 + 30
        ),
        email_success_stale_seconds=(
            config.email_reconciliation_seconds * 2 + 30
        ),
        email_success_startup_grace_seconds=(
            config.email_reconciliation_seconds * 2 + 30
        ),
        job_loop_stale_seconds=config.poll_seconds * 2 + 30,
        job_timeout_seconds=config.job_timeout_seconds + 10,
        lease_heartbeat_stale_seconds=(
            config.lease_heartbeat_seconds * 2 + 10
        ),
        runtime_version=runtime.runtime_version,
    )
    generation_runner = SubprocessGenerationRunner(
        heartbeat_seconds=config.lease_heartbeat_seconds,
        max_output_bytes=config.max_result_bytes + 256 * 1024,
        timeout_seconds=config.job_timeout_seconds,
    )
    service = WorkerService(
        client=client,
        email_reconciliation_limit=config.email_reconciliation_limit,
        email_reconciliation_seconds=config.email_reconciliation_seconds,
        generation_runner=generation_runner,
        health=health,
        lease_seconds=config.lease_seconds,
        poll_seconds=config.poll_seconds,
        runtime=runtime,
    )
    server = WorkerHttpServer(
        ("0.0.0.0", config.port),
        health=health,
        signing_secret=config.signing_secret,
        source_code_sha256=config.source_code_sha256,
        source_code_url=config.source_code_url,
        wake=service.wake,
    )

    shutdown_started = threading.Event()

    def shutdown(_signum: int, _frame: object) -> None:
        if shutdown_started.is_set():
            return
        shutdown_started.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    service.start()
    log_event(
        "WORKER_READY",
        port=config.port,
        runtimeVersion=runtime.runtime_version,
        workerId=config.worker_id,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        service.stop()
        server.server_close()
        health.update(ready=False)
        log_event("WORKER_STOPPED", workerId=config.worker_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
