from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_run_acceptance_script_as_subprocess(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "output" / "acceptance"
    db_url = f"sqlite:///{tmp_path / 'runtime' / 'governance.db'}"
    cmd = [
        "python3",
        "scripts/run_address_governance_mvp_acceptance.py",
        "--db-url",
        db_url,
        "--output-dir",
        str(output_dir),
        "--workdir",
        str(tmp_path),
    ]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    json_files = sorted(output_dir.glob("address-governance-mvp-acceptance-*.json"))
    assert json_files, "acceptance json report not found"
    payload = json.loads(json_files[-1].read_text(encoding="utf-8"))
    assert payload.get("all_passed") is True
    checks = payload.get("checks") or {}
    assert checks.get("A3_dryrun_publish_workpackage", {}).get("passed") is True
    assert checks.get("A4_runtime_query_api", {}).get("passed") is True
    assert checks.get("A5_blocked_audit_confirmation", {}).get("passed") is True
    assert checks.get("A6_db_persistence", {}).get("passed") is True
