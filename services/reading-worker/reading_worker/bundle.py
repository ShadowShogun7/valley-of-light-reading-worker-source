"""Create and verify the immutable production KB/runtime bundle manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import (
    BUNDLE_SCHEMA_VERSION,
    INTAKE_VERSION,
    JOB_VERSION,
    RESULT_CONTRACT_VERSION,
    RUNTIME_VERSION,
)


BUNDLE_MANIFEST_NAME = "worker-runtime-manifest.json"
KB_MANIFEST_NAME = "manifest.json"
REQUIRED_RUNTIME_FILES: dict[str, tuple[str | None, str]] = {
    "kb_articles.json": (None, "article_count"),
    "kb_claims.json": (None, "claim_count"),
    "kb_atoms.json": ("atoms", "atom_count"),
    "kb_rules.json": ("rules", "rule_count"),
    "kb_question_blueprints.json": ("blueprints", "question_blueprint_count"),
    "kb_guardrails.json": ("guardrails", "guardrail_count"),
}


class BundleValidationError(RuntimeError):
    """Raised when a runtime artifact is absent, stale, or not production safe."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_bundle(
    kb_dir: Path,
    *,
    intake_version: str = INTAKE_VERSION,
    job_version: str = JOB_VERSION,
    result_contract_version: str = RESULT_CONTRACT_VERSION,
    runtime_version: str = RUNTIME_VERSION,
) -> dict[str, Any]:
    """Record exact checksums after a published-only compile."""

    kb_dir = kb_dir.resolve()
    counts = _validate_kb_files(kb_dir)
    kb_manifest_path = kb_dir / KB_MANIFEST_NAME
    kb_manifest = _read_object(kb_manifest_path)
    if kb_manifest.get("published_only") is not True:
        raise BundleValidationError(
            "KB manifest is not a published-only production compile"
        )
    _validate_manifest_counts(kb_manifest, counts)

    runtime_files = {
        name: sha256_file(kb_dir / name)
        for name in sorted(REQUIRED_RUNTIME_FILES)
    }
    bundle = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intake_version": intake_version,
        "job_version": job_version,
        "result_contract_version": result_contract_version,
        "runtime_version": runtime_version,
        "published_only": True,
        "counts": counts,
        "kb_manifest_sha256": sha256_file(kb_manifest_path),
        "runtime_file_sha256": runtime_files,
    }
    output_path = kb_dir / BUNDLE_MANIFEST_NAME
    output_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return bundle


def validate_bundle(
    kb_dir: Path,
    *,
    expected_intake_version: str = INTAKE_VERSION,
    expected_job_version: str = JOB_VERSION,
    expected_result_contract_version: str = RESULT_CONTRACT_VERSION,
    expected_runtime_version: str = RUNTIME_VERSION,
) -> dict[str, Any]:
    """Fail closed unless every runtime artifact matches its recorded digest."""

    kb_dir = kb_dir.resolve()
    bundle = _read_object(kb_dir / BUNDLE_MANIFEST_NAME)
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise BundleValidationError("Unsupported worker runtime bundle schema")
    if bundle.get("published_only") is not True:
        raise BundleValidationError("Worker runtime bundle is not published-only")
    expected_versions = {
        "intake_version": expected_intake_version,
        "job_version": expected_job_version,
        "result_contract_version": expected_result_contract_version,
        "runtime_version": expected_runtime_version,
    }
    for key, expected in expected_versions.items():
        if bundle.get(key) != expected:
            raise BundleValidationError(
                f"Worker bundle {key} mismatch: expected {expected!r}"
            )

    counts = _validate_kb_files(kb_dir)
    if bundle.get("counts") != counts:
        raise BundleValidationError("Worker bundle counts do not match runtime files")

    kb_manifest_path = kb_dir / KB_MANIFEST_NAME
    kb_manifest = _read_object(kb_manifest_path)
    if kb_manifest.get("published_only") is not True:
        raise BundleValidationError("KB manifest is not published-only")
    _validate_manifest_counts(kb_manifest, counts)
    if bundle.get("kb_manifest_sha256") != sha256_file(kb_manifest_path):
        raise BundleValidationError("KB manifest checksum mismatch")

    recorded_hashes = bundle.get("runtime_file_sha256")
    if not isinstance(recorded_hashes, dict):
        raise BundleValidationError("Worker bundle has no runtime file checksums")
    if set(recorded_hashes) != set(REQUIRED_RUNTIME_FILES):
        raise BundleValidationError("Worker bundle runtime checksum set is incomplete")
    for name in REQUIRED_RUNTIME_FILES:
        recorded = recorded_hashes.get(name)
        if not isinstance(recorded, str) or len(recorded) != 64:
            raise BundleValidationError(f"Invalid recorded checksum for {name}")
        if recorded != sha256_file(kb_dir / name):
            raise BundleValidationError(f"Runtime checksum mismatch for {name}")
    return bundle


