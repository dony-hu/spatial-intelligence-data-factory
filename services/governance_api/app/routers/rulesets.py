from fastapi import APIRouter, HTTPException

from services.governance_api.app.models.ruleset_models import (
    RulesetPayload,
    RulesetPublishRequest,
    RulesetResponse,
)
from services.governance_api.app.repositories.governance_repository import REPOSITORY

router = APIRouter()


@router.get("/rulesets/{ruleset_id}", response_model=RulesetResponse)
def get_ruleset(ruleset_id: str) -> RulesetResponse:
    ruleset = REPOSITORY.get_ruleset(ruleset_id)
    if not ruleset:
        raise HTTPException(status_code=404, detail="ruleset not found")
    return RulesetResponse(**ruleset)


@router.put("/rulesets/{ruleset_id}", response_model=RulesetResponse)
def update_ruleset(ruleset_id: str, payload: RulesetPayload) -> RulesetResponse:
    ruleset = REPOSITORY.upsert_ruleset(ruleset_id, payload.model_dump())
    return RulesetResponse(**ruleset)


@router.post("/rulesets/{ruleset_id}/publish", response_model=RulesetResponse)
def publish_ruleset(ruleset_id: str, payload: RulesetPublishRequest) -> RulesetResponse:
    ruleset = REPOSITORY.publish_ruleset(
        ruleset_id=ruleset_id,
        operator=payload.operator,
        reason=payload.reason,
    )
    if not ruleset:
        raise HTTPException(status_code=404, detail="ruleset not found")
    return RulesetResponse(**ruleset)
