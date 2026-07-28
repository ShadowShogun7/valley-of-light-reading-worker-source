from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "build_agpl_source_release.py"
)
SPEC = importlib.util.spec_from_file_location("build_agpl_source_release", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
source_release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source_release)


class SourceReleaseTests(unittest.TestCase):
    def test_rejects_draft_inclusive_kb_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            kb_dir = root / "dist" / "kb"
            kb_dir.mkdir(parents=True)
            for name in source_release.REQUIRED_RELEASE_KB_FILES:
                payload = {"published_only": False} if name == "manifest.json" else []
                (kb_dir / name).write_text(json.dumps(payload), encoding="utf-8")

            with mock.patch.object(source_release, "ROOT", root):
                with self.assertRaisesRegex(
                    source_release.SourceReleaseError,
                    "compile_kb.py",
                ):
                    source_release.validate_release_kb()

    def test_accepts_complete_published_only_kb(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            root = Path(raw_directory)
            kb_dir = root / "dist" / "kb"
            kb_dir.mkdir(parents=True)
            for name in source_release.REQUIRED_RELEASE_KB_FILES:
                payload = {"published_only": True} if name == "manifest.json" else []
                (kb_dir / name).write_text(json.dumps(payload), encoding="utf-8")

            with mock.patch.object(source_release, "ROOT", root):
                source_release.validate_release_kb()


if __name__ == "__main__":
    unittest.main()
