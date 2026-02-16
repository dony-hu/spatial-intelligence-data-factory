from __future__ import annotations

from typing import Any, Dict, List

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


class ScorecardMetrics(BaseModel):
    auto_pass_rate: float = Field(ge=0, le=1)
    review_rate: float = Field(ge=0, le=1)
    human_required_rate: float = Field(ge=0, le=1)
    consistency_score: float = Field(ge=0, le=1)
    quality_gate_pass_rate: float = Field(ge=0, le=1)
    review_accept_rate: float = Field(ge=0, le=1)


class ScorecardCompareResponse(BaseModel):
    baseline_task_id: str
    candidate_task_id: str
    thresholds: Dict[str, float] = Field(default_factory=dict)
    baseline: ScorecardMetrics
    candidate: ScorecardMetrics
    delta: ScorecardMetrics
    recommendation: str
    reasons: List[str] = Field(default_factory=list)


class ReadOnlySqlQueryRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20000)
    caller: str = Field(default="panel_user", min_length=1, max_length=128)
    limit: int = Field(default=200, ge=1, le=1000)
    timeout_ms: int = Field(default=1500, ge=100, le=10000)


class ReadOnlySqlQueryResponse(BaseModel):
    status: str
    datasource: str
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    applied_limit: int = Field(ge=1)
