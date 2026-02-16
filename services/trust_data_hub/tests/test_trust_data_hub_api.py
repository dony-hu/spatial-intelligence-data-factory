from fastapi.testclient import TestClient

from services.trust_data_hub.app.main import app
from services.trust_data_hub.app.repositories.trust_repository import trust_repository


client = TestClient(app)


def _register_source(namespace: str, source_id: str, dataset_variant: str = "admin_v1") -> None:
    resp = client.put(
        f"/v1/trust/admin/namespaces/{namespace}/sources/{source_id}",
        json={
            "name": "test-source",
            "category": "admin_division",
            "trust_level": "authoritative",
            "license": "ODbL",
            "entrypoint": "fixture://admin_division",
            "update_frequency": "daily",
            "fetch_method": "download",
            "parser_profile": {"dataset_variant": dataset_variant},
            "validator_profile": {"max_null_ratio": 0.2},
            "enabled": True,
            "allowed_use_notes": "cache allowed",
            "access_mode": "download",
            "robots_tos_flags": {"allow_automation": True, "require_attribution": True},
        },
    )
    assert resp.status_code == 200


def test_four_buttons_workflow_and_audit_chain() -> None:
    namespace = "system.trust"
    source_id = "src-admin-001"
    _register_source(namespace, source_id)

    fetch_resp = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now")
    assert fetch_resp.status_code == 200
    snapshot_id = fetch_resp.json()["snapshot_id"]
    assert fetch_resp.json()["status"] in {"success", "queued", "running"}

    validate_resp = client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    assert validate_resp.status_code == 200
    assert 0 <= validate_resp.json()["quality_score"] <= 100

    publish_resp = client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    assert publish_resp.status_code == 200

    promote_resp = client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": snapshot_id, "activated_by": "tester", "activation_note": "smoke"},
    )
    assert promote_resp.status_code == 200
    assert promote_resp.json()["active_snapshot_id"] == snapshot_id

    audit_resp = client.get(f"/v1/trust/admin/namespaces/{namespace}/audit-events")
    assert audit_resp.status_code == 200
    actions = [e["action"] for e in audit_resp.json()["events"]]
    assert "fetch" in actions
    assert "validate" in actions
    assert "publish" in actions
    assert "activate" in actions


def test_publish_requires_validation() -> None:
    namespace = "system.trust"
    source_id = "src-admin-002"
    _register_source(namespace, source_id)

    fetch_resp = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now")
    snapshot_id = fetch_resp.json()["snapshot_id"]

    publish_resp = client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    assert publish_resp.status_code == 400
    assert publish_resp.json()["detail"] == "snapshot_not_validated"


def test_query_and_validation_api_include_evidence_refs() -> None:
    namespace = "system.trust"
    source_id = "src-admin-003"
    _register_source(namespace, source_id, dataset_variant="admin_v1")

    snapshot_id = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": snapshot_id, "activated_by": "tester", "activation_note": "go live"},
    )

    q_resp = client.get(f"/v1/trust/query/namespaces/{namespace}/admin-division", params={"name": "杭州市"})
    assert q_resp.status_code == 200
    candidates = q_resp.json()["candidates"]
    assert candidates
    assert any(item["source_id"] == source_id for item in candidates)
    assert any(item["snapshot_id"] == snapshot_id for item in candidates)

    evidence_resp = client.post(
        "/v1/trust/validation/evidence",
        params={"namespace": namespace},
        json={
            "province": "浙江省",
            "city": "杭州市",
            "district": "西湖区",
            "road": "文三路",
            "poi": "西溪银泰城",
        },
    )
    assert evidence_resp.status_code == 200
    payload = evidence_resp.json()
    assert "signals" in payload
    assert "evidence_refs" in payload
    assert all("source_id" in item and "snapshot_id" in item for item in payload["evidence_refs"])


