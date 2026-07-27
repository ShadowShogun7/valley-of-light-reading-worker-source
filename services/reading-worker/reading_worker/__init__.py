"""Production worker for paid Valley of Light relationship readings."""

from __future__ import annotations


JOB_VERSION = "paid-reading-job-v1"
RESULT_CONTRACT_VERSION = "complete-relationship-result-v1"
RUNTIME_VERSION = "valley-paid-reading-runtime-v1"
BUNDLE_SCHEMA_VERSION = "valley-reading-runtime-bundle-v1"
INTAKE_VERSION = "relationship-intake-v1"

__all__ = [
    "BUNDLE_SCHEMA_VERSION",
    "INTAKE_VERSION",
    "JOB_VERSION",
    "RESULT_CONTRACT_VERSION",
    "RUNTIME_VERSION",
]
