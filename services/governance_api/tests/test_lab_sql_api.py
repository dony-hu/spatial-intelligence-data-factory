from pathlib import Path

from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.routers import lab


def test_lab_sql_templates_and_history_empty(tmp_path: Path) -> None:
    history_path = tmp_path / "history.json"
    lab._SQL_HISTORY_PATH = history_path
    lab._SQL_ALLOWED_TABLES = {"failure_queue", "replay_runs"}

    client = TestClient(app)
    templates = client.get("/v1/governance/lab/sql/templates")
    assert templates.status_code == 200
    payload = templates.json()
    assert payload["max_rows"] == 200
    assert "failure_queue" in payload["whitelist_tables"]

    history = client.get("/v1/governance/lab/sql/history")
    assert history.status_code == 200
    assert history.json()["total"] == 0


def test_lab_sql_query_enforces_readonly_whitelist_and_limit(tmp_path: Path, monkeypatch) -> None:
    history_path = tmp_path / "history.json"
    lab._SQL_HISTORY_PATH = history_path
    lab._SQL_ALLOWED_TABLES = {"failure_queue", "replay_runs"}
    monkeypatch.setattr(
        lab,
        "_execute_lab_postgres_readonly",
        lambda _sql, _timeout_sec: (
            ["id", "case_id", "reason"],
            [
                {"id": 1, "case_id": "CNADDR-0001", "reason": "mismatch"},
                {"id": 2, "case_id": "CNADDR-0002", "reason": "mismatch"},
                {"id": 3, "case_id": "CNADDR-0003", "reason": "mismatch"},
                {"id": 4, "case_id": "CNADDR-0004", "reason": "mismatch"},
                {"id": 5, "case_id": "CNADDR-0005", "reason": "mismatch"},
            ],
        ),
    )

    client = TestClient(app)
    ok = client.post(
        "/v1/governance/lab/sql/query",
        json={
            "operator": "tester",
            "sql": "SELECT id, case_id, reason FROM failure_queue ORDER BY id LIMIT 9999",
            "page": 1,
            "page_size": 2,
        },
    )
    assert ok.status_code == 200
    ok_payload = ok.json()
    assert ok_payload["success"] is True
    assert ok_payload["effective_limit"] == 200
    assert ok_payload["total_rows"] == 5
    assert len(ok_payload["rows"]) == 2

    readonly_block = client.post(
        "/v1/governance/lab/sql/query",
        json={"operator": "tester", "sql": "DELETE FROM failure_queue"},
    )
    assert readonly_block.status_code == 400
    assert readonly_block.json()["detail"]["code"] == "readonly_enforced"

    whitelist_block = client.post(
        "/v1/governance/lab/sql/query",
        json={"operator": "tester", "sql": "SELECT tablename FROM pg_catalog.pg_tables"},
    )
    assert whitelist_block.status_code == 400
    assert whitelist_block.json()["detail"]["code"] == "table_whitelist_enforced"

    history = client.get("/v1/governance/lab/sql/history")
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) >= 3
    assert any(item.get("status") == "success" for item in items)
    assert any(item.get("status") == "error" for item in items)
