from __future__ import annotations

import hmac
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import HTMLResponse

from services.governance_api.app.models.observability_models import (
    ObservationAlert,
    ObservationAlertAckRequest,
    ObservationAlertsResponse,
    ObservationEventsResponse,
    ObservationSnapshotResponse,
    ObservationTimeseriesResponse,
    ObservationTraceReplayResponse,
)
from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE, GovernanceGateError

router = APIRouter()


def _resolve_role(role: str, x_role: Optional[str]) -> str:
    resolved = str(x_role or role or "viewer").strip().lower()
    if resolved not in {"viewer", "oncall", "admin"}:
        raise HTTPException(status_code=403, detail={"code": "ROLE_FORBIDDEN", "message": "role is not allowed"})
    return resolved


def _require_role(role: str, allowed: set[str]) -> None:
    if role not in allowed:
        raise HTTPException(
            status_code=403,
            detail={"code": "ROLE_FORBIDDEN", "message": f"role '{role}' is not allowed for this operation"},
        )


def _token_for_role(role: str) -> str:
    if role == "admin":
        return str(os.getenv("OBSERVABILITY_ADMIN_TOKEN") or "").strip()
    if role == "oncall":
        return str(os.getenv("OBSERVABILITY_ONCALL_TOKEN") or "").strip()
    return ""


def _resolve_effective_role(
    role: str,
    x_role: Optional[str],
    x_observability_token: Optional[str],
) -> str:
    requested = _resolve_role(role, x_role)
    if requested == "viewer":
        return "viewer"
    configured_token = _token_for_role(requested)
    if not configured_token:
        return "viewer"
    incoming = str(x_observability_token or "").strip()
    if incoming and hmac.compare_digest(incoming, configured_token):
        return requested
    return "viewer"


def _mask_text(text: str) -> str:
    raw = str(text or "")
    if len(raw) <= 4:
        return "*" * len(raw)
    return f"{raw[:2]}***{raw[-2:]}"


def _mask_object(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = str(k).lower()
            if key in {"name", "phone", "mobile", "id_card", "idcard", "email"}:
                out[k] = _mask_text(str(v))
            else:
                out[k] = _mask_object(v)
        return out
    if isinstance(value, list):
        return [_mask_object(item) for item in value]
    if isinstance(value, str) and len(value) >= 6:
        return _mask_text(value)
    return value


@router.get("/observability/snapshot", response_model=ObservationSnapshotResponse)
def get_observability_snapshot(env: str = Query(default="dev")) -> ObservationSnapshotResponse:
    payload = GOVERNANCE_SERVICE.get_observability_snapshot(env=env)
    return ObservationSnapshotResponse(**payload)


@router.get("/observability/events", response_model=ObservationEventsResponse)
def list_observability_events(
    trace_id: str = Query(default=""),
    task_id: str = Query(default=""),
    status: str = Query(default=""),
    event_type: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=1000),
) -> ObservationEventsResponse:
    items = GOVERNANCE_SERVICE.list_observation_events(
        trace_id=trace_id,
        task_id=task_id,
        status=status,
        event_type=event_type,
        limit=limit,
    )
    return ObservationEventsResponse(total=len(items), items=items)


@router.get("/observability/traces/{trace_id}/replay", response_model=ObservationTraceReplayResponse)
def get_trace_replay(trace_id: str, limit: int = Query(default=500, ge=1, le=2000)) -> ObservationTraceReplayResponse:
    timeline = GOVERNANCE_SERVICE.get_trace_replay(trace_id=trace_id, limit=limit)
    if not timeline:
        raise HTTPException(status_code=404, detail="trace not found")
    return ObservationTraceReplayResponse(trace_id=trace_id, total=len(timeline), timeline=timeline)


@router.get("/observability/timeseries", response_model=ObservationTimeseriesResponse)
def get_metric_timeseries(metric_name: str = Query(..., min_length=1), limit: int = Query(default=200, ge=1, le=1000)) -> ObservationTimeseriesResponse:
    points = GOVERNANCE_SERVICE.query_observation_metric_series(metric_name=metric_name, limit=limit)
    return ObservationTimeseriesResponse(metric_name=metric_name, total=len(points), points=points)


@router.get("/observability/alerts", response_model=ObservationAlertsResponse)
def list_alerts(status: str = Query(default=""), limit: int = Query(default=200, ge=1, le=1000)) -> ObservationAlertsResponse:
    items = GOVERNANCE_SERVICE.list_observation_alerts(status=status, limit=limit)
    return ObservationAlertsResponse(total=len(items), items=items)


@router.post("/observability/alerts/{alert_id}/ack", response_model=ObservationAlert)
def ack_alert(
    alert_id: str,
    payload: ObservationAlertAckRequest,
    role: str = Query(default="viewer"),
    actor: str = Query(default=""),
    x_observability_role: Optional[str] = Header(default=None),
    x_observability_token: Optional[str] = Header(default=None),
) -> ObservationAlert:
    resolved_role = _resolve_effective_role(role, x_observability_role, x_observability_token)
    _require_role(resolved_role, {"oncall", "admin"})
    acked = GOVERNANCE_SERVICE.ack_observation_alert(alert_id=alert_id, actor=payload.actor)
    if not acked:
        raise HTTPException(status_code=404, detail="alert not found")
    GOVERNANCE_SERVICE.log_audit_event(
        event_type="runtime_alert_ack",
        caller=str(actor or payload.actor or "unknown"),
        payload={"alert_id": alert_id, "role": resolved_role},
    )
    return ObservationAlert(**acked)


