from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RulesetPayload(BaseModel):
    version: str = Field(min_length=1, max_length=64)
    config_json: Dict[str, Any]
    is_active: bool = False


class RulesetPublishRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class RulesetResponse(BaseModel):
    ruleset_id: str
    version: str
    is_active: bool
    config_json: Dict[str, Any]


class ChangeRequestCreatePayload(BaseModel):
    from_ruleset_id: str = Field(min_length=1, max_length=64)
    to_ruleset_id: str = Field(min_length=1, max_length=64)
    baseline_task_id: str = Field(min_length=1, max_length=64)
    candidate_task_id: str = Field(min_length=1, max_length=64)
    diff: Dict[str, Any] = Field(default_factory=dict)
    scorecard: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str = Field(pattern="^(accept|reject|needs-human)$")
    evidence_bullets: List[str] = Field(default_factory=list, max_length=3)


class ChangeRequestApprovalPayload(BaseModel):
    approver: str = Field(min_length=1, max_length=128)
    comment: Optional[str] = Field(default=None, max_length=512)


class ChangeRequestRejectPayload(BaseModel):
    reviewer: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)


class ChangeRequestResponse(BaseModel):
    change_id: str
    from_ruleset_id: str
    to_ruleset_id: str
    baseline_task_id: str
    candidate_task_id: str
    diff: Dict[str, Any] = Field(default_factory=dict)
    scorecard: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    review_comment: Optional[str] = None
    evidence_bullets: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RulesetActivateRequest(BaseModel):
    change_id: str = Field(min_length=1, max_length=64)
    caller: str = Field(min_length=1, max_length=128)
    reason: Optional[str] = Field(default=None, max_length=512)


class RulesetActivateResponse(BaseModel):
    ruleset_id: str
    change_id: str
    activated: bool
    active_ruleset_id: str
