from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.trust_data_hub.app.models.trust_models import DiffRequest, PromoteRequest
from services.trust_data_hub.app.repositories.trust_repository import trust_repository

router = APIRouter()


@router.post("/namespaces/{namespace}/sources/{source_id}/fetch-now")
def fetch_now(namespace: str, source_id: str) -> dict:
    try:
        snapshot = trust_repository.fetch_now(namespace, source_id)
        return {
            "namespace": namespace,
            "snapshot_id": snapshot["snapshot_id"],
            "status": snapshot["status"],
            "version_tag": snapshot["version_tag"],
            "row_count": snapshot["row_count"],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
def validate_snapshot(namespace: str, snapshot_id: str) -> dict:
    try:
        return trust_repository.validate_snapshot(namespace, snapshot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
def publish_snapshot(namespace: str, snapshot_id: str) -> dict:
    try:
        return trust_repository.publish_snapshot(namespace, snapshot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        if str(exc) == "snapshot_not_validated":
            raise HTTPException(status_code=400, detail="snapshot_not_validated") from exc
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/namespaces/{namespace}/sources/{source_id}/promote")
def promote_active(namespace: str, source_id: str, payload: PromoteRequest) -> dict:
    try:
        return trust_repository.promote_active(
            namespace,
            source_id,
            payload.snapshot_id,
            payload.activated_by,
            payload.activation_note,
            payload.confirm_high_diff,
        )
    except PermissionError as exc:
        code = 400 if str(exc) == "high_diff_requires_confirmation" else 403
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@router.post("/namespaces/{namespace}/snapshots/diff")
def diff_snapshots(namespace: str, payload: DiffRequest) -> dict:
    try:
        return trust_repository.diff_snapshots(namespace, payload.base_snapshot_id, payload.new_snapshot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
