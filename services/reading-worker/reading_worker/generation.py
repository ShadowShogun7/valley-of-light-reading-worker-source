"""Killable subprocess boundary for one paid-reading generation."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable


class GenerationProcessError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class SubprocessGenerationRunner:
    heartbeat_seconds: float
    max_output_bytes: int
    timeout_seconds: float
    command: tuple[str, ...] | None = None

    def run(
        self,
        job: dict[str, Any],
        *,
        heartbeat: Callable[[], None],
    ) -> dict[str, Any]:
        raw_input = json.dumps(
            job,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        process = subprocess.Popen(
            list(
                self.command
                or (
                    sys.executable,
                    "-m",
                    "reading_worker.generation_subprocess",
                )
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        started_at = time.monotonic()
        first_communicate = True
        try:
            while True:
                remaining = self.timeout_seconds - (time.monotonic() - started_at)
                if remaining <= 0:
                    _terminate_and_reap(process)
                    raise GenerationProcessError(
                        "GENERATION_TIMEOUT",
                        retryable=True,
                    )
                try:
                    stdout, stderr = process.communicate(
                        input=raw_input if first_communicate else None,
                        timeout=min(self.heartbeat_seconds, remaining),
                    )
                    break
                except subprocess.TimeoutExpired:
                    first_communicate = False
                    try:
                        heartbeat()
                    except Exception as exc:
                        _terminate_and_reap(process)
                        raise GenerationProcessError(
                            "WORKER_LEASE_HEARTBEAT_FAILED",
                            retryable=True,
                        ) from exc
        except BaseException:
            if process.poll() is None:
                _terminate_and_reap(process)
            raise

        if len(stdout) > self.max_output_bytes or len(stderr) > 64 * 1024:
            raise GenerationProcessError(
                "GENERATION_PROCESS_OUTPUT_TOO_LARGE",
                retryable=False,
            )
        if process.returncode != 0:
            raise GenerationProcessError(
                "GENERATION_PROCESS_FAILED",
                retryable=True,
            )
        try:
            envelope = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GenerationProcessError(
                "GENERATION_PROCESS_INVALID_RESPONSE",
                retryable=True,
            ) from exc
        if not isinstance(envelope, dict):
            raise GenerationProcessError(
                "GENERATION_PROCESS_INVALID_RESPONSE",
                retryable=True,
            )
        if envelope.get("ok") is False:
            code = envelope.get("errorCode")
            retryable = envelope.get("retryable")
            if (
                not isinstance(code, str)
                or not code
                or not isinstance(retryable, bool)
            ):
                raise GenerationProcessError(
                    "GENERATION_PROCESS_INVALID_RESPONSE",
                    retryable=True,
                )
            raise GenerationProcessError(code, retryable=retryable)
        result = envelope.get("result")
        if envelope.get("ok") is not True or not isinstance(result, dict):
            raise GenerationProcessError(
                "GENERATION_PROCESS_INVALID_RESPONSE",
                retryable=True,
            )
        return result


def _terminate_and_reap(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
