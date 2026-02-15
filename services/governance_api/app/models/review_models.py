from pydantic import BaseModel, Field
from typing import Optional


class ReviewDecisionRequest(BaseModel):
    raw_id: Optional[str] = Field(default=None, min_length=1, max_length=64)
    review_status: str = Field(pattern="^(approved|rejected|edited)$")
    final_canon_text: Optional[str] = Field(default=None, max_length=2048)
    reviewer: str = Field(min_length=1, max_length=128)
    comment: Optional[str] = Field(default=None, max_length=1024)


class ReviewDecisionResponse(BaseModel):
    task_id: str
    review_status: str
    accepted: bool
    updated_count: int = 0
    target_raw_id: Optional[str] = None
