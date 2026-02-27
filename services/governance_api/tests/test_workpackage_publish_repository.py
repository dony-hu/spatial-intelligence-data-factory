from __future__ import annotations

import os

os.environ.setdefault("GOVERNANCE_ALLOW_MEMORY_FALLBACK", "1")

from services.governance_api.app.repositories.governance_repository import REPOSITORY


def test_upsert_and_get_workpackage_publish_record() -> None:
    saved = REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-v1.0.0",
        version="v1.0.0",
        status="published",
        evidence_ref="output/workpackages/demo-v1.0.0.publish.json",
        bundle_path="workpackages/bundles/demo-v1.0.0",
        published_by="ut",
        confirmation_user="owner",
        confirmation_decision="approved",
        confirmation_timestamp="2026-02-27T12:00:00Z",
    )
    assert saved["workpackage_id"] == "demo-v1.0.0"
    assert saved["version"] == "v1.0.0"
    assert saved["status"] == "published"
    assert saved["published_at"]

    fetched = REPOSITORY.get_workpackage_publish("demo-v1.0.0", "v1.0.0")
    assert fetched is not None
    assert fetched["evidence_ref"].endswith(".publish.json")
    assert fetched["confirmation_user"] == "owner"
    assert fetched["published_at"]


def test_upsert_workpackage_publish_updates_existing_version() -> None:
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-v1.0.1",
        version="v1.0.1",
        status="published",
        evidence_ref="output/workpackages/demo-v1.0.1.publish.json",
    )
    updated = REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-v1.0.1",
        version="v1.0.1",
        status="blocked",
        evidence_ref="output/workpackages/demo-v1.0.1.publish.blocked.json",
        confirmation_user="owner",
        confirmation_decision="rollback",
        confirmation_timestamp="2026-02-27T13:00:00Z",
    )
    assert updated["status"] == "blocked"
    fetched = REPOSITORY.get_workpackage_publish("demo-v1.0.1", "v1.0.1")
    assert fetched is not None
    assert fetched["status"] == "blocked"
    assert fetched["confirmation_decision"] == "rollback"


def test_list_workpackage_publish_records_with_filters() -> None:
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-filter",
        version="v1.0.0",
        status="published",
        evidence_ref="output/workpackages/demo-filter.v1.publish.json",
        published_by="ut",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-filter",
        version="v1.1.0",
        status="blocked",
        evidence_ref="output/workpackages/demo-filter.v1.1.blocked.json",
        published_by="ut",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-filter",
        version="v1.2.0",
        status="published",
        evidence_ref="output/workpackages/demo-filter.v1.2.publish.json",
        published_by="ut",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="other-filter",
        version="v9.0.0",
        status="published",
        evidence_ref="output/workpackages/other-filter.v9.publish.json",
        published_by="ut",
    )
    published = REPOSITORY.list_workpackage_publishes(workpackage_id="demo-filter", status="published")
    assert len(published) == 2
    assert all(item["workpackage_id"] == "demo-filter" for item in published)
    assert all(item["status"] == "published" for item in published)


def test_compare_workpackage_publish_versions() -> None:
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-compare",
        version="v2.0.0",
        status="published",
        evidence_ref="output/workpackages/demo-compare.v2.publish.json",
        bundle_path="workpackages/bundles/demo-compare-v2",
        published_by="dev_a",
    )
    REPOSITORY.upsert_workpackage_publish(
        workpackage_id="demo-compare",
        version="v2.1.0",
        status="blocked",
        evidence_ref="output/workpackages/demo-compare.v2.1.blocked.json",
        bundle_path="workpackages/bundles/demo-compare-v2.1",
        published_by="dev_b",
        confirmation_user="owner",
        confirmation_decision="rollback",
        confirmation_timestamp="2026-02-27T14:00:00Z",
    )
    diff = REPOSITORY.compare_workpackage_publish_versions(
        workpackage_id="demo-compare",
        baseline_version="v2.0.0",
        candidate_version="v2.1.0",
    )
    assert diff is not None
    assert diff["baseline"]["version"] == "v2.0.0"
    assert diff["candidate"]["version"] == "v2.1.0"
    changed = set(diff["changed_fields"])
    assert "status" in changed
    assert "evidence_ref" in changed
