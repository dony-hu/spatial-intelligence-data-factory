#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_E2E_RESULT_PATH = PROJECT_ROOT / "output" / "lab_mode" / "web_e2e_latest.json"
OUT_DIR = PROJECT_ROOT / "output" / "workpackages"
GATE_JSON_LATEST_PATH = OUT_DIR / "nightly-quality-gate-latest.json"
FAILURE_ALERT_LATEST_PATH = OUT_DIR / "nightly-failure-alert-latest.json"
FAILURE_ALERT_HISTORY_PATH = OUT_DIR / "nightly-failure-alert-history.jsonl"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _run(cmd: list[str], timeout_sec: int = 600) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        merged = "\n".join([(completed.stdout or "").strip(), (completed.stderr or "").strip()]).strip()
        return int(completed.returncode), merged[-8000:]
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        merged = "\n".join([stdout, stderr, f"timeout after {timeout_sec}s"]).strip()
        return 124, merged[-8000:]


def _run_with_retry(cmd: list[str], max_attempts: int, timeout_sec: int, retry_delay_sec: float) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, max_attempts + 1):
        rc, output = _run(cmd, timeout_sec=timeout_sec)
        attempts.append(
            {
                "attempt": attempt,
                "return_code": rc,
                "output_tail": output[-3000:],
            }
        )
        if rc == 0:
            break
        if attempt < max_attempts and retry_delay_sec > 0:
            time.sleep(retry_delay_sec)
    return attempts


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _run_web_e2e_with_retry(max_attempts: int = 2) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    last_payload: dict[str, Any] = {}
    for attempt in range(1, max_attempts + 1):
        rc, output = _run([sys.executable, "scripts/run_web_e2e_catalog.py"], timeout_sec=300)
        payload: dict[str, Any] = {}
        if WEB_E2E_RESULT_PATH.exists():
            try:
                payload = json.loads(WEB_E2E_RESULT_PATH.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        attempts.append(
            {
                "attempt": attempt,
                "return_code": rc,
                "status": str(payload.get("status") or "failed"),
                "passed": int(payload.get("passed") or 0),
                "failed": int(payload.get("failed") or 0),
                "duration_sec": float(payload.get("duration_sec") or 0.0),
                "output_tail": output[-2000:],
            }
        )
        last_payload = payload
        if rc == 0 and str(payload.get("status") or "") == "passed":
            break
    return {
        "passed": bool(last_payload and str(last_payload.get("status") or "") == "passed"),
        "attempts": attempts,
        "final": last_payload,
        "retry_policy": {
            "max_attempts": max_attempts,
            "retry_delay_sec": 1.5,
        },
    }


def _run_sql_security_with_retry(max_attempts: int = 2) -> dict[str, Any]:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "services/governance_api/tests/test_ops_sql_readonly_api.py",
        "services/governance_api/tests/test_lab_sql_api.py",
    ]
    attempts = _run_with_retry(cmd, max_attempts=max_attempts, timeout_sec=180, retry_delay_sec=1.0)
    last_attempt = attempts[-1] if attempts else {"return_code": 1, "output_tail": ""}
    rc = _to_int(last_attempt.get("return_code"), default=1)
    output = str(last_attempt.get("output_tail") or "")
    passed = int(re.search(r"(\d+)\s+passed", output).group(1)) if re.search(r"(\d+)\s+passed", output) else 0
    failed = int(re.search(r"(\d+)\s+failed", output).group(1)) if re.search(r"(\d+)\s+failed", output) else 0
    errors = int(re.search(r"(\d+)\s+errors?", output).group(1)) if re.search(r"(\d+)\s+errors?", output) else 0
    return {
        "passed": rc == 0,
        "return_code": rc,
        "test_passed": passed,
        "test_failed": failed + errors,
        "output_tail": output[-3000:],
        "attempts": attempts,
        "retry_policy": {
            "max_attempts": max_attempts,
            "retry_delay_sec": 1.0,
        },
    }


