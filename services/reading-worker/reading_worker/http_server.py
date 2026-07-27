"""Minimal authenticated HTTP surface for health checks and wake hints."""

from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from . import JOB_VERSION
from .client import verify_body_signature
from .service import HealthState


MAX_WAKE_BODY_BYTES = 16 * 1024


class WorkerHttpServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        health: HealthState,
        signing_secret: str,
        source_code_sha256: str,
        source_code_url: str,
        wake: Callable[[], None],
    ):
        self.health = health
        self.signing_secret = signing_secret
        self.source_code_sha256 = source_code_sha256
        self.source_code_url = source_code_url
        self.wake_worker = wake
        super().__init__(server_address, WorkerRequestHandler)


class WorkerRequestHandler(BaseHTTPRequestHandler):
    server: WorkerHttpServer
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def do_GET(self) -> None:
        if self.path == "/source":
            self._json(
                200,
                {
                    "license": "AGPL-3.0-or-later",
                    "sourceCodeSha256": self.server.source_code_sha256,
                    "sourceCodeUrl": self.server.source_code_url,
                },
            )
            return
        if self.path != "/healthz":
            self._json(404, {"error": "NOT_FOUND"})
            return
        health = self.server.health.snapshot()
        self._json(200 if health.get("ready") is True else 503, health)

    def do_POST(self) -> None:
        if self.path != "/wake":
            self._json(404, {"error": "NOT_FOUND"})
            return
        raw_length = self.headers.get("Content-Length")
        if raw_length is None or not raw_length.isdigit():
            self._json(411, {"error": "CONTENT_LENGTH_REQUIRED"})
            return
        length = int(raw_length)
        if length <= 0 or length > MAX_WAKE_BODY_BYTES:
            self._json(413, {"error": "REQUEST_BODY_TOO_LARGE"})
            return
        raw_body = self.rfile.read(length)
        if not verify_body_signature(
            raw_body,
            self.headers.get("X-Valley-Worker-Timestamp"),
            self.headers.get("X-Valley-Worker-Signature"),
            self.server.signing_secret,
        ):
            self._json(401, {"error": "INVALID_WORKER_SIGNATURE"})
            return
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "INVALID_WAKE_HINT"})
            return
        if not _valid_wake_hint(payload):
            self._json(400, {"error": "INVALID_WAKE_HINT"})
            return
        self.server.wake_worker()
        self._json(202, {"accepted": True})

    def log_message(self, format: str, *args: Any) -> None:
        # Do not copy paths, tokens, or request bodies into default access logs.
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header(
            "Link",
            f'<{self.server.source_code_url}>; rel="source"',
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header(
            "X-Valley-Source-Sha256",
            self.server.source_code_sha256,
        )
        self.end_headers()
        self.wfile.write(encoded)


def _valid_wake_hint(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != {
        "fulfillmentId",
        "readingId",
        "version",
    }:
        return False
    if payload.get("version") != JOB_VERSION:
        return False
    try:
        uuid.UUID(str(payload.get("fulfillmentId")))
        uuid.UUID(str(payload.get("readingId")))
    except (ValueError, TypeError, AttributeError):
        return False
    return True
