from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


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


def test_run_acceptance_script_as_subprocess(tmp_path) -> None:
    if not _pg_available():
        pytest.skip("requires reachable PostgreSQL for PG-only acceptance")
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "output" / "acceptance"
    db_url = _postgres_db_url()
    cmd = [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/run_address_governance_mvp_acceptance.py",
        "--db-url",
        db_url,
        "--output-dir",
        str(output_dir),
        "--workdir",
        str(tmp_path),
    ]
    env = os.environ.copy()
    env["MVP_ACCEPTANCE_MOCK_LLM"] = "1"
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False, env=env)
    assert proc.returncode == 0, proc.stderr or proc.stdout

    json_files = sorted(output_dir.glob("address-governance-mvp-acceptance-*.json"))
    assert json_files, "acceptance json report not found"
    payload = json.loads(json_files[-1].read_text(encoding="utf-8"))
    assert payload.get("all_passed") is True
    checks = payload.get("checks") or {}
    assert checks.get("A1_cli_agent_llm_interaction", {}).get("passed") is True
    assert checks.get("A2_governance_dryrun", {}).get("passed") is True
    assert checks.get("A3_dryrun_publish_workpackage", {}).get("passed") is True
    assert checks.get("A4_runtime_query_api", {}).get("passed") is True
    assert checks.get("A5_blocked_audit_confirmation", {}).get("passed") is True
    assert checks.get("A6_db_persistence", {}).get("passed") is True


def test_run_acceptance_script_real_llm_gate_blocked_without_config(tmp_path) -> None:
    if not _pg_available():
        pytest.skip("requires reachable PostgreSQL for PG-only acceptance")
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "output" / "acceptance"
    db_url = _postgres_db_url()
    cmd = [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/run_address_governance_mvp_acceptance.py",
        "--db-url",
        db_url,
        "--output-dir",
        str(output_dir),
        "--workdir",
        str(tmp_path),
        "--llm-config",
        "config/not_exists.json",
    ]
    env = os.environ.copy()
    env.pop("MVP_ACCEPTANCE_MOCK_LLM", None)
    env.pop("LLM_MODEL", None)
    env.pop("LLM_API_KEY", None)
    env.pop("LLM_ENDPOINT", None)
    env.pop("LLM_PROVIDER", None)
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False, env=env)
    assert proc.returncode == 2, proc.stderr or proc.stdout

    json_files = sorted(output_dir.glob("address-governance-mvp-acceptance-*.json"))
    assert json_files, "acceptance json report not found"
    payload = json.loads(json_files[-1].read_text(encoding="utf-8"))
    checks = payload.get("checks") or {}
    llm_gate = checks.get("A1_llm_real_service_gate") or {}
    assert llm_gate.get("passed") is False
    assert llm_gate.get("evidence", {}).get("mode") == "real"


def test_run_acceptance_script_rejects_non_pg_db_url(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "output" / "acceptance"
    db_url = "mysql://user:pass@localhost/governance"
    cmd = [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/run_address_governance_mvp_acceptance.py",
        "--db-url",
        db_url,
        "--output-dir",
        str(output_dir),
        "--workdir",
        str(tmp_path),
    ]
    env = os.environ.copy()
    env["MVP_ACCEPTANCE_MOCK_LLM"] = "1"
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False, env=env)
    assert proc.returncode == 2, proc.stderr or proc.stdout
    assert "postgresql://" in (proc.stderr + proc.stdout)


def test_run_acceptance_script_uses_env_database_url_when_db_url_not_provided(tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "output" / "acceptance"
    cmd = [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/run_address_governance_mvp_acceptance.py",
        "--output-dir",
        str(output_dir),
        "--workdir",
        str(tmp_path),
        "--profile",
        "unit",
    ]
    env = os.environ.copy()
    env["MVP_ACCEPTANCE_MOCK_LLM"] = "1"
    env["DATABASE_URL"] = "mysql://env-user:env-pass@localhost/env_db"
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False, env=env)
    assert proc.returncode == 2, proc.stderr or proc.stdout
    assert "postgresql://" in (proc.stderr + proc.stdout)
