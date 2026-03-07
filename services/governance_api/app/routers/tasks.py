from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.governance_api.app.models.task_models import (
    TaskResultResponse,
    TaskStatusResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
)
from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE

router = APIRouter()


@router.post("/tasks", response_model=TaskSubmitResponse)
def submit_task(payload: TaskSubmitRequest) -> TaskSubmitResponse:
    try:
        submitted = GOVERNANCE_SERVICE.submit_task(
            batch_name=payload.batch_name,
            ruleset_id=payload.ruleset_id,
            records=[item.model_dump() for item in payload.records],
            workpackage_id=str(payload.workpackage_id or ""),
            version=str(payload.version or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TaskSubmitResponse(
        task_id=str(submitted.get("task_id") or ""),
        status=str(submitted.get("status") or "FAILED"),
        trace_id=str(submitted.get("trace_id") or ""),
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str) -> TaskStatusResponse:
    task = GOVERNANCE_SERVICE.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResponse(task_id=task_id, status=task["status"], message=None)


@router.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
def get_task_result(task_id: str) -> TaskResultResponse:
    task = GOVERNANCE_SERVICE.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskResultResponse(task_id=task_id, status=task["status"], results=GOVERNANCE_SERVICE.get_results(task_id))
