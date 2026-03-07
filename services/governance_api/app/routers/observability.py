from __future__ import annotations

import hmac
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

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
_AGENT_CHAT_SESSIONS: dict[str, list[dict[str, Any]]] = {}
_AGENT_TRACE_SESSIONS: dict[str, dict[str, list[dict[str, Any]]]] = {}
_FACTORY_AGENT: Any = None


def _get_factory_agent() -> Any:
    global _FACTORY_AGENT
    if _FACTORY_AGENT is None:
        from packages.factory_agent.agent import FactoryAgent

        _FACTORY_AGENT = FactoryAgent()
    return _FACTORY_AGENT


def _split_bundle_name(bundle_name: str) -> tuple[str, str]:
    name = str(bundle_name or "").strip()
    match = re.match(r"^(.+)-v(\d+\.\d+\.\d+)$", name)
    if not match:
        return "", ""
    return str(match.group(1) or ""), f"v{match.group(2)}"


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


def _ok_response(data: Any, message: str = "ok") -> dict[str, Any]:
    return {
        "code": "OK",
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
    }


def _append_runtime_api_trace(
    *,
    event_type: str,
    endpoint: str,
    status: str,
    session_id: str = "",
    payload: Optional[dict[str, Any]] = None,
) -> None:
    log_path = Path(str(os.getenv("RUNTIME_API_TRACE_LOG") or "output/runtime_traces/runtime_api_trace.jsonl"))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": str(event_type or ""),
            "endpoint": str(endpoint or ""),
            "status": str(status or "ok"),
            "session_id": str(session_id or ""),
            "payload": payload if isinstance(payload, dict) else {},
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        # trace logging must not break primary API path
        return


