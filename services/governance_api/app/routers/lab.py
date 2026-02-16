from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from packages.address_core.trusted_fengtu import FengtuTrustedClient
from services.governance_api.app.models.lab_models import (
    FengtuConflictDecisionPayload,
    FengtuConflictDecisionResponse,
    FengtuConflictItem,
    FengtuConflictListResponse,
    FengtuConfirmNetworkPayload,
    FengtuNetworkStatusResponse,
    LabCoverageRunRequest,
    LabCoverageRunResponse,
    LabCoverageStatusResponse,
    LabOptimizeRequest,
    LabOptimizeResponse,
    LabReplayResponse,
    LabSqlHistoryResponse,
    LabSqlQueryRequest,
    LabSqlQueryResponse,
    LabSqlTemplatesResponse,
    LabSampleDelta,
)
from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_worker.app.jobs.governance_job import run as run_governance_job

router = APIRouter()
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_LAB_OUTPUT_DIR = _PROJECT_ROOT / "output" / "lab_mode"
_CONFLICT_DECISIONS_PATH = _LAB_OUTPUT_DIR / "fengtu_conflict_decisions.json"
_COVERAGE_PROGRESS_PATH = _LAB_OUTPUT_DIR / "cn1300_module_coverage_progress.json"
_COVERAGE_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "run_cn1300_module_coverage.py"
_COVERAGE_RUN_LOCK = threading.Lock()
_COVERAGE_RUN_THREAD: threading.Thread | None = None
_SQL_HISTORY_PATH = _LAB_OUTPUT_DIR / "lab_sql_query_history.json"
_SQL_ALLOWED_TABLES = {
    "failure_queue",
    "replay_runs",
}
_SQL_MAX_ROWS = 200
_SQL_TIMEOUT_SEC = 2.0
_WORKPACKAGE_REPORT_PATH = _PROJECT_ROOT / "output" / "workpackages" / "wp-core-engine-p0-stabilization-v0.1.0.report.json"
_LINE_FEEDBACK_PATH = _PROJECT_ROOT / "output" / "workpackages" / "line_feedback.latest.json"
_SQL_FORBIDDEN_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|pragma|vacuum|replace|truncate)\b",
    re.IGNORECASE,
)
_SQL_TABLE_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z0-9_\".`]+)", re.IGNORECASE)
_DASHBOARD_DIR = _PROJECT_ROOT / "output" / "dashboard"
_DASHBOARD_TEST_STATUS_PATH = _DASHBOARD_DIR / "test_status_board.json"
_DASHBOARD_WORKPACKAGES_PATH = _DASHBOARD_DIR / "workpackages_live.json"
_DASHBOARD_PROJECT_PATH = _DASHBOARD_DIR / "project_overview.json"
_DASHBOARD_EVENTS_PATH = _DASHBOARD_DIR / "dashboard_events.jsonl"


def _readonly_postgres_dsn() -> str:
    dsn = str(os.getenv("DATABASE_URL") or os.getenv("READONLY_DATABASE_URL") or "").strip()
    if not dsn.startswith("postgresql"):
        raise HTTPException(
            status_code=500,
            detail={"code": "PG_DSN_MISSING", "message": "DATABASE_URL (postgresql://...) is required in PG-only mode"},
        )
    return dsn


def _parse_iso_to_dt(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _recent_audit_events(limit: int = 12) -> list[dict]:
    events = REPOSITORY.list_audit_events()
    sorted_events = sorted(events, key=lambda item: str(item.get("created_at", "")), reverse=True)
    return sorted_events[: max(1, min(100, int(limit)))]


def _count_recent_workpackages(hours: int = 24 * 7) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(hours)))
    count = 0
    for event in REPOSITORY.list_audit_events():
        event_type = str(event.get("event_type") or "")
        if event_type not in {"change_request_created", "ruleset_activated"}:
            continue
        dt = _parse_iso_to_dt(str(event.get("created_at") or ""))
        if dt and dt >= cutoff:
            count += 1
    return count


def _address_line_metrics() -> dict:
    ops = REPOSITORY.get_ops_summary()
    status_counts = ops.get("status_counts", {}) if isinstance(ops.get("status_counts"), dict) else {}
    avg_confidence = float(ops.get("avg_confidence") or 0.0)
    quality_score = round(max(0.0, min(100.0, avg_confidence * 100.0)), 2)

    failure_refs: list[dict] = []
    # Task-level failure references.
    for task_id, task in REPOSITORY._memory.tasks.items():  # type: ignore[attr-defined]
        task_status = str((task or {}).get("status") or "")
        if task_status.upper() != "FAILED":
            continue
        failure_refs.append(
            {
                "type": "task_failed",
                "ref": f"/v1/governance/tasks/{task_id}",
                "note": f"task_id={task_id} status=FAILED",
            }
        )
        if len(failure_refs) >= 5:
            break

    # Coverage-level failure replay reference.
    report_path = _latest_cn_report_path()
    if report_path:
        report = _load_json_file(report_path)
        case_details = report.get("case_details", []) if isinstance(report.get("case_details"), list) else []
        fail_rows = [row for row in case_details if isinstance(row, dict) and str(row.get("overall_result") or "") == "fail"]
        if fail_rows:
            failure_refs.append(
                {
                    "type": "coverage_fail_cases",
                    "ref": "/v1/governance/lab/coverage/view?result=fail&page=1&page_size=50",
                    "note": f"fail_cases={len(fail_rows)} report={report_path.name}",
                }
            )

    sample_trace_links: list[dict] = []
    if report_path:
        report = _load_json_file(report_path)
        case_details = report.get("case_details", []) if isinstance(report.get("case_details"), list) else []
        for row in case_details[:5]:
            if not isinstance(row, dict):
                continue
            case_id = str(row.get("case_id") or "")
            if not case_id:
                continue
            sample_trace_links.append(
                {
                    "case_id": case_id,
                    "raw_text": str(row.get("raw_text") or ""),
                    "overall_result": str(row.get("overall_result") or ""),
                    "observability_ref": f"/v1/governance/lab/coverage/view?case_id={case_id}&page=1&page_size=50",
                }
            )

    if not failure_refs:
        failure_refs.append(
            {
                "type": "none",
                "ref": "/v1/governance/lab/coverage/view",
                "note": "no failure reference found",
            }
        )

    line_feedback = _load_json_file(_LINE_FEEDBACK_PATH)
    runtime_observability = (
        line_feedback.get("runtime_observability", {})
        if isinstance(line_feedback.get("runtime_observability"), dict)
        else {}
    )

    return {
        "task_status": status_counts,
        "quality_score": quality_score,
        "failure_replay_refs": failure_refs,
        "sample_trace_links": sample_trace_links,
        "runtime_observability": {
            "step_total": int(runtime_observability.get("step_total") or 0),
            "step_failed": int(runtime_observability.get("step_failed") or 0),
            "step_error_rate": float(runtime_observability.get("step_error_rate") or 0.0),
            "collector": str(runtime_observability.get("collector") or "unknown"),
        },
    }


def _load_release_gate_status() -> dict:
    report = _load_json_file(_WORKPACKAGE_REPORT_PATH)
    gate_results = report.get("gate_results", {}) if isinstance(report.get("gate_results"), dict) else {}
    release_decision = str(report.get("release_decision") or "HOLD").upper()
    if release_decision not in {"GO", "NO_GO", "HOLD"}:
        release_decision = "HOLD"
    failed_gates = [k for k, v in gate_results.items() if not bool(v)]
    return {
        "release_decision": release_decision,
        "gate_results": gate_results,
        "failed_gates": failed_gates,
        "no_go_risk": release_decision == "NO_GO" or len(failed_gates) > 0,
        "report_ref": str(_WORKPACKAGE_REPORT_PATH.relative_to(_PROJECT_ROOT)) if _WORKPACKAGE_REPORT_PATH.exists() else "",
    }


def _build_observability_snapshot(env: str = "all", include_events: bool = True) -> dict:
    ops = REPOSITORY.get_ops_summary()
    status_counts = ops.get("status_counts", {}) if isinstance(ops.get("status_counts"), dict) else {}
    quality_reasons = ops.get("quality_gate_reasons", []) if isinstance(ops.get("quality_gate_reasons"), list) else []
    coverage = _coverage_status_payload()
    total_tasks = int(ops.get("total_tasks") or 0)
    failed_tasks = int(status_counts.get("FAILED") or 0)
    succeeded_tasks = int(status_counts.get("SUCCEEDED") or 0)
    reviewed_tasks = int(status_counts.get("REVIEWED") or 0)
    success_rate = (
        round(float(succeeded_tasks + reviewed_tasks) / float(total_tasks), 4)
        if total_tasks > 0
        else 1.0
    )
    alerts: list[dict] = []
    gate_alignment = _load_release_gate_status()
    if failed_tasks > 0:
        alerts.append(
            {
                "level": "P1",
                "code": "TASK_FAILED_EXISTS",
                "message": f"failed_tasks={failed_tasks}",
            }
        )
    for reason in quality_reasons:
        alerts.append(
            {
                "level": "P2",
                "code": "QUALITY_GATE_REASON",
                "message": str(reason),
            }
        )
    if gate_alignment.get("no_go_risk"):
        alerts.append(
            {
                "level": "P0",
                "code": "NO_GO_RISK",
                "message": f"release_decision={gate_alignment.get('release_decision')} failed_gates={','.join(gate_alignment.get('failed_gates', [])) or 'none'}",
            }
        )
    if not alerts:
        alerts.append({"level": "P3", "code": "ALL_GREEN", "message": "no blocking alerts"})

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": env,
        "l1": {
            "workpackages_7d": _count_recent_workpackages(),
            "total_tasks": total_tasks,
            "success_rate": success_rate,
            "pending_decisions": int(ops.get("pending_review_tasks") or 0),
        },
        "l2": {
            "active_ruleset_id": str(ops.get("active_ruleset_id") or "default"),
            "quality_gate_passed": bool(ops.get("quality_gate_passed")),
            "quality_gate_reasons": quality_reasons,
            "avg_confidence": float(ops.get("avg_confidence") or 0.0),
        },
        "l3": {
            "status_counts": status_counts,
            "gate_alignment": gate_alignment,
            "coverage_status": {
                "status": str(coverage.get("status") or "idle"),
                "processed_rows": int(coverage.get("processed_rows") or 0),
                "total_rows": int(coverage.get("total_rows") or 0),
                "progress_rate": float(coverage.get("progress_rate") or 0.0),
            },
        },
        "alerts": alerts,
        "address_line": _address_line_metrics(),
        "metric_explanations": {
            "l1.success_rate": "(SUCCEEDED + REVIEWED) / total_tasks，反映任务闭环完成率。",
            "l2.avg_confidence": "运营摘要中的平均置信度，范围[0,1]。",
            "address_line.quality_score": "avg_confidence × 100，线性换算为0-100质量分。",
            "address_line.runtime_observability.step_error_rate": "step_failed / step_total，反映运行时步骤失败占比。",
            "l3.gate_alignment.release_decision": "来自工作包门槛报告的 GO/NO_GO/HOLD 判定。",
        },
    }
    if include_events:
        payload["events"] = _recent_audit_events(limit=10)
    return payload


