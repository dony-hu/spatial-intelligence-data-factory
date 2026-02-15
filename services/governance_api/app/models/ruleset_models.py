from __future__ import annotations

from typing import Any, Dict

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
