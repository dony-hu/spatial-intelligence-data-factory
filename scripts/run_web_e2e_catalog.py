#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "lab_mode"
RESULT_PATH = OUTPUT_DIR / "web_e2e_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_counts(text: str) -> dict[str, int]:
    def _pick(pattern: str) -> int:
        m = re.search(pattern, text)
        return int(m.group(1)) if m else 0

    return {
        "passed": _pick(r"(\d+)\s+passed"),
        "failed": _pick(r"(\d+)\s+failed"),
        "skipped": _pick(r"(\d+)\s+skipped"),
        "errors": _pick(r"(\d+)\s+errors?"),
        "xfailed": _pick(r"(\d+)\s+xfailed"),
        "xpassed": _pick(r"(\d+)\s+xpassed"),
    }


def _parse_duration(text: str) -> float:
    m = re.search(r"in\s+([0-9.]+)s", text)
    return float(m.group(1)) if m else 0.0


def run() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    help_result = subprocess.run(
        [sys.executable, "-m", "pytest", "--help"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    supports_browser_args = "--browser" in ((help_result.stdout or "") + (help_result.stderr or ""))

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/web_e2e",
        "-q",
    ]
    if supports_browser_args:
        cmd.extend(["--browser", "chromium", "--browser-channel", "chrome"])

    run_env = os.environ.copy()
    run_env.setdefault("WEB_E2E_SERVER_WAIT_SEC", "60")
    run_env.setdefault("WEB_E2E_OPTIMIZE_TIMEOUT_SEC", "90")
    run_env.setdefault("WEB_E2E_OPTIMIZE_RETRIES", "3")
    run_env.setdefault("WEB_E2E_OPTIMIZE_RETRY_DELAY_SEC", "1.5")

    started_at = _now_iso()
    completed = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        env=run_env,
    )
    ended_at = _now_iso()

    merged_output = "\n".join([completed.stdout or "", completed.stderr or ""]).strip()
    counts = _parse_counts(merged_output)
    duration_sec = _parse_duration(merged_output)
    total = (
        counts["passed"]
        + counts["failed"]
        + counts["skipped"]
        + counts["errors"]
        + counts["xfailed"]
        + counts["xpassed"]
    )

    status = "passed"
    if completed.returncode != 0:
        status = "failed"

    payload: dict[str, Any] = {
        "suite_id": "suite_web_e2e_catalog",
        "name": "web_e2e_catalog",
        "scope": "ui",
        "status": status,
        "return_code": int(completed.returncode),
        "last_run_at": ended_at,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": duration_sec,
        "total": total,
        "passed": counts["passed"],
        "failed": counts["failed"] + counts["errors"],
        "skipped": counts["skipped"],
        "xfailed": counts["xfailed"],
        "xpassed": counts["xpassed"],
        "command": " ".join(cmd),
        "browser_args_enabled": supports_browser_args,
        "runtime_config": {
            "web_e2e_server_wait_sec": run_env.get("WEB_E2E_SERVER_WAIT_SEC"),
            "web_e2e_optimize_timeout_sec": run_env.get("WEB_E2E_OPTIMIZE_TIMEOUT_SEC"),
            "web_e2e_optimize_retries": run_env.get("WEB_E2E_OPTIMIZE_RETRIES"),
            "web_e2e_optimize_retry_delay_sec": run_env.get("WEB_E2E_OPTIMIZE_RETRY_DELAY_SEC"),
        },
        "output_tail": merged_output[-4000:],
        "report_ref": "output/lab_mode/web_e2e_latest.json",
    }

    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run())
