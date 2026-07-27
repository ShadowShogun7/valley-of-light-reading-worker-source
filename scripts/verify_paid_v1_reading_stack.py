#!/usr/bin/env python3
"""Run the paid V1 Western reading backend verification stack."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from kb_utils import ROOT


WEB_DIR = ROOT / "apps" / "web"
WEB_SMOKE_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    command: tuple[str, ...]
    cwd: Path = ROOT
    report_path: Path | None = None


def python_script(name: str, *args: str) -> tuple[str, ...]:
    return (sys.executable, str(ROOT / "scripts" / name), *args)


BACKEND_STEPS: tuple[Step, ...] = (
    Step("kb_validate", "KB source validation", python_script("validate.py")),
    Step("kb_compile", "Compile KB runtime artifacts", python_script("compile_kb.py", "--skip-validate")),
    Step("kb_lint", "KB lint health check", python_script("lint_kb.py")),
    Step("book_coverage_validate", "Book coverage validation", python_script("validate_book_coverage.py")),
    Step("book_digests_validate", "Book digest validation", python_script("validate_book_digests.py")),
    Step(
        "book_digestion_matrix_validate",
        "Book digestion matrix staleness",
        python_script("validate_book_digestion_execution_matrix.py"),
    ),
    Step("method_claim_validate", "Method claim runtime usage validation", python_script("validate_method_claim_runtime_usage.py")),
    Step("structured_runtime", "Structured runtime contract", python_script("structured_runtime_contract.py")),
    Step("runtime_method", "Western runtime method trace contract", python_script("validate_western_runtime_method_contract.py")),
    Step("paid_v1_contract", "Paid V1 result section contract", python_script("validate_paid_v1_result_section_contract.py")),
    Step("answer_rule_matrix", "Western answer rule matrix", python_script("smoke_western_answer_rule_matrix.py")),
    Step("answer_layer", "Western answer layer matrix", python_script("smoke_western_answer_layer.py")),
    Step(
        "relationship_status_answer_policy",
        "Relationship status answer policy matrix",
        python_script("smoke_relationship_status_answer_policy.py"),
    ),
    Step(
        "relationship_input_contract",
        "Relationship intake/API status contract",
        python_script("smoke_relationship_input_contract.py"),
    ),
    Step(
        "section_narrative_spec",
        "Section narrative ownership contract",
        python_script("smoke_section_narrative_spec.py"),
    ),
    Step(
        "final_narrative_fact_contract",
        "Final narrative typed fact boundary",
        python_script("smoke_final_narrative_fact_contract.py"),
    ),
    Step(
        "final_narrative_phase2_fact_only",
        "Final narrative Phase 2 fact-only isolation",
        python_script("verify_final_narrative_phase2_fact_only.py"),
    ),
    Step(
        "final_narrative_phase2_page_modules",
        "Final narrative Phase 2 independent page modules",
        python_script("verify_final_narrative_phase2_page_modules.py"),
    ),
    Step(
        "final_narrative_phase3_realization",
        "Final narrative Phase 3 controlled realization",
        python_script("verify_final_narrative_phase3_realization.py"),
    ),
    Step(
        "final_narrative_native_zh_tw_foundation",
        "Final narrative native Traditional Chinese R0/R1 foundation",
        python_script("verify_final_narrative_native_zh_tw_foundation.py"),
    ),
    Step(
        "final_narrative_chart_positioning_native_zh_tw",
        "Final narrative R2 native chart-positioning renderer",
        python_script("verify_final_narrative_chart_positioning_native_zh_tw.py"),
    ),
    Step(
        "final_narrative_relationship_fit_native_zh_tw",
        "Final narrative R3 native relationship-fit renderer",
        python_script("verify_final_narrative_relationship_fit_native_zh_tw.py"),
    ),
    Step(
        "final_narrative_r5_page_realizers",
        "Final narrative R5 unified native page realizers",
        python_script("verify_final_narrative_r5_page_realizers.py"),
    ),
    Step(
        "final_narrative_paragraph_plans",
        "Final narrative page-level paragraph plans",
        python_script("verify_final_narrative_paragraph_plans.py"),
    ),
    Step(
        "final_narrative_story_arc",
        "Final narrative five-page story progression",
        python_script("verify_final_narrative_story_arc.py"),
    ),
    Step(
        "final_narrative_phase4_semantic_coverage",
        "Final narrative Phase 4 semantic coverage",
        python_script("verify_final_narrative_phase4_semantic_coverage.py"),
    ),
    Step(
        "final_narrative_phase5_composition",
        "Final narrative Phase 5 composition constraints",
        python_script("verify_final_narrative_phase5_composition.py"),
    ),
    Step(
        "final_narrative_r6_chinese_quality",
        "Final narrative R6 hard Traditional Chinese quality gates",
        python_script("verify_final_narrative_r6_chinese_quality.py"),
    ),
    Step(
        "final_narrative_phase6_test_engine",
        "Final narrative Phase 6 semantic test engine",
        python_script("verify_final_narrative_phase6_test_engine.py"),
    ),
    Step(
        "reading_phase7_calibration",
        "Final narrative Phase 7 split calibration corpus",
        python_script("verify_reading_phase7_calibration.py", "--no-write"),
    ),
    Step(
        "section_narrative_phase2",
        "Section narrative Phase 2 spec-consumer boundary",
        python_script("smoke_section_narrative_phase2.py"),
    ),
    Step(
        "section_narrative_phase3",
        "Section narrative Phase 3 evidence-to-language depth",
        python_script("smoke_section_narrative_phase3.py"),
    ),
    Step(
        "reading_phase4_provenance",
        "Phase 4 case-model provenance and pair grammar",
        python_script("smoke_reading_phase4_provenance.py"),
    ),
    Step(
        "reading_phase5_calibration",
        "Phase 5 structural calibration holdout",
        python_script("test_reading_phase5_calibration.py", "--no-write"),
    ),
    Step(
        "final_narrative_production_readiness",
        "Final narrative Phase 2-4 automated copy gate",
        python_script(
            "audit_final_narrative_production_readiness.py",
            "--corpus",
            str(ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"),
            "--contract",
            str(ROOT / "data" / "reading-quality-cases" / "final-layer-production-contract-v3.json"),
            "--no-write",
        ),
    ),
    Step(
        "reading_phase5_human_feedback",
        "Phase 5 human-feedback copy regressions",
        python_script("smoke_phase5_human_feedback_regressions.py"),
    ),
    Step(
        "reading_production_baseline",
        "Phase 0 production reading baseline",
        python_script("smoke_reading_production_baseline.py"),
    ),
    Step(
        "reading_production_phase2_baseline",
        "Phase 2 production reading baseline",
        python_script(
            "smoke_reading_production_baseline.py",
            "--output-dir",
            str(ROOT / "data" / "reading-production-baseline" / "v2"),
            "--expected-version",
            "relationship-reading-baseline-v2",
            "--renderer-consumes-specs",
            "true",
        ),
    ),
    Step(
        "reading_phase2_diversity",
        "Phase 2 production diversity comparison",
        python_script("smoke_reading_phase2_diversity.py"),
    ),
    Step(
        "reading_production_phase3_baseline",
        "Phase 3 production reading baseline",
        python_script(
            "smoke_reading_production_baseline.py",
            "--output-dir",
            str(ROOT / "data" / "reading-production-baseline" / "v3"),
            "--expected-version",
            "relationship-reading-baseline-v3",
            "--renderer-consumes-specs",
            "true",
        ),
    ),
    Step(
        "reading_phase3_depth",
        "Phase 3 evidence-to-language depth comparison",
        python_script("smoke_reading_phase3_depth.py"),
    ),
    Step("when_to_contact_matrix", "When-to-contact rule priority matrix", python_script("smoke_western_when_to_contact_rule_matrix.py")),
    Step(
        "safety_validation_language",
        "Safety validation language matrix",
        python_script("smoke_western_safety_validation_language_matrix.py"),
    ),
    Step("timing_window_matrix", "Timing reducer branch matrix", python_script("smoke_western_timing_window_matrix.py")),
    Step("complete_result_flow", "Complete Western result flow smoke", python_script("smoke_western_complete_result_flow.py")),
    Step(
        "relationship_insight_blocks",
        "Relationship insight block matrix",
        python_script("smoke_western_relationship_insight_blocks.py"),
    ),
    Step(
        "relationship_thesis",
        "Relationship thesis layer matrix",
        python_script("smoke_western_relationship_thesis.py"),
    ),
    Step(
        "relationship_case_model",
        "Relationship case model matrix",
        python_script("smoke_western_relationship_case_model.py"),
    ),
    Step(
        "fixture_depth_coverage",
        "Western V2 fixture depth coverage matrix",
        python_script("smoke_western_fixture_depth_coverage.py"),
    ),
    Step(
        "visible_reading_depth",
        "Visible reading depth and anti-repetition matrix",
        python_script("smoke_western_visible_reading_depth.py"),
    ),
    Step(
        "final_interpretation_layer",
        "Final interpretation layer matrix",
        python_script("smoke_western_final_interpretation_layer.py"),
    ),
    Step(
        "final_narrative_lock",
        "Final narrative composer lock/evolve contract",
        python_script("smoke_final_narrative_lock.py"),
    ),
    Step(
        "final_narrative_v6_semantic_diversity",
        "Final narrative V21 semantic diversity matrix",
        python_script("smoke_final_narrative_v6_semantic_diversity.py"),
    ),
    Step(
        "final_narrative_context_storyline",
        "Final narrative context-combo storyline matrix",
        python_script("smoke_final_narrative_context_storyline.py"),
    ),
    Step("native_copy_contract", "Western native Traditional Chinese copy contract", python_script("smoke_western_native_copy_contract.py")),
    Step("precision_layer_boundaries", "Western precision-layer boundary contract", python_script("smoke_western_precision_layer_boundaries.py")),
    Step("context_matrix", "Western context matrix smoke", python_script("smoke_western_context_matrix.py")),
    Step("chart_variation_matrix", "Western chart variation matrix smoke", python_script("smoke_western_chart_variation_matrix.py")),
    Step(
        "paid_surface_report",
        "Paid V1 result surface evidence report",
        python_script("report_paid_v1_result_surface_evidence.py", "--check"),
    ),
    Step(
        "timing_branch_report",
        "Timing reducer branch evidence report",
        python_script("report_timing_reducer_branch_evidence.py", "--check"),
    ),
)


GENERATED_REPORT_STEPS: tuple[Step, ...] = (
    Step(
        "source_inventory_audit_report",
        "Western source inventory audit report staleness",
        python_script("report_western_source_inventory_audit.py"),
        report_path=ROOT / "docs" / "research" / "21-western-source-inventory-audit.md",
    ),
    Step(
        "structured_coverage_report",
        "Structured KB coverage report staleness",
        python_script("report_structured_kb_coverage.py"),
        report_path=ROOT / "docs" / "research" / "06-structured-kb-coverage.md",
    ),
    Step(
        "method_claim_usage_report",
        "Method claim runtime usage report staleness",
        python_script("report_method_claim_runtime_usage.py"),
        report_path=ROOT / "docs" / "research" / "13-western-method-claim-runtime-usage.md",
    ),
    Step(
        "v1_function_coverage_report",
        "V1 reading function coverage report staleness",
        python_script("report_v1_reading_function_coverage.py"),
        report_path=ROOT / "docs" / "research" / "15-western-v1-reading-function-coverage.md",
    ),
    Step(
        "book_digestion_execution_report",
        "Book digestion execution matrix report staleness",
        python_script("report_book_digestion_execution_matrix.py"),
        report_path=ROOT / "docs" / "research" / "17-western-book-digestion-execution-matrix.md",
    ),
    Step(
        "paid_v1_completion_audit_report",
        "Paid V1 Western completion audit report staleness",
        python_script("report_paid_v1_western_completion_audit.py"),
        report_path=ROOT / "docs" / "research" / "22-paid-v1-western-completion-audit.md",
    ),
    Step(
        "paid_v11_precision_depth_audit_report",
        "Paid V1.1 Western precision/depth audit report staleness",
        python_script("report_paid_v11_precision_depth_audit.py"),
        report_path=ROOT / "docs" / "research" / "23-paid-v11-precision-depth-audit.md",
    ),
    Step(
        "visible_reading_depth_report",
        "Paid V1 visible reading depth audit report staleness",
        python_script("report_visible_reading_depth.py"),
        report_path=ROOT / "docs" / "research" / "24-paid-v1-visible-reading-depth-audit.md",
    ),
    Step(
        "relationship_case_model_audit_report",
        "Phase 4 relationship case model provenance gate",
        python_script("report_relationship_case_model_audit.py"),
        report_path=ROOT / "docs" / "research" / "25-paid-v3-relationship-case-model-audit.md",
    ),
    Step(
        "reading_quality_engine_report",
        "Paid relationship reading quality engine report staleness",
        python_script("test_reading_quality_engine.py"),
        report_path=ROOT / "docs" / "research" / "28-reading-quality-engine-report.md",
    ),
    Step(
        "real_input_variation_audit_report",
        "Real input variation release gate",
        python_script("audit_relationship_result_variation.py"),
        report_path=ROOT / "docs" / "research" / "26-real-input-variation-audit.md",
    ),
    Step(
        "relationship_fit_similarity_audit_report",
        "Relationship-fit semantic similarity release gate",
        python_script("audit_relationship_fit_semantic_similarity.py"),
        report_path=ROOT / "docs" / "research" / "27-relationship-fit-semantic-similarity-audit.md",
    ),
    Step(
        "phase5_calibration_report",
        "Phase 5 production calibration report staleness",
        python_script("test_reading_phase5_calibration.py"),
        report_path=ROOT / "docs" / "research" / "29-phase5-production-calibration.md",
    ),
    Step(
        "final_narrative_phase6_test_engine_report",
        "Final narrative Phase 6 semantic test-engine report staleness",
        python_script("verify_final_narrative_phase6_test_engine.py"),
        report_path=ROOT / "docs" / "research" / "35-final-narrative-phase6-test-engine.md",
    ),
    Step(
        "reading_phase7_calibration_report",
        "Final narrative Phase 7 calibration report staleness",
        python_script("verify_reading_phase7_calibration.py"),
        report_path=ROOT / "docs" / "research" / "36-final-narrative-phase7-calibration.md",
    ),
    Step(
        "final_narrative_r6_chinese_quality_report",
        "Final narrative R6 Chinese quality report staleness",
        python_script("verify_final_narrative_r6_chinese_quality.py"),
        report_path=ROOT
        / "docs"
        / "research"
        / "41-final-narrative-native-zh-tw-r6-hard-gates.md",
    ),
    Step(
        "final_narrative_production_readiness_report",
        "Final narrative Phase 2-4 automated report staleness",
        python_script(
            "audit_final_narrative_production_readiness.py",
            "--corpus",
            str(ROOT / "data" / "reading-production-calibration" / "v2" / "holdout-corpus.json"),
            "--contract",
            str(ROOT / "data" / "reading-quality-cases" / "final-layer-production-contract-v3.json"),
            "--json-output",
            str(ROOT / "data" / "reading-production-calibration" / "v2" / "final-layer-production-audit.json"),
            "--report-output",
            str(ROOT / "docs" / "research" / "32-final-layer-production-readiness.md"),
        ),
        report_path=ROOT / "docs" / "research" / "32-final-layer-production-readiness.md",
    ),
)


WEB_STEPS: tuple[Step, ...] = (
    Step("web_typecheck", "Web TypeScript typecheck", ("npm", "run", "typecheck"), cwd=WEB_DIR),
    Step("web_build", "Web build", ("npm", "run", "build"), cwd=WEB_DIR),
    Step(
        "web_production_api_matrix",
        "Web production API context and chart matrix",
        ("npm", "run", "smoke:production-matrix"),
        cwd=WEB_DIR,
    ),
    Step("web_dashboard_smoke", "Web rendered dashboard smoke", ("npm", "run", "smoke:dashboard"), cwd=WEB_DIR),
)

HUMAN_ACCEPTANCE_STEPS: tuple[Step, ...] = (
    Step(
        "phase8_human_acceptance",
        "Phase 8 human-reviewed Phase 7 production golden set",
        python_script("smoke_reading_phase7_human_acceptance.py"),
    ),
)


def command_display(command: tuple[str, ...]) -> str:
    return " ".join(command)


def print_tail(text: str, *, prefix: str = "  ", max_lines: int = 80) -> None:
    if not text:
        return
    lines = text.rstrip().splitlines()
    if len(lines) > max_lines:
        lines = ["... output truncated ...", *lines[-max_lines:]]
    for line in lines:
        print(f"{prefix}{line}")


def run_subprocess(step: Step, command: tuple[str, ...] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    actual_command = command or step.command
    result = subprocess.run(
        list(actual_command),
        cwd=step.cwd,
        text=True,
        capture_output=True,
    )
    elapsed = time.monotonic() - started
    return {
        "id": step.id,
        "title": step.title,
        "command": command_display(actual_command),
        "cwd": str(step.cwd),
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "elapsedSeconds": round(elapsed, 2),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_url(url: str, *, timeout_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (OSError, URLError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def stop_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=8)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def existing_next_dev_url(server_output: str) -> str | None:
    if "Another next dev server is already running" not in server_output:
        return None
    matches = re.findall(r"http://(?:localhost|127\.0\.0\.1):\d+", server_output)
    if not matches:
        return None
    return matches[-1].replace("localhost", "127.0.0.1")


def run_dashboard_smoke_command(step: Step, target_url: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DASHBOARD_URL": target_url}
    return subprocess.run(
        list(step.command),
        cwd=step.cwd,
        text=True,
        capture_output=True,
        env=env,
        timeout=WEB_SMOKE_TIMEOUT_SECONDS,
    )


def run_web_dashboard_smoke(step: Step) -> dict[str, Any]:
    started = time.monotonic()
    port = free_local_port()
    target_url = f"http://127.0.0.1:{port}"
    next_env_path = WEB_DIR / "next-env.d.ts"
    original_next_env = next_env_path.read_text(encoding="utf-8") if next_env_path.exists() else None
    server_log = tempfile.NamedTemporaryFile(prefix=".web-dashboard-smoke-server.", suffix=".log", delete=False)
    server_log_path = Path(server_log.name)
    server_log.close()
    server_output = ""
    server: subprocess.Popen[str] | None = None
    try:
        with server_log_path.open("w", encoding="utf-8") as log_file:
            server = subprocess.Popen(
                ["npm", "run", "dev", "--", "-p", str(port)],
                cwd=WEB_DIR,
                text=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        try:
            wait_for_url(target_url)
        except Exception:
            server_output = server_log_path.read_text(encoding="utf-8") if server_log_path.exists() else ""
            reusable_url = existing_next_dev_url(server_output)
            if not reusable_url:
                raise
            target_url = reusable_url
            wait_for_url(target_url, timeout_seconds=10)
        result = run_dashboard_smoke_command(step, target_url)
        server_output = server_log_path.read_text(encoding="utf-8") if server_log_path.exists() else ""
        stdout = result.stdout.strip()
        if result.returncode != 0 and server_output:
            stdout = f"{stdout}\n\nDev server log:\n{server_output[-4000:]}".strip()
        return {
            "id": step.id,
            "title": step.title,
            "command": f"DASHBOARD_URL={target_url} {command_display(step.command)}",
            "cwd": str(step.cwd),
            "returncode": result.returncode,
            "ok": result.returncode == 0,
            "elapsedSeconds": round(time.monotonic() - started, 2),
            "stdout": stdout,
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired as exc:
        server_output = server_log_path.read_text(encoding="utf-8") if server_log_path.exists() else ""
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "").strip() if isinstance(exc.stderr, str) else ""
        return {
            "id": step.id,
            "title": step.title,
            "command": f"DASHBOARD_URL={target_url} {command_display(step.command)}",
            "cwd": str(step.cwd),
            "returncode": 1,
            "ok": False,
            "elapsedSeconds": round(time.monotonic() - started, 2),
            "stdout": (
                f"Timed out after {WEB_SMOKE_TIMEOUT_SECONDS}s.\n{stdout}"
                f"\n\nDev server log:\n{server_output[-4000:]}"
            ).strip(),
            "stderr": stderr,
        }
    except Exception as exc:
        server_output = server_log_path.read_text(encoding="utf-8") if server_log_path.exists() else ""
        return {
            "id": step.id,
            "title": step.title,
            "command": f"DASHBOARD_URL={target_url} {command_display(step.command)}",
            "cwd": str(step.cwd),
            "returncode": 1,
            "ok": False,
            "elapsedSeconds": round(time.monotonic() - started, 2),
            "stdout": f"{exc}\n\nDev server log:\n{server_output[-4000:]}".strip(),
            "stderr": "",
        }
    finally:
        if server is not None:
            stop_process_group(server)
        if original_next_env is not None and next_env_path.exists():
            next_env_path.write_text(original_next_env, encoding="utf-8")
        server_log_path.unlink(missing_ok=True)


def compare_generated_report(step: Step) -> dict[str, Any]:
    if step.report_path is None:
        raise ValueError(f"{step.id}: report_path required")
    started = time.monotonic()
    temp_file = tempfile.NamedTemporaryFile(
        prefix=f".{step.report_path.stem}.",
        suffix=step.report_path.suffix,
        dir=step.report_path.parent,
        delete=False,
    )
    temp_file.close()
    out_path = Path(temp_file.name)
    try:
        command = (*step.command, "--out", str(out_path))
        record = run_subprocess(step, command)
        if not record["ok"]:
            return record
        expected = step.report_path.read_text(encoding="utf-8") if step.report_path.exists() else ""
        actual = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if expected != actual:
            record.update(
                {
                    "ok": False,
                    "returncode": 1,
                    "stdout": (
                        f"{step.report_path.relative_to(ROOT)} is stale. "
                        f"Run `{command_display(step.command)}` to regenerate it."
                    ),
                    "stderr": "",
                }
            )
        record["elapsedSeconds"] = round(time.monotonic() - started, 2)
        return record
    finally:
        out_path.unlink(missing_ok=True)


def run_step(step: Step, *, json_mode: bool = False) -> dict[str, Any]:
    print(f"[RUN] {step.title}") if not json_mode else None
    if step.id in {"web_dashboard_smoke", "web_production_api_matrix"}:
        record = run_web_dashboard_smoke(step)
    elif step.report_path:
        record = compare_generated_report(step)
    else:
        record = run_subprocess(step)
    if json_mode:
        return record

    status = "ok" if record["ok"] else f"failed ({record['returncode']})"
    print(f"[{status.upper()}] {step.id} in {record['elapsedSeconds']}s")
    if not record["ok"]:
        print(f"Command: {record['command']}")
        if record.get("stdout"):
            print("stdout:")
            print_tail(record["stdout"])
        if record.get("stderr"):
            print("stderr:")
            print_tail(record["stderr"])
    return record


def selected_steps(*, include_web: bool, skip_report_staleness: bool, require_human_review: bool) -> list[Step]:
    steps = list(BACKEND_STEPS)
    if not skip_report_staleness:
        steps.extend(GENERATED_REPORT_STEPS)
    if include_web:
        steps.extend(WEB_STEPS)
    if require_human_review:
        steps.extend(HUMAN_ACCEPTANCE_STEPS)
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paid V1 Western reading backend verification.")
    parser.add_argument("--include-web", action="store_true", help="Also run apps/web typecheck and build.")
    parser.add_argument(
        "--require-human-review",
        action="store_true",
        help="Also require the Phase 8 human-reviewed Phase 7 production golden set.",
    )
    parser.add_argument(
        "--skip-report-staleness",
        action="store_true",
        help="Skip regenerated-vs-committed Markdown report comparisons.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON summary only.")
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    start = time.monotonic()
    for step in selected_steps(
        include_web=args.include_web,
        skip_report_staleness=args.skip_report_staleness,
        require_human_review=args.require_human_review,
    ):
        record = run_step(step, json_mode=args.json)
        records.append(record)
        if not record["ok"]:
            break

    elapsed = round(time.monotonic() - start, 2)
    failed = next((record for record in records if not record["ok"]), None)
    summary = {
        "ok": failed is None,
        "elapsedSeconds": elapsed,
        "stepsRun": len(records),
        "includeWeb": args.include_web,
        "requireHumanReview": args.require_human_review,
        "skipReportStaleness": args.skip_report_staleness,
        "failedStep": failed["id"] if failed else None,
        "steps": [
            {
                "id": record["id"],
                "title": record["title"],
                "command": record["command"],
                "cwd": record["cwd"],
                "returncode": record["returncode"],
                "ok": record["ok"],
                "elapsedSeconds": record["elapsedSeconds"],
            }
            for record in records
        ],
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print()
        print("Paid V1 reading stack verification")
        print(f"- status: {'PASS' if failed is None else 'FAIL'}")
        print(f"- steps run: {len(records)}")
        print(f"- elapsed: {elapsed}s")
        if failed:
            print(f"- failed step: {failed['id']}")
        else:
            print("- backend stack: verified")
            if args.include_web:
                print("- web stack: verified")

    return 0 if failed is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
