from __future__ import annotations

from datetime import datetime, timezone

from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_worker.app.jobs.ingest_job import run as ingest_run
from services.governance_worker.app.jobs.result_persist_job import persist_results
from services.governance_worker.app.runtime.workpackage_executor import WorkpackageExecutor


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
        workpackage_id = str(processed.get("workpackage_id") or "").strip()
        version = str(processed.get("version") or "").strip()
        if not workpackage_id or not version:
            raise RuntimeError("blocked: worker requires workpackage_id/version")
        published = REPOSITORY.get_runtime_workpackage_record(
            workpackage_id=workpackage_id,
            version=version,
            include_deleted=False,
        )
        if not published:
            raise RuntimeError(f"blocked: runtime workpackage record not found: {workpackage_id}@{version}")
        executor = WorkpackageExecutor()
        execution = executor.execute(
            workpackage_id=workpackage_id,
            version=version,
            task_context={
                "task_id": processed.get("task_id"),
                "trace_id": trace_id,
                "records": processed.get("records", []),
            },
            ruleset={"ruleset_id": processed.get("ruleset_id", "default")},
        )
        output = persist_results(processed, execution.runtime_result, execution.records)
        REPOSITORY.record_observation_event(
            source_service="governance_worker",
            event_type="task_succeeded",
            status="success",
            trace_id=trace_id,
            task_id=str(task_id or ""),
            ruleset_id=str(task_payload.get("ruleset_id") or ""),
            payload={
                "result_status": output.get("status", ""),
                "workpackage_id": workpackage_id,
                "version": version,
                "runtime_report_path": execution.report_path,
            },
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
