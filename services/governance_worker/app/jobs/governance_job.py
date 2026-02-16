from __future__ import annotations

import os

from packages.address_core.pipeline import run as run_address_pipeline
from packages.agent_runtime.runtime_selector import get_runtime
from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_worker.app.jobs.ingest_job import run as ingest_run
from services.governance_worker.app.jobs.result_persist_job import persist_results


def run(task_payload: dict) -> dict:
    task_id = task_payload.get("task_id")
    REPOSITORY.set_task_status(task_id, "RUNNING")
    original_strict = os.getenv("OPENHANDS_STRICT")
    if original_strict is None:
        os.environ["OPENHANDS_STRICT"] = "0"
    try:
        processed = ingest_run(task_payload)
        pipeline_outputs = run_address_pipeline(
            processed.get("records", []),
            {"ruleset_id": processed.get("ruleset_id", "default")},
        )
        runtime = get_runtime()
        runtime_result = runtime.run_task(
            task_context={
                "task_id": processed.get("task_id"),
                "records": processed.get("records", []),
            },
            ruleset={"ruleset_id": processed.get("ruleset_id", "default")},
        )
        return persist_results(processed, runtime_result.model_dump(), pipeline_outputs)
    except Exception:
        REPOSITORY.set_task_status(task_id, "FAILED")
        return {"task_id": task_id, "status": "FAILED"}
    finally:
        if original_strict is None:
            os.environ.pop("OPENHANDS_STRICT", None)
        else:
            os.environ["OPENHANDS_STRICT"] = original_strict
