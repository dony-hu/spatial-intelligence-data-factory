from __future__ import annotations

import os
from datetime import datetime, timezone

from packages.address_core.pipeline import run as run_address_pipeline
from packages.agent_runtime.runtime_selector import get_runtime
from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_worker.app.jobs.ingest_job import run as ingest_run
from services.governance_worker.app.jobs.result_persist_job import persist_results


def _resolve_ruleset_context(ruleset_id: str) -> dict:
    context = {"ruleset_id": ruleset_id}
    ruleset = REPOSITORY.get_ruleset(ruleset_id)
    config = ruleset.get("config_json") if isinstance(ruleset, dict) else None
    if isinstance(config, dict):
        context.update(config)
    return context


def _new_trust_provider():
    from services.trust_data_hub.app.repositories.trustdb_persister import TrustDbPersister

    return TrustDbPersister()


def _resolve_trust_provider(ruleset_context: dict):
    trust_required = bool(ruleset_context.get("require_trust_enhancement", False))
    trust_namespace = str(ruleset_context.get("trust_namespace") or "").strip()
    if not trust_required and not trust_namespace:
        return None
    provider = _new_trust_provider()
    if provider.enabled():
        return provider
    if trust_required:
        raise RuntimeError("blocked: trust provider unavailable")
    return None


def run(task_payload: dict) -> dict:
    task_id = task_payload.get("task_id")
    trace_id = str(task_payload.get("trace_id") or f"trace_{task_id or 'unknown'}")
    REPOSITORY.set_task_status(task_id, "RUNNING")
    REPOSITORY.record_observation_event(
        source_service="governance_worker",
        event_type="task_running",
        status="success",
        trace_id=trace_id,
        task_id=str(task_id or ""),
        ruleset_id=str(task_payload.get("ruleset_id") or ""),
        payload={"stage": "start"},
    )
    try:
        processed = ingest_run(task_payload)
        ruleset_context = _resolve_ruleset_context(str(processed.get("ruleset_id", "default")))
        trust_provider = _resolve_trust_provider(ruleset_context)
        if trust_provider is None:
            pipeline_outputs = run_address_pipeline(
                processed.get("records", []),
                ruleset_context,
            )
        else:
            pipeline_outputs = run_address_pipeline(
                processed.get("records", []),
                ruleset_context,
                trust_provider=trust_provider,
            )
        runtime = get_runtime()
        runtime_result = runtime.run_task(
            task_context={
                "task_id": processed.get("task_id"),
                "trace_id": trace_id,
                "records": processed.get("records", []),
            },
            ruleset={"ruleset_id": processed.get("ruleset_id", "default")},
        )
        output = persist_results(processed, runtime_result.model_dump(), pipeline_outputs)
        REPOSITORY.record_observation_event(
            source_service="governance_worker",
            event_type="task_succeeded",
            status="success",
            trace_id=trace_id,
            task_id=str(task_id or ""),
            ruleset_id=str(task_payload.get("ruleset_id") or ""),
            payload={"result_status": output.get("status", "")},
        )
        return output
    except Exception as exc:
        message = str(exc)
        if "blocked:" in message:
            reason = message.split("blocked:", 1)[1].strip() or "unknown_blocked_reason"
            REPOSITORY.set_task_status(task_id, "BLOCKED")
            REPOSITORY.log_blocked_confirmation(
                event_type="governance_job_blocked",
                caller="governance_worker",
                payload={
                    "task_id": task_id,
                    "reason": reason,
                    "confirmation_user": "pending_owner",
                    "confirmation_decision": "pending",
                    "confirmation_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            REPOSITORY.record_observation_event(
                source_service="governance_worker",
                event_type="task_blocked",
                status="blocked",
                severity="error",
                trace_id=trace_id,
                task_id=str(task_id or ""),
                ruleset_id=str(task_payload.get("ruleset_id") or ""),
                payload={"reason": reason},
            )
            return {"task_id": task_id, "status": "BLOCKED", "block_reason": reason}
        REPOSITORY.set_task_status(task_id, "FAILED")
        REPOSITORY.record_observation_event(
            source_service="governance_worker",
            event_type="task_failed",
            status="error",
            severity="error",
            trace_id=trace_id,
            task_id=str(task_id or ""),
            ruleset_id=str(task_payload.get("ruleset_id") or ""),
            payload={"error": message[:400]},
        )
        return {"task_id": task_id, "status": "FAILED"}
