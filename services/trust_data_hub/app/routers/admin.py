from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.trust_data_hub.app.models.trust_models import SourceScheduleUpsertRequest, SourceUpsertRequest
from services.trust_data_hub.app.repositories.trust_repository import trust_repository

router = APIRouter()


@router.put("/namespaces/{namespace}/sources/{source_id}")
def upsert_source(namespace: str, source_id: str, payload: SourceUpsertRequest) -> dict:
    return trust_repository.upsert_source(namespace, source_id, payload.model_dump())


@router.put("/namespaces/{namespace}/sources/{source_id}/schedule")
def upsert_source_schedule(namespace: str, source_id: str, payload: SourceScheduleUpsertRequest) -> dict:
    try:
        return trust_repository.upsert_source_schedule(namespace, source_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/namespaces/{namespace}/sources/{source_id}/schedule")
def get_source_schedule(namespace: str, source_id: str) -> dict:
    row = trust_repository.get_source_schedule(namespace, source_id)
    if not row:
        raise HTTPException(status_code=404, detail="schedule_not_found")
    return row


@router.get("/namespaces/{namespace}/snapshots/{snapshot_id}/quality")
def get_snapshot_quality(namespace: str, snapshot_id: str) -> dict:
    row = trust_repository.get_quality_report(namespace, snapshot_id)
    if not row:
        raise HTTPException(status_code=404, detail="quality_report_not_found")
    return row


@router.get("/namespaces/{namespace}/sources/{source_id}/active-release")
def get_active_release(namespace: str, source_id: str) -> dict:
    row = trust_repository.get_active_release(namespace, source_id)
    if not row:
        raise HTTPException(status_code=404, detail="active_release_not_found")
    return row


@router.get("/namespaces/{namespace}/audit-events")
def list_audit_events(namespace: str) -> dict:
    return {"events": trust_repository.list_audit_events(namespace)}


@router.get("/namespaces/{namespace}/validation/replay-runs")
def list_validation_replay_runs(
    namespace: str,
    snapshot_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {
        "runs": trust_repository.list_validation_replay_runs(namespace, snapshot_id=snapshot_id, limit=limit),
    }


@router.post("/namespaces/{namespace}/bootstrap/samples")
def bootstrap_sample_sources(namespace: str) -> dict:
    return {"sources": trust_repository.bootstrap_sample_sources(namespace)}