def _sse_pack(event: str, data: dict, event_id: str | None = None) -> str:
    lines: list[str] = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    body = json.dumps(data, ensure_ascii=False)
    for line in body.splitlines():
        lines.append(f"data: {line}")
    return "\n".join(lines) + "\n\n"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _load_json_file(path: Path) -> dict:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_json_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _sql_templates() -> list[dict[str, str]]:
    return [
        {
            "name": "failure_queue_latest",
            "sql": "SELECT failure_id, status, created_at, payload_json FROM failure_queue ORDER BY created_at DESC LIMIT 50",
        },
        {
            "name": "replay_runs_latest",
            "sql": "SELECT replay_id, failure_id, status, created_at FROM replay_runs ORDER BY created_at DESC LIMIT 50",
        },
    ]


def _sanitize_sql_summary(sql: str, max_len: int = 180) -> str:
    compact = " ".join(str(sql or "").split())
    return compact[:max_len]


def _extract_tables(sql: str) -> set[str]:
    tables: set[str] = set()
    for match in _SQL_TABLE_PATTERN.findall(str(sql or "")):
        normalized = str(match or "").strip().strip("\"").strip("`")
        if "." in normalized:
            normalized = normalized.split(".")[-1]
        if normalized:
            tables.add(normalized.lower())
    return tables


def _enforce_limit(sql: str, max_rows: int) -> tuple[str, int]:
    if re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE):
        def _replace(m: re.Match[str]) -> str:
            requested = int(m.group(1))
            return f"LIMIT {min(requested, max_rows)}"

        sql = re.sub(r"\blimit\s+(\d+)\b", _replace, sql, count=1, flags=re.IGNORECASE)
        limit_match = re.search(r"\blimit\s+(\d+)\b", sql, flags=re.IGNORECASE)
        effective_limit = int(limit_match.group(1)) if limit_match else max_rows
        return sql, effective_limit
    return f"{sql.rstrip()} LIMIT {max_rows}", max_rows


def _validate_readonly_sql(sql: str) -> tuple[str, set[str], int]:
    statement = str(sql or "").strip()
    if not statement:
        raise HTTPException(status_code=400, detail={"code": "empty_sql", "message": "sql is required"})
    if ";" in statement:
        raise HTTPException(status_code=400, detail={"code": "single_statement_only", "message": "only single statement is allowed"})
    lowered = statement.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise HTTPException(status_code=400, detail={"code": "readonly_enforced", "message": "only SELECT/WITH is allowed"})
    if _SQL_FORBIDDEN_PATTERN.search(statement):
        raise HTTPException(status_code=400, detail={"code": "readonly_enforced", "message": "forbidden keyword detected"})
    tables = _extract_tables(statement)
    if not tables:
        raise HTTPException(status_code=400, detail={"code": "table_required", "message": "query must reference whitelist tables"})
    disallowed = sorted(t for t in tables if t not in _SQL_ALLOWED_TABLES)
    if disallowed:
        raise HTTPException(
            status_code=400,
            detail={"code": "table_whitelist_enforced", "message": f"table not allowed: {', '.join(disallowed)}"},
        )
    limited_sql, effective_limit = _enforce_limit(statement, _SQL_MAX_ROWS)
    return limited_sql, tables, effective_limit


def _load_sql_history() -> list[dict[str, Any]]:
    payload = _load_json_file(_SQL_HISTORY_PATH)
    items = payload.get("items", [])
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def _save_sql_history(items: list[dict[str, Any]]) -> None:
    _save_json_file(_SQL_HISTORY_PATH, {"items": items[:200]})


def _append_sql_history(item: dict[str, Any]) -> None:
    items = _load_sql_history()
    items.insert(0, item)
    _save_sql_history(items)


def _execute_lab_postgres_readonly(sql: str, timeout_sec: float) -> tuple[list[str], list[dict[str, Any]]]:
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(_readonly_postgres_dsn(), row_factory=dict_row)
    try:
        timeout_ms = int(float(timeout_sec) * 1000)
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {timeout_ms}")
            cur.execute("SET search_path TO control_plane, address_line, trust_meta, trust_db, public")
            cur.execute(sql)
            fetched = cur.fetchall()
            columns = [str(getattr(col, "name", col[0])) for col in (cur.description or [])]
        return columns, [dict(row) for row in fetched]
    except Exception as exc:
        if "canceling statement due to statement timeout" in str(exc).lower():
            raise HTTPException(
                status_code=408,
                detail={"code": "timeout_enforced", "message": f"query timed out after {timeout_sec}s"},
            ) from exc
        raise HTTPException(status_code=400, detail={"code": "sql_invalid", "message": str(exc)}) from exc
    finally:
        conn.close()


def _read_dashboard_json(path: Path) -> dict[str, Any]:
    payload = _load_json_file(path)
    return payload if isinstance(payload, dict) else {}


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(_PROJECT_ROOT))
    except ValueError:
        return str(path)


def _read_dashboard_events(limit: int = 200) -> list[dict[str, Any]]:
    if not _DASHBOARD_EVENTS_PATH.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw in _DASHBOARD_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    events.sort(key=lambda x: str(x.get("time") or x.get("created_at") or ""), reverse=True)
    return events[: max(1, min(1000, int(limit)))]


def _merge_timeline_events(workpackages_live: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    recent_changes = workpackages_live.get("recent_changes", [])
    if isinstance(recent_changes, list):
        for item in recent_changes:
            if not isinstance(item, dict):
                continue
            merged.append(
                {
                    "time": str(item.get("time") or ""),
                    "event_type": str(item.get("event_type") or ""),
                    "workpackage_id": str(item.get("workpackage_id") or ""),
                    "summary": str(item.get("summary") or ""),
                    "operator": str(item.get("operator") or ""),
                    "evidence_ref": str(item.get("evidence_ref") or ""),
                }
            )
    for item in _read_dashboard_events(limit=200):
        merged.append(
            {
                "time": str(item.get("time") or item.get("created_at") or ""),
                "event_type": str(item.get("event_type") or ""),
                "workpackage_id": str(item.get("workpackage_id") or ""),
                "summary": str(item.get("summary") or ""),
                "operator": str(item.get("operator") or item.get("caller") or ""),
                "evidence_ref": str(item.get("payload", {}).get("evidence_ref") or "") if isinstance(item.get("payload"), dict) else "",
            }
        )
    merged.sort(key=lambda x: x.get("time", ""), reverse=True)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in merged:
        key = f"{row.get('time')}|{row.get('event_type')}|{row.get('workpackage_id')}|{row.get('summary')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped[: max(1, min(200, int(limit)))]


def _build_management_observability_data(owner_line: str = "", workpackage_id: str = "") -> dict[str, Any]:
    test_status_board = _read_dashboard_json(_DASHBOARD_TEST_STATUS_PATH)
    workpackages_live = _read_dashboard_json(_DASHBOARD_WORKPACKAGES_PATH)
    project_overview = _read_dashboard_json(_DASHBOARD_PROJECT_PATH)

    overall_progress = test_status_board.get("overall_progress", {}) if isinstance(test_status_board.get("overall_progress"), dict) else {}
    suites = test_status_board.get("test_suites", []) if isinstance(test_status_board.get("test_suites"), list) else []
    last_run_at = ""
    for suite in suites:
        if not isinstance(suite, dict):
            continue
        ts = str(suite.get("last_run_at") or "")
        if ts > last_run_at:
            last_run_at = ts
    gate_overall = bool((test_status_board.get("quality_gates") or {}).get("overall", False)) if isinstance(test_status_board.get("quality_gates"), dict) else False
    project_release = str(project_overview.get("release_decision") or "").upper()
    current_gate = project_release if project_release in {"GO", "NO_GO"} else ("GO" if gate_overall else "NO_GO")

    packages = workpackages_live.get("packages", []) if isinstance(workpackages_live.get("packages"), list) else []
    filtered_packages: list[dict[str, Any]] = []
    for row in packages:
        if not isinstance(row, dict):
            continue
        if owner_line and str(row.get("owner_line") or "") != owner_line:
            continue
        if workpackage_id and str(row.get("workpackage_id") or "") != workpackage_id:
            continue
        filtered_packages.append(row)

    execution_rows: list[dict[str, Any]] = []
    for row in filtered_packages:
        execution_rows.append(
            {
                "task_batch_id": str(row.get("task_batch_id") or row.get("workpackage_id") or "-"),
                "workpackage_id": str(row.get("workpackage_id") or "-"),
                "status": str(row.get("status") or "-"),
                "progress": int(row.get("progress") or 0),
                "owner": str(row.get("owner") or "-"),
                "owner_line": str(row.get("owner_line") or "-"),
                "eta": str(row.get("eta") or ""),
                "updated_at": str(row.get("updated_at") or "-"),
                "evidence_ref": str(row.get("test_report_ref") or ""),
                "release_decision": str(row.get("release_decision") or "-"),
            }
        )

    workline_status: list[dict[str, Any]] = []
    by_owner_line = workpackages_live.get("by_owner_line", []) if isinstance(workpackages_live.get("by_owner_line"), list) else []
    for line_row in by_owner_line:
        if not isinstance(line_row, dict):
            continue
        line_name = str(line_row.get("owner_line") or "")
        if owner_line and line_name != owner_line:
            continue
        line_pkgs = [pkg for pkg in packages if isinstance(pkg, dict) and str(pkg.get("owner_line") or "") == line_name]
        status = "GO"
        if any(str(pkg.get("release_decision") or "").upper() == "NO_GO" for pkg in line_pkgs):
            status = "NO_GO"
        owner = str(line_pkgs[0].get("owner") or "-") if line_pkgs else "-"
        eta = str(line_pkgs[0].get("eta") or "") if line_pkgs else ""
        evidence_ref = str(line_pkgs[0].get("test_report_ref") or "") if line_pkgs else ""
        workline_status.append(
            {
                "line_name": line_name,
                "status": status,
                "owner": owner,
                "eta": eta,
                "evidence_ref": evidence_ref,
            }
        )

    wp_gate_rows: list[dict[str, Any]] = []
    for row in filtered_packages:
        wp_gate_rows.append(
            {
                "scope": "workpackage",
                "id": str(row.get("workpackage_id") or "-"),
                "gate_status": str(row.get("release_decision") or "-"),
                "owner": str(row.get("owner") or "-"),
                "eta": str(row.get("eta") or ""),
                "evidence_ref": str(row.get("test_report_ref") or ""),
            }
        )

    project_gate_row = {
        "scope": "project",
        "id": str(project_overview.get("project_id") or "spatial-intelligence-data-factory"),
        "gate_status": current_gate,
        "owner": str(project_overview.get("owner") or "可观测与运营指标线-Codex"),
        "eta": str(project_overview.get("eta") or ""),
        "evidence_ref": str(project_overview.get("evidence_ref") or _relative(_DASHBOARD_PROJECT_PATH) if _DASHBOARD_PROJECT_PATH.exists() else ""),
    }

    failure_classification: list[dict[str, Any]] = []
    regressions = test_status_board.get("regressions", []) if isinstance(test_status_board.get("regressions"), list) else []
    suite_ref_map: dict[str, str] = {}
    for suite in suites:
        if isinstance(suite, dict):
            suite_ref_map[str(suite.get("suite_id") or "")] = str(suite.get("report_ref") or "")
    for reg in regressions:
        if not isinstance(reg, dict):
            continue
        sid = str(reg.get("suite_id") or "")
        failure_classification.append(
            {
                "failure_type": "regression_open",
                "severity": "P1",
                "retryable": True,
                "gate_impact": True,
                "owner": str(reg.get("owner") or "-"),
                "eta": str(reg.get("eta") or ""),
                "evidence_ref": suite_ref_map.get(sid, ""),
            }
        )
    if not failure_classification:
        failure_classification.append(
            {
                "failure_type": "none",
                "severity": "P3",
                "retryable": False,
                "gate_impact": False,
                "owner": "可观测与运营指标线-Codex",
                "eta": "",
                "evidence_ref": str(_relative(_DASHBOARD_TEST_STATUS_PATH) if _DASHBOARD_TEST_STATUS_PATH.exists() else ""),
            }
        )

    timeline = _merge_timeline_events(workpackages_live, limit=80)
    if owner_line:
        timeline = [item for item in timeline if owner_line in str(item.get("summary") or "") or owner_line == str(item.get("owner_line") or "")]
    if workpackage_id:
        timeline = [item for item in timeline if str(item.get("workpackage_id") or "") == workpackage_id]
    timeline = timeline[:50]
    while len(timeline) < 20:
        timeline.append(
            {
                "time": "",
                "event_type": "placeholder",
                "workpackage_id": "",
                "summary": "insufficient source events; placeholder",
                "operator": "system",
                "evidence_ref": "",
            }
        )

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "owner_line": owner_line,
            "workpackage_id": workpackage_id,
            "owner_line_options": sorted({str(row.get("owner_line") or "") for row in packages if isinstance(row, dict) and str(row.get("owner_line") or "")}),
            "workpackage_options": sorted({str(row.get("workpackage_id") or "") for row in packages if isinstance(row, dict) and str(row.get("workpackage_id") or "")}),
        },
        "test_overview": {
            "total": int(overall_progress.get("total_cases") or 0),
            "executed": int(overall_progress.get("executed_cases") or 0),
            "passed": int(overall_progress.get("passed_cases") or 0),
            "failed": int(overall_progress.get("failed_cases") or 0),
            "skipped": int(overall_progress.get("skipped_cases") or 0),
            "pass_rate": float(overall_progress.get("pass_rate") or 0.0),
            "quality_score": round(float(overall_progress.get("pass_rate") or 0.0) * 100, 2),
            "last_run_at": last_run_at or str(overall_progress.get("last_run_at") or ""),
            "gate_decision": current_gate,
            "owner": "可观测与运营指标线-Codex",
            "eta": str(project_overview.get("eta") or ""),
            "evidence_ref": str(_relative(_DASHBOARD_TEST_STATUS_PATH) if _DASHBOARD_TEST_STATUS_PATH.exists() else ""),
        },
        "gate_layers": {
            "workpackage": wp_gate_rows,
            "workline": workline_status,
            "project": [project_gate_row],
        },
        "failure_classification": failure_classification,
        "execution_process": {
            "chain": ["任务下发", "执行", "回传", "回放", "门槛判定"],
            "rows": execution_rows,
            "timeline": timeline[: max(20, min(50, len(timeline)))],
        },
        "sql_capability": {
            "templates": _sql_templates(),
            "whitelist_tables": sorted(_SQL_ALLOWED_TABLES),
            "max_rows": _SQL_MAX_ROWS,
            "timeout_sec": _SQL_TIMEOUT_SEC,
            "audit_history_ref": "/v1/governance/lab/sql/history",
        },
    }


