from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InMemoryStore:
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    reviews: dict[str, dict[str, Any]] = field(default_factory=dict)
    rulesets: dict[str, dict[str, Any]] = field(default_factory=dict)


STORE = InMemoryStore(
    rulesets={
        "default": {
            "ruleset_id": "default",
            "version": "v0",
            "is_active": True,
            "config_json": {"thresholds": {"t_high": 0.85, "t_low": 0.6}},
        }
    }
)
