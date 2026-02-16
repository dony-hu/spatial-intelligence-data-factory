from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from services.governance_api.app.models.task_models import AddressRecordInput


class LabOptimizeRequest(BaseModel):
    caller: str = Field(default="lab_operator", min_length=1, max_length=128)
    sample_spec: str = Field(default="sample", min_length=1, max_length=64)
    sample_size: int = Field(default=20, ge=1, le=200)
    candidate_count: int = Field(default=3, ge=1, le=3)
    records: List[AddressRecordInput] = Field(min_length=1, max_length=200)


class LabOptimizeResponse(BaseModel):
    baseline_run_id: str
    candidate_run_ids: List[str] = Field(default_factory=list)
    change_id: str
    recommendation: str
    top_evidence_bullets: List[str] = Field(default_factory=list)


class LabSampleDelta(BaseModel):
    raw_id: str
    baseline_confidence: float
    candidate_confidence: float
    confidence_delta: float
    baseline_strategy: str
    candidate_strategy: str
    baseline_canon_text: str
    candidate_canon_text: str
    evidence_summary: List[Dict[str, Any]] = Field(default_factory=list)


class LabReplayResponse(BaseModel):
    change_id: str
    from_ruleset_id: str
    to_ruleset_id: str
    baseline_run_id: str
    candidate_run_id: str
    recommendation: str
    status: str
    scorecard: Dict[str, Any] = Field(default_factory=dict)
    diff: Dict[str, Any] = Field(default_factory=dict)
    evidence_bullets: List[str] = Field(default_factory=list)
    improved_samples: List[LabSampleDelta] = Field(default_factory=list)
    worsened_samples: List[LabSampleDelta] = Field(default_factory=list)
    audit_events: List[Dict[str, Any]] = Field(default_factory=list)
    activation: Dict[str, Any] = Field(default_factory=dict)


class FengtuNetworkStatusResponse(BaseModel):
    enabled: bool
    confirmation_required: bool
    last_network_error: str = ""
    last_confirm_by: str = ""


class FengtuConfirmNetworkPayload(BaseModel):
    operator: str = Field(min_length=1, max_length=128)


class FengtuConflictItem(BaseModel):
    case_id: str
    raw_text: str
    expected_normalized: str
    fengtu_candidate: str
    note: str = "pending_user_confirmation"
    status: str = "pending"
    decision: str = ""
    decision_comment: str = ""
    decided_by: str = ""
    decided_at: str = ""


class FengtuConflictListResponse(BaseModel):
    report_path: str
    total_conflicts: int
    pending_conflicts: int
    resolved_conflicts: int
    items: List[FengtuConflictItem] = Field(default_factory=list)


class FengtuConflictDecisionPayload(BaseModel):
    operator: str = Field(min_length=1, max_length=128)
    decision: str = Field(pattern="^(accept_expected|accept_fengtu|needs-investigation)$")
    comment: str = Field(default="", max_length=1024)


class FengtuConflictDecisionResponse(BaseModel):
    case_id: str
    status: str
    decision: str
    comment: str
    decided_by: str
    decided_at: str


class LabCoverageRunRequest(BaseModel):
    dataset: str = Field(default="testdata/fixtures/lab-mode-phase1_5-中文地址测试用例-1300-2026-02-15.csv")
    limit: Optional[int] = Field(default=None, ge=1, le=5000)
    enable_fengtu: bool = True


class LabCoverageRunResponse(BaseModel):
    accepted: bool
    status: str
    message: str
    progress_path: str
    report_path: str = ""


class LabCoverageStatusResponse(BaseModel):
    status: str
    started_at: str = ""
    updated_at: str = ""
    processed_rows: int = 0
    total_rows: int = 0
    progress_rate: float = 0.0
    last_case_id: str = ""
    report_path: str = ""
    message: str = ""


class LabSqlQueryRequest(BaseModel):
    operator: str = Field(default="lab_operator", min_length=1, max_length=128)
    sql: str = Field(min_length=1, max_length=10000)
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=50, ge=1, le=200)


class LabSqlQueryResponse(BaseModel):
    success: bool
    code: str = ""
    message: str = ""
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total_rows: int = 0
    page: int = 1
    page_size: int = 50
    elapsed_ms: int = 0
    sql_summary: str = ""
    effective_limit: int = 0


class LabSqlTemplatesResponse(BaseModel):
    templates: List[Dict[str, str]] = Field(default_factory=list)
    whitelist_tables: List[str] = Field(default_factory=list)
    max_rows: int = 200
    timeout_sec: float = 2.0


class LabSqlHistoryResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