def _is_valid_cn_coverage_report(path: Path) -> bool:
    payload = _load_json_file(path)
    rows_total = payload.get("rows_total", 0)
    module_coverage = payload.get("module_coverage")
    if not isinstance(rows_total, int) or rows_total <= 0:
        return False
    if not isinstance(module_coverage, dict):
        return False
    return all(key in module_coverage for key in ("normalize", "parse", "match", "score"))


def _latest_cn_report_path() -> Path | None:
    candidates = sorted(_LAB_OUTPUT_DIR.glob("cn1300_module_coverage_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    for path in candidates:
        if _is_valid_cn_coverage_report(path):
            return path
    return candidates[0]


def _coverage_status_payload() -> dict:
    payload = _load_json_file(_COVERAGE_PROGRESS_PATH)
    status = str(payload.get("status") or "")
    report_path = str(payload.get("report_path") or "")
    if status:
        return {
            "status": status,
            "started_at": str(payload.get("started_at") or ""),
            "updated_at": str(payload.get("updated_at") or ""),
            "processed_rows": int(payload.get("processed_rows") or 0),
            "total_rows": int(payload.get("total_rows") or 0),
            "progress_rate": float(payload.get("progress_rate") or 0.0),
            "last_case_id": str(payload.get("last_case_id") or ""),
            "report_path": report_path,
            "message": str(payload.get("message") or ""),
        }
    report_path_obj = _latest_cn_report_path()
    if report_path_obj:
        report = _load_json_file(report_path_obj)
        rows_total = int(report.get("rows_total") or 0)
        return {
            "status": "completed",
            "started_at": "",
            "updated_at": str(report.get("generated_at") or ""),
            "processed_rows": rows_total,
            "total_rows": rows_total,
            "progress_rate": 1.0 if rows_total > 0 else 0.0,
            "last_case_id": "",
            "report_path": str(report_path_obj),
            "message": "latest report available",
        }
    return {
        "status": "idle",
        "started_at": "",
        "updated_at": "",
        "processed_rows": 0,
        "total_rows": 0,
        "progress_rate": 0.0,
        "last_case_id": "",
        "report_path": "",
        "message": "no report yet",
    }


def _run_coverage_subprocess(payload: LabCoverageRunRequest) -> None:
    cmd = [
        sys.executable,
        str(_COVERAGE_SCRIPT_PATH),
        "--dataset",
        payload.dataset,
        "--output-dir",
        str(_LAB_OUTPUT_DIR),
        "--progress-file",
        str(_COVERAGE_PROGRESS_PATH),
    ]
    if payload.limit is not None:
        cmd.extend(["--limit", str(payload.limit)])
    if payload.enable_fengtu:
        cmd.append("--enable-fengtu")

    env = os.environ.copy()
    existing_python_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_PROJECT_ROOT}:{existing_python_path}" if existing_python_path else str(_PROJECT_ROOT)
    completed = subprocess.run(cmd, cwd=str(_PROJECT_ROOT), env=env, capture_output=True, text=True)
    if completed.returncode != 0:
        _save_json_file(
            _COVERAGE_PROGRESS_PATH,
            {
                "status": "failed",
                "started_at": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "processed_rows": 0,
                "total_rows": 0,
                "progress_rate": 0.0,
                "last_case_id": "",
                "report_path": "",
                "message": (completed.stderr or completed.stdout or "coverage run failed").strip(),
            },
        )


def _start_coverage_run(payload: LabCoverageRunRequest) -> bool:
    global _COVERAGE_RUN_THREAD
    with _COVERAGE_RUN_LOCK:
        if _COVERAGE_RUN_THREAD is not None and _COVERAGE_RUN_THREAD.is_alive():
            return False
        _COVERAGE_RUN_THREAD = threading.Thread(target=_run_coverage_subprocess, args=(payload,), daemon=True)
        _COVERAGE_RUN_THREAD.start()
        return True


def _coverage_filters(case_details: list[dict]) -> tuple[list[str], list[str], list[str]]:
    result_values = sorted({str(item.get("overall_result", "")) for item in case_details if str(item.get("overall_result", ""))})
    case_types = sorted({str(item.get("case_type", "")) for item in case_details if str(item.get("case_type", ""))})
    cities = sorted({str(item.get("city", "")) for item in case_details if str(item.get("city", ""))})
    return result_values, case_types, cities


def _apply_case_filters(
    case_details: list[dict],
    case_id_filter: str,
    result_filter: str,
    case_type_filter: str,
    city_filter: str,
    module_filter: str,
    module_outcome: str,
    status_filter: str,
) -> list[dict]:
    filtered = case_details
    if case_id_filter.strip():
        expected_case_id = case_id_filter.strip()
        filtered = [row for row in filtered if str(row.get("case_id", "")) == expected_case_id]
    if result_filter != "all":
        filtered = [row for row in filtered if str(row.get("overall_result")) == result_filter]
    if case_type_filter != "all":
        filtered = [row for row in filtered if str(row.get("case_type")) == case_type_filter]
    if city_filter != "all":
        filtered = [row for row in filtered if str(row.get("city")) == city_filter]
    if status_filter != "all":
        filtered = [row for row in filtered if str(row.get("status")) == status_filter]
    if module_filter != "all" and module_outcome in {"pass", "fail"}:
        expected_value = module_outcome == "pass"
        filtered = [
            row
            for row in filtered
            if bool((row.get("module_result") or {}).get(module_filter, False)) is expected_value
        ]
    return filtered


@router.get("/lab/trusted/fengtu/status", response_model=FengtuNetworkStatusResponse)
def get_fengtu_status() -> FengtuNetworkStatusResponse:
    client = FengtuTrustedClient()
    state = FengtuTrustedClient.network_confirmation_state()
    return FengtuNetworkStatusResponse(
        enabled=client.enabled(),
        confirmation_required=bool(state.get("confirmation_required", False)),
        last_network_error=str(state.get("last_network_error") or ""),
        last_confirm_by=str(state.get("last_confirm_by") or ""),
    )


@router.post("/lab/trusted/fengtu/confirm-network", response_model=FengtuNetworkStatusResponse)
def confirm_fengtu_network(payload: FengtuConfirmNetworkPayload) -> FengtuNetworkStatusResponse:
    client = FengtuTrustedClient()
    state = FengtuTrustedClient.confirm_network_resume(payload.operator)
    REPOSITORY.log_audit_event(
        "approval_changed",
        payload.operator,
        {
            "target": "fengtu_network",
            "status": "confirmed",
            "last_network_error": str(state.get("last_network_error") or ""),
        },
    )
    return FengtuNetworkStatusResponse(
        enabled=client.enabled(),
        confirmation_required=bool(state.get("confirmation_required", False)),
        last_network_error=str(state.get("last_network_error") or ""),
        last_confirm_by=str(state.get("last_confirm_by") or ""),
    )


@router.get("/lab/trusted/fengtu/conflicts", response_model=FengtuConflictListResponse)
def list_fengtu_conflicts(status: str = "pending") -> FengtuConflictListResponse:
    report_path = _latest_cn_report_path()
    if report_path is None:
        return FengtuConflictListResponse(
            report_path="",
            total_conflicts=0,
            pending_conflicts=0,
            resolved_conflicts=0,
            items=[],
        )

    report = _load_json_file(report_path)
    raw_items = (
        report.get("samples", {}).get("fengtu_conflicts_pending_confirmation_top50", [])
        if isinstance(report.get("samples"), dict)
        else []
    )
    decisions = _load_json_file(_CONFLICT_DECISIONS_PATH)
    decision_items = decisions.get("items", {}) if isinstance(decisions.get("items"), dict) else {}

    items: list[FengtuConflictItem] = []
    for row in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(row, dict):
            continue
        case_id = str(row.get("case_id") or "")
        decision = decision_items.get(case_id, {}) if isinstance(decision_items.get(case_id), dict) else {}
        state = "resolved" if decision else "pending"
        if status in {"pending", "resolved"} and state != status:
            continue
        items.append(
            FengtuConflictItem(
                case_id=case_id,
                raw_text=str(row.get("raw_text") or ""),
                expected_normalized=str(row.get("expected_normalized") or ""),
                fengtu_candidate=str(row.get("fengtu_candidate") or ""),
                note=str(row.get("note") or "pending_user_confirmation"),
                status=state,
                decision=str(decision.get("decision") or ""),
                decision_comment=str(decision.get("comment") or ""),
                decided_by=str(decision.get("operator") or ""),
                decided_at=str(decision.get("decided_at") or ""),
            )
        )

    pending_count = sum(1 for row in raw_items if isinstance(row, dict) and str(row.get("case_id") or "") not in decision_items)
    resolved_count = sum(1 for row in raw_items if isinstance(row, dict) and str(row.get("case_id") or "") in decision_items)
    return FengtuConflictListResponse(
        report_path=str(report_path),
        total_conflicts=len(raw_items) if isinstance(raw_items, list) else 0,
        pending_conflicts=pending_count,
        resolved_conflicts=resolved_count,
        items=items,
    )


@router.post("/lab/coverage/run", response_model=LabCoverageRunResponse)
def start_coverage_run(payload: LabCoverageRunRequest) -> LabCoverageRunResponse:
    accepted = _start_coverage_run(payload)
    status = _coverage_status_payload()
    if not accepted:
        return LabCoverageRunResponse(
            accepted=False,
            status=str(status.get("status") or "running"),
            message="a coverage run is already in progress",
            progress_path=str(_COVERAGE_PROGRESS_PATH),
            report_path=str(status.get("report_path") or ""),
        )
    return LabCoverageRunResponse(
        accepted=True,
        status="running",
        message="coverage run started",
        progress_path=str(_COVERAGE_PROGRESS_PATH),
        report_path="",
    )


@router.get("/lab/coverage/status", response_model=LabCoverageStatusResponse)
def get_coverage_run_status() -> LabCoverageStatusResponse:
    status = _coverage_status_payload()
    return LabCoverageStatusResponse(**status)


@router.get("/lab/observability/snapshot")
def get_observability_snapshot(env: str = "all", include_events: bool = True) -> dict:
    return _build_observability_snapshot(env=env, include_events=include_events)


@router.get("/lab/observability/stream")
def observability_event_stream(
    env: str = "all",
    interval_sec: float = 2.0,
    max_events: Optional[int] = None,
) -> StreamingResponse:
    interval = max(1.0, min(30.0, float(interval_sec)))
    safe_max = max(1, min(100, int(max_events))) if max_events is not None else None

    def _generate():
        sent = 0
        yield _sse_pack(
            event="connected",
            data={"ok": True, "generated_at": datetime.now(timezone.utc).isoformat(), "environment": env},
            event_id=str(uuid4()),
        )
        while True:
            snapshot = _build_observability_snapshot(env=env, include_events=True)
            yield _sse_pack(
                event="snapshot",
                data=snapshot,
                event_id=str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            )
            sent += 1
            if safe_max is not None and sent >= safe_max:
                break
            time.sleep(interval)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/lab/observability/view", response_class=HTMLResponse)
def observability_live_view(env: str = "all") -> HTMLResponse:
    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>系统可观测性管理看板</title>
        <style>
          :root {{
            --bg: #edf3f7;
            --card: #fff;
            --line: #dbe6ef;
            --ink: #102a43;
            --soft: #5b7286;
            --blue: #1d5f91;
            --warn: #b88217;
            --danger: #b42318;
            --ok: #177245;
          }}
          * {{ box-sizing: border-box; }}
          body {{ margin: 0; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--ink); }}
          .wrap {{ max-width: 1400px; margin: 0 auto; padding: 14px; }}
          .hero {{ background: linear-gradient(120deg,#123f62,#145f7f); color: #fff; border-radius: 12px; padding: 14px; }}
          .row {{ display: grid; gap: 10px; grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 10px; }}
          .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 10px; }}
          .split {{ display: grid; gap: 10px; grid-template-columns: 1fr 1fr; margin-top: 10px; }}
          .tabs {{ display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 8px; margin-top: 10px; }}
          .tab-btn {{ border: 1px solid #b8cbdb; border-radius: 8px; background: #f4f9fd; color: #184968; padding: 8px; cursor: pointer; }}
          .tab-btn.active {{ background: #1d5f91; color: #fff; border-color: #1d5f91; }}
          .tab-view {{ display: none; margin-top: 10px; }}
          .tab-view.active {{ display: block; }}
          .k {{ font-size: 12px; color: var(--soft); }}
          .v {{ font-size: 30px; font-weight: 700; }}
          .chain {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; }}
          .node {{ background: #eef6fc; border: 1px solid #cbdceb; border-radius: 999px; padding: 4px 10px; }}
          table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
          th, td {{ border-bottom: 1px solid #e3edf5; padding: 6px; text-align: left; vertical-align: top; }}
          .meta {{ color: #d5ebfb; font-size: 12px; }}
          .meta-dark {{ color: var(--soft); font-size: 12px; }}
          .warn-row {{ background: #fff8e7; }}
          .btn {{ border: 1px solid #b8cbdb; border-radius: 8px; background: #f4f9fd; color: #184968; padding: 6px 8px; cursor: pointer; }}
          .field-warn {{ color: var(--warn); font-weight: 600; }}
          .tag-go {{ color: var(--ok); font-weight: 700; }}
          .tag-no {{ color: var(--danger); font-weight: 700; }}
          pre {{ background: #f8fbfe; border: 1px solid #dbe6ef; border-radius: 8px; padding: 8px; max-height: 260px; overflow: auto; }}
          @media (max-width: 1000px) {{ .row, .split {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <main class="wrap">
          <section class="hero">
            <h2 style="margin:0;">系统可观测性管理看板</h2>
            <div class="meta">目标：看得见、点得进、查得到 · env=<code>{escape(env)}</code></div>
            <div class="meta">最后刷新：<span id="asOf">-</span></div>
          </section>
          <section class="row">
            <article class="card"><div class="k">总测试数</div><div class="v" id="kTotal">0</div></article>
            <article class="card"><div class="k">执行数</div><div class="v" id="kExec">0</div></article>
            <article class="card"><div class="k">通过率</div><div class="v" id="kPassRate">0%</div></article>
            <article class="card"><div class="k">当前门槛结论</div><div class="v" id="kGate">-</div></article>
          </section>
          <section class="card" style="margin-top:10px;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <h3 style="margin:0;">首页摘要（测试结果 + 执行过程）</h3>
              <button class="btn" id="jumpSql">一键进入 SQL 交互查询</button>
            </div>
            <table style="margin-top:8px;">
              <thead><tr><th>摘要项</th><th>Owner</th><th>ETA</th><th>证据链接</th><th>状态</th></tr></thead>
              <tbody id="summaryRows"></tbody>
            </table>
          </section>
          <section class="tabs">
            <button class="tab-btn active" data-tab="tab-test">测试结果视图</button>
            <button class="tab-btn" data-tab="tab-process">执行过程视图</button>
            <button class="tab-btn" data-tab="tab-sql">SQL交互查询</button>
          </section>
          <section id="tab-test" class="tab-view active">
            <div class="split">
              <article class="card">
                <h3 style="margin:0 0 8px 0;">测试总览</h3>
                <table>
                  <tbody id="testOverviewRows"></tbody>
                </table>
              </article>
              <article class="card">
                <h3 style="margin:0 0 8px 0;">失败分类</h3>
                <table>
                  <thead><tr><th>failure_type</th><th>severity</th><th>retryable</th><th>gate_impact</th><th>证据</th></tr></thead>
                  <tbody id="failureRows"></tbody>
                </table>
              </article>
            </div>
            <article class="card" style="margin-top:10px;">
              <h3 style="margin:0 0 8px 0;">分层门槛状态（工作包/工作线/项目）</h3>
              <table>
                <thead><tr><th>scope</th><th>id</th><th>gate_status</th><th>Owner</th><th>ETA</th><th>证据</th></tr></thead>
                <tbody id="layerRows"></tbody>
              </table>
            </article>
          </section>
          <section id="tab-process" class="tab-view">
            <article class="card">
              <h3 style="margin:0 0 8px 0;">流程链路</h3>
              <div class="chain" id="chainNodes"></div>
            </article>
            <article class="card" style="margin-top:10px;">
              <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                <h3 style="margin:0;">执行过程字段</h3>
                <label class="meta-dark">工作线
                  <select id="filterOwnerLine"></select>
                </label>
                <label class="meta-dark">工作包
                  <select id="filterWorkpackage"></select>
                </label>
                <button class="btn" id="applyFilters">筛选</button>
              </div>
              <table style="margin-top:8px;">
                <thead><tr><th>task_batch_id</th><th>workpackage_id</th><th>status</th><th>progress</th><th>owner</th><th>eta</th><th>updated_at</th><th>证据</th></tr></thead>
                <tbody id="processRows"></tbody>
              </table>
            </article>
            <article class="card" style="margin-top:10px;">
              <h3 style="margin:0 0 8px 0;">最近事件时间线（倒序）</h3>
              <table>
                <thead><tr><th>time</th><th>event_type</th><th>workpackage_id</th><th>summary</th><th>operator</th><th>证据</th></tr></thead>
                <tbody id="timelineRows"></tbody>
              </table>
            </article>
          </section>
          <section id="tab-sql" class="tab-view">
            <article class="card">
              <h3 style="margin:0 0 8px 0;">只读 SQL 查询区</h3>
              <div class="meta-dark">只允许 SELECT/WITH；白名单表；LIMIT/超时/审计已启用。缺字段统一显示“-”。</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
                <div>
                  <label class="meta-dark">模板</label>
                  <select id="sqlTemplate" style="width:100%;"></select>
                </div>
                <div>
                  <label class="meta-dark">分页</label>
                  <div><input id="sqlPage" value="1" style="width:80px;" /> <input id="sqlPageSize" value="50" style="width:80px;" /> <button class="btn" id="runSql">执行</button></div>
                </div>
              </div>
              <textarea id="sqlText" style="width:100%;height:120px;margin-top:8px;"></textarea>
              <div class="meta-dark" id="sqlMeta"></div>
              <table style="margin-top:8px;">
                <thead id="sqlHead"></thead>
                <tbody id="sqlBody"></tbody>
              </table>
              <pre id="sqlError" style="display:none;"></pre>
            </article>
          </section>
        </main>
        <script>
          const v = (x) => (x === null || x === undefined || x === '' ? '-' : x);
          const fill = (id, val) => document.getElementById(id).textContent = val;
          const tabButtons = [...document.querySelectorAll('.tab-btn')];
          const tabViews = [...document.querySelectorAll('.tab-view')];
          tabButtons.forEach((btn) => btn.addEventListener('click', () => {{
            tabButtons.forEach((b) => b.classList.remove('active'));
            tabViews.forEach((view) => view.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
          }}));
          document.getElementById('jumpSql').addEventListener('click', () => {{
            document.querySelector('[data-tab="tab-sql"]').click();
          }});

          function warnClass(eta, evidence) {{
            return (!eta || !evidence) ? 'warn-row' : '';
          }}

          async function loadData() {{
            const ownerLine = encodeURIComponent(document.getElementById('filterOwnerLine').value || '');
            const wp = encodeURIComponent(document.getElementById('filterWorkpackage').value || '');
            const resp = await fetch(`/v1/governance/lab/observability/management/data?owner_line=${{ownerLine}}&workpackage_id=${{wp}}`);
            const data = await resp.json();
            fill('asOf', v(data.as_of));

            const t = data.test_overview || {{}};
            fill('kTotal', String(t.total || 0));
            fill('kExec', String(t.executed || 0));
            fill('kPassRate', `${{(Number(t.pass_rate || 0) * 100).toFixed(2)}}%`);
            fill('kGate', v(t.gate_decision));
            document.getElementById('kGate').className = String(t.gate_decision || '').toUpperCase() === 'GO' ? 'tag-go' : 'tag-no';

            const summaryRows = document.getElementById('summaryRows');
            summaryRows.innerHTML = '';
            const summaryItems = [
              {{ item: '测试结果摘要', owner: v(t.owner), eta: v(t.eta), evidence_ref: v(t.evidence_ref), status: v(t.gate_decision) }},
              {{ item: '执行过程摘要', owner: '可观测与运营指标线-Codex', eta: v((data.execution_process || {{}}).rows?.[0]?.eta), evidence_ref: v((data.execution_process || {{}}).rows?.[0]?.evidence_ref), status: '可追踪' }},
              {{ item: 'SQL交互能力', owner: '测试平台与质量门槛线-Codex', eta: '-', evidence_ref: '/v1/governance/lab/sql/templates', status: '只读' }},
            ];
            summaryItems.forEach((row) => {{
              const tr = document.createElement('tr');
              tr.className = warnClass(row.eta, row.evidence_ref);
              tr.innerHTML = `<td>${{v(row.item)}}</td><td>${{v(row.owner)}}</td><td>${{v(row.eta)}}</td><td><a href="${{v(row.evidence_ref)}}" target="_blank">${{v(row.evidence_ref)}}</a></td><td>${{v(row.status)}}</td>`;
              summaryRows.appendChild(tr);
            }});

            const testOverviewRows = document.getElementById('testOverviewRows');
            testOverviewRows.innerHTML = '';
            [
              ['total', t.total], ['executed', t.executed], ['passed', t.passed], ['failed', t.failed], ['skipped', t.skipped],
              ['pass_rate', `${{(Number(t.pass_rate || 0) * 100).toFixed(2)}}%`], ['quality_score', `${{Number(t.quality_score || 0).toFixed(2)}}`], ['last_run_at', t.last_run_at], ['gate_decision', t.gate_decision]
            ].forEach((pair) => {{
              const tr = document.createElement('tr');
              tr.innerHTML = `<td>${{pair[0]}}</td><td>${{v(pair[1])}}</td>`;
              testOverviewRows.appendChild(tr);
            }});

            const layerRows = document.getElementById('layerRows');
            layerRows.innerHTML = '';
            const layers = [];
            (data.gate_layers?.workpackage || []).forEach((x) => layers.push(x));
            (data.gate_layers?.workline || []).forEach((x) => layers.push({{ scope: 'workline', id: x.line_name, gate_status: x.status, owner: x.owner, eta: x.eta, evidence_ref: x.evidence_ref }}));
            (data.gate_layers?.project || []).forEach((x) => layers.push(x));
            layers.forEach((row) => {{
              const tr = document.createElement('tr');
              tr.className = warnClass(row.eta, row.evidence_ref);
              tr.innerHTML = `<td>${{v(row.scope)}}</td><td>${{v(row.id)}}</td><td>${{v(row.gate_status)}}</td><td>${{v(row.owner)}}</td><td>${{v(row.eta)}}</td><td><a href="${{v(row.evidence_ref)}}" target="_blank">${{v(row.evidence_ref)}}</a></td>`;
              layerRows.appendChild(tr);
            }});

            const failureRows = document.getElementById('failureRows');
            failureRows.innerHTML = '';
            (data.failure_classification || []).forEach((row) => {{
              const tr = document.createElement('tr');
              tr.className = warnClass(row.eta, row.evidence_ref);
              tr.innerHTML = `<td>${{v(row.failure_type)}}</td><td>${{v(row.severity)}}</td><td>${{v(row.retryable)}}</td><td>${{v(row.gate_impact)}}</td><td><a href="${{v(row.evidence_ref)}}" target="_blank">${{v(row.evidence_ref)}}</a></td>`;
              failureRows.appendChild(tr);
            }});

            const chainNodes = document.getElementById('chainNodes');
            chainNodes.innerHTML = '';
            (data.execution_process?.chain || []).forEach((s) => {{
              const span = document.createElement('span');
              span.className = 'node';
              span.textContent = s;
              chainNodes.appendChild(span);
            }});

            const processRows = document.getElementById('processRows');
            processRows.innerHTML = '';
            (data.execution_process?.rows || []).forEach((row) => {{
              const tr = document.createElement('tr');
              tr.className = warnClass(row.eta, row.evidence_ref);
              tr.innerHTML = `<td>${{v(row.task_batch_id)}}</td><td>${{v(row.workpackage_id)}}</td><td>${{v(row.status)}}</td><td>${{v(row.progress)}}</td><td>${{v(row.owner)}}</td><td>${{v(row.eta)}}</td><td>${{v(row.updated_at)}}</td><td><a href="${{v(row.evidence_ref)}}" target="_blank">${{v(row.evidence_ref)}}</a></td>`;
              processRows.appendChild(tr);
            }});

            const timelineRows = document.getElementById('timelineRows');
            timelineRows.innerHTML = '';
            (data.execution_process?.timeline || []).slice(0, 50).forEach((row) => {{
              const tr = document.createElement('tr');
              tr.innerHTML = `<td>${{v(row.time)}}</td><td>${{v(row.event_type)}}</td><td>${{v(row.workpackage_id)}}</td><td>${{v(row.summary)}}</td><td>${{v(row.operator)}}</td><td><a href="${{v(row.evidence_ref)}}" target="_blank">${{v(row.evidence_ref)}}</a></td>`;
              timelineRows.appendChild(tr);
            }});

            const ownerSel = document.getElementById('filterOwnerLine');
            const wpSel = document.getElementById('filterWorkpackage');
            if (!ownerSel.dataset.loaded) {{
              ownerSel.innerHTML = '<option value="">全部</option>' + (data.filters.owner_line_options || []).map((x) => `<option value="${{x}}">${{x}}</option>`).join('');
              ownerSel.value = data.filters.owner_line || '';
              ownerSel.dataset.loaded = '1';
            }}
            if (!wpSel.dataset.loaded) {{
              wpSel.innerHTML = '<option value="">全部</option>' + (data.filters.workpackage_options || []).map((x) => `<option value="${{x}}">${{x}}</option>`).join('');
              wpSel.value = data.filters.workpackage_id || '';
              wpSel.dataset.loaded = '1';
            }}
          }}

          async function loadSqlTemplates() {{
            const resp = await fetch('/v1/governance/lab/sql/templates');
            const data = await resp.json();
            const sel = document.getElementById('sqlTemplate');
            sel.innerHTML = (data.templates || []).map((t, idx) => `<option value="${{idx}}">${{t.name}}</option>`).join('');
            sel.addEventListener('change', () => {{
              const idx = Number(sel.value || 0);
              const item = (data.templates || [])[idx] || {{}};
              document.getElementById('sqlText').value = item.sql || '';
            }});
            if ((data.templates || []).length > 0) {{
              document.getElementById('sqlText').value = data.templates[0].sql || '';
            }}
            document.getElementById('sqlMeta').textContent = `whitelist=${{(data.whitelist_tables || []).join(',')}}; max_rows=${{data.max_rows}}; timeout=${{data.timeout_sec}}s`;
          }}

          async function runSql(pageDelta = 0) {{
            const sqlError = document.getElementById('sqlError');
            sqlError.style.display = 'none';
            const pageInput = document.getElementById('sqlPage');
            const pageSizeInput = document.getElementById('sqlPageSize');
            const payload = {{
              operator: 'observability_dashboard',
              sql: document.getElementById('sqlText').value,
              page: Math.max(1, Number(pageInput.value || 1) + pageDelta),
              page_size: Math.max(1, Number(pageSizeInput.value || 50)),
            }};
            pageInput.value = String(payload.page);
            const resp = await fetch('/v1/governance/lab/sql/query', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify(payload),
            }});
            const data = await resp.json();
            if (!resp.ok || !data.success) {{
              document.getElementById('sqlHead').innerHTML = '';
              document.getElementById('sqlBody').innerHTML = '';
              sqlError.style.display = 'block';
              sqlError.textContent = JSON.stringify(data.detail || data, null, 2);
              return;
            }}
            const cols = data.columns || [];
            document.getElementById('sqlHead').innerHTML = `<tr>${{cols.map((c) => `<th>${{c}}</th>`).join('')}}</tr>`;
            const tbody = document.getElementById('sqlBody');
            tbody.innerHTML = '';
            (data.rows || []).forEach((row) => {{
              const tr = document.createElement('tr');
              tr.innerHTML = cols.map((c) => `<td>${{v(row[c])}}</td>`).join('');
              tbody.appendChild(tr);
            }});
            document.getElementById('sqlMeta').textContent = `rows=${{data.total_rows}} returned=${{(data.rows || []).length}} elapsed_ms=${{data.elapsed_ms}} limit=${{data.effective_limit}}`;
          }}

          document.getElementById('applyFilters').addEventListener('click', async () => {{
            document.getElementById('filterOwnerLine').dataset.loaded = '';
            document.getElementById('filterWorkpackage').dataset.loaded = '';
            await loadData();
          }});
          document.getElementById('runSql').addEventListener('click', () => runSql(0));
          loadData();
          loadSqlTemplates();
          setInterval(loadData, 15000);
        </script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/lab/observability/management/data")
def observability_management_data(owner_line: str = "", workpackage_id: str = "") -> dict:
    return _build_management_observability_data(owner_line=owner_line, workpackage_id=workpackage_id)


@router.get("/lab/coverage/data")
def coverage_dashboard_data(
    case_id: str = "",
    result: str = "all",
    case_type: str = "all",
    city: str = "all",
    module: str = "all",
    module_outcome: str = "all",
    status: str = "all",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    report_path = _latest_cn_report_path()
    report = _load_json_file(report_path) if report_path else {}
    module_coverage = report.get("module_coverage", {}) if isinstance(report.get("module_coverage"), dict) else {}
    case_details = report.get("case_details", []) if isinstance(report.get("case_details"), list) else []
    result_values, case_types, cities = _coverage_filters(case_details)
    filtered_rows = _apply_case_filters(
        case_details=case_details,
        case_id_filter=case_id,
        result_filter=result,
        case_type_filter=case_type,
        city_filter=city,
        module_filter=module,
        module_outcome=module_outcome,
        status_filter=status,
    )
    page = max(1, int(page))
    page_size = max(1, min(200, int(page_size)))
    total_filtered = len(filtered_rows)
    start_idx = (page - 1) * page_size
    page_rows = filtered_rows[start_idx : start_idx + page_size]
    return {
        "report_path": str(report_path) if report_path else "",
        "generated_at": str(report.get("generated_at") or ""),
        "dataset": str(report.get("dataset") or ""),
        "rows_total": int(report.get("rows_total") or 0),
        "execution": report.get("execution", {}),
        "coverage_status": _coverage_status_payload(),
        "module_coverage": module_coverage,
        "case_summary": report.get("case_summary", {}),
        "filters": {
            "result_values": result_values,
            "case_types": case_types,
            "cities": cities,
            "status_values": ["completed"],
        },
        "query": {
            "case_id": case_id,
            "result": result,
            "case_type": case_type,
            "city": city,
            "module": module,
            "module_outcome": module_outcome,
            "status": status,
            "page": page,
            "page_size": page_size,
        },
        "pagination": {
            "total_filtered": total_filtered,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total_filtered + page_size - 1) // page_size),
        },
        "rows": page_rows,
    }


@router.get("/lab/coverage/view", response_class=HTMLResponse)
def coverage_dashboard_view(
    case_id: str = "",
    result: str = "all",
    case_type: str = "all",
    city: str = "all",
    module: str = "all",
    module_outcome: str = "all",
    status: str = "all",
    page: int = 1,
    page_size: int = 50,
) -> HTMLResponse:
    data = coverage_dashboard_data(
        case_id=case_id,
        result=result,
        case_type=case_type,
        city=city,
        module=module,
        module_outcome=module_outcome,
        status=status,
        page=page,
        page_size=page_size,
    )
    module_coverage = data.get("module_coverage", {})
    normalize_rate = (module_coverage.get("normalize") or {}).get("hit_rate", 0.0)
    parse_rates = (module_coverage.get("parse") or {}).get("field_hit_rate", {})
    match_rate = (module_coverage.get("match") or {}).get("hit_rate", 0.0)
    score_rate = (module_coverage.get("score") or {}).get("judgement_hit_rate", 0.0)
    dedup_stats = (module_coverage.get("dedup") or {})
    case_summary = data.get("case_summary", {}) if isinstance(data.get("case_summary"), dict) else {}
    overall_result_dist = case_summary.get("overall_result_distribution", {})
    case_type_dist = case_summary.get("case_type_distribution", {})
    city_dist = case_summary.get("city_distribution_top20", {})
    status_payload = data.get("coverage_status", {})
    pagination = data.get("pagination", {})
    query = data.get("query", {})

    conflict_resp = list_fengtu_conflicts(status="pending")
    pending_items = conflict_resp.items
    conflict_rows = []
    for item in pending_items:
        conflict_rows.append(
            "<tr>"
            f"<td>{escape(item.case_id)}</td>"
            f"<td>{escape(item.raw_text)}</td>"
            f"<td>{escape(item.expected_normalized)}</td>"
            f"<td>{escape(item.fengtu_candidate)}</td>"
            "<td>"
            f"<button onclick=\"decide('{escape(item.case_id)}','accept_expected')\">accept_expected</button> "
            f"<button onclick=\"decide('{escape(item.case_id)}','accept_fengtu')\">accept_fengtu</button> "
            f"<button onclick=\"decide('{escape(item.case_id)}','needs-investigation')\">needs-investigation</button>"
            "</td>"
            "</tr>"
        )
    conflict_html = "".join(conflict_rows) if conflict_rows else "<tr><td colspan='5'>No pending conflicts</td></tr>"

    row_html: list[str] = []
    for item in data.get("rows", []):
        if not isinstance(item, dict):
            continue
        module_result = item.get("module_result", {})
        row_html.append(
            "<tr>"
            f"<td>{escape(str(item.get('case_id') or ''))}</td>"
            f"<td>{escape(str(item.get('overall_result') or ''))}</td>"
            f"<td>{escape(str(item.get('case_type') or ''))}</td>"
            f"<td>{escape(str(item.get('city') or ''))}</td>"
            f"<td>{escape(str(item.get('status') or ''))}</td>"
            f"<td>{'Y' if bool((module_result or {}).get('normalize')) else 'N'}</td>"
            f"<td>{'Y' if bool((module_result or {}).get('parse')) else 'N'}</td>"
            f"<td>{'Y' if bool((module_result or {}).get('match')) else 'N'}</td>"
            f"<td>{'Y' if bool((module_result or {}).get('score')) else 'N'}</td>"
            f"<td>{float(item.get('confidence') or 0.0):.3f}</td>"
            f"<td>{escape(str(item.get('strategy') or ''))}</td>"
            f"<td>{escape(str(item.get('raw_text') or ''))}</td>"
            "</tr>"
        )
    case_rows = "".join(row_html) if row_html else "<tr><td colspan='12'>No rows for current filters</td></tr>"

    def _render_options(values: list[str], selected: str) -> str:
        options = ["<option value='all'>all</option>"]
        for value in values:
            sel = " selected" if value == selected else ""
            options.append(f"<option value='{escape(value)}'{sel}>{escape(value)}</option>")
        return "".join(options)

    result_options = _render_options(list(data.get("filters", {}).get("result_values", [])), str(query.get("result") or "all"))
    case_type_options = _render_options(list(data.get("filters", {}).get("case_types", [])), str(query.get("case_type") or "all"))
    city_options = _render_options(list(data.get("filters", {}).get("cities", [])), str(query.get("city") or "all"))
    status_options = _render_options(list(data.get("filters", {}).get("status_values", [])), str(query.get("status") or "all"))
    module_options = _render_options(["normalize", "parse", "match", "score"], str(query.get("module") or "all"))
    module_outcome_options = _render_options(["pass", "fail"], str(query.get("module_outcome") or "all"))

    running_refresh = ""
    if str(status_payload.get("status") or "") == "running":
        running_refresh = "<meta http-equiv='refresh' content='5' />"

    prev_page = max(1, int(query.get("page", 1)) - 1)
    next_page = min(int(pagination.get("total_pages", 1)), int(query.get("page", 1)) + 1)
    page_size_value = int(query.get("page_size", 50))
    query_prefix = (
        f"case_id={escape(str(query.get('case_id', '')))}"
        f"&result={escape(str(query.get('result', 'all')))}"
        f"&case_type={escape(str(query.get('case_type', 'all')))}"
        f"&city={escape(str(query.get('city', 'all')))}"
        f"&module={escape(str(query.get('module', 'all')))}"
        f"&module_outcome={escape(str(query.get('module_outcome', 'all')))}"
        f"&status={escape(str(query.get('status', 'all')))}"
        f"&page_size={page_size_value}"
    )

    html = f"""
    <html>
      <head>
        <title>Lab Coverage Dashboard</title>
        {running_refresh}
        <style>
          body {{ font-family: Helvetica, Arial, sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
          .card {{ background: #fff; border: 1px solid #d1d5db; border-radius: 8px; padding: 12px; margin-bottom: 16px; }}
          .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }}
          table {{ width: 100%; border-collapse: collapse; background: #fff; }}
          th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 13px; vertical-align: top; }}
          th {{ background: #e5e7eb; }}
          button {{ padding: 6px 10px; margin: 2px; font-size: 12px; }}
          .muted {{ color: #6b7280; font-size: 12px; }}
          .ok {{ color: #065f46; font-weight: 600; }}
          form.filter {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 8px; align-items: end; }}
          label {{ font-size: 12px; color: #374151; display: block; margin-bottom: 4px; }}
          select, input[type='number'] {{ width: 100%; padding: 6px; border: 1px solid #cbd5e1; border-radius: 6px; }}
          .toolbar {{ display: flex; gap: 8px; align-items: center; }}
          .mono {{ font-family: Menlo, Monaco, monospace; font-size: 12px; }}
        </style>
      </head>
      <body>
        <h1>Lab Coverage Dashboard</h1>
        <div class="card">
          <div class="toolbar">
            <button onclick="runCoverage()">Run Coverage</button>
            <a href="/v1/governance/lab/coverage/view">Reset Filters</a>
          </div>
          <div><b>Latest report</b>: <span class="muted">{escape(str(data.get("report_path") or ""))}</span></div>
          <div><b>Generated at</b>: <span class="muted">{escape(str(data.get("generated_at") or ""))}</span></div>
          <div><b>Dataset</b>: <span class="mono">{escape(str(data.get("dataset") or ""))}</span></div>
        </div>
        <div class="card">
          <h2>Execution Progress & Status</h2>
          <div class="grid">
            <div><b>status</b>: {escape(str(status_payload.get("status") or ""))}</div>
            <div><b>processed/total</b>: {int(status_payload.get("processed_rows") or 0)}/{int(status_payload.get("total_rows") or 0)}</div>
            <div><b>progress_rate</b>: {float(status_payload.get("progress_rate") or 0.0):.2%}</div>
            <div><b>updated_at</b>: {escape(str(status_payload.get("updated_at") or ""))}</div>
            <div><b>last_case_id</b>: {escape(str(status_payload.get("last_case_id") or ""))}</div>
            <div><b>message</b>: {escape(str(status_payload.get("message") or ""))}</div>
          </div>
        </div>
        <div class="card">
          <h2>All Cases Execution Statistics</h2>
          <div class="grid">
            <div><b>rows_total</b>: {int(data.get("rows_total") or 0)}</div>
            <div><b>pass/fail</b>: {int((overall_result_dist or {}).get("pass", 0))}/{int((overall_result_dist or {}).get("fail", 0))}</div>
            <div><b>pass_rate</b>: {(int((overall_result_dist or {}).get("pass", 0)) / max(1, int(data.get("rows_total") or 1))):.2%}</div>
          </div>
          <h3>Coverage Metrics</h3>
          <table>
            <thead><tr><th>module</th><th>metric</th><th>value</th></tr></thead>
            <tbody>
              <tr><td>normalize</td><td>hit_rate</td><td class="ok">{normalize_rate}</td></tr>
              <tr><td>parse</td><td>province/city/district/road/house_no</td><td>{escape(str(parse_rates))}</td></tr>
              <tr><td>match</td><td>hit_rate</td><td>{match_rate}</td></tr>
              <tr><td>dedup</td><td>dedup_exact_pass</td><td>{escape(str((dedup_stats or {}).get("dedup_exact_pass", False)).lower())}</td></tr>
              <tr><td>score</td><td>judgement_hit_rate</td><td class="ok">{score_rate}</td></tr>
            </tbody>
          </table>
          <div class="muted">case_type_distribution={escape(str(case_type_dist))}</div>
          <div class="muted">city_distribution_top20={escape(str(city_dist))}</div>
        </div>
        <div class="card">
          <h2>Case Details Query</h2>
          <form class="filter" method="get" action="/v1/governance/lab/coverage/view">
            <div><label>case_id</label><input type="text" name="case_id" value="{escape(str(query.get('case_id') or ''))}" /></div>
            <div><label>overall result</label><select name="result">{result_options}</select></div>
            <div><label>case type</label><select name="case_type">{case_type_options}</select></div>
            <div><label>city</label><select name="city">{city_options}</select></div>
            <div><label>module</label><select name="module">{module_options}</select></div>
            <div><label>module outcome</label><select name="module_outcome">{module_outcome_options}</select></div>
            <div><label>status</label><select name="status">{status_options}</select></div>
            <div><label>page_size</label><input type="number" min="1" max="200" name="page_size" value="{page_size_value}" /></div>
            <div><button type="submit">Apply Filters</button></div>
          </form>
          <div class="muted">filtered={int(pagination.get("total_filtered") or 0)}, page={int(pagination.get("page") or 1)}/{int(pagination.get("total_pages") or 1)}</div>
          <table>
            <thead>
              <tr>
                <th>case_id</th><th>result</th><th>type</th><th>city</th><th>status</th>
                <th>N</th><th>P</th><th>M</th><th>S</th><th>confidence</th><th>strategy</th><th>raw_text</th>
              </tr>
            </thead>
            <tbody>{case_rows}</tbody>
          </table>
          <div class="toolbar">
            <a href="/v1/governance/lab/coverage/view?{query_prefix}&page={prev_page}">Prev</a>
            <a href="/v1/governance/lab/coverage/view?{query_prefix}&page={next_page}">Next</a>
          </div>
        </div>
        <div class="card">
          <h2>Fengtu Conflicts (Pending)</h2>
          <div class="muted">operator is fixed to current owner for quick handling.</div>
          <table>
            <thead>
              <tr><th>case_id</th><th>raw_text</th><th>expected</th><th>fengtu</th><th>decision</th></tr>
            </thead>
            <tbody>
              {conflict_html}
            </tbody>
          </table>
        </div>
        <script>
          async function decide(caseId, decision) {{
            const res = await fetch(`/v1/governance/lab/trusted/fengtu/conflicts/${{caseId}}/decision`, {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ operator: 'huda', decision: decision, comment: 'confirmed in coverage dashboard' }})
            }});
            if (res.ok) {{
              window.location.reload();
            }} else {{
              const txt = await res.text();
              alert('decision failed: ' + txt);
            }}
          }}
          async function runCoverage() {{
            const res = await fetch('/v1/governance/lab/coverage/run', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ enable_fengtu: true }})
            }});
            const payload = await res.json();
            if (!res.ok || !payload.accepted) {{
              alert('run not started: ' + JSON.stringify(payload));
              return;
            }}
            window.location.reload();
          }}
        </script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/lab/sql/templates", response_model=LabSqlTemplatesResponse)
def list_lab_sql_templates() -> LabSqlTemplatesResponse:
    return LabSqlTemplatesResponse(
        templates=_sql_templates(),
        whitelist_tables=sorted(_SQL_ALLOWED_TABLES),
        max_rows=_SQL_MAX_ROWS,
        timeout_sec=_SQL_TIMEOUT_SEC,
    )


@router.get("/lab/sql/history", response_model=LabSqlHistoryResponse)
def list_lab_sql_history(limit: int = 50) -> LabSqlHistoryResponse:
    safe_limit = max(1, min(200, int(limit)))
    items = _load_sql_history()
    return LabSqlHistoryResponse(items=items[:safe_limit], total=len(items))


@router.post("/lab/sql/query", response_model=LabSqlQueryResponse)
def query_lab_sql(payload: LabSqlQueryRequest) -> LabSqlQueryResponse:
    sql_summary = _sanitize_sql_summary(payload.sql)
    limited_sql = ""
    effective_limit = 0
    started_at = time.perf_counter()
    try:
        limited_sql, _, effective_limit = _validate_readonly_sql(payload.sql)
        columns, fetched = _execute_lab_postgres_readonly(limited_sql, _SQL_TIMEOUT_SEC)

        total_rows = len(fetched)
        page = int(payload.page)
        page_size = int(payload.page_size)
        start_idx = (page - 1) * page_size
        page_rows = fetched[start_idx : start_idx + page_size]
        rows = []
        for row in page_rows:
            record: dict[str, Any] = {}
            for col in columns:
                value = row.get(col)
                record[col] = "-" if value is None else value
            rows.append(record)

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        history_item = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "operator": payload.operator,
            "sql_summary": sql_summary,
            "effective_limit": effective_limit,
            "total_rows": total_rows,
            "returned_rows": len(rows),
            "elapsed_ms": elapsed_ms,
            "status": "success",
        }
        _append_sql_history(history_item)
        REPOSITORY.log_audit_event(
            "tool_call",
            payload.operator,
            {
                "tool_name": "LabReadonlySQL",
                "sql_summary": sql_summary,
                "elapsed_ms": elapsed_ms,
                "total_rows": total_rows,
            },
        )
        return LabSqlQueryResponse(
            success=True,
            columns=columns,
            rows=rows,
            total_rows=total_rows,
            page=page,
            page_size=page_size,
            elapsed_ms=elapsed_ms,
            sql_summary=sql_summary,
            effective_limit=effective_limit,
        )
    except HTTPException as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        history_item = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "operator": payload.operator,
            "sql_summary": sql_summary,
            "effective_limit": effective_limit,
            "elapsed_ms": elapsed_ms,
            "status": "error",
            "code": str(detail.get("code") or "sql_error"),
            "message": str(detail.get("message") or ""),
        }
        _append_sql_history(history_item)
        REPOSITORY.log_audit_event(
            "tool_call",
            payload.operator,
            {
                "tool_name": "LabReadonlySQL",
                "sql_summary": sql_summary,
                "elapsed_ms": elapsed_ms,
                "status": "error",
                "code": history_item["code"],
            },
        )
        raise


@router.post("/lab/trusted/fengtu/conflicts/{case_id}/decision", response_model=FengtuConflictDecisionResponse)
def decide_fengtu_conflict(case_id: str, payload: FengtuConflictDecisionPayload) -> FengtuConflictDecisionResponse:
    case_key = str(case_id or "").strip()
    if not case_key:
        raise HTTPException(status_code=400, detail="case_id is required")

    decisions = _load_json_file(_CONFLICT_DECISIONS_PATH)
    items = decisions.get("items", {}) if isinstance(decisions.get("items"), dict) else {}
    decided_at = datetime.now(timezone.utc).isoformat()
    items[case_key] = {
        "decision": payload.decision,
        "comment": payload.comment,
        "operator": payload.operator,
        "decided_at": decided_at,
    }
    decisions["items"] = items
    _save_json_file(_CONFLICT_DECISIONS_PATH, decisions)

    REPOSITORY.log_audit_event(
        "approval_changed",
        payload.operator,
        {
            "target": "fengtu_conflict",
            "case_id": case_key,
            "decision": payload.decision,
            "comment": payload.comment,
        },
    )
    return FengtuConflictDecisionResponse(
        case_id=case_key,
        status="resolved",
        decision=payload.decision,
        comment=payload.comment,
        decided_by=payload.operator,
        decided_at=decided_at,
    )


def _run_task_sync(batch_id: str, ruleset_id: str, records: list[dict], queue_message: str) -> str:
    task_id = f"task_{uuid4().hex[:12]}"
    REPOSITORY.create_task(
        task_id=task_id,
        batch_name=batch_id,
        ruleset_id=ruleset_id,
        status="PENDING",
        queue_backend="sync",
        queue_message=queue_message,
    )

    original_strict = os.getenv("OPENHANDS_STRICT")
    if not original_strict:
        os.environ["OPENHANDS_STRICT"] = "0"
    try:
        run_governance_job(
            {
                "task_id": task_id,
                "batch_name": batch_id,
                "ruleset_id": ruleset_id,
                "records": records,
            }
        )
    finally:
        if original_strict is None:
            os.environ.pop("OPENHANDS_STRICT", None)
        else:
            os.environ["OPENHANDS_STRICT"] = original_strict
    return task_id


def _sample_deltas(baseline_run_id: str, candidate_run_id: str) -> tuple[list[LabSampleDelta], list[LabSampleDelta]]:
    baseline_items = {str(item.get("raw_id")): item for item in REPOSITORY.get_results(baseline_run_id)}
    candidate_items = {str(item.get("raw_id")): item for item in REPOSITORY.get_results(candidate_run_id)}
    shared_raw_ids = [raw_id for raw_id in baseline_items.keys() if raw_id in candidate_items]

    deltas: list[LabSampleDelta] = []
    for raw_id in shared_raw_ids:
        base = baseline_items[raw_id]
        cand = candidate_items[raw_id]
        base_conf = float(base.get("confidence", 0.0))
        cand_conf = float(cand.get("confidence", 0.0))
        evidence_items = []
        candidate_evidence = cand.get("evidence", {})
        if isinstance(candidate_evidence, dict):
            raw_items = candidate_evidence.get("items", [])
            if isinstance(raw_items, list):
                evidence_items = [item for item in raw_items if isinstance(item, dict)][:2]

        deltas.append(
            LabSampleDelta(
                raw_id=raw_id,
                baseline_confidence=base_conf,
                candidate_confidence=cand_conf,
                confidence_delta=round(cand_conf - base_conf, 6),
                baseline_strategy=str(base.get("strategy", "")),
                candidate_strategy=str(cand.get("strategy", "")),
                baseline_canon_text=str(base.get("canon_text", "")),
                candidate_canon_text=str(cand.get("canon_text", "")),
                evidence_summary=evidence_items,
            )
        )

    improved = sorted(
        [item for item in deltas if item.confidence_delta > 0],
        key=lambda x: x.confidence_delta,
        reverse=True,
    )[:3]
    worsened = sorted(
        [item for item in deltas if item.confidence_delta < 0],
        key=lambda x: x.confidence_delta,
    )[:3]
    return improved, worsened


def _render_sample_rows(samples: list[LabSampleDelta]) -> str:
    rows: list[str] = []
    for sample in samples:
        rows.append(
            "<tr>"
            f"<td>{escape(sample.raw_id)}</td>"
            f"<td>{sample.baseline_confidence:.3f}</td>"
            f"<td>{sample.candidate_confidence:.3f}</td>"
            f"<td>{sample.confidence_delta:+.3f}</td>"
            f"<td>{escape(sample.baseline_strategy)}</td>"
            f"<td>{escape(sample.candidate_strategy)}</td>"
            "</tr>"
        )
    return "".join(rows) if rows else "<tr><td colspan='6'>None</td></tr>"


def _render_scorecard_rows(scorecard: dict) -> str:
    baseline = scorecard.get("baseline", {})
    candidate = scorecard.get("candidate", {})
    delta = scorecard.get("delta", {})
    metric_order = [
        "auto_pass_rate",
        "review_rate",
        "human_required_rate",
        "consistency_score",
        "quality_gate_pass_rate",
        "review_accept_rate",
    ]
    rows: list[str] = []
    for key in metric_order:
        base = float(baseline.get(key, 0.0))
        cand = float(candidate.get(key, 0.0))
        diff = float(delta.get(key, 0.0))
        rows.append(
            "<tr>"
            f"<td>{escape(key)}</td>"
            f"<td>{base:.3f}</td>"
            f"<td>{cand:.3f}</td>"
            f"<td>{diff:+.3f}</td>"
            "</tr>"
        )
    return "".join(rows)


@router.post("/lab/optimize/{batch_id}", response_model=LabOptimizeResponse)
def optimize_batch(batch_id: str, payload: LabOptimizeRequest) -> LabOptimizeResponse:
    if payload.sample_spec.lower() != "sample":
        raise HTTPException(status_code=400, detail="lab optimize only supports sample_spec=sample")

    records = [record.model_dump() for record in payload.records[: payload.sample_size]]
    if not records:
        raise HTTPException(status_code=400, detail="records is required")

    active_ruleset_id = REPOSITORY.get_ops_summary().get("active_ruleset_id", "default")
    active_ruleset = REPOSITORY.get_ruleset(active_ruleset_id)
    if not active_ruleset:
        raise HTTPException(status_code=404, detail="active ruleset not found")

    REPOSITORY.log_audit_event(
        "agent_run_start",
        payload.caller,
        {
            "batch_id": batch_id,
            "active_ruleset_id": active_ruleset_id,
            "sample_spec": payload.sample_spec,
            "sample_size": len(records),
            "candidate_count": payload.candidate_count,
        },
    )

    REPOSITORY.log_audit_event(
        "tool_call",
        payload.caller,
        {"tool_name": "RunGovernance", "phase": "baseline", "batch_id": batch_id},
    )
    baseline_run_id = _run_task_sync(
        batch_id=batch_id,
        ruleset_id=active_ruleset_id,
        records=records,
        queue_message="lab_baseline_sync",
    )
    REPOSITORY.log_audit_event(
        "baseline_completed",
        payload.caller,
        {"batch_id": batch_id, "run_id": baseline_run_id, "ruleset_id": active_ruleset_id},
    )

    base_config = deepcopy(active_ruleset.get("config_json", {}))
    base_thresholds = deepcopy(base_config.get("thresholds", {}))
    base_t_low = float(base_thresholds.get("t_low", 0.6))
    base_t_high = float(base_thresholds.get("t_high", 0.85))
    candidate_deltas = [(0.0, -0.03), (0.02, -0.01), (-0.01, -0.04)]

    candidate_run_ids: list[str] = []
    candidate_rule_ids: list[str] = []
    scorecards: list[dict] = []
    for idx in range(payload.candidate_count):
        delta_high, delta_low = candidate_deltas[idx]
        candidate_t_high = _clamp(base_t_high + delta_high)
        candidate_t_low = _clamp(base_t_low + delta_low)
        if candidate_t_low >= candidate_t_high:
            candidate_t_low = max(0.0, round(candidate_t_high - 0.05, 6))

        candidate_ruleset_id = f"lab_{batch_id}_{idx + 1}_{uuid4().hex[:6]}"
        candidate_config = deepcopy(base_config)
        candidate_config["thresholds"] = {
            "t_high": round(candidate_t_high, 6),
            "t_low": round(candidate_t_low, 6),
        }
        REPOSITORY.upsert_ruleset(
            candidate_ruleset_id,
            {
                "version": f"lab-{idx + 1}",
                "is_active": False,
                "config_json": candidate_config,
            },
        )
        candidate_rule_ids.append(candidate_ruleset_id)

        REPOSITORY.log_audit_event(
            "tool_call",
            payload.caller,
            {
                "tool_name": "CreateRulesetCandidate",
                "batch_id": batch_id,
                "candidate_ruleset_id": candidate_ruleset_id,
            },
        )
        REPOSITORY.log_audit_event(
            "tool_call",
            payload.caller,
            {"tool_name": "RunGovernance", "phase": "candidate", "candidate_index": idx + 1},
        )
        run_id = _run_task_sync(
            batch_id=batch_id,
            ruleset_id=candidate_ruleset_id,
            records=records,
            queue_message=f"lab_candidate_sync_{idx + 1}",
        )
        candidate_run_ids.append(run_id)
        REPOSITORY.log_audit_event(
            "candidate_completed",
            payload.caller,
            {
                "batch_id": batch_id,
                "run_id": run_id,
                "candidate_ruleset_id": candidate_ruleset_id,
            },
        )

        REPOSITORY.log_audit_event(
            "tool_call",
            payload.caller,
            {"tool_name": "ComputeScorecard", "baseline_run_id": baseline_run_id, "candidate_run_id": run_id},
        )
        scorecard = REPOSITORY.compute_scorecard(
            baseline_task_id=baseline_run_id,
            candidate_task_id=run_id,
        )
        scorecards.append(scorecard)

    ranking = {"accept": 3, "needs-human": 2, "reject": 1}
    best_index = 0
    best_tuple = (-1, -1.0)
    for idx, scorecard in enumerate(scorecards):
        recommendation = str(scorecard.get("recommendation") or "needs-human")
        auto_pass_delta = float(scorecard.get("delta", {}).get("auto_pass_rate", 0.0))
        score_tuple = (ranking.get(recommendation, 0), auto_pass_delta)
        if score_tuple > best_tuple:
            best_tuple = score_tuple
            best_index = idx
    best_scorecard = scorecards[best_index]
    best_candidate_run_id = candidate_run_ids[best_index]
    best_candidate_ruleset_id = candidate_rule_ids[best_index]

    evidence_bullets = [
        f"recommendation={best_scorecard.get('recommendation')}",
        f"delta.auto_pass_rate={best_scorecard.get('delta', {}).get('auto_pass_rate', 0.0)}",
        f"delta.human_required_rate={best_scorecard.get('delta', {}).get('human_required_rate', 0.0)}",
    ]

    REPOSITORY.log_audit_event(
        "scorecard_computed",
        payload.caller,
        {
            "baseline_run_id": baseline_run_id,
            "candidate_run_id": best_candidate_run_id,
            "recommendation": best_scorecard.get("recommendation"),
        },
    )
    REPOSITORY.log_audit_event(
        "tool_call",
        payload.caller,
        {"tool_name": "CreateChangeRequest", "candidate_ruleset_id": best_candidate_ruleset_id},
    )
    change = REPOSITORY.create_change_request(
        {
            "from_ruleset_id": active_ruleset_id,
            "to_ruleset_id": best_candidate_ruleset_id,
            "baseline_task_id": baseline_run_id,
            "candidate_task_id": best_candidate_run_id,
            "diff": {"thresholds": REPOSITORY.get_ruleset(best_candidate_ruleset_id).get("config_json", {}).get("thresholds", {})},
            "scorecard": best_scorecard,
            "recommendation": best_scorecard.get("recommendation", "needs-human"),
            "evidence_bullets": evidence_bullets,
        }
    )

    return LabOptimizeResponse(
        baseline_run_id=baseline_run_id,
        candidate_run_ids=candidate_run_ids,
        change_id=change["change_id"],
        recommendation=change["recommendation"],
        top_evidence_bullets=evidence_bullets,
    )


@router.get("/lab/change_requests/{change_id}", response_model=LabReplayResponse)
def replay_change_request(change_id: str) -> LabReplayResponse:
    change = REPOSITORY.get_change_request(change_id)
    if not change:
        raise HTTPException(status_code=404, detail="change request not found")

    baseline_run_id = str(change.get("baseline_task_id"))
    candidate_run_id = str(change.get("candidate_task_id"))
    improved_samples, worsened_samples = _sample_deltas(baseline_run_id, candidate_run_id)
    run_refs = {baseline_run_id, candidate_run_id}
    audit_events: list[dict] = []
    for event in REPOSITORY.list_audit_events():
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        if event.get("related_change_id") == change_id:
            audit_events.append(event)
            continue
        if payload.get("run_id") in run_refs:
            audit_events.append(event)
            continue
        if payload.get("baseline_run_id") in run_refs:
            audit_events.append(event)
            continue
        if payload.get("candidate_run_id") in run_refs:
            audit_events.append(event)
            continue

    return LabReplayResponse(
        change_id=change_id,
        from_ruleset_id=str(change.get("from_ruleset_id")),
        to_ruleset_id=str(change.get("to_ruleset_id")),
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        recommendation=str(change.get("recommendation", "needs-human")),
        status=str(change.get("status", "pending")),
        scorecard=change.get("scorecard", {}),
        diff=change.get("diff", {}),
        evidence_bullets=list(change.get("evidence_bullets", [])),
        improved_samples=improved_samples,
        worsened_samples=worsened_samples,
        audit_events=audit_events,
        activation={
            "allowed": str(change.get("status", "")) == "approved",
            "endpoint": f"/v1/governance/rulesets/{change.get('to_ruleset_id')}/activate",
            "requires_admin": True,
            "change_id": change_id,
        },
    )


@router.get("/lab/change_requests/{change_id}/view", response_class=HTMLResponse)
def replay_change_request_view(change_id: str) -> HTMLResponse:
    replay = replay_change_request(change_id)
    score_rows = _render_scorecard_rows(replay.scorecard)
    improved_rows = _render_sample_rows(replay.improved_samples)
    worsened_rows = _render_sample_rows(replay.worsened_samples)
    diff_json = escape(str(replay.diff))
    audit_items = "".join(
        [
            (
                "<li>"
                f"{escape(str(event.get('created_at', '')))} | "
                f"{escape(str(event.get('event_type', '')))} | "
                f"{escape(str(event.get('caller', '')))}"
                "</li>"
            )
            for event in replay.audit_events
        ]
    )
    if not audit_items:
        audit_items = "<li>None</li>"

    html = f"""
    <html>
      <head>
        <title>Lab Replay {escape(replay.change_id)}</title>
        <style>
          body {{ font-family: 'Helvetica Neue', Helvetica, sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
          h1, h2 {{ margin: 12px 0; }}
          .meta {{ background: #ffffff; border: 1px solid #d1d5db; padding: 12px; border-radius: 8px; }}
          table {{ width: 100%; border-collapse: collapse; margin: 10px 0 18px; background: #ffffff; }}
          th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; font-size: 14px; }}
          th {{ background: #e5e7eb; }}
          pre {{ background: #111827; color: #e5e7eb; padding: 12px; border-radius: 8px; overflow-x: auto; }}
        </style>
      </head>
      <body>
        <h1>Lab Change Request Replay</h1>
        <div class="meta">
          <div><b>change_id</b>: {escape(replay.change_id)}</div>
          <div><b>status</b>: {escape(replay.status)}</div>
          <div><b>recommendation</b>: {escape(replay.recommendation)}</div>
          <div><b>from_ruleset</b>: {escape(replay.from_ruleset_id)} -> <b>to_ruleset</b>: {escape(replay.to_ruleset_id)}</div>
          <div><b>baseline_run</b>: {escape(replay.baseline_run_id)} | <b>candidate_run</b>: {escape(replay.candidate_run_id)}</div>
          <div><b>activate_allowed</b>: {str(replay.activation.get("allowed", False)).lower()}</div>
        </div>
        <h2>Scorecard</h2>
        <table>
          <thead><tr><th>metric</th><th>baseline</th><th>candidate</th><th>delta</th></tr></thead>
          <tbody>{score_rows}</tbody>
        </table>
        <h2>Ruleset Diff</h2>
        <pre>{diff_json}</pre>
        <h2>Improved Samples (Top 3)</h2>
        <table>
          <thead><tr><th>raw_id</th><th>baseline_conf</th><th>candidate_conf</th><th>delta</th><th>baseline_strategy</th><th>candidate_strategy</th></tr></thead>
          <tbody>{improved_rows}</tbody>
        </table>
        <h2>Worsened Samples (Top 3)</h2>
        <table>
          <thead><tr><th>raw_id</th><th>baseline_conf</th><th>candidate_conf</th><th>delta</th><th>baseline_strategy</th><th>candidate_strategy</th></tr></thead>
          <tbody>{worsened_rows}</tbody>
        </table>
        <h2>Audit Events</h2>
        <ul>{audit_items}</ul>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
