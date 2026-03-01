from __future__ import annotations

import os

os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://si_factory_user:SiFactory2026@127.0.0.1:5432/si_factory")
os.environ["OBSERVABILITY_ONCALL_TOKEN"] = os.getenv("OBSERVABILITY_ONCALL_TOKEN", "oncall-token-local")

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def _seed_unhealthy_runtime_sample() -> None:
    for idx in range(12):
        task_id = f"task_runtime_slo_{idx:03d}"
        status = "SUCCEEDED" if idx < 7 else ("BLOCKED" if idx < 10 else "FAILED")
        REPOSITORY.create_task(
            task_id=task_id,
            batch_name="runtime-sli-slo-seed",
            ruleset_id="default",
            status=status,
            queue_backend="sync",
            queue_message="seeded",
            trace_id=f"trace_runtime_slo_{idx:03d}",
        )
        REPOSITORY.save_raw_records(
            task_id=task_id,
            raw_records=[{"raw_id": f"raw_{task_id}_00", "raw_text": "上海市徐汇区肇嘉浜路111号"}],
        )
        if status == "SUCCEEDED":
            REPOSITORY.save_results(
                task_id=task_id,
                results=[
                    {
                        "raw_id": f"raw_{task_id}_00",
                        "canon_text": "上海市徐汇区肇嘉浜路111号",
                        "confidence": 0.72,
                        "strategy": "human_required",
                        "evidence": {"items": [{"kind": "seed"}]},
                    }
                ],
                raw_records=[{"raw_id": f"raw_{task_id}_00", "raw_text": "上海市徐汇区肇嘉浜路111号"}],
            )
        REPOSITORY.record_observation_event(
            source_service="governance_worker",
            event_type="task_finished",
            status="success" if status == "SUCCEEDED" else "error",
            severity="info" if status == "SUCCEEDED" else "warning",
            trace_id=f"trace_runtime_slo_{idx:03d}",
            task_id=task_id,
            payload={"duration_ms": 1200 + idx * 200},
        )


def test_runtime_reliability_summary_and_evaluate_contract() -> None:
    client = TestClient(app)
    _seed_unhealthy_runtime_sample()

    summary_resp = client.get("/v1/governance/observability/runtime/reliability/summary?window=24h")
    assert summary_resp.status_code == 200
    summary_payload = summary_resp.json()
    assert "sli" in summary_payload
    assert "slo" in summary_payload
    assert "error_budget" in summary_payload
    assert "violations" in summary_payload
    assert "open_alerts" in summary_payload

    eval_resp = client.post("/v1/governance/observability/runtime/reliability/evaluate?window=24h")
    assert eval_resp.status_code == 200
    eval_payload = eval_resp.json()
    assert "triggered_alerts" in eval_payload
    assert isinstance(eval_payload["triggered_alerts"], list)
    assert int(eval_payload.get("violation_count") or 0) >= 1

    # Suppression should dedupe second evaluation call.
    eval_resp_2 = client.post("/v1/governance/observability/runtime/reliability/evaluate?window=24h")
    assert eval_resp_2.status_code == 200
    eval_payload_2 = eval_resp_2.json()
    assert int(eval_payload_2.get("triggered_count") or 0) == 0


def test_runtime_reliability_alert_ack_writes_audit_log() -> None:
    client = TestClient(app)
    _seed_unhealthy_runtime_sample()
    eval_resp = client.post("/v1/governance/observability/runtime/reliability/evaluate?window=24h")
    assert eval_resp.status_code == 200
    alerts = (eval_resp.json() or {}).get("triggered_alerts", [])
    if not alerts:
        # In case suppression by previous tests already opened alert, read existing open alerts.
        open_alerts = client.get("/v1/governance/observability/alerts?status=open").json().get("items", [])
        assert open_alerts
        alert_id = str(open_alerts[0]["alert_id"])
    else:
        alert_id = str(alerts[0]["alert_id"])

    ack = client.post(
        f"/v1/governance/observability/alerts/{alert_id}/ack?role=oncall&actor=ops_owner",
        headers={"x-observability-token": "oncall-token-local"},
        json={"actor": "ops_owner"},
    )
    assert ack.status_code == 200
    assert ack.json().get("status") == "acked"

    found = False
    for evt in REPOSITORY.list_audit_events():
        payload = evt.get("payload") if isinstance(evt.get("payload"), dict) else {}
        if str(evt.get("event_type") or "") == "observation_alert_acked" and str(payload.get("alert_id") or "") == alert_id:
            found = True
            break
    assert found
