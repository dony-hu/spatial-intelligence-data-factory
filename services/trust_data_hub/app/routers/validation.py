from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from services.trust_data_hub.app.models.trust_models import ValidationEvidenceRequest
from services.trust_data_hub.app.repositories.trust_repository import trust_repository

router = APIRouter()


@router.post("/evidence")
def validation_evidence(payload: ValidationEvidenceRequest, namespace: str = Query(...)) -> dict:
    return trust_repository.build_validation_evidence(namespace, payload.model_dump())


@router.post("/replay")
def validation_replay(
    payload: ValidationEvidenceRequest,
    namespace: str = Query(...),
    snapshot_id: str = Query(...),
) -> dict:
    try:
        return trust_repository.replay_validation_evidence_by_snapshot(namespace, snapshot_id, payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