def test_high_diff_requires_manual_confirmation() -> None:
    namespace = "system.trust"
    source_id = "src-admin-004"
    _register_source(namespace, source_id, dataset_variant="admin_v1")
    s1 = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{s1}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{s1}/publish")
    promote_first = client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": s1, "activated_by": "tester", "activation_note": "baseline"},
    )
    assert promote_first.status_code == 200

    _register_source(namespace, source_id, dataset_variant="osm_china_v1")
    s2 = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{s2}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{s2}/publish")

    promote_blocked = client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": s2, "activated_by": "tester", "activation_note": "large change"},
    )
    assert promote_blocked.status_code == 400
    assert promote_blocked.json()["detail"] == "high_diff_requires_confirmation"

    promote_ok = client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={
            "snapshot_id": s2,
            "activated_by": "tester",
            "activation_note": "large change approved",
            "confirm_high_diff": True,
        },
    )
    assert promote_ok.status_code == 200


def test_namespace_isolation_for_query() -> None:
    ns_a = "system.trust"
    ns_b = "business.prod"
    source_id = "src-admin-ns-001"

    _register_source(ns_a, source_id, dataset_variant="admin_v1")
    s1 = client.post(f"/v1/trust/ops/namespaces/{ns_a}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{ns_a}/snapshots/{s1}/validate")
    client.post(f"/v1/trust/ops/namespaces/{ns_a}/snapshots/{s1}/publish")
    client.post(
        f"/v1/trust/ops/namespaces/{ns_a}/sources/{source_id}/promote",
        json={"snapshot_id": s1, "activated_by": "tester", "activation_note": "ns_a"},
    )

    q_a = client.get(f"/v1/trust/query/namespaces/{ns_a}/admin-division", params={"name": "杭州市"})
    q_b = client.get(f"/v1/trust/query/namespaces/{ns_b}/admin-division", params={"name": "杭州市"})
    assert q_a.status_code == 200
    assert q_b.status_code == 200
    assert len(q_a.json()["candidates"]) > 0
    assert q_b.json()["candidates"] == []


def test_phase1_schedule_and_reports_and_replay() -> None:
    namespace = "system.trust.phase1"
    source_id = "src-phase1-001"
    _register_source(namespace, source_id, dataset_variant="admin_v1")

    schedule_resp = client.put(
        f"/v1/trust/admin/namespaces/{namespace}/sources/{source_id}/schedule",
        json={
            "schedule_type": "interval",
            "schedule_spec": "6h",
            "window_policy": {"rate_limit_qps": 1, "timezone": "Asia/Shanghai"},
            "enabled": True,
        },
    )
    assert schedule_resp.status_code == 200
    assert schedule_resp.json()["source_id"] == source_id

    fetched = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now")
    snapshot_id = fetched.json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": snapshot_id, "activated_by": "phase1", "activation_note": "activate"},
    )

    quality_resp = client.get(f"/v1/trust/admin/namespaces/{namespace}/snapshots/{snapshot_id}/quality")
    assert quality_resp.status_code == 200
    assert quality_resp.json()["snapshot_id"] == snapshot_id

    active_resp = client.get(f"/v1/trust/admin/namespaces/{namespace}/sources/{source_id}/active-release")
    assert active_resp.status_code == 200
    assert active_resp.json()["active_snapshot_id"] == snapshot_id

    replay_resp = client.post(
        f"/v1/trust/validation/replay",
        params={"namespace": namespace, "snapshot_id": snapshot_id},
        json={"province": "浙江省", "city": "杭州市", "district": "西湖区", "road": "文三路", "poi": "西溪银泰城"},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["snapshot_id"] == snapshot_id
    assert replay_resp.json()["replay_id"]


def test_phase2_bootstrap_sample_sources() -> None:
    namespace = "system.trust.phase2"
    resp = client.post(f"/v1/trust/admin/namespaces/{namespace}/bootstrap/samples")
    assert resp.status_code == 200
    source_ids = {item["source_id"] for item in resp.json()["sources"]}
    assert "sample-admin-authoritative" in source_ids
    assert "sample-osm-geofabrik-china" in source_ids


def test_phase2_file_fetcher_and_parser_profiles() -> None:
    namespace = "system.trust.phase2.real"
    source_id = "src-file-admin-001"
    fixture_path = "/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/tests/fixtures/admin_division_sample.json"

    register = client.put(
        f"/v1/trust/admin/namespaces/{namespace}/sources/{source_id}",
        json={
            "name": "file-admin-source",
            "category": "admin_division",
            "trust_level": "authoritative",
            "license": "ODbL",
            "entrypoint": f"file://{fixture_path}",
            "update_frequency": "daily",
            "fetch_method": "download",
            "parser_profile": {"dataset_variant": "file_json"},
            "validator_profile": {"max_null_ratio": 0.2},
            "enabled": True,
            "allowed_use_notes": "cache allowed",
            "access_mode": "download",
            "robots_tos_flags": {"allow_automation": True, "require_attribution": True},
        },
    )
    assert register.status_code == 200

    fetched = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now")
    assert fetched.status_code == 200
    snapshot_id = fetched.json()["snapshot_id"]

    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": snapshot_id, "activated_by": "phase2", "activation_note": "file source"},
    )

    q = client.get(f"/v1/trust/query/namespaces/{namespace}/admin-division", params={"name": "苏州市"})
    assert q.status_code == 200
    assert any(item.get("adcode") == "320500" for item in q.json()["candidates"])


