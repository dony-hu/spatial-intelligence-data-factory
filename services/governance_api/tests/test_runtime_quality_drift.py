from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_quality_drift_data() -> None:
    # Baseline quality metrics: high quality.
    REPOSITORY.upsert_observation_metric(
        metric_name="runtime.quality.normalization_coverage",
        metric_value=0.96,
        labels={"profile": "baseline-seed"},
    )
    REPOSITORY.upsert_observation_metric(
        metric_name="runtime.quality.district_match_rate",
        metric_value=0.95,
        labels={"profile": "baseline-seed"},
    )
    REPOSITORY.upsert_observation_metric(
        metric_name="runtime.quality.low_confidence_ratio",
        metric_value=0.08,
        labels={"profile": "baseline-seed"},
    )
    REPOSITORY.upsert_observation_metric(
        metric_name="runtime.quality.blocked_reason_stability",
        metric_value=0.72,
        labels={"profile": "baseline-seed"},
    )

    for idx in range(10):
        task_id = f"task_quality_drift_{idx:03d}"
        status = "SUCCEEDED" if idx < 5 else ("BLOCKED" if idx < 8 else "FAILED")
        queue_message = "district_mismatch" if status == "BLOCKED" else "seeded"
        REPOSITORY.create_task(
            task_id=task_id,
            batch_name="runtime-quality-drift-seed",
            ruleset_id="default",
            status=status,
            queue_backend="sync",
            queue_message=queue_message,
            trace_id=f"trace_quality_drift_{idx:03d}",
        )
        REPOSITORY.save_raw_records(
            task_id=task_id,
            raw_records=[{"raw_id": f"raw_{task_id}_00", "raw_text": "北京市朝阳区建国路88号"}],
        )
        if status == "SUCCEEDED":
            REPOSITORY.save_results(
                task_id=task_id,
                results=[
                    {
                        "raw_id": f"raw_{task_id}_00",
                        "canon_text": "北京市朝阳区建国路88号",
                        "confidence": 0.62 if idx % 2 == 0 else 0.79,
                        "strategy": "human_required",
                        "evidence": {"items": [{"kind": "seed"}]},
                    }
                ],
                raw_records=[{"raw_id": f"raw_{task_id}_00", "raw_text": "北京市朝阳区建国路88号"}],
            )


def test_runtime_quality_drift_summary_contract() -> None:
    client = TestClient(app)
    _seed_quality_drift_data()
    resp = client.get("/v1/governance/observability/runtime/quality-drift/summary?window=24h&baseline_profile=baseline-seed")
    assert resp.status_code == 200
    payload = resp.json()
    assert "candidate_metrics" in payload
    assert "baseline_metrics" in payload
    assert "drift" in payload
    assert "anomalies" in payload
    assert "sample_task_ids" in payload
    assert isinstance(payload["sample_task_ids"], list)


def test_runtime_quality_drift_evaluate_contract() -> None:
    client = TestClient(app)
    _seed_quality_drift_data()
    resp = client.post("/v1/governance/observability/runtime/quality-drift/evaluate?window=24h&baseline_profile=baseline-seed")
    assert resp.status_code == 200
    payload = resp.json()
    assert "triggered_alerts" in payload
    assert "triggered_count" in payload
    assert int(payload.get("violation_count") or 0) >= 1
