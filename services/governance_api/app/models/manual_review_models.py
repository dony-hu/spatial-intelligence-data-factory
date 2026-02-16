from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ManualReviewItem(BaseModel):
    task_id: str
    raw_id: str
    raw_text: str
    canon_text: str
    confidence: float = Field(ge=0, le=1)
    strategy: str
    task_status: str
    review_status: str = ""
    reviewer: str = ""
    review_comment: str = ""
    reviewed_at: str = ""
    task_created_at: str = ""
    task_updated_at: str = ""
    canonical_updated_at: str = ""
    stage: str
    risk_level: str
    evidence_ref: str


class ManualReviewQueueResponse(BaseModel):
    as_of: str
    total: int
    pending: int
    items: list[ManualReviewItem]


class ManualReviewDecisionRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64)
    raw_id: str = Field(min_length=1, max_length=64)
    review_status: str = Field(pattern="^(approved|rejected|edited)$")
    reviewer: str = Field(min_length=1, max_length=128)
    next_route: str = Field(min_length=1, max_length=64)
    comment: str = Field(default="", max_length=2000)
    final_canon_text: Optional[str] = Field(default=None, max_length=1024)


class ManualReviewDecisionResponse(BaseModel):
    accepted: bool
    task_id: str
    raw_id: str
    review_status: str
    next_route: str
    audit_event_id: str = ""
    updated_count: int = 0
