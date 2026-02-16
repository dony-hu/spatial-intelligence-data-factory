#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKPACKAGE = PROJECT_ROOT / "workpackages" / "wp-core-engine-p0-stabilization-v0.1.0.json"
DEFAULT_SCHEMA = PROJECT_ROOT / "contracts" / "workpackage.schema.json"
DEFAULT_FEEDBACK = PROJECT_ROOT / "output" / "workpackages" / "line_feedback.latest.json"
DEFAULT_EVIDENCE_JSON = PROJECT_ROOT / "output" / "workpackages" / "line_feedback_ci_block_demo.latest.json"
DEFAULT_EVIDENCE_MD = PROJECT_ROOT / "output" / "workpackages" / "line_feedback_ci_block_demo.latest.md"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not DEFAULT_FEEDBACK.exists():
        raise SystemExit(f"line feedback payload not found: {DEFAULT_FEEDBACK}")

    with tempfile.TemporaryDirectory(prefix="line-feedback-block-demo-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        tampered_payload = tmp_path / "line_feedback.latest.json"
        tampered_hash = tmp_path / "line_feedback.latest.sha256"
        report_out = tmp_path / "wp-core-engine-p0-stabilization-v0.1.0.report.json"

        tampered_payload.write_text(DEFAULT_FEEDBACK.read_text(encoding="utf-8"), encoding="utf-8")
        tampered_hash.write_text("0" * 64 + "\n", encoding="utf-8")

        command = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_p0_workpackage.py"),
            "--workpackage",
            str(DEFAULT_WORKPACKAGE),
            "--schema",
            str(DEFAULT_SCHEMA),
            "--line-feedback-input",
            str(tampered_payload),
            "--line-feedback-hash",
            str(tampered_hash),
            "--output",
            str(report_out),
            "--skip-package-tests",
        ]
        proc = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )

        report_payload: dict[str, Any] = {}
        if report_out.exists():
            report_payload = json.loads(report_out.read_text(encoding="utf-8"))

        release_decision = str(report_payload.get("release_decision") or "")
        gate_results = report_payload.get("gate_results") if isinstance(report_payload, dict) else {}
        hash_verified = bool(gate_results.get("line_feedback_hash_verified")) if isinstance(gate_results, dict) else False

        expected_blocked = proc.returncode != 0 and release_decision == "NO_GO" and not hash_verified
        evidence = {
            "generated_at_utc": _now_utc(),
            "scenario": "tampered_line_feedback_hash",
            "expected": {
                "run_p0_returncode_nonzero": True,
                "release_decision": "NO_GO",
                "line_feedback_hash_verified": False,
            },
            "actual": {
                "run_p0_returncode": proc.returncode,
                "release_decision": release_decision,
                "line_feedback_hash_verified": hash_verified,
                "line_feedback_hash": report_payload.get("meta", {}).get("line_feedback_hash", {}),
            },
            "status": "blocked_as_expected" if expected_blocked else "unexpected",
            "command": " ".join(command),
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
        }
        _write_json(DEFAULT_EVIDENCE_JSON, evidence)
        _write_md(
            DEFAULT_EVIDENCE_MD,
            [
                "# line_feedback CI 阻断演示证据",
                "",
                f"- 生成时间(UTC)：{evidence['generated_at_utc']}",
                f"- 场景：`{evidence['scenario']}`",
                f"- run_p0 返回码：`{evidence['actual']['run_p0_returncode']}`",
                f"- 发布判定：`{evidence['actual']['release_decision']}`",
                f"- hash 校验通过：`{evidence['actual']['line_feedback_hash_verified']}`",
                f"- 结论：`{evidence['status']}`",
                f"- JSON 证据：`{DEFAULT_EVIDENCE_JSON}`",
            ],
        )

    print(f"evidence_json={DEFAULT_EVIDENCE_JSON}")
    print(f"evidence_md={DEFAULT_EVIDENCE_MD}")
    return 0 if expected_blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
