from __future__ import annotations

from uuid import uuid4

from packages.agent_runtime.models.runtime_result import RuntimeResult


class LegacyRuntime:
    def run_task(self, task_context: dict, ruleset: dict) -> RuntimeResult:
        return RuntimeResult(
            strategy="rule_only",
            confidence=0.45,
            evidence={
                "items": [
                    {
                        "runtime": "legacy",
                        "message": "fallback runtime",
                        "ruleset": ruleset.get("ruleset_id", "default"),
                    }
                ]
            },
            agent_run_id=f"legacy_{uuid4().hex[:10]}",
            raw_response={"task_context_keys": list(task_context.keys())},
        )
