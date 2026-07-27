from __future__ import annotations

import sys
import time
import unittest

from reading_worker.generation import (
    GenerationProcessError,
    SubprocessGenerationRunner,
)


class GenerationRunnerTests(unittest.TestCase):
    def test_returns_valid_child_result(self) -> None:
        runner = SubprocessGenerationRunner(
            command=(
                sys.executable,
                "-c",
                (
                    "import json,sys;"
                    "job=json.load(sys.stdin);"
                    "json.dump({'ok':True,'result':{'reading':job['id']}},sys.stdout)"
                ),
            ),
            heartbeat_seconds=0.1,
            max_output_bytes=4096,
            timeout_seconds=2,
        )
        result = runner.run({"id": "r-1"}, heartbeat=lambda: None)
        self.assertEqual(result, {"reading": "r-1"})

    def test_timeout_heartbeats_then_kills_child(self) -> None:
        heartbeats = 0

        def heartbeat() -> None:
            nonlocal heartbeats
            heartbeats += 1

        runner = SubprocessGenerationRunner(
            command=(sys.executable, "-c", "import time; time.sleep(10)"),
            heartbeat_seconds=0.03,
            max_output_bytes=4096,
            timeout_seconds=0.12,
        )
        started = time.monotonic()
        with self.assertRaises(GenerationProcessError) as context:
            runner.run({"id": "r-1"}, heartbeat=heartbeat)
        self.assertEqual(context.exception.code, "GENERATION_TIMEOUT")
        self.assertTrue(context.exception.retryable)
        self.assertGreaterEqual(heartbeats, 2)
        self.assertLess(time.monotonic() - started, 2)

    def test_heartbeat_failure_kills_child_and_fails_closed(self) -> None:
        runner = SubprocessGenerationRunner(
            command=(sys.executable, "-c", "import time; time.sleep(10)"),
            heartbeat_seconds=0.03,
            max_output_bytes=4096,
            timeout_seconds=2,
        )
        started = time.monotonic()

        def heartbeat() -> None:
            raise RuntimeError("lease unavailable")

        with self.assertRaises(GenerationProcessError) as context:
            runner.run({"id": "r-1"}, heartbeat=heartbeat)
        self.assertEqual(
            context.exception.code,
            "WORKER_LEASE_HEARTBEAT_FAILED",
        )
        self.assertTrue(context.exception.retryable)
        self.assertLess(time.monotonic() - started, 2)

    def test_preserves_child_retryability(self) -> None:
        runner = SubprocessGenerationRunner(
            command=(
                sys.executable,
                "-c",
                (
                    "import json,sys;"
                    "json.load(sys.stdin);"
                    "json.dump({'ok':False,'errorCode':'UNSUPPORTED_BIRTH_PLACE',"
                    "'retryable':False},sys.stdout)"
                ),
            ),
            heartbeat_seconds=0.1,
            max_output_bytes=4096,
            timeout_seconds=2,
        )
        with self.assertRaises(GenerationProcessError) as context:
            runner.run({"id": "r-1"}, heartbeat=lambda: None)
        self.assertEqual(context.exception.code, "UNSUPPORTED_BIRTH_PLACE")
        self.assertFalse(context.exception.retryable)


if __name__ == "__main__":
    unittest.main()
