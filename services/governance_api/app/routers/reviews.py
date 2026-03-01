from fastapi import APIRouter, HTTPException

from services.governance_api.app.models.review_models import ReviewDecisionRequest, ReviewDecisionResponse
from services.governance_api.app.services.governance_service import GOVERNANCE_SERVICE

router = APIRouter()


@router.post("/reviews/{task_id}/decision", response_model=ReviewDecisionResponse)
def submit_review_decision(task_id: str, payload: ReviewDecisionRequest) -> ReviewDecisionResponse:
    task = GOVERNANCE_SERVICE.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    review_data = payload.model_dump()
    reconcile_result = GOVERNANCE_SERVICE.submit_review_decision(task_id, review_data)
    return ReviewDecisionResponse(
        task_id=task_id,
        review_status=payload.review_status,
        accepted=True,
        updated_count=int(reconcile_result.get("updated_count", 0)),
        target_raw_id=reconcile_result.get("target_raw_id"),
    )
