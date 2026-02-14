from __future__ import annotations

from services.governance_api.app.models.task_models import CanonicalAddressResult, EvidenceSummary
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def persist_results(task_payload: dict, runtime_result: dict, pipeline_outputs: list[dict] | None = None) -> dict:
    task_id = task_payload["task_id"]
    records = task_payload.get("records", [])
    pipeline_outputs = pipeline_outputs or []
    strategy = runtime_result.get("strategy", "human_required")
    runtime_confidence = float(runtime_result.get("confidence", 0.5))
    runtime_evidence_items = runtime_result.get("evidence", {}).get("items", [])

    by_raw_id = {item.get("raw_id"): item for item in pipeline_outputs}

    REPOSITORY.save_results(
        task_id,
        [
        CanonicalAddressResult(
            raw_id=item.get("raw_id"),
            canon_text=by_raw_id.get(item.get("raw_id"), {}).get("canon_text", item.get("raw_text", "").strip()),
            confidence=float(by_raw_id.get(item.get("raw_id"), {}).get("confidence", runtime_confidence)),
            strategy=by_raw_id.get(item.get("raw_id"), {}).get("strategy", strategy),
            evidence=EvidenceSummary(
                items=by_raw_id.get(item.get("raw_id"), {}).get("evidence", {}).get("items", [])
                + runtime_evidence_items
            ),
        ).model_dump()
        for item in records
    ],
        raw_records=records,
    )
    REPOSITORY.set_task_status(task_id, "SUCCEEDED")
    return {"task_id": task_id, "status": "SUCCEEDED"}
