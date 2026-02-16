from __future__ import annotations

import os
import re
import time
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from services.governance_api.app.models.ops_models import (
    OpsSummaryResponse,
    ReadOnlySqlQueryRequest,
    ReadOnlySqlQueryResponse,
    ScorecardCompareResponse,
)
from services.governance_api.app.repositories.governance_repository import REPOSITORY

router = APIRouter()

_DISALLOWED_SQL_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|attach|detach|pragma|vacuum|reindex|replace)\b",
    re.IGNORECASE,
)
_TABLE_REF_PATTERN = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", re.IGNORECASE)
_CTE_PATTERN = re.compile(
    r"(?:\bwith(?:\s+recursive)?\b|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*\([^)]*\))?\s+as\s*\(",
    re.IGNORECASE,
)
_LIMIT_PATTERN = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)


def _whitelist_tables() -> set[str]:
    env_value = os.getenv("READONLY_SQL_TABLE_WHITELIST", "").strip()
    if env_value:
        return {item.strip().lower() for item in env_value.split(",") if item.strip()}
    return {
        "addr_batch",
        "addr_task_run",
        "addr_raw",
        "addr_canonical",
        "addr_review",
        "addr_ruleset",
        "addr_change_request",
        "addr_audit_event",
        "api_audit_log",
        "process_definition",
        "process_version",
        "task_run",
        "task_step_run",
        "task_output_json",
        "operation_audit",
        "confirmation_record",
    }


def _validate_readonly_sql(raw_sql: str) -> tuple[str, list[str]]:
    sql = str(raw_sql or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail={"code": "SQL_EMPTY", "message": "sql is required"})
    if sql.endswith(";"):
        sql = sql[:-1].strip()
    if ";" in sql:
        raise HTTPException(status_code=400, detail={"code": "SQL_MULTI_STATEMENT", "message": "multiple statements are not allowed"})

    lowered = sql.lower().lstrip()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise HTTPException(status_code=400, detail={"code": "SQL_READONLY_ONLY", "message": "only SELECT/WITH queries are allowed"})
    if _DISALLOWED_SQL_KEYWORDS.search(sql):
        raise HTTPException(status_code=400, detail={"code": "SQL_KEYWORD_BLOCKED", "message": "query contains blocked keyword"})

    cte_names = {name.lower() for name in _CTE_PATTERN.findall(sql)}
    table_refs = [value.split(".")[-1].lower() for value in _TABLE_REF_PATTERN.findall(sql)]
    table_refs = [table for table in table_refs if table not in cte_names]
    whitelist = _whitelist_tables()
    denied = [table for table in table_refs if table not in whitelist]
    if denied:
        raise HTTPException(
            status_code=403,
            detail={"code": "SQL_TABLE_NOT_ALLOWED", "message": f"table not allowed: {sorted(set(denied))}"},
        )
    return sql, sorted(set(table_refs))


def _apply_limit(sql: str, limit: int) -> str:
    found = _LIMIT_PATTERN.search(sql)
    if found:
        existing_limit = int(found.group(1))
        if existing_limit <= limit:
            return sql
    return f"SELECT * FROM ({sql}) AS _panel_readonly_query LIMIT {int(limit)}"


def _readonly_postgres_dsn() -> str:
    dsn = str(os.getenv("DATABASE_URL") or os.getenv("READONLY_DATABASE_URL") or "").strip()
    if not dsn.startswith("postgresql"):
        raise HTTPException(
            status_code=500,
            detail={"code": "PG_DSN_MISSING", "message": "DATABASE_URL (postgresql://...) is required in PG-only mode"},
        )
    return dsn


def _execute_postgres_readonly(sql: str, timeout_ms: int) -> tuple[list[str], list[dict[str, Any]], int]:
    started = time.monotonic()
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(_readonly_postgres_dsn(), row_factory=dict_row)
    try:
        with conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {int(timeout_ms)}")
            cur.execute("SET search_path TO control_plane, address_line, trust_meta, trust_db, public")
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [str(getattr(col, "name", col[0])) for col in (cur.description or [])]
            payload_rows = [dict(row) for row in rows]
        elapsed_ms = int((time.monotonic() - started) * 1000.0)
        return columns, payload_rows, elapsed_ms
    except Exception as exc:
        if "canceling statement due to statement timeout" in str(exc).lower():
            raise HTTPException(status_code=408, detail={"code": "SQL_TIMEOUT", "message": "query timeout"}) from exc
        raise HTTPException(status_code=400, detail={"code": "SQL_EXECUTION_ERROR", "message": str(exc)}) from exc
    finally:
        conn.close()


@router.get("/ops/summary", response_model=OpsSummaryResponse)
def get_ops_summary(
    task_id: Optional[str] = Query(default=None),
    batch_name: Optional[str] = Query(default=None),
    ruleset_id: Optional[str] = Query(default=None),
    status: Optional[List[str]] = Query(default=None),
    recent_hours: Optional[int] = Query(default=None, ge=0),
    t_low: Optional[float] = Query(default=None, ge=0, le=1),
    t_high: Optional[float] = Query(default=None, ge=0, le=1),
) -> OpsSummaryResponse:
    return OpsSummaryResponse(
        **REPOSITORY.get_ops_summary(
            task_id=task_id,
            batch_name=batch_name,
            ruleset_id=ruleset_id,
            status_list=status,
            recent_hours=recent_hours,
            t_low_override=t_low,
            t_high_override=t_high,
        )
    )


@router.get("/ops/scorecard", response_model=ScorecardCompareResponse)
def get_ops_scorecard(
    baseline_task_id: str = Query(..., min_length=1),
    candidate_task_id: str = Query(..., min_length=1),
    t_low: Optional[float] = Query(default=None, ge=0, le=1),
    t_high: Optional[float] = Query(default=None, ge=0, le=1),
) -> ScorecardCompareResponse:
    return ScorecardCompareResponse(
        **REPOSITORY.compute_scorecard(
            baseline_task_id=baseline_task_id,
            candidate_task_id=candidate_task_id,
            t_low_override=t_low,
            t_high_override=t_high,
        )
    )


@router.post("/ops/sql/read-only-query", response_model=ReadOnlySqlQueryResponse)
def run_readonly_sql_query(payload: ReadOnlySqlQueryRequest) -> ReadOnlySqlQueryResponse:
    try:
        validated_sql, table_refs = _validate_readonly_sql(payload.sql)
        limited_sql = _apply_limit(validated_sql, payload.limit)
        columns, rows, elapsed_ms = _execute_postgres_readonly(limited_sql, payload.timeout_ms)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        REPOSITORY.log_audit_event(
            "readonly_sql_query_blocked",
            payload.caller,
            {
                "sql_preview": str(payload.sql)[:300],
                "limit": payload.limit,
                "timeout_ms": payload.timeout_ms,
                "error_code": str(detail.get("code") or "SQL_BLOCKED"),
                "error_message": str(detail.get("message") or "query blocked"),
                "datasource": "postgres",
            },
        )
        raise

    REPOSITORY.log_audit_event(
        "readonly_sql_query_executed",
        payload.caller,
        {
            "tables": table_refs,
            "row_count": len(rows),
            "elapsed_ms": elapsed_ms,
            "limit": payload.limit,
            "timeout_ms": payload.timeout_ms,
            "sql_preview": validated_sql[:300],
            "datasource": "postgres",
        },
    )
    return ReadOnlySqlQueryResponse(
        status="ok",
        datasource="postgres",
        columns=columns,
        rows=rows,
        row_count=len(rows),
        elapsed_ms=elapsed_ms,
        applied_limit=payload.limit,
    )
