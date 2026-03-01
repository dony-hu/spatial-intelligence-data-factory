from __future__ import annotations

import os


from fastapi.testclient import TestClient

from services.governance_api.app.main import app
from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_get_workpackage_publish_record_success() -> None:
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-v2.0.0",
        version="v2.0.0",
        status="published",
        evidence_ref="output/workpackages/demo-v2.0.0.publish.json",
        bundle_path="workpackages/bundles/demo-v2.0.0",
        published_by="ut",
    )
    client = TestClient(app)
    resp = client.get("/v1/governance/ops/workpackages/demo-v2.0.0/versions/v2.0.0")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["workpackage_id"] == "demo-v2.0.0"
    assert payload["version"] == "v2.0.0"
    assert payload["status"] == "published"
    assert payload["evidence_ref"].endswith(".json")
    assert payload["published_at"]


def test_get_workpackage_publish_record_not_found() -> None:
    client = TestClient(app)
    resp = client.get("/v1/governance/ops/workpackages/not-found/versions/v0.0.1")
    assert resp.status_code == 404


def test_list_workpackage_publish_versions_with_status_filter() -> None:
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-list",
        version="v1.0.0",
        status="published",
        evidence_ref="output/workpackages/demo-list.v1.publish.json",
        published_by="ut",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-list",
        version="v1.1.0",
        status="blocked",
        evidence_ref="output/workpackages/demo-list.v1.1.blocked.json",
        published_by="ut",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-list",
        version="v1.2.0",
        status="published",
        evidence_ref="output/workpackages/demo-list.v1.2.publish.json",
        published_by="ut",
    )
    client = TestClient(app)
    resp = client.get("/v1/governance/ops/workpackages/demo-list/versions?status=published")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["workpackage_id"] == "demo-list"
    assert payload["status_filter"] == "published"
    assert payload["total"] == 2
    assert all(item["status"] == "published" for item in payload["items"])


def test_compare_workpackage_publish_versions_api() -> None:
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-compare-api",
        version="v3.0.0",
        status="published",
        evidence_ref="output/workpackages/demo-compare-api.v3.publish.json",
        published_by="ut",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-compare-api",
        version="v3.1.0",
        status="blocked",
        evidence_ref="output/workpackages/demo-compare-api.v3.1.blocked.json",
        published_by="ut",
        confirmation_user="owner",
        confirmation_decision="hold",
        confirmation_timestamp="2026-02-27T15:00:00Z",
    )
    client = TestClient(app)
    resp = client.get(
        "/v1/governance/ops/workpackages/demo-compare-api/compare"
        "?baseline_version=v3.0.0&candidate_version=v3.1.0"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["workpackage_id"] == "demo-compare-api"
    assert payload["baseline"]["version"] == "v3.0.0"
    assert payload["candidate"]["version"] == "v3.1.0"
    assert "status" in payload["changed_fields"]
