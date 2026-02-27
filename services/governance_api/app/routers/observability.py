from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from services.governance_api.app.models.observability_models import (
    ObservationAlert,
    ObservationAlertAckRequest,
    ObservationAlertsResponse,
    ObservationEventsResponse,
    ObservationSnapshotResponse,
    ObservationTimeseriesResponse,
    ObservationTraceReplayResponse,
)
from services.governance_api.app.repositories.governance_repository import REPOSITORY

router = APIRouter()


@router.get("/observability/snapshot", response_model=ObservationSnapshotResponse)
def get_observability_snapshot(env: str = Query(default="dev")) -> ObservationSnapshotResponse:
    payload = REPOSITORY.get_observability_snapshot(env=env)
    return ObservationSnapshotResponse(**payload)


@router.get("/observability/events", response_model=ObservationEventsResponse)
def list_observability_events(
    trace_id: str = Query(default=""),
    task_id: str = Query(default=""),
    status: str = Query(default=""),
    event_type: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=1000),
) -> ObservationEventsResponse:
    items = REPOSITORY.list_observation_events(
        trace_id=trace_id,
        task_id=task_id,
        status=status,
        event_type=event_type,
        limit=limit,
    )
    return ObservationEventsResponse(total=len(items), items=items)


@router.get("/observability/traces/{trace_id}/replay", response_model=ObservationTraceReplayResponse)
def get_trace_replay(trace_id: str, limit: int = Query(default=500, ge=1, le=2000)) -> ObservationTraceReplayResponse:
    timeline = REPOSITORY.get_trace_replay(trace_id=trace_id, limit=limit)
    if not timeline:
        raise HTTPException(status_code=404, detail="trace not found")
    return ObservationTraceReplayResponse(trace_id=trace_id, total=len(timeline), timeline=timeline)


@router.get("/observability/timeseries", response_model=ObservationTimeseriesResponse)
def get_metric_timeseries(metric_name: str = Query(..., min_length=1), limit: int = Query(default=200, ge=1, le=1000)) -> ObservationTimeseriesResponse:
    points = REPOSITORY.query_observation_metric_series(metric_name=metric_name, limit=limit)
    return ObservationTimeseriesResponse(metric_name=metric_name, total=len(points), points=points)


@router.get("/observability/alerts", response_model=ObservationAlertsResponse)
def list_alerts(status: str = Query(default=""), limit: int = Query(default=200, ge=1, le=1000)) -> ObservationAlertsResponse:
    items = REPOSITORY.list_observation_alerts(status=status, limit=limit)
    return ObservationAlertsResponse(total=len(items), items=items)


@router.post("/observability/alerts/{alert_id}/ack", response_model=ObservationAlert)
def ack_alert(alert_id: str, payload: ObservationAlertAckRequest) -> ObservationAlert:
    acked = REPOSITORY.ack_observation_alert(alert_id=alert_id, actor=payload.actor)
    if not acked:
        raise HTTPException(status_code=404, detail="alert not found")
    return ObservationAlert(**acked)
