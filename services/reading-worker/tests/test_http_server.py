from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from reading_worker.client import sign_body
from reading_worker.http_server import WorkerHttpServer
from reading_worker.service import HealthState


class HttpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = "worker-secret-with-more-than-thirty-two-bytes"
        self.woken = threading.Event()
        self.server = WorkerHttpServer(
            ("127.0.0.1", 0),
            health=HealthState(
                runtime_version="valley-paid-reading-runtime-v1",
            ),
            signing_secret=self.secret,
            source_code_sha256="a" * 64,
            source_code_url="https://github.com/example/valley/releases/tag/v1",
            wake=self.woken.set,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def test_health_and_authenticated_wake(self) -> None:
        with urllib.request.urlopen(f"{self.base_url}/healthz", timeout=2) as response:
            health = json.loads(response.read())
        self.assertTrue(health["ready"])
        self.assertFalse(health["activeJob"])

        with urllib.request.urlopen(f"{self.base_url}/source", timeout=2) as response:
            source = json.loads(response.read())
            self.assertEqual(
                response.headers["Link"],
                '<https://github.com/example/valley/releases/tag/v1>; rel="source"',
            )
            self.assertEqual(response.headers["X-Valley-Source-Sha256"], "a" * 64)
        self.assertEqual(source["license"], "AGPL-3.0-or-later")
        self.assertEqual(source["sourceCodeSha256"], "a" * 64)
        self.assertEqual(
            source["sourceCodeUrl"],
            "https://github.com/example/valley/releases/tag/v1",
        )

        raw_body = json.dumps(
            {
                "fulfillmentId": "0ac33044-0ba1-49cb-ad7d-4f5f4fd05c02",
                "readingId": "936c0fbc-6a0c-4511-ab44-10f9859e6847",
                "version": "paid-reading-job-v1",
            },
            separators=(",", ":"),
        ).encode()
        timestamp = str(int(time.time()))
        request = urllib.request.Request(
            f"{self.base_url}/wake",
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Valley-Worker-Signature": sign_body(
                    raw_body,
                    timestamp,
                    self.secret,
                ),
                "X-Valley-Worker-Timestamp": timestamp,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=2) as response:
            payload = json.loads(response.read())
            self.assertEqual(response.status, 202)
        self.assertEqual(payload, {"accepted": True})
        self.assertTrue(self.woken.wait(timeout=1))

    def test_wake_rejects_invalid_signature(self) -> None:
        raw_body = b'{"fulfillmentId":"0ac33044-0ba1-49cb-ad7d-4f5f4fd05c02","readingId":"936c0fbc-6a0c-4511-ab44-10f9859e6847","version":"paid-reading-job-v1"}'
        request = urllib.request.Request(
            f"{self.base_url}/wake",
            data=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Valley-Worker-Signature": "x" * 43,
                "X-Valley-Worker-Timestamp": str(int(time.time())),
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(context.exception.code, 401)
        self.assertFalse(self.woken.is_set())

    def test_health_returns_503_when_worker_is_not_ready(self) -> None:
        self.server.health.update(ready=False)
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(f"{self.base_url}/healthz", timeout=2)
        self.assertEqual(context.exception.code, 503)
        health = json.loads(context.exception.read())
        self.assertFalse(health["ready"])


if __name__ == "__main__":
    unittest.main()
