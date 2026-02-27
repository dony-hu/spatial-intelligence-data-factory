from __future__ import annotations

import subprocess
from pathlib import Path


def _run(script: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        ["python3", script],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_init_governance_pg_schema_blocked_by_default() -> None:
    proc = _run("scripts/init_governance_pg_schema.py")
    assert proc.returncode != 0
    assert "Legacy SQL init is disabled" in (proc.stdout + proc.stderr)


def test_init_unified_pg_schema_blocked_by_default() -> None:
    proc = _run("scripts/init_unified_pg_schema.py")
    assert proc.returncode != 0
    assert "Legacy unified SQL init is disabled" in (proc.stdout + proc.stderr)
