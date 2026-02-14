from __future__ import annotations

from typing import Protocol

from packages.agent_runtime.models.runtime_result import RuntimeResult


class AgentRuntimeAdapter(Protocol):
    def run_task(self, task_context: dict, ruleset: dict) -> RuntimeResult:
        ...