def _classify_failures(web_e2e: dict[str, Any], sql_security: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    web_attempts = web_e2e.get("attempts") if isinstance(web_e2e.get("attempts"), list) else []
    web_failed_attempts = sum(1 for item in web_attempts if _to_int(item.get("return_code"), default=1) != 0)
    if not bool(web_e2e.get("passed")):
        failures.append(
            {
                "suite_id": "suite_web_e2e_catalog",
                "failure_type": "persistent_test_failure" if web_failed_attempts > 1 else "single_run_failure",
                "severity": "P1",
                "retryable": True,
                "retest_attempts": len(web_attempts),
                "gate_impact": "NO_GO",
                "reason": "web_e2e failed after nightly retry policy",
            }
        )
    elif web_failed_attempts > 0:
        failures.append(
            {
                "suite_id": "suite_web_e2e_catalog",
                "failure_type": "transient_recovered_by_retry",
                "severity": "P3",
                "retryable": True,
                "retest_attempts": len(web_attempts),
                "gate_impact": "GO_WITH_RISK_NOTE",
                "reason": "web_e2e recovered after retry",
            }
        )

    sql_attempts = sql_security.get("attempts") if isinstance(sql_security.get("attempts"), list) else []
    sql_failed_attempts = sum(1 for item in sql_attempts if _to_int(item.get("return_code"), default=1) != 0)
    if not bool(sql_security.get("passed")):
        failures.append(
            {
                "suite_id": "ops_sql_readonly_and_lab_sql",
                "failure_type": "security_regression",
                "severity": "P0",
                "retryable": True,
                "retest_attempts": len(sql_attempts),
                "gate_impact": "NO_GO",
                "reason": "sql readonly security regression failed",
            }
        )
    elif sql_failed_attempts > 0:
        failures.append(
            {
                "suite_id": "ops_sql_readonly_and_lab_sql",
                "failure_type": "transient_recovered_by_retry",
                "severity": "P2",
                "retryable": True,
                "retest_attempts": len(sql_attempts),
                "gate_impact": "GO_WITH_RISK_NOTE",
                "reason": "sql security suite recovered after retry",
            }
        )

    return failures


def _build_gate_judgement_card(
    generated_at: str,
    web_e2e: dict[str, Any],
    sql_security: dict[str, Any],
    release_decision: str,
    failures: list[dict[str, Any]],
    gate_path: Path,
) -> dict[str, Any]:
    gate_thresholds = {
        "suite_web_e2e_catalog": {
            "max_failed": 0,
            "required_status": "passed",
        },
        "ops_sql_readonly_and_lab_sql": {
            "max_failed": 0,
            "required_status": "passed",
        },
    }
    judgement = {
        "generated_at": generated_at,
        "workpackage_id": "wp-quality-gate-nightly-hardening-v0.2.0",
        "task_batch_id": "dispatch-address-line-closure-004",
        "release_decision": release_decision,
        "gate_thresholds": gate_thresholds,
        "retry_observations": {
            "web_e2e_attempts": len(web_e2e.get("attempts", [])),
            "sql_security_attempts": len(sql_security.get("attempts", [])),
        },
        "failed_classification": failures,
        "gate_report_path": str(gate_path),
        "evidence_paths": [
            str(gate_path),
            "output/lab_mode/web_e2e_latest.json",
            "output/dashboard/test_status_board.json",
            "output/dashboard/dashboard_events.jsonl",
        ],
    }
    return judgement


def _write_gate_file(payload: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _now_utc().strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"nightly-quality-gate-{stamp}.md"
    lines = [
        "# Nightly Quality Gate",
        "",
        f"- generated_at_utc: {payload['generated_at']}",
        f"- decision: {payload['release_decision']}",
        "",
        "## Web E2E",
        f"- final_status: {payload['web_e2e']['final'].get('status', 'failed')}",
        f"- passed: {payload['web_e2e']['final'].get('passed', 0)}",
        f"- failed: {payload['web_e2e']['final'].get('failed', 0)}",
        f"- attempts: {len(payload['web_e2e']['attempts'])}",
        "",
        "## SQL Security Regression",
        f"- passed: {payload['sql_security']['test_passed']}",
        f"- failed: {payload['sql_security']['test_failed']}",
        "",
        "## Risk Notes",
    ]
    for note in payload.get("risk_notes", []):
        lines.append(f"- {note}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    latest = OUT_DIR / "nightly-quality-gate-latest.md"
    latest.write_text(out_path.read_text(encoding="utf-8"), encoding="utf-8")
    GATE_JSON_LATEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def _write_failure_alert(payload: dict[str, Any]) -> None:
    alert_payload = {
        "generated_at": payload.get("generated_at"),
        "release_decision": payload.get("release_decision"),
        "risk_notes": payload.get("risk_notes", []),
        "failed_classification": payload.get("failed_classification", []),
        "gate_report_path": payload.get("gate_report_path"),
    }
    FAILURE_ALERT_LATEST_PATH.write_text(json.dumps(alert_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with FAILURE_ALERT_HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert_payload, ensure_ascii=False) + "\n")


def _emit_ci_alert(payload: dict[str, Any]) -> None:
    if str(payload.get("release_decision") or "") != "NO_GO":
        return
    failures = payload.get("failed_classification", []) if isinstance(payload.get("failed_classification"), list) else []
    labels = [str(item.get("failure_type") or "unknown") for item in failures[:3] if isinstance(item, dict)]
    summary = ", ".join(labels) if labels else "nightly quality gate failure"
    print(f"::error::Nightly quality gate NO_GO - {summary}")


def _emit_dashboard_event(event_type: str, workpackage_id: str, summary: str, payload: dict[str, Any]) -> None:
    cmd = [
        sys.executable,
        "scripts/update_dashboard_on_event.py",
        "--event-type",
        event_type,
        "--workpackage-id",
        workpackage_id,
        "--summary",
        summary,
        "--operator",
        "nightly-bot",
        "--payload-json",
        json.dumps(payload, ensure_ascii=False),
    ]
    _run(cmd)


def main() -> int:
    generated_at = _now_iso()
    web_e2e = _run_web_e2e_with_retry(max_attempts=2)
    sql_security = _run_sql_security_with_retry(max_attempts=2)
    _run([sys.executable, "scripts/build_dashboard_data.py"], timeout_sec=120)

    failures = _classify_failures(web_e2e=web_e2e, sql_security=sql_security)
    decision = "GO" if web_e2e["passed"] and sql_security["passed"] else "NO_GO"
    risk_notes: list[str] = []
    if not web_e2e["passed"]:
        risk_notes.append("web_e2e still failing after retry")
    if not sql_security["passed"]:
        risk_notes.append("sql readonly security regression has failures")
    if any(str(item.get("failure_type") or "") == "transient_recovered_by_retry" for item in failures if isinstance(item, dict)):
        risk_notes.append("transient failures recovered by retry; monitor stability trend")
    if not risk_notes:
        risk_notes.append("no blocking risk found in nightly quality gate")

    summary_payload = {
        "generated_at": generated_at,
        "web_e2e": web_e2e,
        "sql_security": sql_security,
        "failed_classification": failures,
        "release_decision": decision,
        "risk_notes": risk_notes,
    }
    gate_path = _write_gate_file(summary_payload)
    summary_payload["gate_report_path"] = str(gate_path)
    summary_payload["gate_judgement_card"] = _build_gate_judgement_card(
        generated_at=generated_at,
        web_e2e=web_e2e,
        sql_security=sql_security,
        release_decision=decision,
        failures=failures,
        gate_path=gate_path,
    )
    GATE_JSON_LATEST_PATH.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if decision == "NO_GO":
        _write_failure_alert(summary_payload)

    _emit_ci_alert(summary_payload)

    _emit_dashboard_event(
        event_type="test_synced",
        workpackage_id="wp-pm-dashboard-test-progress-v0.1.0",
        summary=f"nightly web_e2e {'passed' if web_e2e['passed'] else 'failed'}",
        payload={
            "suite_id": "suite_web_e2e_catalog",
            "status": web_e2e["final"].get("status", "failed"),
            "passed": int(web_e2e["final"].get("passed") or 0),
            "failed": int(web_e2e["final"].get("failed") or 0),
            "attempts": len(web_e2e["attempts"]),
            "failed_classification": [item for item in failures if item.get("suite_id") == "suite_web_e2e_catalog"],
            "gate_report_path": str(gate_path),
        },
    )
    _emit_dashboard_event(
        event_type="test_synced",
        workpackage_id="wp-test-panel-sql-query-readonly-v0.1.0",
        summary=f"nightly sql security {'passed' if sql_security['passed'] else 'failed'}",
        payload={
            "suite_id": "ops_sql_readonly_and_lab_sql",
            "status": "passed" if sql_security["passed"] else "failed",
            "passed": sql_security["test_passed"],
            "failed": sql_security["test_failed"],
            "attempts": len(sql_security.get("attempts", [])),
            "failed_classification": [item for item in failures if item.get("suite_id") == "ops_sql_readonly_and_lab_sql"],
            "gate_report_path": str(gate_path),
        },
    )
    _emit_dashboard_event(
        event_type="release_decision_changed",
        workpackage_id="wp-pm-dashboard-test-progress-v0.1.0",
        summary=f"nightly quality gate {decision}",
        payload={
            "release_decision": decision,
            "gate_report_path": str(gate_path),
            "risk_notes": risk_notes,
            "failed_classification": failures,
            "gate_judgement_card": summary_payload["gate_judgement_card"],
            "failure_alert_path": str(FAILURE_ALERT_LATEST_PATH) if decision == "NO_GO" else "",
        },
    )

    print(json.dumps(summary_payload, ensure_ascii=False, indent=2))
    return 0 if decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