@router.get("/observability/runtime/summary")
def get_runtime_summary(
    window: str = Query(default="24h"),
    ruleset_id: str = Query(default=""),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_summary(window=window, ruleset_id=ruleset_id)


@router.get("/observability/runtime/risk-distribution")
def get_runtime_risk_distribution(window: str = Query(default="24h")) -> dict:
    return GOVERNANCE_SERVICE.runtime_risk_distribution(window=window)


@router.get("/observability/runtime/reliability/summary")
def get_runtime_reliability_summary(window: str = Query(default="24h")) -> dict:
    return GOVERNANCE_SERVICE.runtime_reliability_summary(window=window)


@router.post("/observability/runtime/reliability/evaluate")
def evaluate_runtime_reliability(window: str = Query(default="24h"), suppress_minutes: int = Query(default=30, ge=1, le=240)) -> dict:
    return GOVERNANCE_SERVICE.runtime_reliability_evaluate(window=window, suppress_minutes=suppress_minutes)


@router.get("/observability/runtime/freshness-latency/summary")
def get_runtime_freshness_latency_summary(
    window: str = Query(default="24h"),
    ruleset_id: str = Query(default=""),
    status: str = Query(default=""),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_freshness_latency_summary(window=window, ruleset_id=ruleset_id, status=status)


@router.post("/observability/runtime/freshness-latency/evaluate")
def evaluate_runtime_freshness_latency(
    window: str = Query(default="24h"),
    ruleset_id: str = Query(default=""),
    status: str = Query(default=""),
    suppress_minutes: int = Query(default=30, ge=1, le=240),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_freshness_latency_evaluate(
        window=window,
        ruleset_id=ruleset_id,
        status=status,
        suppress_minutes=suppress_minutes,
    )


@router.get("/observability/runtime/quality-drift/summary")
def get_runtime_quality_drift_summary(
    window: str = Query(default="24h"),
    ruleset_id: str = Query(default=""),
    status: str = Query(default=""),
    baseline_profile: str = Query(default="rolling-7d"),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_quality_drift_summary(
        window=window,
        ruleset_id=ruleset_id,
        status=status,
        baseline_profile=baseline_profile,
    )


@router.post("/observability/runtime/quality-drift/evaluate")
def evaluate_runtime_quality_drift(
    window: str = Query(default="24h"),
    ruleset_id: str = Query(default=""),
    status: str = Query(default=""),
    baseline_profile: str = Query(default="rolling-7d"),
    suppress_minutes: int = Query(default=30, ge=1, le=240),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_quality_drift_evaluate(
        window=window,
        ruleset_id=ruleset_id,
        status=status,
        baseline_profile=baseline_profile,
        suppress_minutes=suppress_minutes,
    )


@router.get("/observability/runtime/performance/summary")
def get_runtime_performance_summary(
    window: str = Query(default="24h"),
    aggregate_threshold_ms: float = Query(default=1500.0, gt=0),
    detail_threshold_ms: float = Query(default=800.0, gt=0),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_performance_summary(
        window=window,
        aggregate_threshold_ms=aggregate_threshold_ms,
        detail_threshold_ms=detail_threshold_ms,
    )


@router.post("/observability/runtime/performance/evaluate")
def evaluate_runtime_performance(
    window: str = Query(default="24h"),
    aggregate_threshold_ms: float = Query(default=1500.0, gt=0),
    detail_threshold_ms: float = Query(default=800.0, gt=0),
    suppress_minutes: int = Query(default=30, ge=1, le=240),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_performance_evaluate(
        window=window,
        aggregate_threshold_ms=aggregate_threshold_ms,
        detail_threshold_ms=detail_threshold_ms,
        suppress_minutes=suppress_minutes,
    )


@router.get("/observability/runtime/version-compare")
def get_runtime_version_compare(
    baseline: str = Query(..., min_length=1),
    candidate: str = Query(..., min_length=1),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_version_compare(baseline=baseline, candidate=candidate)


@router.get("/observability/runtime/tasks")
def list_runtime_tasks(
    window: str = Query(default="24h"),
    status: str = Query(default=""),
    ruleset_id: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    page: int = Query(default=1, ge=1),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_tasks(
        window=window,
        status=status,
        ruleset_id=ruleset_id,
        limit=limit,
        page=page,
    )


@router.get("/observability/runtime/workpackage-pipeline")
def get_runtime_workpackage_pipeline(
    window: str = Query(default="24h"),
    client_type: str = Query(default=""),
) -> dict:
    return GOVERNANCE_SERVICE.runtime_workpackage_pipeline(window=window, client_type=client_type)


@router.get("/observability/runtime/workpackage-events")
def get_runtime_workpackage_events(
    workpackage_id: str = Query(..., min_length=1),
    version: str = Query(default=""),
    window: str = Query(default="24h"),
    client_type: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict:
    try:
        return GOVERNANCE_SERVICE.runtime_workpackage_events(
            workpackage_id=workpackage_id,
            version=version,
            window=window,
            client_type=client_type,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ARGUMENT", "message": str(exc)}) from exc


@router.get("/observability/runtime/llm-interactions")
def get_runtime_llm_interactions(
    window: str = Query(default="24h"),
    workpackage_id: str = Query(default=""),
    version: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
    role: str = Query(default="viewer"),
    actor: str = Query(default=""),
    x_observability_role: Optional[str] = Header(default=None),
    x_observability_token: Optional[str] = Header(default=None),
) -> dict:
    resolved_role = _resolve_effective_role(role, x_observability_role, x_observability_token)
    payload = GOVERNANCE_SERVICE.runtime_llm_interactions(
        window=window,
        workpackage_id=workpackage_id,
        version=version,
        limit=limit,
    )
    samples = payload.get("samples") if isinstance(payload.get("samples"), list) else []
    if resolved_role != "admin":
        masked_samples = []
        for item in samples:
            if not isinstance(item, dict):
                continue
            cloned = dict(item)
            cloned["prompt"] = _mask_text(str(item.get("prompt") or ""))
            cloned["response"] = _mask_text(str(item.get("response") or ""))
            masked_samples.append(cloned)
        payload["samples"] = masked_samples
    GOVERNANCE_SERVICE.log_audit_event(
        event_type="runtime_llm_interactions_access",
        caller=str(actor or "anonymous"),
        payload={
            "role": resolved_role,
            "workpackage_id": str(workpackage_id or ""),
            "version": str(version or ""),
            "limit": int(limit),
        },
    )
    return payload


@router.get("/observability/runtime/tasks/{task_id}/detail")
def get_runtime_task_detail(
    task_id: str,
    role: str = Query(default="viewer"),
    actor: str = Query(default=""),
    x_observability_role: Optional[str] = Header(default=None),
    x_observability_token: Optional[str] = Header(default=None),
) -> dict:
    resolved_role = _resolve_effective_role(role, x_observability_role, x_observability_token)
    detail = GOVERNANCE_SERVICE.runtime_task_detail(task_id=task_id)
    if not detail:
        raise HTTPException(status_code=404, detail="task not found")
    GOVERNANCE_SERVICE.log_audit_event(
        event_type="runtime_detail_access",
        caller=str(actor or "anonymous"),
        payload={"task_id": task_id, "role": resolved_role},
    )
    if resolved_role != "admin":
        source_data = detail.get("source_data") if isinstance(detail.get("source_data"), list) else []
        for item in source_data:
            if isinstance(item, dict):
                item["raw_text"] = _mask_text(str(item.get("raw_text") or ""))
        results = detail.get("governance_results") if isinstance(detail.get("governance_results"), list) else []
        for item in results:
            if isinstance(item, dict):
                item["canon_text"] = _mask_text(str(item.get("canon_text") or ""))
                item["evidence"] = _mask_object(item.get("evidence"))
        detail["source_data"] = source_data
        detail["governance_results"] = results
    return detail


@router.get("/observability/runtime/tasks/{task_id}/export")
def export_runtime_task_detail(
    task_id: str,
    role: str = Query(default="viewer"),
    actor: str = Query(default=""),
    x_observability_role: Optional[str] = Header(default=None),
    x_observability_token: Optional[str] = Header(default=None),
) -> dict:
    resolved_role = _resolve_effective_role(role, x_observability_role, x_observability_token)
    _require_role(resolved_role, {"admin"})
    detail = GOVERNANCE_SERVICE.runtime_task_detail(task_id=task_id)
    if not detail:
        raise HTTPException(status_code=404, detail="task not found")
    GOVERNANCE_SERVICE.log_audit_event(
        event_type="runtime_task_export",
        caller=str(actor or "anonymous"),
        payload={"task_id": task_id, "role": resolved_role},
    )
    return detail


@router.get("/observability/runtime/compliance/audit")
def list_runtime_compliance_audit(
    role: str = Query(default="viewer"),
    actor: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=2000),
    x_observability_role: Optional[str] = Header(default=None),
    x_observability_token: Optional[str] = Header(default=None),
) -> dict:
    resolved_role = _resolve_effective_role(role, x_observability_role, x_observability_token)
    _require_role(resolved_role, {"admin"})
    events = GOVERNANCE_SERVICE.list_audit_events()
    filtered = []
    for event in events:
        event_type = str(event.get("event_type") or "")
        if event_type.startswith("runtime_") or event_type.startswith("observation_alert_"):
            filtered.append(event)
        if len(filtered) >= int(limit):
            break
    GOVERNANCE_SERVICE.log_audit_event(
        event_type="runtime_compliance_audit_access",
        caller=str(actor or "anonymous"),
        payload={"role": resolved_role, "limit": int(limit)},
    )
    return {"total": len(filtered), "items": filtered}


@router.post("/observability/runtime/seed-demo")
def seed_runtime_demo(total: int = Query(default=60, ge=20, le=300)) -> dict:
    return GOVERNANCE_SERVICE.runtime_seed_demo_cases(total=total)


@router.post("/observability/runtime/seed-workpackage-demo")
def seed_runtime_workpackage_demo(total: int = Query(default=12, ge=3, le=200)) -> dict:
    return GOVERNANCE_SERVICE.runtime_seed_workpackage_demo_cases(total=total)


@router.post("/observability/runtime/upload-batch")
def upload_runtime_batch(payload: dict[str, Any]) -> dict:
    batch_name = str(payload.get("batch_name") or "runtime-upload-batch")
    ruleset_id = str(payload.get("ruleset_id") or "default")
    actor = str(payload.get("actor") or "runtime_upload")
    addresses_raw = payload.get("addresses")
    if not isinstance(addresses_raw, list):
        raise HTTPException(status_code=400, detail={"code": "INVALID_ADDRESSES", "message": "addresses must be array"})
    addresses = [str(item or "").strip() for item in addresses_raw if str(item or "").strip()]
    if not addresses:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ADDRESSES", "message": "addresses is empty"})
    try:
        return GOVERNANCE_SERVICE.submit_runtime_uploaded_batch(
            batch_name=batch_name,
            ruleset_id=ruleset_id,
            addresses=addresses,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": str(exc)}) from exc
    except GovernanceGateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.get("/observability/runtime/view", response_class=HTMLResponse)
def runtime_observability_view(window: str = Query(default="24h")) -> HTMLResponse:
    safe_window = str(window or "24h")
    html = f"""
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>系统运行态可观测总览</title>
    <style>
      :root {{
        --bg: #f4f7f9;
        --panel: #ffffff;
        --line: #d7e0e8;
        --ink: #0f2742;
        --muted: #526377;
        --blue: #0d6aa8;
        --green: #0e805a;
        --orange: #b06a12;
        --red: #b3261e;
      }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }}
      .wrap {{ max-width: 1400px; margin: 0 auto; padding: 14px; }}
      .hero {{
        background: linear-gradient(120deg, #11476e, #0d6aa8 60%, #1e8bb7);
        color: #fff;
        border-radius: 14px;
        padding: 18px;
      }}
      .hero p {{ margin: 8px 0 0; color: rgba(255, 255, 255, 0.88); }}
      .toolbar {{
        margin-top: 12px;
        display: grid;
        grid-template-columns: 140px 160px 160px 160px 1fr 1fr;
        gap: 10px;
      }}
      select, button {{
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 8px 10px;
        font-size: 14px;
        background: #fff;
      }}
      button {{
        background: var(--ink);
        color: #fff;
        border-color: var(--ink);
        cursor: pointer;
      }}
      .kpi {{
        margin-top: 12px;
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 10px;
      }}
      .card {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px;
      }}
      .k {{ font-size: 12px; color: var(--muted); }}
      .v {{ margin-top: 6px; font-weight: 700; font-size: 22px; }}
      .split {{
        margin-top: 12px;
        display: grid;
        grid-template-columns: 1.1fr 1fr 1fr;
        gap: 10px;
      }}
      .reliability {{
        margin-top: 12px;
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 10px;
      }}
      .panel-title {{ margin: 0 0 8px; font-size: 15px; }}
      ul {{
        margin: 0;
        padding: 0 0 0 18px;
      }}
      li {{ margin: 5px 0; color: var(--muted); }}
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }}
      th, td {{
        border-bottom: 1px solid var(--line);
        padding: 8px 6px;
        text-align: left;
      }}
      th {{ color: var(--muted); font-weight: 600; }}
      .status {{
        display: inline-block;
        min-width: 72px;
        text-align: center;
        padding: 3px 8px;
        border-radius: 999px;
        font-size: 12px;
      }}
      .SUCCEEDED {{ background: rgba(14,128,90,.12); color: var(--green); }}
      .BLOCKED {{ background: rgba(179,38,30,.12); color: var(--red); }}
      .REVIEWED {{ background: rgba(13,106,168,.12); color: var(--blue); }}
      .RUNNING {{ background: rgba(176,106,18,.12); color: var(--orange); }}
      .PENDING {{ background: rgba(82,99,119,.12); color: var(--muted); }}
      .muted {{ color: var(--muted); }}
      .task-link {{
        color: var(--blue);
        text-decoration: underline;
        cursor: pointer;
      }}
      .modal-mask {{
        position: fixed;
        inset: 0;
        background: rgba(9, 22, 38, 0.5);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 9999;
      }}
      .modal-mask.show {{
        display: flex;
      }}
      .modal {{
        width: min(1320px, calc(100vw - 32px));
        max-height: calc(100vh - 32px);
        overflow: auto;
        background: #fff;
        border-radius: 14px;
        border: 1px solid var(--line);
        padding: 12px;
      }}
      .modal-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
      }}
      .modal-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 10px;
      }}
      .modal-close {{
        background: #fff;
        color: var(--ink);
        border: 1px solid var(--line);
      }}
      pre {{
        white-space: pre-wrap;
        word-break: break-word;
        background: #f6f9fc;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 8px;
        color: #22354b;
        max-height: 340px;
        overflow: auto;
      }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <section class="hero">
        <h1 style="margin:0;">系统运行态可观测总览</h1>
        <p>只展示治理运行成果与质量，不展示研发过程指标。默认时间窗：<span id="windowLabel">{safe_window}</span></p>
      </section>

      <section class="toolbar">
        <select id="window">
          <option value="1h">近1小时</option>
          <option value="24h" selected>近24小时</option>
          <option value="7d">近7天</option>
          <option value="30d">近30天</option>
        </select>
        <select id="status">
          <option value="">全部状态</option>
          <option value="PENDING">PENDING</option>
          <option value="RUNNING">RUNNING</option>
          <option value="SUCCEEDED">SUCCEEDED</option>
          <option value="REVIEWED">REVIEWED</option>
          <option value="BLOCKED">BLOCKED</option>
          <option value="FAILED">FAILED</option>
        </select>
        <select id="ruleset">
          <option value="">全部规则集</option>
          <option value="default">default</option>
        </select>
        <select id="role">
          <option value="viewer">viewer(只读脱敏)</option>
          <option value="oncall">oncall(可ACK)</option>
          <option value="admin">admin(全量)</option>
        </select>
        <input id="roleToken" type="password" placeholder="输入 oncall/admin token（viewer 可留空）" />
        <button id="refreshBtn" type="button">刷新观测数据</button>
      </section>
      <section class="card" style="margin-top:12px;">
        <h2 class="panel-title">上传地址批次并执行任务</h2>
        <p class="muted" style="margin:0 0 8px;">支持 txt/csv/json 文本上传。每行一条地址，提交后自动创建并执行 task。</p>
        <div style="display:grid;grid-template-columns:220px 1fr 170px;gap:10px;">
          <input id="uploadFile" type="file" accept=".txt,.csv,.json,.jsonl,.ndjson,.log,.md" />
          <textarea id="uploadText" placeholder="粘贴地址（每行一条）" style="min-height:96px;border:1px solid var(--line);border-radius:10px;padding:8px;font-size:13px;"></textarea>
          <button id="uploadBtn" type="button">上传并执行</button>
        </div>
        <p id="uploadStatus" class="muted" style="margin:8px 0 0;">等待上传</p>
      </section>

      <section class="kpi">
        <article class="card"><div class="k">任务总数</div><div id="kTotal" class="v">-</div></article>
        <article class="card"><div class="k">完成率</div><div id="kSuccessRate" class="v">-</div></article>
        <article class="card"><div class="k">阻塞率</div><div id="kBlockedRate" class="v">-</div></article>
        <article class="card"><div class="k">平均置信度</div><div id="kConfidence" class="v">-</div></article>
        <article class="card"><div class="k">待审核积压</div><div id="kPendingReview" class="v">-</div></article>
        <article class="card"><div class="k">最近处理时间</div><div id="kLatest" class="v" style="font-size:14px;">-</div></article>
      </section>

      <section class="split">
        <article class="card">
          <h2 class="panel-title">置信度分层</h2>
          <ul id="confidenceBuckets"></ul>
        </article>
        <article class="card">
          <h2 class="panel-title">阻塞原因 Top5</h2>
          <ul id="blockedTop"></ul>
        </article>
        <article class="card">
          <h2 class="panel-title">低置信模式 Top5</h2>
          <ul id="lowPatternTop"></ul>
        </article>
      </section>

      <section class="reliability">
        <article class="card"><div class="k">可靠性-可用性</div><div id="rAvailability" class="v">-</div></article>
        <article class="card"><div class="k">可靠性-P95延迟</div><div id="rLatencyP95" class="v">-</div></article>
        <article class="card"><div class="k">可靠性-新鲜度(分钟)</div><div id="rFreshness" class="v">-</div></article>
        <article class="card"><div class="k">可靠性-正确性</div><div id="rCorrectness" class="v">-</div></article>
        <article class="card"><div class="k">SLO违约项</div><div id="rViolations" class="v">-</div></article>
        <article class="card"><div class="k">未ACK告警</div><div id="rOpenAlerts" class="v">-</div></article>
      </section>
      <section class="reliability">
        <article class="card"><div class="k">质量漂移异常数</div><div id="qAnomalies" class="v">-</div></article>
        <article class="card"><div class="k">覆盖率漂移</div><div id="qCoverageDelta" class="v">-</div></article>
        <article class="card"><div class="k">区划一致率漂移</div><div id="qDistrictDelta" class="v">-</div></article>
        <article class="card"><div class="k">低置信占比漂移</div><div id="qLowConfDelta" class="v">-</div></article>
        <article class="card"><div class="k">阻塞稳定性漂移</div><div id="qBlockedDelta" class="v">-</div></article>
        <article class="card"><div class="k">异常样本任务</div><div id="qSampleTask" class="v" style="font-size:14px;">-</div></article>
      </section>
      <section class="reliability">
        <article class="card"><div class="k">聚合查询耗时</div><div id="pAggregateMs" class="v">-</div></article>
        <article class="card"><div class="k">下钻查询耗时</div><div id="pDetailMs" class="v">-</div></article>
        <article class="card"><div class="k">性能违约数</div><div id="pViolations" class="v">-</div></article>
      </section>

      <section class="card" style="margin-top:12px;">
        <h2 class="panel-title">新增治理包链路观测</h2>
        <div style="display:flex;justify-content:flex-end;margin-bottom:8px;">
          <button id="seedWpBtn" type="button">灌入链路样例</button>
        </div>
        <div class="reliability" style="margin-top:0;">
          <article class="card"><div class="k">工作包总数</div><div id="wpTotal" class="v">-</div></article>
          <article class="card"><div class="k">端到端闭环率</div><div id="wpE2E" class="v">-</div></article>
          <article class="card"><div class="k">Runtime提交成功率</div><div id="wpSubmitRate" class="v">-</div></article>
        </div>
        <p id="wpSeedStatus" class="muted" style="margin:8px 0 0;">可点击“灌入链路样例”生成可观测数据</p>
        <table style="margin-top:8px;">
          <thead>
            <tr>
              <th>Workpackage ID</th>
              <th>Version</th>
              <th>Client</th>
              <th>当前阶段</th>
              <th>提交状态</th>
              <th>阶段数</th>
              <th>Skills</th>
              <th>Artifacts</th>
              <th>Checksum</th>
              <th>Runtime Receipt</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody id="workpackageRows">
            <tr><td colspan="11" class="muted">加载中...</td></tr>
          </tbody>
        </table>
      </section>

      <section class="card" style="margin-top:12px;">
        <h2 class="panel-title">任务明细</h2>
        <p class="muted" style="margin:0 0 8px;">点击 Task ID 可查看“源数据 / 治理成果 / 过程日志”。</p>
        <table>
          <thead>
            <tr>
              <th>Task ID</th>
              <th>状态</th>
              <th>规则集</th>
              <th>地址条数</th>
              <th>置信度</th>
              <th>策略</th>
              <th>审核状态</th>
              <th>更新时间</th>
            </tr>
          </thead>
          <tbody id="taskRows">
            <tr><td colspan="8" class="muted">加载中...</td></tr>
          </tbody>
        </table>
      </section>
    </div>
    <div id="wpModalMask" class="modal-mask">
      <section class="modal">
        <div class="modal-head">
          <h2 id="wpDetailTitle" class="panel-title" style="margin:0;">工作包链路事件</h2>
          <button id="closeWpModalBtn" class="modal-close" type="button">关闭</button>
        </div>
        <article class="card">
          <h2 class="panel-title">事件时间线（CLI / Agent / LLM / Runtime）</h2>
          <pre id="wpProcessLogs">请选择工作包</pre>
        </article>
      </section>
    </div>
    <div id="modalMask" class="modal-mask">
      <section class="modal">
        <div class="modal-head">
          <h2 id="detailTitle" class="panel-title" style="margin:0;">任务详情（批次）</h2>
          <button id="closeModalBtn" class="modal-close" type="button">关闭</button>
        </div>
        <div class="modal-grid">
          <article class="card">
            <h2 class="panel-title">源数据（输入）</h2>
            <pre id="sourceData">请选择任务</pre>
          </article>
          <article class="card">
            <h2 class="panel-title">治理成果（输出）</h2>
            <pre id="governanceData">请选择任务</pre>
          </article>
          <article class="card">
            <h2 class="panel-title">治理过程日志</h2>
            <pre id="processLogs">请选择任务</pre>
          </article>
        </div>
      </section>
    </div>
    <script>
      const els = {{
        window: document.getElementById("window"),
        status: document.getElementById("status"),
        ruleset: document.getElementById("ruleset"),
        role: document.getElementById("role"),
        roleToken: document.getElementById("roleToken"),
        refreshBtn: document.getElementById("refreshBtn"),
        uploadFile: document.getElementById("uploadFile"),
        uploadText: document.getElementById("uploadText"),
        uploadBtn: document.getElementById("uploadBtn"),
        uploadStatus: document.getElementById("uploadStatus"),
        windowLabel: document.getElementById("windowLabel"),
        kTotal: document.getElementById("kTotal"),
        kSuccessRate: document.getElementById("kSuccessRate"),
        kBlockedRate: document.getElementById("kBlockedRate"),
        kConfidence: document.getElementById("kConfidence"),
        kPendingReview: document.getElementById("kPendingReview"),
        kLatest: document.getElementById("kLatest"),
        confidenceBuckets: document.getElementById("confidenceBuckets"),
        blockedTop: document.getElementById("blockedTop"),
        lowPatternTop: document.getElementById("lowPatternTop"),
        taskRows: document.getElementById("taskRows"),
        rAvailability: document.getElementById("rAvailability"),
        rLatencyP95: document.getElementById("rLatencyP95"),
        rFreshness: document.getElementById("rFreshness"),
        rCorrectness: document.getElementById("rCorrectness"),
        rViolations: document.getElementById("rViolations"),
        rOpenAlerts: document.getElementById("rOpenAlerts"),
        qAnomalies: document.getElementById("qAnomalies"),
        qCoverageDelta: document.getElementById("qCoverageDelta"),
        qDistrictDelta: document.getElementById("qDistrictDelta"),
        qLowConfDelta: document.getElementById("qLowConfDelta"),
        qBlockedDelta: document.getElementById("qBlockedDelta"),
        qSampleTask: document.getElementById("qSampleTask"),
        pAggregateMs: document.getElementById("pAggregateMs"),
        pDetailMs: document.getElementById("pDetailMs"),
        pViolations: document.getElementById("pViolations"),
        wpTotal: document.getElementById("wpTotal"),
        wpE2E: document.getElementById("wpE2E"),
        wpSubmitRate: document.getElementById("wpSubmitRate"),
        workpackageRows: document.getElementById("workpackageRows"),
        seedWpBtn: document.getElementById("seedWpBtn"),
        wpSeedStatus: document.getElementById("wpSeedStatus"),
        wpModalMask: document.getElementById("wpModalMask"),
        wpDetailTitle: document.getElementById("wpDetailTitle"),
        wpProcessLogs: document.getElementById("wpProcessLogs"),
        closeWpModalBtn: document.getElementById("closeWpModalBtn"),
        modalMask: document.getElementById("modalMask"),
        closeModalBtn: document.getElementById("closeModalBtn"),
        detailTitle: document.getElementById("detailTitle"),
        sourceData: document.getElementById("sourceData"),
        governanceData: document.getElementById("governanceData"),
        processLogs: document.getElementById("processLogs"),
      }};

      els.window.value = "{safe_window}";

      function fmtPct(v) {{
        return (Number(v || 0) * 100).toFixed(1) + "%";
      }}

      function qs(params) {{
        const sp = new URLSearchParams();
        Object.entries(params).forEach(([k, v]) => {{
          if (v !== "" && v !== null && v !== undefined) sp.set(k, String(v));
        }});
        return sp.toString();
      }}

      function safeJson(value) {{
        try {{
          return JSON.stringify(value, null, 2);
        }} catch (_err) {{
          return String(value || "");
        }}
      }}

      function parseCsvRow(line) {{
        const out = [];
        let current = "";
        let inQuotes = false;
        for (let i = 0; i < line.length; i++) {{
          const ch = line[i];
          if (ch === '"') {{
            if (inQuotes && line[i + 1] === '"') {{
              current += '"';
              i += 1;
            }} else {{
              inQuotes = !inQuotes;
            }}
            continue;
          }}
          if (ch === "," && !inQuotes) {{
            out.push(current);
            current = "";
            continue;
          }}
          current += ch;
        }}
        out.push(current);
        return out.map((x) => x.trim());
      }}

      function parseAddressInput(text) {{
        const raw = String(text || "").trim();
        if (!raw) return [];

        const firstChar = raw.slice(0, 1);
        if (firstChar === "[" || firstChar === "{{") {{
          try {{
            const parsed = JSON.parse(raw);
            const fromObject = (obj) => {{
              if (!obj || typeof obj !== "object") return "";
              return String(obj.raw_text || obj.address || obj.addr || obj.text || "").trim();
            }};
            if (Array.isArray(parsed)) {{
              return parsed
                .map((item) => (typeof item === "string" ? String(item).trim() : fromObject(item)))
                .filter(Boolean);
            }}
            if (parsed && typeof parsed === "object" && Array.isArray(parsed.addresses)) {{
              return parsed.addresses
                .map((item) => (typeof item === "string" ? String(item).trim() : fromObject(item)))
                .filter(Boolean);
            }}
          }} catch (_err) {{
          }}
        }}

        const lines = raw
          .split(/\\r?\\n/)
          .map((x) => x.trim())
          .filter(Boolean);
        if (!lines.length) return [];

        if (lines[0].includes(",")) {{
          const headers = parseCsvRow(lines[0]).map((h) => h.toLowerCase());
          const textIdx = headers.findIndex((h) => ["raw_text", "address", "addr", "text"].includes(h));
          if (textIdx >= 0) {{
            return lines
              .slice(1)
              .map((line) => {{
                const cols = parseCsvRow(line);
                return String(cols[textIdx] || "").trim();
              }})
              .filter(Boolean);
          }}
        }}
        return lines;
      }}

      function authHeaders() {{
        const token = (els.roleToken.value || "").trim();
        if (!token) return {{}};
        return {{ "x-observability-token": token }};
      }}

      async function loadTaskDetail(taskId) {{
        const base = "/v1/governance/observability/runtime";
        const role = els.role.value || "viewer";
        els.detailTitle.textContent = "任务详情（批次） - " + taskId;
        els.sourceData.textContent = "加载中...";
        els.governanceData.textContent = "加载中...";
        els.processLogs.textContent = "加载中...";
        els.modalMask.classList.add("show");
        const resp = await fetch(
          base + "/tasks/" + encodeURIComponent(taskId) + "/detail?" + qs({{ role, actor: "runtime_view" }}),
          {{ headers: authHeaders() }}
        );
        if (!resp.ok) {{
          els.sourceData.textContent = "加载失败";
          els.governanceData.textContent = "加载失败";
          els.processLogs.textContent = "加载失败";
          return;
        }}
        const detail = await resp.json();
        els.sourceData.textContent = safeJson(detail.source_data || []);
        els.governanceData.textContent = safeJson(detail.governance_results || []);
        els.processLogs.textContent = safeJson(detail.process_logs || {{}});
      }}

      async function loadWorkpackageEvents(workpackageId, version) {{
        const role = els.role.value || "viewer";
        els.wpDetailTitle.textContent = "工作包链路事件 - " + workpackageId + (version ? ("@" + version) : "");
        els.wpProcessLogs.textContent = "加载中...";
        els.wpModalMask.classList.add("show");
        const resp = await fetch(
          "/v1/governance/observability/runtime/workpackage-events?" + qs({{
            workpackage_id: workpackageId,
            version: version || "",
            window: els.window.value || "24h",
            client_type: "",
            limit: 500,
          }}),
          {{ headers: authHeaders() }}
        );
        if (!resp.ok) {{
          els.wpProcessLogs.textContent = "加载失败";
          return;
        }}
        const payload = await resp.json();
        els.wpProcessLogs.textContent = safeJson(payload.items || []);
      }}

      async function loadData() {{
        const window = els.window.value || "24h";
        const status = els.status.value || "";
        const ruleset = els.ruleset.value || "";
        els.windowLabel.textContent = window;
        const base = "/v1/governance/observability/runtime";

        const [summaryResp, riskResp, tasksResp] = await Promise.all([
          fetch(base + "/summary?" + qs({{ window, ruleset_id: ruleset }})),
          fetch(base + "/risk-distribution?" + qs({{ window }})),
          fetch(base + "/tasks?" + qs({{ window, status, ruleset_id: ruleset, limit: 50, page: 1 }})),
        ]);
        const pipelineResp = await fetch(base + "/workpackage-pipeline?" + qs({{ window, client_type: "" }}));
        const reliabilityResp = await fetch(base + "/reliability/summary?" + qs({{ window }}));
        const qualityDriftResp = await fetch(base + "/quality-drift/summary?" + qs({{ window, status, ruleset_id: ruleset }}));
        const performanceResp = await fetch(base + "/performance/summary?" + qs({{ window }}));

        if (!summaryResp.ok || !riskResp.ok || !tasksResp.ok) {{
          els.taskRows.innerHTML = '<tr><td colspan="8" class="muted">加载失败：请检查 API 状态</td></tr>';
          return;
        }}

        const summary = await summaryResp.json();
        const risk = await riskResp.json();
        const tasks = await tasksResp.json();
        const pipeline = pipelineResp.ok ? await pipelineResp.json() : {{}};
        const reliability = reliabilityResp.ok ? await reliabilityResp.json() : {{}};
        const qualityDrift = qualityDriftResp.ok ? await qualityDriftResp.json() : {{}};
        const performance = performanceResp.ok ? await performanceResp.json() : {{}};

        const total = Number(summary.total_tasks || 0);
        const statusCounts = summary.status_counts || {{}};
        const done = Number(statusCounts.SUCCEEDED || 0) + Number(statusCounts.REVIEWED || 0);
        const blocked = Number(statusCounts.BLOCKED || 0);

        els.kTotal.textContent = String(total);
        els.kSuccessRate.textContent = total > 0 ? fmtPct(done / total) : "0.0%";
        els.kBlockedRate.textContent = total > 0 ? fmtPct(blocked / total) : "0.0%";
        els.kConfidence.textContent = Number(summary.avg_confidence || 0).toFixed(3);
        els.kPendingReview.textContent = String(summary.pending_review_tasks || 0);
        els.kLatest.textContent = summary.latest_task_at || "-";
        const sli = reliability.sli || {{}};
        els.rAvailability.textContent = fmtPct(sli.availability || 0);
        els.rLatencyP95.textContent = Number(sli.latency_p95_ms || 0).toFixed(0) + "ms";
        els.rFreshness.textContent = Number(sli.freshness_minutes || 0).toFixed(1);
        els.rCorrectness.textContent = Number(sli.correctness || 0).toFixed(3);
        els.rViolations.textContent = String((reliability.violations || []).length);
        els.rOpenAlerts.textContent = String((reliability.open_alerts || []).length);
        const drift = qualityDrift.drift || {{}};
        els.qAnomalies.textContent = String((qualityDrift.anomalies || []).length);
        els.qCoverageDelta.textContent = Number(drift.normalization_coverage || 0).toFixed(3);
        els.qDistrictDelta.textContent = Number(drift.district_match_rate || 0).toFixed(3);
        els.qLowConfDelta.textContent = Number(drift.low_confidence_ratio || 0).toFixed(3);
        els.qBlockedDelta.textContent = Number(drift.blocked_reason_stability || 0).toFixed(3);
        els.qSampleTask.textContent = ((qualityDrift.sample_task_ids || []).slice(0, 2)).join(", ") || "-";
        const perfMetrics = performance.metrics || {{}};
        els.pAggregateMs.textContent = Number(perfMetrics.aggregate_api_ms || 0).toFixed(1) + "ms";
        els.pDetailMs.textContent = Number(perfMetrics.task_detail_api_ms || 0).toFixed(1) + "ms";
        els.pViolations.textContent = String((performance.violations || []).length);
        els.wpTotal.textContent = String(Number(pipeline.total_workpackages || 0));
        els.wpE2E.textContent = fmtPct(Number(pipeline.end_to_end_success_rate || 0));
        els.wpSubmitRate.textContent = fmtPct(Number(pipeline.runtime_submit_success_rate || 0));
        const wpRows = pipeline.items || [];
        if (!wpRows.length) {{
          els.workpackageRows.innerHTML = '<tr><td colspan="11" class="muted">暂无工作包链路数据</td></tr>';
        }} else {{
          els.workpackageRows.innerHTML = wpRows.map((row) => `
            <tr>
              <td><span class="task-link" data-workpackage-id="${{row.workpackage_id || ""}}" data-version="${{row.version || ""}}">${{row.workpackage_id || ""}}</span></td>
              <td>${{row.version || ""}}</td>
              <td>${{row.client_type || ""}}</td>
              <td>${{row.current_stage || "-"}}</td>
              <td>${{row.submit_status || "-"}}</td>
              <td>${{Number(row.stage_count || 0)}}</td>
              <td>${{Number(row.skills_count || 0)}}</td>
              <td>${{Number(row.artifact_count || 0)}}</td>
              <td>${{(row.checksum || "-").toString().slice(0, 10)}}</td>
              <td>${{row.runtime_receipt_id || "-"}}</td>
              <td>${{row.updated_at || "-"}}</td>
            </tr>
          `).join("");
        }}

        const buckets = risk.confidence_buckets || {{}};
        els.confidenceBuckets.innerHTML = [
          ["≥ 0.85", buckets.ge_085 || 0],
          ["0.60 ~ 0.85", buckets.between_060_085 || 0],
          ["< 0.60", buckets.lt_060 || 0],
        ].map(([label, count]) => `<li>${{label}}: <b>${{count}}</b></li>`).join("");

        const blockedTop = risk.blocked_reason_top || [];
        els.blockedTop.innerHTML = blockedTop.length
          ? blockedTop.map(i => `<li>${{i.reason}}: <b>${{i.count}}</b></li>`).join("")
          : '<li class="muted">暂无阻塞</li>';

        const patternTop = risk.low_confidence_pattern_top || [];
        els.lowPatternTop.innerHTML = patternTop.length
          ? patternTop.map(i => `<li>${{i.pattern}}: <b>${{i.count}}</b></li>`).join("")
          : '<li class="muted">暂无低置信模式</li>';

        const rows = tasks.items || [];
        if (!rows.length) {{
          els.taskRows.innerHTML = '<tr><td colspan="8" class="muted">暂无任务数据，可先灌入样例包</td></tr>';
        }} else {{
          els.taskRows.innerHTML = rows.map(row => `
            <tr>
              <td><span class="task-link" data-task-id="${{row.task_id || ""}}">${{row.task_id || ""}}</span></td>
              <td><span class="status ${{row.status || ""}}">${{row.status || ""}}</span></td>
              <td>${{row.ruleset_id || ""}}</td>
              <td>${{Number(row.batch_size || 0)}}</td>
              <td>${{Number(row.confidence || 0).toFixed(3)}}</td>
              <td>${{row.strategy || ""}}</td>
              <td>${{row.review_status || "-"}}</td>
              <td>${{row.updated_at || "-"}}</td>
            </tr>
          `).join("");
        }}
      }}

      els.refreshBtn.addEventListener("click", loadData);
      els.window.addEventListener("change", loadData);
      els.status.addEventListener("change", loadData);
      els.ruleset.addEventListener("change", loadData);
      els.taskRows.addEventListener("click", (ev) => {{
        const target = ev.target;
        if (!target || !target.dataset || !target.dataset.taskId) return;
        loadTaskDetail(target.dataset.taskId).catch(() => {{
          els.processLogs.textContent = "任务详情加载失败";
        }});
      }});
      els.workpackageRows.addEventListener("click", (ev) => {{
        const target = ev.target;
        if (!target || !target.dataset || !target.dataset.workpackageId) return;
        loadWorkpackageEvents(target.dataset.workpackageId, target.dataset.version || "").catch(() => {{
          els.wpProcessLogs.textContent = "工作包链路加载失败";
        }});
      }});
      els.closeModalBtn.addEventListener("click", () => {{
        els.modalMask.classList.remove("show");
      }});
      els.modalMask.addEventListener("click", (ev) => {{
        if (ev.target === els.modalMask) {{
          els.modalMask.classList.remove("show");
        }}
      }});
      els.closeWpModalBtn.addEventListener("click", () => {{
        els.wpModalMask.classList.remove("show");
      }});
      els.wpModalMask.addEventListener("click", (ev) => {{
        if (ev.target === els.wpModalMask) {{
          els.wpModalMask.classList.remove("show");
        }}
      }});
      els.uploadFile.addEventListener("change", async () => {{
        const file = (els.uploadFile.files || [])[0];
        if (!file) return;
        const text = await file.text();
        const addresses = parseAddressInput(text);
        if (!addresses.length) {{
          els.uploadStatus.textContent = "文件已选择，但未解析出地址，请检查内容格式";
          els.uploadFile.value = "";
          return;
        }}
        els.uploadText.value = addresses.join("\\n");
        els.uploadStatus.textContent = "已加载文件: " + (file.name || "-") + "，共 " + addresses.length + " 条地址";
        els.uploadFile.value = "";
      }});
      els.uploadBtn.addEventListener("click", async () => {{
        const lines = parseAddressInput(els.uploadText.value || "");
        if (!lines.length) {{
          els.uploadStatus.textContent = "请先输入或上传地址数据";
          return;
        }}
        const payload = {{
          batch_name: "runtime-upload-" + Date.now(),
          ruleset_id: els.ruleset.value || "default",
          addresses: lines,
          actor: "runtime_view_upload",
        }};
        els.uploadStatus.textContent = "执行中...";
        const resp = await fetch("/v1/governance/observability/runtime/upload-batch", {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json",
          }},
          body: JSON.stringify(payload),
        }});
        const data = await resp.json().catch(() => ({{}}));
        if (!resp.ok) {{
          els.uploadStatus.textContent = "执行失败: " + (data?.detail?.message || data?.detail || resp.statusText || "unknown");
          return;
        }}
        els.uploadStatus.textContent = "已创建并执行 task: " + (data.task_id || "-") + "，状态: " + (data.status || "-");
        await loadData();
      }});
      els.seedWpBtn.addEventListener("click", async () => {{
        els.wpSeedStatus.textContent = "灌入中...";
        const resp = await fetch("/v1/governance/observability/runtime/seed-workpackage-demo?total=12", {{
          method: "POST",
        }});
        const payload = await resp.json().catch(() => ({{}}));
        if (!resp.ok) {{
          els.wpSeedStatus.textContent = "灌入失败: " + (payload?.detail?.message || payload?.detail || resp.statusText || "unknown");
          return;
        }}
        els.wpSeedStatus.textContent = "已灌入链路样例: " + (payload.total_seeded || 0) + " 个工作包";
        await loadData();
      }});
      loadData().catch(() => {{
        els.taskRows.innerHTML = '<tr><td colspan="8" class="muted">加载失败：请检查服务日志</td></tr>';
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)
