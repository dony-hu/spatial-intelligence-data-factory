from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from services.governance_api.app.main import app


def _database_url() -> str:
    return str(os.getenv("DATABASE_URL") or "")


def _apply_schema(database_url: str) -> None:
    if database_url.startswith("sqlite"):
        from scripts.init_governance_sqlite import init_db
        path = database_url.replace("sqlite:///", "")
        init_db(path)
        return

    root = Path(__file__).resolve().parents[3]
    sql_paths = [
        root / "database" / "postgres" / "sql" / "001_enable_extensions.sql",
        root / "database" / "postgres" / "sql" / "002_init_tables.sql",
        root / "database" / "postgres" / "sql" / "003_init_indexes.sql",
    ]
    engine = create_engine(database_url)
    with engine.begin() as conn:
        for sql_path in sql_paths:
            conn.execute(text(sql_path.read_text(encoding="utf-8")))


def test_activate_ruleset_requires_approved_change_request_postgres() -> None:
    database_url = _database_url()
    if not database_url.startswith("postgresql") and not database_url.startswith("sqlite"):
        pytest.skip("requires DATABASE_URL=postgresql://... or sqlite://... for real DB integration")

    _apply_schema(database_url)
    client = TestClient(app)

    case_suffix = uuid4().hex[:8]
    target_ruleset_id = f"rule-pg-{case_suffix}"

    create_ruleset_resp = client.put(
        f"/v1/governance/rulesets/{target_ruleset_id}",
        json={
            "version": "v1",
            "is_active": False,
            "config_json": {"thresholds": {"t_high": 0.83, "t_low": 0.59}},
        },
    )
    assert create_ruleset_resp.status_code == 200

    create_change_resp = client.post(
        "/v1/governance/change-requests",
        json={
            "from_ruleset_id": "default",
            "to_ruleset_id": target_ruleset_id,
            "baseline_task_id": f"baseline-{case_suffix}",
            "candidate_task_id": f"candidate-{case_suffix}",
            "diff": {"thresholds": {"t_high": 0.83, "t_low": 0.59}},
            "scorecard": {"delta": {"auto_pass_rate": 0.02}},
            "recommendation": "accept",
            "evidence_bullets": ["auto pass up", "human required stable", "quality gate stable"],
        },
    )
    assert create_change_resp.status_code == 200
    change_id = create_change_resp.json()["change_id"]

    activate_pending = client.post(
        f"/v1/governance/rulesets/{target_ruleset_id}/activate",
        json={"change_id": change_id, "caller": "admin"},
    )
    assert activate_pending.status_code == 409
    assert activate_pending.json()["detail"]["code"] == "APPROVAL_PENDING"

    approve_resp = client.post(
        f"/v1/governance/change-requests/{change_id}/approve",
        json={"approver": "admin-reviewer", "comment": "approved for rollout"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    activate_ok = client.post(
        f"/v1/governance/rulesets/{target_ruleset_id}/activate",
        json={"change_id": change_id, "caller": "admin", "reason": "integration-promotion"},
    )
    assert activate_ok.status_code == 200

    engine = create_engine(database_url)
    with engine.begin() as conn:
        stored_change = conn.execute(
            text("SELECT status, approved_by FROM addr_change_request WHERE change_id = :change_id"),
            {"change_id": change_id},
        ).mappings().first()
        assert stored_change is not None
        assert stored_change["status"] == "approved"
        assert stored_change["approved_by"] == "admin-reviewer"

        target_ruleset = conn.execute(
            text("SELECT is_active FROM addr_ruleset WHERE ruleset_id = :ruleset_id"),
            {"ruleset_id": target_ruleset_id},
        ).mappings().first()
        assert target_ruleset is not None
        assert bool(target_ruleset["is_active"]) is True

        activated_event = conn.execute(
            text(
                """
                SELECT event_type, caller
                FROM addr_audit_event
                WHERE related_change_id = :change_id
                  AND event_type = 'ruleset_activated'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"change_id": change_id},
        ).mappings().first()
        assert activated_event is not None
        assert activated_event["event_type"] == "ruleset_activated"
        assert activated_event["caller"] == "admin"
