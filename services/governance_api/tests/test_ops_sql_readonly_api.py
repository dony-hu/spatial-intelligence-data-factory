from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_api.app.routers import ops


def test_readonly_sql_query_accepts_select_with_limit_and_audit(monkeypatch) -> None:
    monkeypatch.setattr(
        ops,
        "_execute_postgres_readonly",
        lambda _sql, _timeout_ms: (["value"], [{"value": 1}], 12),
    )
    client = TestClient(app)
    before = len(REPOSITORY.list_audit_events())
    response = client.post(
        "/v1/governance/ops/sql/read-only-query",
        json={
            "caller": "panel-qa",
            "limit": 1,
            "timeout_ms": 1200,
            "sql": "WITH t AS (SELECT 1 AS value UNION ALL SELECT 2 AS value) SELECT value FROM t",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["datasource"] == "postgres"
    assert data["row_count"] == 1
    assert data["applied_limit"] == 1
    assert "value" in data["columns"]
    after_events = REPOSITORY.list_audit_events()
    assert len(after_events) >= before + 1
    assert any(event.get("event_type") == "readonly_sql_query_executed" for event in after_events[before:])


def test_readonly_sql_query_rejects_non_select_statement() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/governance/ops/sql/read-only-query",
        json={
            "caller": "panel-qa",
            "sql": "DELETE FROM process_definition",
        },
    )
    assert response.status_code == 400
    detail = response.json().get("detail", {})
    assert detail.get("code") == "SQL_READONLY_ONLY"


def test_readonly_sql_query_rejects_non_whitelisted_table() -> None:
    client = TestClient(app)
    before = len(REPOSITORY.list_audit_events())
    response = client.post(
        "/v1/governance/ops/sql/read-only-query",
        json={
            "caller": "panel-qa",
            "sql": "SELECT tablename FROM pg_catalog.pg_tables",
        },
    )
    assert response.status_code == 403
    detail = response.json().get("detail", {})
    assert detail.get("code") == "SQL_TABLE_NOT_ALLOWED"
    after_events = REPOSITORY.list_audit_events()
    assert len(after_events) >= before + 1
    assert any(event.get("event_type") == "readonly_sql_query_blocked" for event in after_events[before:])


def test_readonly_sql_query_timeout_is_enforced(monkeypatch) -> None:
    def _raise_timeout(_sql: str, _timeout_ms: int):
        raise ops.HTTPException(status_code=408, detail={"code": "SQL_TIMEOUT", "message": "query timeout"})

    monkeypatch.setattr(ops, "_execute_postgres_readonly", _raise_timeout)
    client = TestClient(app)
    response = client.post(
        "/v1/governance/ops/sql/read-only-query",
        json={
            "caller": "panel-qa",
            "limit": 50,
            "timeout_ms": 100,
            "sql": (
                "WITH RECURSIVE cnt(x) AS ("
                "VALUES(0) "
                "UNION ALL SELECT x + 1 FROM cnt WHERE x < 100000000"
                ") SELECT sum(x) AS total FROM cnt"
            ),
        },
    )
    assert response.status_code == 408
    detail = response.json().get("detail", {})
    assert detail.get("code") == "SQL_TIMEOUT"
