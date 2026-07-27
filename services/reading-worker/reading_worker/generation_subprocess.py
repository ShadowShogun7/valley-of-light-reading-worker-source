"""Private child-process entrypoint for one bounded reading generation."""

from __future__ import annotations

import json
import sys
from typing import Any

from .config import WorkerConfig
from .runtime import ReadingRuntime


MAX_JOB_BYTES = 2 * 1024 * 1024


def main() -> int:
    try:
        raw_job = sys.stdin.buffer.read(MAX_JOB_BYTES + 1)
        if len(raw_job) > MAX_JOB_BYTES:
            raise ChildGenerationError("GENERATION_JOB_TOO_LARGE", retryable=False)
        job = json.loads(raw_job.decode("utf-8"))
        if not isinstance(job, dict):
            raise ChildGenerationError("GENERATION_JOB_INVALID", retryable=False)

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
        result = runtime.generate(job)
        _write({"ok": True, "result": result})
        return 0
    except Exception as error:
        code = getattr(error, "code", None)
        retryable = getattr(error, "retryable", True)
        if not isinstance(code, str) or not code:
            code = "RUNTIME_GENERATION_FAILED"
        _write(
            {
                "errorCode": code,
                "ok": False,
                "retryable": bool(retryable),
            }
        )
        return 0


class ChildGenerationError(RuntimeError):
    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


def _write(payload: dict[str, Any]) -> None:
    sys.stdout.buffer.write(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(main())
