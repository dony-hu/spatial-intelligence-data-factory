from fastapi import APIRouter, HTTPException

from services.governance_api.app.models.ruleset_models import (
    ChangeRequestApprovalPayload,
    ChangeRequestCreatePayload,
    ChangeRequestRejectPayload,
    ChangeRequestResponse,
    RulesetActivateRequest,
    RulesetActivateResponse,
    RulesetPayload,
    RulesetPublishRequest,
    RulesetResponse,
)
from services.governance_api.app.repositories.governance_repository import GovernanceGateError, REPOSITORY

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
    REPOSITORY.log_audit_event(
        event_type="ruleset_publish_blocked",
        caller=payload.operator,
        payload={
            "ruleset_id": ruleset_id,
            "task_run_id": None,
            "reason": payload.reason,
            "gate_reason": "approval_required_via_change_request",
            "gate_code": "APPROVAL_GATE_REQUIRED",
        },
    )
    raise HTTPException(
        status_code=409,
        detail={
            "code": "APPROVAL_GATE_REQUIRED",
            "message": "direct publish is blocked; use change request approval then activate ruleset",
        },
    )


@router.post("/change-requests", response_model=ChangeRequestResponse)
def create_change_request(payload: ChangeRequestCreatePayload) -> ChangeRequestResponse:
    if not REPOSITORY.get_ruleset(payload.from_ruleset_id):
        raise HTTPException(status_code=404, detail="from_ruleset not found")
    if not REPOSITORY.get_ruleset(payload.to_ruleset_id):
        raise HTTPException(status_code=404, detail="to_ruleset not found")
    item = REPOSITORY.create_change_request(payload.model_dump())
    return ChangeRequestResponse(**item)


@router.get("/change-requests/{change_id}", response_model=ChangeRequestResponse)
def get_change_request(change_id: str) -> ChangeRequestResponse:
    item = REPOSITORY.get_change_request(change_id)
    if not item:
        raise HTTPException(status_code=404, detail="change request not found")
    return ChangeRequestResponse(**item)


@router.post("/change-requests/{change_id}/approve", response_model=ChangeRequestResponse)
def approve_change_request(change_id: str, payload: ChangeRequestApprovalPayload) -> ChangeRequestResponse:
    item = REPOSITORY.update_change_request_status(
        change_id,
        status="approved",
        actor=payload.approver,
        comment=payload.comment,
    )
    if not item:
        raise HTTPException(status_code=404, detail="change request not found")
    return ChangeRequestResponse(**item)


@router.post("/change-requests/{change_id}/reject", response_model=ChangeRequestResponse)
def reject_change_request(change_id: str, payload: ChangeRequestRejectPayload) -> ChangeRequestResponse:
    item = REPOSITORY.update_change_request_status(
        change_id,
        status="rejected",
        actor=payload.reviewer,
        comment=payload.reason,
    )
    if not item:
        raise HTTPException(status_code=404, detail="change request not found")
    return ChangeRequestResponse(**item)


@router.post("/rulesets/{ruleset_id}/activate", response_model=RulesetActivateResponse)
def activate_ruleset(ruleset_id: str, payload: RulesetActivateRequest) -> RulesetActivateResponse:
    try:
        activated = REPOSITORY.activate_ruleset(
            ruleset_id=ruleset_id,
            change_id=payload.change_id,
            caller=payload.caller,
            reason=payload.reason,
        )
    except GovernanceGateError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RulesetActivateResponse(
        ruleset_id=ruleset_id,
        change_id=payload.change_id,
        activated=True,
        active_ruleset_id=activated["ruleset_id"],
    )
