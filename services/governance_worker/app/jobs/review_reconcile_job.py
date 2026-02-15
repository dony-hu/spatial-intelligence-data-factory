from __future__ import annotations

from services.governance_api.app.repositories.governance_repository import REPOSITORY


def run(task_payload: dict) -> dict:
    task_id = task_payload.get("task_id")
    if not task_id:
        return {"task_id": None, "status": "FAILED"}
    return REPOSITORY.reconcile_review(task_id, task_payload.get("review_data"))
