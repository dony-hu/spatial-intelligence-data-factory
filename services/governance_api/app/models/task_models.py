from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AddressRecordInput(BaseModel):
    raw_id: str = Field(min_length=1, max_length=64)
    raw_text: str = Field(min_length=1, max_length=1024)
    province: Optional[str] = Field(default=None, max_length=64)
    city: Optional[str] = Field(default=None, max_length=64)
    district: Optional[str] = Field(default=None, max_length=64)
    street: Optional[str] = Field(default=None, max_length=128)
    detail: Optional[str] = Field(default=None, max_length=1024)


class TaskSubmitRequest(BaseModel):
    idempotency_key: str = Field(min_length=6, max_length=128)
    batch_name: str = Field(min_length=1, max_length=255)
    ruleset_id: str = Field(min_length=1, max_length=64)
    records: List[AddressRecordInput] = Field(min_length=1, max_length=2000)


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str


class EvidenceSummary(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)


class CanonicalAddressResult(BaseModel):
    raw_id: str
    canon_text: str
    confidence: float = Field(ge=0, le=1)
    strategy: str
    evidence: EvidenceSummary


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    results: List[CanonicalAddressResult] = Field(default_factory=list)