def source_fingerprints(bundle: dict[str, Any]) -> dict[str, Any]:
    """Return the auditable, customer-safe source fingerprint payload."""

    return {
        "bundleSchemaVersion": bundle["schema_version"],
        "jobVersion": bundle["job_version"],
        "intakeVersion": bundle["intake_version"],
        "kbManifestSha256": bundle["kb_manifest_sha256"],
        "publishedOnly": bundle["published_only"],
        "resultContractVersion": bundle["result_contract_version"],
        "runtimeFileSha256": dict(bundle["runtime_file_sha256"]),
        "runtimeVersion": bundle["runtime_version"],
    }


def _validate_kb_files(kb_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, (record_key, count_key) in REQUIRED_RUNTIME_FILES.items():
        path = kb_dir / name
        payload = _read_json(path)
        records = payload.get(record_key) if record_key and isinstance(payload, dict) else payload
        if not isinstance(records, list) or not records:
            raise BundleValidationError(f"{name} must contain a non-empty record list")
        if not all(isinstance(item, dict) for item in records):
            raise BundleValidationError(f"{name} contains a non-object record")
        counts[count_key] = len(records)
    return counts


def _validate_manifest_counts(
    manifest: dict[str, Any],
    actual_counts: dict[str, int],
) -> None:
    for key, actual in actual_counts.items():
        recorded = manifest.get(key)
        if not isinstance(recorded, int) or recorded <= 0:
            raise BundleValidationError(f"KB manifest {key} must be nonzero")
        if recorded != actual:
            raise BundleValidationError(
                f"KB manifest {key} mismatch: recorded {recorded}, actual {actual}"
            )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BundleValidationError(f"Missing runtime artifact: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise BundleValidationError(f"Invalid JSON runtime artifact: {path.name}") from exc


def _read_object(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise BundleValidationError(f"{path.name} must be a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record or validate the paid-reading runtime bundle"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("record", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--kb-dir", required=True, type=Path)
        subparser.add_argument("--job-version", default=JOB_VERSION)
        subparser.add_argument("--intake-version", default=INTAKE_VERSION)
        subparser.add_argument(
            "--result-contract-version", default=RESULT_CONTRACT_VERSION
        )
        subparser.add_argument("--runtime-version", default=RUNTIME_VERSION)
    args = parser.parse_args()

    kwargs = {
        (
            "intake_version"
            if args.command == "record"
            else "expected_intake_version"
        ): args.intake_version,
        "job_version" if args.command == "record" else "expected_job_version": args.job_version,
        (
            "result_contract_version"
            if args.command == "record"
            else "expected_result_contract_version"
        ): args.result_contract_version,
        (
            "runtime_version"
            if args.command == "record"
            else "expected_runtime_version"
        ): args.runtime_version,
    }
    if args.command == "record":
        result = record_bundle(args.kb_dir, **kwargs)
    else:
        result = validate_bundle(args.kb_dir, **kwargs)
    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": result["schema_version"],
                "runtime_version": result["runtime_version"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
