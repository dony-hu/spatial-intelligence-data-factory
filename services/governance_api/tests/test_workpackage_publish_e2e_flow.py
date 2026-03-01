from __future__ import annotations

import os
from pathlib import Path


from fastapi.testclient import TestClient

from packages.factory_agent.agent import FactoryAgent
from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_agent_publish_then_query_api_end_to_end(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    bundle_v300 = Path("workpackages/bundles/e2e-demo-v3.0.0")
    bundle_v300.mkdir(parents=True, exist_ok=True)
    (bundle_v300 / "workpackage.json").write_text(
        '{"name":"e2e-demo","version":"v3.0.0","sources":["gaode","baidu"]}',
        encoding="utf-8",
    )
    (bundle_v300 / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    (bundle_v300 / "skills").mkdir(exist_ok=True)
    (bundle_v300 / "observability").mkdir(exist_ok=True)
    bundle_v310 = Path("workpackages/bundles/e2e-demo-v3.1.0")
    bundle_v310.mkdir(parents=True, exist_ok=True)
    (bundle_v310 / "workpackage.json").write_text(
        '{"name":"e2e-demo","version":"v3.1.0","sources":["gaode","baidu","amap"]}',
        encoding="utf-8",
    )
    (bundle_v310 / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    (bundle_v310 / "skills").mkdir(exist_ok=True)
    (bundle_v310 / "observability").mkdir(exist_ok=True)

    agent = FactoryAgent()
    publish_v300 = agent.converse("发布 e2e-demo-v3.0.0 到 runtime")
    publish_v310 = agent.converse("发布 e2e-demo-v3.1.0 到 runtime")
    blocked = agent.converse("发布 e2e-missing-v9.9.9 到 runtime")
    assert publish_v300["status"] == "ok"
    assert publish_v310["status"] == "ok"
    assert publish_v300["runtime"]["status"] == "published"
    assert publish_v310["runtime"]["status"] == "published"
    assert blocked["status"] == "blocked"

    client = TestClient(app)
    detail_resp = client.get("/v1/governance/ops/workpackages/e2e-demo-v3.0.0/versions/v3.0.0")
    assert detail_resp.status_code == 200
    detail_payload = detail_resp.json()
    assert detail_payload["workpackage_id"] == "e2e-demo-v3.0.0"
    assert detail_payload["version"] == "v3.0.0"
    assert detail_payload["status"] == "published"
    assert detail_payload["published_at"]
    list_resp = client.get("/v1/governance/ops/workpackages/e2e-demo-v3.0.0/versions?status=published")
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert list_payload["total"] >= 1
    compare_resp = client.get(
        "/v1/governance/ops/workpackages/e2e-demo-v3.0.0/compare"
        "?baseline_version=v3.0.0&candidate_version=v3.1.0"
    )
    assert compare_resp.status_code == 200
    compare_payload = compare_resp.json()
    assert compare_payload["baseline"]["version"] == "v3.0.0"
    assert compare_payload["candidate"]["version"] == "v3.1.0"
    blocked_events = [evt for evt in REPOSITORY.list_audit_events() if evt.get("event_type") == "workpackage_publish_blocked"]
    assert len(blocked_events) >= 1
