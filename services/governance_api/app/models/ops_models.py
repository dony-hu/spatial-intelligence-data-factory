from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class OpsSummaryResponse(BaseModel):
    total_tasks: int = Field(ge=0)
    status_counts: Dict[str, int] = Field(default_factory=dict)
    total_results: int = Field(ge=0)
    avg_confidence: float = Field(ge=0, le=1)
    pending_review_tasks: int = Field(ge=0)
    reviewed_tasks: int = Field(ge=0)
    active_ruleset_id: str
    thresholds: Dict[str, float] = Field(default_factory=dict)
    low_confidence_results: int = Field(ge=0)
    quality_gate_passed: bool
    quality_gate_reasons: List[str] = Field(default_factory=list)
