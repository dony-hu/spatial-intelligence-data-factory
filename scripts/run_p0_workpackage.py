#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKPACKAGE = PROJECT_ROOT / "workpackages" / "wp-core-engine-p0-stabilization-v0.1.0.json"
DEFAULT_SCHEMA = PROJECT_ROOT / "contracts" / "workpackage.schema.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "workpackages" / "wp-core-engine-p0-stabilization-v0.1.0.report.json"
DEFAULT_LINE_FEEDBACK = PROJECT_ROOT / "output" / "workpackages" / "line_feedback.latest.json"
DEFAULT_LINE_FEEDBACK_HASH = PROJECT_ROOT / "output" / "workpackages" / "line_feedback.latest.sha256"

SQLITE_REF_RE = re.compile(r"^sqlite://(?P<path>[^#]+)#(?P<table>[A-Za-z_][A-Za-z0-9_]*)$")
PG_REF_RE = re.compile(r"^pg://(?P<schema>[A-Za-z_][A-Za-z0-9_]*)\.(?P<table>[A-Za-z_][A-Za-z0-9_]*)$")
MIN_RUNTIME = (3, 11)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_schema(instance_path: Path, schema_path: Path) -> tuple[bool, list[str]]:
    schema = _load_json(schema_path)
    instance = _load_json(instance_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda x: list(x.path))
    if not errors:
        return True, []
    messages: list[str] = []
    for err in errors:
        path = ".".join(str(x) for x in err.path) or "<root>"
        messages.append(f"{path}: {err.message}")
    return False, messages


def _declared_python_version() -> str:
    version_path = PROJECT_ROOT / ".python-version"
    if not version_path.exists():
        return ""
    return version_path.read_text(encoding="utf-8").strip()


def _runtime_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _runtime_is_supported() -> bool:
    return (sys.version_info.major, sys.version_info.minor) >= MIN_RUNTIME


