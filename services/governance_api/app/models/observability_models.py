from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ObservationEvent(BaseModel):
    event_id: str
    trace_id: str
    span_id: str = ""
    source_service: str
    event_type: str
    status: str
    severity: str
    task_id: str = ""
    workpackage_id: str = ""
    ruleset_id: str = ""
    payload_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ObservationEventsResponse(BaseModel):
    total: int = Field(ge=0)
    items: List[ObservationEvent] = Field(default_factory=list)


class ObservationTraceReplayResponse(BaseModel):
    trace_id: str
    total: int = Field(ge=0)
    timeline: List[ObservationEvent] = Field(default_factory=list)


class ObservationMetricPoint(BaseModel):
    metric_id: str
    metric_name: str
    metric_value: float
    labels_json: Dict[str, Any] = Field(default_factory=dict)
    window_start: str = ""
    window_end: str = ""
    created_at: str


class ObservationTimeseriesResponse(BaseModel):
    metric_name: str
    total: int = Field(ge=0)
    points: List[ObservationMetricPoint] = Field(default_factory=list)


class ObservationAlert(BaseModel):
    alert_id: str
    alert_rule: str
    severity: str
    status: str
    trigger_value: float
    threshold_value: float
    trace_id: str = ""
    task_id: str = ""
    workpackage_id: str = ""
    owner: str = ""
    ack_by: str = ""
    ack_at: str = ""
    created_at: str
    updated_at: str


class ObservationAlertsResponse(BaseModel):
    total: int = Field(ge=0)
    items: List[ObservationAlert] = Field(default_factory=list)


class ObservationAlertAckRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=128)


class ObservationSnapshotResponse(BaseModel):
    environment: str
    kpis: Dict[str, Any] = Field(default_factory=dict)
    metrics: List[ObservationMetricPoint] = Field(default_factory=list)
    alerts: List[ObservationAlert] = Field(default_factory=list)


class RuntimeWorkpackageRecord(BaseModel):
    workpackage_id: str
    version: str
    name: str = ""
    objective: str = ""
    status: str = "created"
    deleted_at: str = ""
    created_at: str = ""
    updated_at: str = ""
    updated_by: str = ""


class RuntimeWorkpackageCreateRequest(BaseModel):
    workpackage_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    name: str = ""
    objective: str = Field(min_length=1)
    status: str = "created"
    actor: str = ""


class RuntimeWorkpackageUpdateRequest(BaseModel):
    name: str | None = None
    objective: str | None = None
    status: str | None = None
    actor: str = ""