def test_phase2_osm_parser_profile() -> None:
    namespace = "system.trust.phase2.real"
    source_id = "src-file-osm-001"
    fixture_path = "/Users/huda/Code/spatial-intelligence-data-factory/services/trust_data_hub/tests/fixtures/osm_extract_sample.json"

    register = client.put(
        f"/v1/trust/admin/namespaces/{namespace}/sources/{source_id}",
        json={
            "name": "file-osm-source",
            "category": "road_poi",
            "trust_level": "open_license",
            "license": "ODbL",
            "entrypoint": f"file://{fixture_path}",
            "update_frequency": "weekly",
            "fetch_method": "download",
            "parser_profile": {"dataset_variant": "osm_elements_v1"},
            "validator_profile": {"max_null_ratio": 0.3},
            "enabled": True,
            "allowed_use_notes": "cache allowed",
            "access_mode": "download",
            "robots_tos_flags": {"allow_automation": True, "require_attribution": True},
        },
    )
    assert register.status_code == 200

    fetched = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now")
    assert fetched.status_code == 200
    snapshot_id = fetched.json()["snapshot_id"]

    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": snapshot_id, "activated_by": "phase2", "activation_note": "osm source"},
    )

    road_q = client.get(f"/v1/trust/query/namespaces/{namespace}/road", params={"name": "中山路"})
    poi_q = client.get(f"/v1/trust/query/namespaces/{namespace}/poi", params={"name": "拙政园"})
    assert road_q.status_code == 200
    assert poi_q.status_code == 200
    assert len(road_q.json()["candidates"]) >= 1
    assert len(poi_q.json()["candidates"]) >= 1


def test_phase2_publish_calls_trustdb_persister_when_enabled(monkeypatch) -> None:
    namespace = "system.trust.phase2.persist"
    source_id = "src-persist-001"
    _register_source(namespace, source_id, dataset_variant="admin_v1")

    called = {"ok": False}

    monkeypatch.setattr(trust_repository._trustdb, "enabled", lambda: True)

    def _fake_persist(namespace: str, source_id: str, snapshot_id: str, payload: dict, fetched_at: str) -> None:
        called["ok"] = True

    monkeypatch.setattr(trust_repository._trustdb, "persist_snapshot", _fake_persist)

    snapshot_id = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    publish_resp = client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    assert publish_resp.status_code == 200
    assert publish_resp.json()["storage_backend"] == "postgres"
    assert called["ok"] is True


