from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RuntimeResult(BaseModel):
    strategy: str = "human_required"
    canonical: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0, le=1)
    evidence: dict[str, Any] = Field(default_factory=lambda: {"items": []})
    actions: list[dict[str, Any]] = Field(default_factory=list)
    agent_run_id: str = "local-placeholder-run"
    raw_response: dict[str, Any] = Field(default_factory=dict)
