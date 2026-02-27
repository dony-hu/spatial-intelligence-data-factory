from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_run_observability_foundation_acceptance_script() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "output" / "acceptance"
    cmd = [
        "python3",
        "scripts/run_observability_pg_foundation_acceptance.py",
        "--output-dir",
        "output/acceptance",
    ]
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    json_files = sorted(output_dir.glob("observability-pg-foundation-acceptance-*.json"))
    assert json_files
    payload = json.loads(json_files[-1].read_text(encoding="utf-8"))
    assert payload.get("all_passed") is True