def _trace_item(
    *,
    session_id: str,
    trace_id: str,
    channel: str,
    direction: str,
    stage: str,
    event_type: str,
    content_text: str,
    content_json: Any = None,
    artifacts: list[str] | None = None,
    status: str = "success",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "session_id": str(session_id or ""),
        "trace_id": str(trace_id or ""),
        "channel": str(channel or ""),
        "direction": str(direction or ""),
        "stage": str(stage or ""),
        "event_type": str(event_type or ""),
        "content_text": str(content_text or ""),
        "content_json": content_json if isinstance(content_json, (dict, list)) else {},
        "artifacts": [str(x) for x in (artifacts or []) if str(x).strip()],
        "status": str(status or "success"),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    return payload


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
    try:
        return GOVERNANCE_SERVICE.runtime_workpackage_pipeline(window=window, client_type=client_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ARGUMENT", "message": str(exc)}) from exc


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


@router.get("/observability/runtime/workpackage-blueprint")
def get_runtime_workpackage_blueprint(
    workpackage_id: str = Query(..., min_length=1),
    version: str = Query(default=""),
) -> dict:
    try:
        return GOVERNANCE_SERVICE.runtime_workpackage_blueprint(
            workpackage_id=workpackage_id,
            version=version,
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
    for event in reversed(events):
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


@router.post("/observability/runtime/workpackages")
def create_runtime_workpackage(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        item = GOVERNANCE_SERVICE.runtime_workpackage_create(
            workpackage_id=str(payload.get("workpackage_id") or ""),
            version=str(payload.get("version") or ""),
            name=str(payload.get("name") or ""),
            objective=str(payload.get("objective") or ""),
            status=str(payload.get("status") or "created"),
            actor=str(payload.get("actor") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": str(exc)}) from exc
    _append_runtime_api_trace(
        event_type="runtime_workpackage_crud_create",
        endpoint="/v1/governance/observability/runtime/workpackages",
        status="ok",
        payload={"workpackage_id": str(item.get("workpackage_id") or ""), "version": str(item.get("version") or "")},
    )
    return _ok_response(item, message="created")


@router.get("/observability/runtime/workpackages")
def list_runtime_workpackages(
    q: str = Query(default=""),
    status: str = Query(default=""),
    version: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
) -> dict[str, Any]:
    payload = GOVERNANCE_SERVICE.runtime_workpackage_list(
        q=q,
        status=status,
        version=version,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    _append_runtime_api_trace(
        event_type="runtime_workpackage_crud_list",
        endpoint="/v1/governance/observability/runtime/workpackages",
        status="ok",
        payload={
            "q": q,
            "status": status,
            "version": version,
            "limit": limit,
            "offset": offset,
            "total": int(payload.get("total") or 0) if isinstance(payload, dict) else 0,
        },
    )
    return _ok_response(payload)


@router.get("/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
def get_runtime_workpackage(workpackage_id: str, version: str) -> dict[str, Any]:
    item = GOVERNANCE_SERVICE.runtime_workpackage_detail(workpackage_id=workpackage_id, version=version)
    if not item:
        raise HTTPException(status_code=404, detail="workpackage not found")
    _append_runtime_api_trace(
        event_type="runtime_workpackage_crud_get",
        endpoint="/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}",
        status="ok",
        payload={"workpackage_id": workpackage_id, "version": version},
    )
    return _ok_response(item)


@router.put("/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
def update_runtime_workpackage(workpackage_id: str, version: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        item = GOVERNANCE_SERVICE.runtime_workpackage_update(
            workpackage_id=workpackage_id,
            version=version,
            name=payload.get("name"),
            objective=payload.get("objective"),
            status=payload.get("status"),
            actor=str(payload.get("actor") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": str(exc)}) from exc
    if not item:
        raise HTTPException(status_code=404, detail="workpackage not found")
    _append_runtime_api_trace(
        event_type="runtime_workpackage_crud_update",
        endpoint="/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}",
        status="ok",
        payload={"workpackage_id": workpackage_id, "version": version, "status": str(item.get("status") or "")},
    )
    return _ok_response(item, message="updated")


@router.delete("/observability/runtime/workpackages/{workpackage_id}/versions/{version}")
def delete_runtime_workpackage(workpackage_id: str, version: str, actor: str = Query(default="")) -> dict[str, Any]:
    item = GOVERNANCE_SERVICE.runtime_workpackage_delete(workpackage_id=workpackage_id, version=version, actor=actor)
    if not item:
        raise HTTPException(status_code=404, detail="workpackage not found")
    _append_runtime_api_trace(
        event_type="runtime_workpackage_crud_delete",
        endpoint="/v1/governance/observability/runtime/workpackages/{workpackage_id}/versions/{version}",
        status="ok",
        payload={"workpackage_id": workpackage_id, "version": version, "actor": actor},
    )
    return _ok_response({"workpackage_id": workpackage_id, "version": version}, message="deleted")


@router.post("/observability/runtime/workpackages/seed-crud-demo")
def seed_runtime_workpackage_crud_demo(
    total: int = Query(default=12, ge=12, le=200),
    prefix: str = Query(default="wp_seed_crud"),
) -> dict[str, Any]:
    payload = GOVERNANCE_SERVICE.runtime_seed_workpackage_crud_demo(total=total, prefix=prefix)
    return _ok_response(payload)


@router.post("/observability/runtime/upload-batch")
def upload_runtime_batch(payload: dict[str, Any]) -> dict:
    batch_name = str(payload.get("batch_name") or "runtime-upload-batch")
    ruleset_id = str(payload.get("ruleset_id") or "default")
    workpackage_id = str(payload.get("workpackage_id") or "")
    version = str(payload.get("version") or "")
    confirmations_raw = payload.get("confirmations")
    confirmations = []
    if isinstance(confirmations_raw, list):
        confirmations = [str(item or "").strip() for item in confirmations_raw if str(item or "").strip()]
    actor = str(payload.get("actor") or "runtime_upload")
    addresses_raw = payload.get("addresses")
    if not isinstance(addresses_raw, list):
        raise HTTPException(status_code=400, detail={"code": "INVALID_ADDRESSES", "message": "addresses must be array"})
    addresses = [str(item or "").strip() for item in addresses_raw if str(item or "").strip()]
    if not addresses:
        raise HTTPException(status_code=400, detail={"code": "INVALID_ADDRESSES", "message": "addresses is empty"})
    try:
        result = GOVERNANCE_SERVICE.submit_runtime_uploaded_batch(
            batch_name=batch_name,
            ruleset_id=ruleset_id,
            addresses=addresses,
            actor=actor,
            workpackage_id=workpackage_id,
            version=version,
            confirmations=confirmations,
        )
        _append_runtime_api_trace(
            event_type="runtime_upload_batch",
            endpoint="/v1/governance/observability/runtime/upload-batch",
            status="ok",
            payload={
                "workpackage_id": workpackage_id,
                "version": version,
                "record_count": int(result.get("record_count") or 0) if isinstance(result, dict) else 0,
                "runtime_receipt_id": str(result.get("runtime_receipt_id") or "") if isinstance(result, dict) else "",
            },
        )
        return result
    except ValueError as exc:
        _append_runtime_api_trace(
            event_type="runtime_upload_batch",
            endpoint="/v1/governance/observability/runtime/upload-batch",
            status="error",
            payload={"workpackage_id": workpackage_id, "version": version, "error": str(exc)},
        )
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": str(exc)}) from exc
    except GovernanceGateError as exc:
        _append_runtime_api_trace(
            event_type="runtime_upload_batch",
            endpoint="/v1/governance/observability/runtime/upload-batch",
            status="blocked",
            payload={"workpackage_id": workpackage_id, "version": version, "code": exc.code, "message": exc.message},
        )
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


@router.post("/observability/runtime/agent-chat")
def runtime_agent_chat(payload: dict[str, Any]) -> dict:
    session_id = str(payload.get("session_id") or "").strip() or f"runtime_agent_{os.urandom(4).hex()}"
    message = str(payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": "message is required"})
    try:
        agent = _get_factory_agent()
        try:
            result = agent.converse(message, session_id=session_id)
        except TypeError:
            result = agent.converse(message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "AGENT_CHAT_FAILED", "message": str(exc)}) from exc

    history = _AGENT_CHAT_SESSIONS.setdefault(session_id, [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": result})
    trace_payload = (result or {}).get("nanobot_traces") if isinstance(result, dict) else {}
    if not isinstance(trace_payload, dict):
        trace_payload = {"client_nanobot": [], "nanobot_opencode": []}
    memory_payload = (result or {}).get("memory_objects") if isinstance(result, dict) else {}
    if not isinstance(memory_payload, dict):
        memory_payload = {}
    _AGENT_TRACE_SESSIONS[session_id] = {
        "client_nanobot": list(trace_payload.get("client_nanobot") or []),
        "nanobot_opencode": list(trace_payload.get("nanobot_opencode") or []),
    }

    bundle_name = str((result or {}).get("bundle_name") or "")
    bundle_id, version = _split_bundle_name(bundle_name)
    workpackage_ref = ""
    if bundle_id and version:
        workpackage_ref = f"{bundle_id}@{version}"

    try:
        GOVERNANCE_SERVICE.log_audit_event(
            event_type="runtime_agent_chat",
            caller="runtime_view_user",
            payload={"session_id": session_id, "message": message, "result_action": str((result or {}).get("action") or "")},
        )
    except Exception:
        pass
    _append_runtime_api_trace(
        event_type="runtime_agent_chat",
        endpoint="/v1/governance/observability/runtime/agent-chat",
        status=str((result or {}).get("status") or "ok"),
        session_id=session_id,
        payload={
            "message": message,
            "action": str((result or {}).get("action") or ""),
            "workpackage_ref": workpackage_ref,
            "client_trace_count": len(_AGENT_TRACE_SESSIONS.get(session_id, {}).get("client_nanobot") or []),
            "opencode_trace_count": len(_AGENT_TRACE_SESSIONS.get(session_id, {}).get("nanobot_opencode") or []),
        },
    )
    return {
        "session_id": session_id,
        "result": result,
        "workpackage_ref": workpackage_ref,
        "nanobot_traces": trace_payload,
        "trace_log_path": str((result or {}).get("trace_log_path") or ""),
        "schema_fix_rounds": (result or {}).get("schema_fix_rounds") if isinstance(result, dict) else [],
        "workpackage_blueprint_summary": (result or {}).get("workpackage_blueprint_summary") if isinstance(result, dict) else {},
        "memory_objects": memory_payload,
        "history": history[-20:],
    }


@router.get("/observability/runtime/view", response_class=HTMLResponse)
def runtime_observability_view(window: str = Query(default="24h")) -> HTMLResponse:
    template_path = Path(__file__).resolve().parents[4] / "web" / "dashboard" / "factory-agent-governance-prototype-v2.html"
    if not template_path.exists():
        raise HTTPException(status_code=500, detail={"code": "RUNTIME_VIEW_TEMPLATE_MISSING", "message": str(template_path)})
    raw_html = template_path.read_text(encoding="utf-8")
    rendered_html = raw_html.replace("__DEFAULT_WINDOW__", str(window or "24h"))
    return HTMLResponse(content=rendered_html)


@router.get("/observability/runtime/preflight")
def runtime_preflight(
    verify_llm: bool = Query(default=True),
    fail_fast: bool = Query(default=True),
    llm_retries: int = Query(default=3, ge=1, le=5),
    llm_timeout_sec: int = Query(default=45, ge=10, le=120),
) -> dict:
    checks: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    # 1) PostgreSQL / governance repository readiness
    try:
        summary = GOVERNANCE_SERVICE.runtime_summary(window="24h", ruleset_id="")
        checks["postgres"] = {
            "ok": True,
            "detail": "governance repository reachable",
            "sample_total_tasks": int(summary.get("total_tasks") or 0) if isinstance(summary, dict) else 0,
        }
    except Exception as exc:
        checks["postgres"] = {"ok": False, "detail": str(exc)}
        errors.append(f"postgres: {exc}")

    # 2) nanobot runtime (FactoryAgent) readiness
    try:
        agent = _get_factory_agent()
        checks["nanobot"] = {
            "ok": callable(getattr(agent, "converse", None)),
            "detail": "FactoryAgent loaded",
        }
        if not checks["nanobot"]["ok"]:
            errors.append("nanobot: converse method missing")
    except Exception as exc:
        checks["nanobot"] = {"ok": False, "detail": str(exc)}
        errors.append(f"nanobot: {exc}")

    # 3) opencode availability
    try:
        proc = subprocess.run(["opencode", "--version"], capture_output=True, text=True, check=False, timeout=10)
        ok = int(proc.returncode) == 0
        checks["opencode"] = {
            "ok": ok,
            "detail": (proc.stdout or proc.stderr or "").strip(),
        }
        if not ok:
            errors.append(f"opencode: {checks['opencode']['detail'] or 'not available'}")
    except Exception as exc:
        checks["opencode"] = {"ok": False, "detail": str(exc)}
        errors.append(f"opencode: {exc}")

    # 4) real external LLM connectivity
    if verify_llm:
        try:
            llm_error = ""
            llm_detail = ""
            llm_ok = False
            agent = _get_factory_agent()
            for _ in range(max(1, int(llm_retries))):
                try:
                    ping = agent.converse(
                        "请给出一条地址治理建议（20字以内）。",
                        session_id="runtime_preflight_probe",
                    )
                    status = str((ping or {}).get("status") or "").strip().lower()
                    llm_status = str((ping or {}).get("llm_status") or "").strip().lower()
                    action = str((ping or {}).get("action") or "").strip().lower()
                    message = str((ping or {}).get("message") or (ping or {}).get("reply") or "").strip()
                    error_text = str((ping or {}).get("error") or "").strip()
                    llm_detail = message or status or "empty_response"
                    if error_text:
                        llm_detail = f"{llm_detail} | error={error_text}"
                    # Must be explicit success from agent chat route.
                    if status == "ok" and llm_status != "blocked" and action != "general_governance_chat_blocked":
                        llm_ok = True
                        break
                    llm_error = llm_detail
                except Exception as exc:
                    llm_error = str(exc)
                    llm_detail = llm_error
            checks["llm"] = {"ok": llm_ok, "detail": (llm_detail or llm_error or "empty response")[:200]}
            if not llm_ok:
                errors.append(f"llm: {llm_detail or llm_error or 'empty response'}")
        except Exception as exc:
            checks["llm"] = {"ok": False, "detail": str(exc)}
            errors.append(f"llm: {exc}")
    else:
        checks["llm"] = {"ok": True, "detail": "skipped by verify_llm=false"}

    ok = len(errors) == 0
    payload = {
        "status": "ok" if ok else "blocked",
        "checks": checks,
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not ok and fail_fast:
        raise HTTPException(status_code=503, detail=payload)
    return payload
