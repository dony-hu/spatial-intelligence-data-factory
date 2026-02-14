from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from services.governance_worker.app.core.queue import enqueue_task
from services.governance_api.app.models.task_models import (
    TaskResultResponse,
    TaskStatusResponse,
    TaskSubmitRequest,
    TaskSubmitResponse,
)
from services.governance_api.app.repositories.governance_repository import REPOSITORY

router = APIRouter()


@router.post("/tasks", response_model=TaskSubmitResponse)
def submit_task(payload: TaskSubmitRequest) -> TaskSubmitResponse:
    task_id = f"task_{uuid4().hex[:12]}"
    task_payload = {
        "task_id": task_id,
        "batch_name": payload.batch_name,
        "ruleset_id": payload.ruleset_id,
        "records": [item.model_dump() for item in payload.records],
    }

    REPOSITORY.create_task(
        task_id=task_id,
        batch_name=payload.batch_name,
        ruleset_id=payload.ruleset_id,
        status="PENDING",
        queue_backend="pending",
        queue_message="created",
    )

    enqueue_result = enqueue_task(task_payload)

    if not enqueue_result.queued:
        REPOSITORY.set_task_status(task_id, "FAILED")

    status = REPOSITORY.get_task(task_id).get("status", "FAILED")
    if REPOSITORY.get_task(task_id):
        REPOSITORY.get_task(task_id)["queue_backend"] = enqueue_result.backend
        REPOSITORY.get_task(task_id)["queue_message"] = enqueue_result.message
    return TaskSubmitResponse(task_id=task_id, status=status)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str) -> TaskStatusResponse:
    task = REPOSITORY.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskStatusResponse(task_id=task_id, status=task["status"], message=None)


@router.get("/tasks/{task_id}/result", response_model=TaskResultResponse)
def get_task_result(task_id: str) -> TaskResultResponse:
    task = REPOSITORY.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskResultResponse(task_id=task_id, status=task["status"], results=REPOSITORY.get_results(task_id))
