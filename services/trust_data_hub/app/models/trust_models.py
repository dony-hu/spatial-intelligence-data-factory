from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SourceUpsertRequest(BaseModel):
    name: str
    category: str
    trust_level: Literal["authoritative", "open_license", "community_derived", "unknown"]
    license: str
    entrypoint: str
    update_frequency: str
    fetch_method: str
    parser_profile: dict[str, Any] = Field(default_factory=dict)
    validator_profile: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    allowed_use_notes: str
    access_mode: Literal["download", "api", "manual"]
    robots_tos_flags: dict[str, Any] = Field(default_factory=dict)


class PromoteRequest(BaseModel):
    snapshot_id: str
    activated_by: str
    activation_note: str = ""
    confirm_high_diff: bool = False


class DiffRequest(BaseModel):
    base_snapshot_id: str
    new_snapshot_id: str


class SourceScheduleUpsertRequest(BaseModel):
    schedule_type: Literal["cron", "interval"]
    schedule_spec: str
    window_policy: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ValidationEvidenceRequest(BaseModel):
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    road: Optional[str] = None
    street: Optional[str] = None
    poi: Optional[str] = None
    detail: Optional[str] = None