def _run_command(command: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    current_py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{current_py_path}" if current_py_path else str(PROJECT_ROOT)
    started = _now()
    proc = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    ended = _now()
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return {
        "command": " ".join(command),
        "returncode": proc.returncode,
        "started_at": started,
        "ended_at": ended,
        "output_tail": output[-8000:],
    }


def _is_valid_sqlite_ref(ref: str, expected_table: str) -> bool:
    match = SQLITE_REF_RE.match(ref)
    if not match:
        return False
    return match.group("table") == expected_table


def _is_valid_pg_ref(ref: str, expected_table: str) -> bool:
    match = PG_REF_RE.match(ref)
    if not match:
        return False
    return match.group("table") == expected_table


def _parse_sqlite_ref(ref: str, expected_table: str, project_root: Path = PROJECT_ROOT) -> tuple[Path | None, str | None]:
    match = SQLITE_REF_RE.match(ref)
    if not match:
        return None, None
    table = match.group("table")
    if table != expected_table:
        return None, None
    path_part = match.group("path")
    db_path = Path(path_part)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    return db_path, table


def _parse_pg_ref(ref: str, expected_table: str) -> tuple[str | None, str | None]:
    match = PG_REF_RE.match(ref)
    if not match:
        return None, None
    table = match.group("table")
    if table != expected_table:
        return None, None
    return match.group("schema"), table


def _validate_line_feedback_payload(
    payload: dict[str, Any],
    required_fields: list[str],
    expected_failure_ref: str,
    expected_replay_ref: str,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    missing = [field for field in required_fields if field not in payload]
    if missing:
        errors.append(f"missing_fields={','.join(missing)}")

    failure_ref = str(payload.get("failure_queue_snapshot_ref") or "")
    replay_ref = str(payload.get("replay_result_ref") or "")

    if failure_ref != expected_failure_ref:
        errors.append("failure_queue_snapshot_ref does not match line_feedback_contract")
    if replay_ref != expected_replay_ref:
        errors.append("replay_result_ref does not match line_feedback_contract")

    if not (_is_valid_sqlite_ref(failure_ref, "failure_queue") or _is_valid_pg_ref(failure_ref, "failure_queue")):
        errors.append("failure_queue_snapshot_ref must be sqlite://...#failure_queue or pg://<schema>.failure_queue")
    if not (_is_valid_sqlite_ref(replay_ref, "replay_runs") or _is_valid_pg_ref(replay_ref, "replay_runs")):
        errors.append("replay_result_ref must be sqlite://...#replay_runs or pg://<schema>.replay_runs")

    return len(errors) == 0, errors


def _validate_replay_store(
    failure_ref: str,
    replay_ref: str,
    project_root: Path = PROJECT_ROOT,
) -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {
        "failure_ref": failure_ref,
        "replay_ref": replay_ref,
        "failure_queue_table_exists": False,
        "replay_runs_table_exists": False,
        "failure_queue_rows": 0,
        "replay_runs_rows": 0,
        "errors": [],
    }

    if _is_valid_pg_ref(failure_ref, "failure_queue") and _is_valid_pg_ref(replay_ref, "replay_runs"):
        schema_failure, table_failure = _parse_pg_ref(failure_ref, "failure_queue")
        schema_replay, table_replay = _parse_pg_ref(replay_ref, "replay_runs")
        if not schema_failure or not table_failure or not schema_replay or not table_replay:
            details["errors"].append("invalid pg ref format")
            return False, details
        database_url = str(os.getenv("DATABASE_URL") or "")
        if not database_url.startswith("postgresql"):
            details["errors"].append("DATABASE_URL must be postgresql://... for pg replay validation")
            return False, details
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(database_url)
            with engine.begin() as conn:
                exists_failure = conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = :schema AND table_name = :table
                        """
                    ),
                    {"schema": schema_failure, "table": table_failure},
                ).fetchone()
                details["failure_queue_table_exists"] = bool(exists_failure)
                if exists_failure:
                    details["failure_queue_rows"] = int(
                        conn.execute(text(f"SELECT COUNT(*) FROM {schema_failure}.{table_failure}")).scalar() or 0
                    )

                exists_replay = conn.execute(
                    text(
                        """
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = :schema AND table_name = :table
                        """
                    ),
                    {"schema": schema_replay, "table": table_replay},
                ).fetchone()
                details["replay_runs_table_exists"] = bool(exists_replay)
                if exists_replay:
                    details["replay_runs_rows"] = int(
                        conn.execute(text(f"SELECT COUNT(*) FROM {schema_replay}.{table_replay}")).scalar() or 0
                    )
        except Exception as exc:
            details["errors"].append(f"postgres replay validation error: {exc}")
            return False, details
    else:
        failure_db_path, failure_table = _parse_sqlite_ref(failure_ref, "failure_queue", project_root=project_root)
        replay_db_path, replay_table = _parse_sqlite_ref(replay_ref, "replay_runs", project_root=project_root)
        if not failure_db_path or not replay_db_path or not failure_table or not replay_table:
            details["errors"].append("invalid sqlite ref format")
            return False, details

        if not failure_db_path.exists() or not replay_db_path.exists():
            details["errors"].append("replay database path does not exist")
            return False, details

        with sqlite3.connect(str(failure_db_path)) as conn:
            has_failure_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (failure_table,),
            ).fetchone()
            details["failure_queue_table_exists"] = bool(has_failure_table)
            if has_failure_table:
                details["failure_queue_rows"] = int(conn.execute(f"SELECT COUNT(*) FROM {failure_table}").fetchone()[0])

        with sqlite3.connect(str(replay_db_path)) as conn:
            has_replay_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (replay_table,),
            ).fetchone()
            details["replay_runs_table_exists"] = bool(has_replay_table)
            if has_replay_table:
                details["replay_runs_rows"] = int(conn.execute(f"SELECT COUNT(*) FROM {replay_table}").fetchone()[0])

    if not details["failure_queue_table_exists"]:
        details["errors"].append("failure_queue table missing")
    if not details["replay_runs_table_exists"]:
        details["errors"].append("replay_runs table missing")
    if details["failure_queue_rows"] < 1:
        details["errors"].append("failure_queue has no rows")
    if details["replay_runs_rows"] < 1:
        details["errors"].append("replay_runs has no rows")

    return len(details["errors"]) == 0, details


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _validate_line_feedback_hash(payload_path: Path, hash_path: Path) -> tuple[bool, dict[str, Any]]:
    details: dict[str, Any] = {
        "payload_path": str(payload_path),
        "hash_path": str(hash_path),
        "expected_sha256": "",
        "actual_sha256": "",
        "errors": [],
    }
    if not payload_path.exists():
        details["errors"].append("line feedback payload not found")
        return False, details
    if not hash_path.exists():
        details["errors"].append("line feedback hash file not found")
        return False, details
    raw_hash_text = hash_path.read_text(encoding="utf-8").strip()
    expected = raw_hash_text.split()[0] if raw_hash_text else ""
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        details["errors"].append("line feedback hash must be a 64-char sha256 hex")
        return False, details
    actual = _compute_sha256(payload_path)
    details["expected_sha256"] = expected
    details["actual_sha256"] = actual
    if expected != actual:
        details["errors"].append("line feedback hash mismatch")
        return False, details
    return True, details


def _run_package_tests() -> tuple[list[dict[str, Any]], bool]:
    test_plan = [
        {
            "name": "address_core",
            "scope": "A",
            "command": [
                sys.executable,
                "-m",
                "pytest",
                "packages/address_core/tests/test_normalize.py",
                "packages/address_core/tests/test_parse.py",
                "packages/address_core/tests/test_match.py",
                "packages/address_core/tests/test_dedup.py",
                "packages/address_core/tests/test_score.py",
                "packages/address_core/tests/test_pipeline_smoke.py",
                "-q",
            ],
        },
        {
            "name": "governance_api_and_lab",
            "scope": "B",
            "command": [
                sys.executable,
                "-m",
                "pytest",
                "services/governance_api/tests/test_ops_sql_readonly_api.py",
                "services/governance_api/tests/test_rulesets_api.py",
                "services/governance_api/tests/test_ops_api.py",
                "services/governance_api/tests/test_lab_api.py",
                "services/governance_api/tests/test_observability_integration.py",
                "-q",
            ],
        },
        {
            "name": "trust_data_hub",
            "scope": "C",
            "command": [
                sys.executable,
                "-m",
                "pytest",
                "services/trust_data_hub/tests/test_trust_data_hub_api.py",
                "-q",
            ],
        },
    ]
    package_reports: list[dict[str, Any]] = []
    all_passed = True
    for item in test_plan:
        result = _run_command(item["command"])
        passed = result["returncode"] == 0
        all_passed = all_passed and passed
        report_path = PROJECT_ROOT / "output" / "workpackages" / f"p0.{item['name']}.test-report.json"
        _write_json(
            report_path,
            {
                "package": item["name"],
                "scope": item["scope"],
                "passed": passed,
                "result": result,
            },
        )
        package_reports.append(
            {
                "name": item["name"],
                "scope": item["scope"],
                "status": "passed" if passed else "failed",
                "test_report_ref": str(report_path),
            }
        )
    return package_reports, all_passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P0 stabilization workpackage and emit GO/NO_GO report")
    parser.add_argument("--workpackage", default=str(DEFAULT_WORKPACKAGE))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--line-feedback-input", "--line-feedback-output", dest="line_feedback_input", default=str(DEFAULT_LINE_FEEDBACK))
    parser.add_argument("--line-feedback-hash", dest="line_feedback_hash", default=str(DEFAULT_LINE_FEEDBACK_HASH))
    parser.add_argument("--skip-package-tests", action="store_true")
    args = parser.parse_args()

    workpackage_path = Path(args.workpackage)
    schema_path = Path(args.schema)
    output_path = Path(args.output)
    line_feedback_path = Path(args.line_feedback_input)
    line_feedback_hash_path = Path(args.line_feedback_hash)

    schema_ok, schema_errors = _validate_schema(workpackage_path, schema_path)
    workpackage = _load_json(workpackage_path)
    declared_python = _declared_python_version()
    executor_python_short = _runtime_version()
    runtime_ok = _runtime_is_supported()

    if args.skip_package_tests:
        delivery_packages = [
            {
                "name": "address_core",
                "scope": "A",
                "status": "skipped",
                "test_report_ref": "skipped-by-flag",
            },
            {
                "name": "governance_api_and_lab",
                "scope": "B",
                "status": "skipped",
                "test_report_ref": "skipped-by-flag",
            },
            {
                "name": "trust_data_hub",
                "scope": "C",
                "status": "skipped",
                "test_report_ref": "skipped-by-flag",
            },
        ]
        packages_ok = True
    else:
        delivery_packages, packages_ok = _run_package_tests()

    line_feedback_contract = workpackage.get("line_feedback_contract") or {}
    required_fields = list(line_feedback_contract.get("required_fields") or [])
    expected_failure_ref = str(line_feedback_contract.get("failure_queue_snapshot_ref") or "")
    expected_replay_ref = str(line_feedback_contract.get("replay_result_ref") or "")

    line_feedback_errors: list[str] = []
    line_feedback_payload: dict[str, Any] = {}
    if line_feedback_path.exists():
        line_feedback_payload = _load_json(line_feedback_path)
    else:
        line_feedback_errors.append(f"line feedback file not found: {line_feedback_path}")

    line_feedback_ok = False
    if not line_feedback_errors:
        line_feedback_ok, payload_errors = _validate_line_feedback_payload(
            line_feedback_payload,
            required_fields,
            expected_failure_ref=expected_failure_ref,
            expected_replay_ref=expected_replay_ref,
        )
        line_feedback_errors.extend(payload_errors)

    replay_gate_ok, replay_store = _validate_replay_store(
        expected_failure_ref,
        expected_replay_ref,
    )
    line_feedback_hash_ok, line_feedback_hash_details = _validate_line_feedback_hash(
        payload_path=line_feedback_path,
        hash_path=line_feedback_hash_path,
    )

    runtime_declared_ok = bool(declared_python) and executor_python_short.startswith(declared_python)
    gate_results = {
        "runtime_unified_3_11_plus": runtime_ok and runtime_declared_ok,
        "workpackage_schema_ci": schema_ok,
        "line_feedback_contract_enforced": line_feedback_ok,
        "line_feedback_hash_verified": line_feedback_hash_ok,
        "failure_replay_feedback_closed": replay_gate_ok,
    }
    release_decision = (
        "GO"
        if (
            runtime_ok
            and runtime_declared_ok
            and schema_ok
            and line_feedback_ok
            and line_feedback_hash_ok
            and replay_gate_ok
            and packages_ok
        )
        else "NO_GO"
    )

    report = {
        "runtime_baseline": {
            "python_version": declared_python or "3.11",
            "ci_runtime": "github-actions-setup-python@3.11",
            "local_bootstrap": "python3.11 -m venv .venv && .venv/bin/pip install -r requirements-governance.txt",
        },
        "delivery_packages": delivery_packages,
        "gate_results": gate_results,
        "release_decision": release_decision,
        "meta": {
            "workpackage_id": workpackage.get("workpackage_id"),
            "workpackage_version": workpackage.get("version"),
            "executed_at": _now(),
            "executor_python": sys.version,
            "executor_python_short": executor_python_short,
            "runtime_declared": declared_python,
            "runtime_matches_declared": runtime_declared_ok,
            "schema_errors": schema_errors,
            "line_feedback_ref": str(line_feedback_path),
            "line_feedback_hash_ref": str(line_feedback_hash_path),
            "line_feedback_errors": line_feedback_errors,
            "line_feedback_hash": line_feedback_hash_details,
            "replay_store": replay_store,
        },
    }
    _write_json(output_path, report)

    print(f"workpackage={workpackage_path}")
    print(f"schema_ok={schema_ok}")
    print(f"packages_ok={packages_ok}")
    print(f"gate_results={gate_results}")
    print(f"release_decision={release_decision}")
    print(f"report={output_path}")
    return 0 if release_decision == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
