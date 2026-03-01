from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def _postgres_db_url() -> str:
    return str(os.getenv("DATABASE_URL") or "postgresql://postgres:postgres@localhost:5432/spatial_db")


def _pg_available() -> bool:
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(_postgres_db_url())
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def test_mvp_acceptance_unit_script_runs_with_real_gate(tmp_path) -> None:
    assert _pg_available(), "requires reachable PostgreSQL for PG-only acceptance"
    repo_root = Path(__file__).resolve().parents[1]
    db_url = _postgres_db_url()
    out_dir = tmp_path / "output" / "acceptance"
    env = os.environ.copy()
    env["AGENT_RUNTIME"] = "opencode"
    proc = _run(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "scripts/run_address_governance_mvp_acceptance_unit.py",
            "--db-url",
            db_url,
            "--output-dir",
            str(out_dir),
            "--workdir",
            str(tmp_path),
        ],
        cwd=repo_root,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_mvp_acceptance_integration_script_runs_with_real_gate(tmp_path) -> None:
    assert _pg_available(), "requires reachable PostgreSQL for PG-only acceptance"
    repo_root = Path(__file__).resolve().parents[1]
    db_url = _postgres_db_url()
    out_dir = tmp_path / "output" / "acceptance"
    env = os.environ.copy()
    env["AGENT_RUNTIME"] = "opencode"
    proc = _run(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "scripts/run_address_governance_mvp_acceptance_integration.py",
            "--db-url",
            db_url,
            "--output-dir",
            str(out_dir),
            "--workdir",
            str(tmp_path),
        ],
        cwd=repo_root,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_mvp_acceptance_integration_script_isolated_from_llm_gate(tmp_path) -> None:
    assert _pg_available(), "requires reachable PostgreSQL for PG-only acceptance"
    repo_root = Path(__file__).resolve().parents[1]
    db_url = _postgres_db_url()
    out_dir = tmp_path / "output" / "acceptance"
    env = os.environ.copy()
    env["AGENT_RUNTIME"] = "opencode"
    env.pop("LLM_MODEL", None)
    env.pop("LLM_API_KEY", None)
    env.pop("LLM_ENDPOINT", None)
    env.pop("LLM_PROVIDER", None)
    proc = _run(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "scripts/run_address_governance_mvp_acceptance_integration.py",
            "--db-url",
            db_url,
            "--output-dir",
            str(out_dir),
            "--workdir",
            str(tmp_path),
            "--llm-config",
            "config/not_exists.json",
        ],
        cwd=repo_root,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_mvp_acceptance_real_llm_gate_script_fail_fast_without_config(tmp_path) -> None:
    assert _pg_available(), "requires reachable PostgreSQL for PG-only acceptance"
    repo_root = Path(__file__).resolve().parents[1]
    db_url = _postgres_db_url()
    out_dir = tmp_path / "output" / "acceptance"
    env = os.environ.copy()
    env["AGENT_RUNTIME"] = "opencode"
    env.pop("LLM_MODEL", None)
    env.pop("LLM_API_KEY", None)
    env.pop("LLM_ENDPOINT", None)
    env.pop("LLM_PROVIDER", None)
    proc = _run(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "scripts/run_address_governance_mvp_acceptance_real_llm_gate.py",
            "--db-url",
            db_url,
            "--output-dir",
            str(out_dir),
            "--workdir",
            str(tmp_path),
            "--llm-config",
            "config/not_exists.json",
        ],
        cwd=repo_root,
        env=env,
    )
    assert proc.returncode == 2, proc.stderr or proc.stdout


def test_mvp_acceptance_unit_script_rejects_non_pg_db_url(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    db_url = "mysql://user:pass@localhost/governance"
    out_dir = tmp_path / "output" / "acceptance"
    env = os.environ.copy()
    proc = _run(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "scripts/run_address_governance_mvp_acceptance_unit.py",
            "--db-url",
            db_url,
            "--output-dir",
            str(out_dir),
            "--workdir",
            str(tmp_path),
        ],
        cwd=repo_root,
        env=env,
    )
    assert proc.returncode == 2, proc.stderr or proc.stdout