def test_meta_db_persister_path_and_replay_schema_version(monkeypatch) -> None:
    namespace = "system.trust.phase0.persist"
    source_id = "src-meta-001"
    calls = {"source": 0, "snapshot": 0, "quality": 0, "active": 0, "replay": 0}

    monkeypatch.setattr(trust_repository._metadb, "enabled", lambda: True)
    monkeypatch.setattr(trust_repository._metadb, "upsert_source", lambda *_args, **_kwargs: calls.__setitem__("source", calls["source"] + 1))
    monkeypatch.setattr(
        trust_repository._metadb, "insert_snapshot", lambda *_args, **_kwargs: calls.__setitem__("snapshot", calls["snapshot"] + 1)
    )
    monkeypatch.setattr(
        trust_repository._metadb, "upsert_quality_report", lambda *_args, **_kwargs: calls.__setitem__("quality", calls["quality"] + 1)
    )
    monkeypatch.setattr(
        trust_repository._metadb, "upsert_active_release", lambda *_args, **_kwargs: calls.__setitem__("active", calls["active"] + 1)
    )
    monkeypatch.setattr(
        trust_repository._metadb,
        "insert_validation_replay_run",
        lambda *_args, **_kwargs: calls.__setitem__("replay", calls["replay"] + 1),
    )
    _register_source(namespace, source_id, dataset_variant="admin_v1")

    snapshot_id = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")
    client.post(
        f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/promote",
        json={"snapshot_id": snapshot_id, "activated_by": "meta", "activation_note": "meta test"},
    )

    assert calls["source"] >= 1
    assert calls["snapshot"] >= 1
    assert calls["quality"] >= 1
    assert calls["active"] >= 1

    evidence_resp = client.post(
        "/v1/trust/validation/evidence",
        params={"namespace": namespace},
        json={"province": "浙江省", "city": "杭州市", "district": "西湖区", "road": "文三路", "poi": "西溪银泰城"},
    )
    replay_resp = client.post(
        "/v1/trust/validation/replay",
        params={"namespace": namespace, "snapshot_id": snapshot_id},
        json={"province": "浙江省", "city": "杭州市", "district": "西湖区", "road": "文三路", "poi": "西溪银泰城"},
    )
    assert evidence_resp.status_code == 200
    assert replay_resp.status_code == 200
    assert evidence_resp.json()["schema_version"] == "trust.validation.v1"
    assert replay_resp.json()["schema_version"] == "trust.validation.v1"
    assert replay_resp.json()["snapshot_id"] == snapshot_id
    assert calls["replay"] >= 1


def test_replay_persistence_and_governance_mapping_contract(monkeypatch) -> None:
    namespace = "system.trust.phase2.replay"
    source_id = "src-replay-001"
    _register_source(namespace, source_id, dataset_variant="admin_v1")

    snapshot_id = client.post(f"/v1/trust/ops/namespaces/{namespace}/sources/{source_id}/fetch-now").json()["snapshot_id"]
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/validate")
    client.post(f"/v1/trust/ops/namespaces/{namespace}/snapshots/{snapshot_id}/publish")

    monkeypatch.setattr(trust_repository._metadb, "enabled", lambda: True)

    captured: dict = {}

    def _fake_insert_validation_replay_run(ns: str, replay_run: dict) -> None:
        captured["namespace"] = ns
        captured["run"] = replay_run

    monkeypatch.setattr(trust_repository._metadb, "insert_validation_replay_run", _fake_insert_validation_replay_run)

    replay_resp = client.post(
        "/v1/trust/validation/replay",
        params={"namespace": namespace, "snapshot_id": snapshot_id},
        json={
            "province": "浙江省",
            "city": "杭州市",
            "district": "西湖区",
            "street": "文三路",
            "detail": "西溪银泰城",
        },
    )
    assert replay_resp.status_code == 200
    payload = replay_resp.json()
    assert payload["storage_backend"] == "postgres"
    assert payload["input_mapping"]["road"] == "road|street"
    assert payload["input_mapping"]["poi"] == "poi|detail"
    assert isinstance(payload["evidence"]["items"], list)
    assert all("source_id" in item and "snapshot_id" in item for item in payload["evidence"]["items"])

    assert captured["namespace"] == namespace
    assert captured["run"]["snapshot_id"] == snapshot_id
    assert captured["run"]["request_payload"]["road"] == "文三路"
    assert captured["run"]["request_payload"]["poi"] == "西溪银泰城"

    runs_resp = client.get(
        f"/v1/trust/admin/namespaces/{namespace}/validation/replay-runs",
        params={"snapshot_id": snapshot_id, "limit": 5},
    )
    assert runs_resp.status_code == 200
    runs = runs_resp.json()["runs"]
    assert runs
    assert any(item["snapshot_id"] == snapshot_id for item in runs)
