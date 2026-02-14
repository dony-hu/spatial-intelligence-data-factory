from typing import List, Optional

from fastapi import APIRouter, Query

from services.governance_api.app.models.ops_models import OpsSummaryResponse
from services.governance_api.app.repositories.governance_repository import REPOSITORY

router = APIRouter()


@router.get("/ops/summary", response_model=OpsSummaryResponse)
def get_ops_summary(
    task_id: Optional[str] = Query(default=None),
    batch_name: Optional[str] = Query(default=None),
    ruleset_id: Optional[str] = Query(default=None),
    status: Optional[List[str]] = Query(default=None),
    recent_hours: Optional[int] = Query(default=None, ge=0),
    t_low: Optional[float] = Query(default=None, ge=0, le=1),
    t_high: Optional[float] = Query(default=None, ge=0, le=1),
) -> OpsSummaryResponse:
    return OpsSummaryResponse(
        **REPOSITORY.get_ops_summary(
            task_id=task_id,
            batch_name=batch_name,
            ruleset_id=ruleset_id,
            status_list=status,
            recent_hours=recent_hours,
            t_low_override=t_low,
            t_high_override=t_high,
        )
    )
