from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from reading_worker.config import ConfigurationError, WorkerConfig


BASE_ENV = {
    "VALLEY_APP_API_BASE_URL": "https://app.valeoflight.com",
    "VALLEY_AGPL_SOURCE_SHA256": "a" * 64,
    "VALLEY_AGPL_SOURCE_URL": "https://github.com/example/valley/releases/tag/v1",
    "VALLEY_ASTROLOGY_LICENSE_DECISION": "agpl-3.0",
    "VALLEY_WORKER_SIGNING_SECRET": "s" * 32,
}


class ConfigTests(unittest.TestCase):
    def test_accepts_minimal_production_configuration(self) -> None:
        with patch.dict(os.environ, BASE_ENV, clear=True):
            config = WorkerConfig.from_environment()
        self.assertEqual(config.app_base_url, "https://app.valeoflight.com")
        self.assertEqual(config.email_reconciliation_seconds, 60)
        self.assertEqual(config.job_timeout_seconds, 900)
        self.assertEqual(config.lease_heartbeat_seconds, 60)
        self.assertEqual(config.lease_seconds, 300)
        self.assertEqual(config.source_code_sha256, "a" * 64)
        self.assertEqual(
            config.source_code_url,
            "https://github.com/example/valley/releases/tag/v1",
        )

    def test_license_decision_is_required(self) -> None:
        environment = dict(BASE_ENV)
        environment.pop("VALLEY_ASTROLOGY_LICENSE_DECISION")
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(
                ConfigurationError,
                "VALLEY_ASTROLOGY_LICENSE_DECISION",
            ):
                WorkerConfig.from_environment()

    def test_public_source_release_is_required(self) -> None:
        for key in ("VALLEY_AGPL_SOURCE_URL", "VALLEY_AGPL_SOURCE_SHA256"):
            with self.subTest(key=key):
                environment = dict(BASE_ENV)
                environment.pop(key)
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(ConfigurationError, key):
                        WorkerConfig.from_environment()

    def test_source_release_must_use_safe_https_metadata(self) -> None:
        invalid_values = {
            "VALLEY_AGPL_SOURCE_URL": "http://example.com/source.zip",
            "VALLEY_AGPL_SOURCE_SHA256": "not-a-sha256",
        }
        for key, value in invalid_values.items():
            with self.subTest(key=key):
                environment = {**BASE_ENV, key: value}
                with patch.dict(os.environ, environment, clear=True):
                    with self.assertRaisesRegex(ConfigurationError, key):
                        WorkerConfig.from_environment()

    def test_app_origin_must_be_https(self) -> None:
        environment = {
            **BASE_ENV,
            "VALLEY_APP_API_BASE_URL": "http://app.valeoflight.com",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "HTTPS origin"):
                WorkerConfig.from_environment()

    def test_heartbeat_must_leave_lease_safety_margin(self) -> None:
        environment = {
            **BASE_ENV,
            "VALLEY_WORKER_LEASE_HEARTBEAT_SECONDS": "150",
            "VALLEY_WORKER_LEASE_SECONDS": "300",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "less than half"):
                WorkerConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
