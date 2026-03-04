#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


CORE_MODULES = ["pipeline", "events", "llm", "rbac", "upload-batch"]
CORE_SUITES = [
    {
        "suite": "pipeline",
        "command": "PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_pipeline_api_contract.py",
    },
    {
        "suite": "events",
        "command": "PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_events_api_contract.py",
    },
    {
        "suite": "llm",
        "command": "PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_llm_interactions_api_contract.py",
    },
    {
        "suite": "rbac",
        "command": "PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_workpackage_observability_rbac.py",
    },
    {
        "suite": "upload-batch",
        "command": "PYTHONPATH=. .venv/bin/pytest -q services/governance_api/tests/test_runtime_upload_batch.py",
    },
    {
        "suite": "web-e2e-minimal",
        "command": "PYTHONPATH=. .venv/bin/pytest -q tests/web_e2e/test_runtime_observability_workpackage_search_ui.py",
    },
]


def _no_fallback_verdict() -> str:
    dsn = str(os.getenv("DATABASE_URL") or "")
    allow_mem_a = str(os.getenv("TRUST_ALLOW_MEMORY_FALLBACK") or "")
    allow_mem_b = str(os.getenv("GOVERNANCE_ALLOW_MEMORY_FALLBACK") or "")
    if not dsn.startswith("postgresql://"):
        return "FAIL: DATABASE_URL must be postgresql://"
    if allow_mem_a != "0" or allow_mem_b != "0":
        return "FAIL: memory fallback must be disabled"
    return "PASS"


def validate_report_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("commands", "results", "failure_analysis", "no_fallback_verdict", "covered_modules", "decision"):
        if key not in payload:
            errors.append(f"missing required field: {key}")
    covered = set(str(item) for item in (payload.get("covered_modules") or []))
    missing_modules = [name for name in CORE_MODULES if name not in covered]
    if missing_modules:
        errors.append(f"missing covered modules: {', '.join(missing_modules)}")
    has_critical_failure = any(not bool(item.get("passed")) for item in (payload.get("results") or []) if str(item.get("suite")) in CORE_MODULES)
    if has_critical_failure and str(payload.get("decision")) != "NO_GO":
        errors.append("critical suite failed, decision must be NO_GO")
    return errors


def _run_suite(cmd: str, cwd: Path) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True, check=False)
    merged = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    summary = "\n".join(line for line in merged.splitlines()[-12:] if line.strip())
    return proc.returncode == 0, summary


def run(cwd: Path) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    commands: list[str] = []
    failure_analysis: list[str] = []

    for suite in CORE_SUITES:
        name = str(suite["suite"])
        cmd = str(suite["command"])
        passed, summary = _run_suite(cmd, cwd)
        commands.append(cmd)
        results.append({"suite": name, "passed": passed, "summary": summary})
        if not passed:
            failure_analysis.append(f"{name} failed: {summary}")

    no_fallback = _no_fallback_verdict()
    if no_fallback != "PASS":
        failure_analysis.append(no_fallback)

    decision = "GO"
    if failure_analysis or any(not bool(item.get("passed")) for item in results if str(item.get("suite")) in CORE_MODULES):
        decision = "NO_GO"

    payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "commands": commands,
        "results": results,
        "failure_analysis": failure_analysis,
        "no_fallback_verdict": no_fallback,
        "covered_modules": CORE_MODULES,
        "decision": decision,
    }
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Epic 3 核心回归汇总（{datetime.now().date().isoformat()}）",
        "",
        f"- 决策：`{payload.get('decision')}`",
        f"- No-Fallback：`{payload.get('no_fallback_verdict')}`",
        "",
        "## 测试命令",
    ]
    for cmd in payload.get("commands") or []:
        lines.append(f"- `{cmd}`")
    lines.extend(["", "## 结果"])
    for item in payload.get("results") or []:
        mark = "PASS" if item.get("passed") else "FAIL"
        lines.append(f"- `{item.get('suite')}`: `{mark}`")
    lines.extend(["", "## 失败归因"])
    for row in payload.get("failure_analysis") or ["无"]:
        lines.append(f"- {row}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run epic3 core acceptance and emit single report")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--acceptance-dir", default="docs/acceptance")
    parser.add_argument("--report-dir", default="output/test-reports")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    acceptance_dir = Path(args.acceptance_dir).resolve()
    report_dir = Path(args.report_dir).resolve()
    acceptance_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    payload = run(root)
    errors = validate_report_payload(payload)
    if errors:
        payload["decision"] = "NO_GO"
        payload.setdefault("failure_analysis", []).extend(errors)

    day = datetime.now().date().isoformat()
    summary_md = report_dir / f"epic-3-regression-summary-{day}.md"
    accept_json = acceptance_dir / f"epic3-full-acceptance-{day}.json"
    accept_md = acceptance_dir / f"epic3-full-acceptance-{day}.md"

    summary_md.write_text(_render_markdown(payload), encoding="utf-8")
    acceptance_payload = {
        "epic": "Runtime Observability V2",
        "date": day,
        "result": "PASS" if payload.get("decision") == "GO" else "NO_GO",
        "summary": payload,
        "evidence": [
            str(summary_md),
        ],
    }
    accept_json.write_text(json.dumps(acceptance_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    accept_md.write_text(
        f"# Epic3 Full Acceptance ({day})\n\n- 结论：`{acceptance_payload['result']}`\n- 汇总：`{summary_md}`\n",
        encoding="utf-8",
    )
    print(f"Summary: {summary_md}")
    print(f"Acceptance JSON: {accept_json}")
    print(f"Acceptance Markdown: {accept_md}")
    return 0 if payload.get("decision") == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
