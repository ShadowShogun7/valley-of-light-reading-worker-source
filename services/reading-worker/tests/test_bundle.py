from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reading_worker.bundle import (
    BUNDLE_MANIFEST_NAME,
    BundleValidationError,
    REQUIRED_RUNTIME_FILES,
    record_bundle,
    validate_bundle,
)


class BundleTests(unittest.TestCase):
    def test_record_and_validate_then_reject_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            kb_dir = Path(raw_directory)
            counts: dict[str, int] = {}
            for name, (record_key, count_key) in REQUIRED_RUNTIME_FILES.items():
                record = {"id": f"{name}-record"}
                payload = [record] if record_key is None else {record_key: [record]}
                (kb_dir / name).write_text(
                    json.dumps(payload),
                    encoding="utf-8",
                )
                counts[count_key] = 1
            (kb_dir / "manifest.json").write_text(
                json.dumps({"published_only": True, **counts}),
                encoding="utf-8",
            )

            recorded = record_bundle(kb_dir)
            validated = validate_bundle(kb_dir)
            self.assertEqual(validated["runtime_file_sha256"], recorded["runtime_file_sha256"])
            self.assertTrue((kb_dir / BUNDLE_MANIFEST_NAME).is_file())

            (kb_dir / "kb_claims.json").write_text(
                json.dumps([{"id": "tampered"}]),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BundleValidationError, "checksum mismatch"):
                validate_bundle(kb_dir)

    def test_rejects_non_published_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            kb_dir = Path(raw_directory)
            counts: dict[str, int] = {}
            for name, (record_key, count_key) in REQUIRED_RUNTIME_FILES.items():
                payload = [{}] if record_key is None else {record_key: [{}]}
                (kb_dir / name).write_text(json.dumps(payload), encoding="utf-8")
                counts[count_key] = 1
            (kb_dir / "manifest.json").write_text(
                json.dumps({"published_only": False, **counts}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BundleValidationError, "published-only"):
                record_bundle(kb_dir)


if __name__ == "__main__":
    unittest.main()
