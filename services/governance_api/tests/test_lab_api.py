import json
from pathlib import Path

from fastapi.testclient import TestClient

from packages.address_core.trusted_fengtu import FengtuTrustedClient
from services.governance_api.app.main import app


def test_lab_optimize_creates_pending_change_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/governance/lab/optimize/lab-batch-001",
        json={
            "caller": "lab-admin",
            "sample_spec": "sample",
            "sample_size": 3,
            "candidate_count": 3,
            "records": [
                {"raw_id": "lab-r1", "raw_text": "深圳市福田区福中三路100号"},
                {"raw_id": "lab-r2", "raw_text": "深圳市南山区科技园南区1号"},
                {"raw_id": "lab-r3", "raw_text": "广州市天河区体育东路1号"},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["baseline_run_id"].startswith("task_")
    assert len(data["candidate_run_ids"]) == 3
    assert data["recommendation"] in {"accept", "reject", "needs-human"}
    assert len(data["top_evidence_bullets"]) == 3

    change_id = data["change_id"]
    change_response = client.get(f"/v1/governance/change-requests/{change_id}")
    assert change_response.status_code == 200
    change_data = change_response.json()
    assert change_data["status"] == "pending"

    blocked_activation = client.post(
        f"/v1/governance/rulesets/{change_data['to_ruleset_id']}/activate",
        json={"change_id": change_id, "caller": "admin"},
    )
    assert blocked_activation.status_code == 409

    replay_response = client.get(f"/v1/governance/lab/change_requests/{change_id}")
    assert replay_response.status_code == 200
    replay_data = replay_response.json()
    assert replay_data["change_id"] == change_id
    assert replay_data["baseline_run_id"].startswith("task_")
    assert replay_data["candidate_run_id"].startswith("task_")
    assert "baseline" in replay_data["scorecard"]
    assert "candidate" in replay_data["scorecard"]
    assert "delta" in replay_data["scorecard"]
    assert isinstance(replay_data["diff"], dict)
    assert isinstance(replay_data["improved_samples"], list)
    assert isinstance(replay_data["worsened_samples"], list)
    assert isinstance(replay_data["audit_events"], list)
    assert any(event.get("event_type") == "change_request_created" for event in replay_data["audit_events"])
    assert replay_data["activation"]["allowed"] is False

    replay_html = client.get(f"/v1/governance/lab/change_requests/{change_id}/view")
    assert replay_html.status_code == 200
    assert "text/html" in replay_html.headers.get("content-type", "")
    assert "Lab Change Request Replay" in replay_html.text
    assert change_id in replay_html.text


def test_lab_fengtu_network_confirmation_flow() -> None:
    client = TestClient(app)
    FengtuTrustedClient._network_confirmation_required = True
    FengtuTrustedClient._last_network_error = "TimeoutError"
    FengtuTrustedClient._network_confirmed_once = False
    FengtuTrustedClient._last_confirm_by = ""

    status_before = client.get("/v1/governance/lab/trusted/fengtu/status")
    assert status_before.status_code == 200
    before_data = status_before.json()
    assert before_data["enabled"] is True
    assert before_data["confirmation_required"] is True
    assert before_data["last_network_error"] == "TimeoutError"

    confirm = client.post(
        "/v1/governance/lab/trusted/fengtu/confirm-network",
        json={"operator": "huda"},
    )
    assert confirm.status_code == 200
    confirm_data = confirm.json()
    assert confirm_data["last_confirm_by"] == "huda"

    # confirm action sets one-time resume token and keeps current state visible until next call.
    assert FengtuTrustedClient._network_confirmed_once is True


def test_lab_fengtu_conflicts_list_and_decision() -> None:
    client = TestClient(app)
    project_root = Path(__file__).resolve().parents[3]
    output_dir = project_root / "output" / "lab_mode"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "cn1300_module_coverage_29990101_000000.json"
    report_path.write_text(
        json.dumps(
            {
                "rows_total": 1,
                "module_coverage": {
                    "normalize": {"hit_rate": 0.0},
                    "parse": {"field_hit_rate": {}},
                    "match": {"hit_rate": 0.0},
                    "score": {"judgement_hit_rate": 0.0},
                },
                "samples": {
                    "fengtu_conflicts_pending_confirmation_top50": [
                        {
                            "case_id": "CNADDR-X001",
                            "raw_text": "深圳市罗湖区不存在路64号龙湖天街",
                            "expected_normalized": "广东省深圳市罗湖区不存在路64号",
                            "fengtu_candidate": "广东省深圳市罗湖区不存在路64号龙湖天街",
                            "note": "pending_user_confirmation",
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    decisions_path = output_dir / "fengtu_conflict_decisions.json"
    backup_decisions = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else None
    decisions_path.write_text(json.dumps({"items": {}}, ensure_ascii=False), encoding="utf-8")

    try:
        listed = client.get("/v1/governance/lab/trusted/fengtu/conflicts?status=pending")
        assert listed.status_code == 200
        listed_json = listed.json()
        assert listed_json["total_conflicts"] >= 1
        assert listed_json["pending_conflicts"] >= 1
        assert any(item["case_id"] == "CNADDR-X001" for item in listed_json["items"])

        decided = client.post(
            "/v1/governance/lab/trusted/fengtu/conflicts/CNADDR-X001/decision",
            json={"operator": "huda", "decision": "accept_expected", "comment": "keep fixture expectation"},
        )
        assert decided.status_code == 200
        assert decided.json()["status"] == "resolved"

        resolved = client.get("/v1/governance/lab/trusted/fengtu/conflicts?status=resolved")
        assert resolved.status_code == 200
        resolved_json = resolved.json()
        assert any(item["case_id"] == "CNADDR-X001" and item["status"] == "resolved" for item in resolved_json["items"])
    finally:
        if report_path.exists():
            report_path.unlink()
        if backup_decisions is None:
            if decisions_path.exists():
                decisions_path.unlink()
        else:
            decisions_path.write_text(backup_decisions, encoding="utf-8")


def test_lab_coverage_dashboard_view() -> None:
    client = TestClient(app)
    page = client.get("/v1/governance/lab/coverage/view")
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "")
    assert "Lab Coverage Dashboard" in page.text
    assert "Coverage Metrics" in page.text
    assert "Fengtu Conflicts (Pending)" in page.text


def test_lab_coverage_data_filters_and_status() -> None:
    client = TestClient(app)
    project_root = Path(__file__).resolve().parents[3]
    output_dir = project_root / "output" / "lab_mode"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "cn1300_module_coverage_29990101_010101.json"
    progress_path = output_dir / "cn1300_module_coverage_progress.json"
    report_payload = {
        "dataset": "testdata/fixtures/lab-mode-phase1_5-中文地址测试用例-1300-2026-02-15.csv",
        "generated_at": "2026-02-15T11:40:00+00:00",
        "rows_total": 2,
        "execution": {"status": "completed", "processed_rows": 2, "total_rows": 2, "progress_rate": 1.0},
        "module_coverage": {
            "normalize": {"hit_rate": 0.5},
            "parse": {"field_hit_rate": {"province": 1.0}},
            "match": {"hit_rate": 0.5},
            "dedup": {"dedup_exact_pass": True},
            "score": {"judgement_hit_rate": 0.5},
        },
        "case_summary": {
            "overall_result_distribution": {"pass": 1, "fail": 1},
            "case_type_distribution": {"integration": 2},
            "city_distribution_top20": {"上海市": 1, "北京市": 1},
        },
        "case_details": [
            {
                "case_id": "CNADDR-1",
                "case_type": "integration",
                "scenario_tag": "标准地址",
                "city": "上海市",
                "district": "浦东新区",
                "raw_text": "raw-1",
                "normalized": "norm-1",
                "expected_normalized": "norm-1",
                "overall_result": "pass",
                "module_result": {"normalize": True, "parse": True, "match": True, "score": True},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "rule_only",
                "confidence": 0.91,
                "expected_judgement": "accept",
                "predicted_judgement": "accept",
                "expected_human_review": False,
                "predicted_human_review": False,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            },
            {
                "case_id": "CNADDR-2",
                "case_type": "integration",
                "scenario_tag": "疑难地址",
                "city": "北京市",
                "district": "朝阳区",
                "raw_text": "raw-2",
                "normalized": "norm-2",
                "expected_normalized": "norm-2x",
                "overall_result": "fail",
                "module_result": {"normalize": False, "parse": True, "match": False, "score": True},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "match_dict",
                "confidence": 0.55,
                "expected_judgement": "needs-human",
                "predicted_judgement": "needs-human",
                "expected_human_review": True,
                "predicted_human_review": True,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            },
        ],
        "samples": {"fengtu_conflicts_pending_confirmation_top50": []},
    }

    backup_progress = progress_path.read_text(encoding="utf-8") if progress_path.exists() else None
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False), encoding="utf-8")
    progress_path.write_text(
        json.dumps(
            {
                "status": "running",
                "processed_rows": 1,
                "total_rows": 2,
                "progress_rate": 0.5,
                "updated_at": "2026-02-15T11:40:01+00:00",
                "message": "evaluating cases",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    try:
        data = client.get("/v1/governance/lab/coverage/data?result=pass&city=上海市")
        assert data.status_code == 200
        payload = data.json()
        assert payload["rows_total"] >= 2
        assert payload["coverage_status"]["status"] == "running"
        assert payload["pagination"]["total_filtered"] >= 1
        assert any(row.get("case_id") == "CNADDR-1" for row in payload["rows"])

        by_case = client.get("/v1/governance/lab/coverage/data?case_id=CNADDR-2")
        assert by_case.status_code == 200
        by_case_payload = by_case.json()
        assert by_case_payload["pagination"]["total_filtered"] == 1
        assert by_case_payload["rows"][0]["case_id"] == "CNADDR-2"
    finally:
        if report_path.exists():
            report_path.unlink()
        if backup_progress is None:
            if progress_path.exists():
                progress_path.unlink()
        else:
            progress_path.write_text(backup_progress, encoding="utf-8")


def test_lab_coverage_view_shows_all_execution_statistics() -> None:
    client = TestClient(app)
    project_root = Path(__file__).resolve().parents[3]
    output_dir = project_root / "output" / "lab_mode"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "cn1300_module_coverage_29990101_020202.json"
    report_payload = {
        "dataset": "testdata/fixtures/lab-mode-phase1_5-中文地址测试用例-1300-2026-02-15.csv",
        "generated_at": "2026-02-15T12:00:00+00:00",
        "rows_total": 6,
        "module_coverage": {
            "normalize": {"hit_rate": 0.666667},
            "parse": {"field_hit_rate": {"province": 1.0, "city": 1.0, "district": 1.0, "road": 0.833333, "house_no": 0.833333}},
            "match": {"hit_rate": 0.666667},
            "dedup": {"dedup_exact_pass": True},
            "score": {"judgement_hit_rate": 1.0},
        },
        "case_summary": {
            "overall_result_distribution": {"pass": 4, "fail": 2},
            "case_type_distribution": {"integration": 4, "e2e": 2},
            "city_distribution_top20": {"上海市": 1, "北京市": 1, "深圳市": 1, "苏州市": 1, "武汉市": 1, "随州市": 1},
        },
        "case_details": [
            {
                "case_id": "CNADDR-A1",
                "case_type": "integration",
                "scenario_tag": "标准地址",
                "city": "上海市",
                "district": "浦东新区",
                "raw_text": "raw-a1",
                "normalized": "norm-a1",
                "expected_normalized": "norm-a1",
                "overall_result": "pass",
                "module_result": {"normalize": True, "parse": True, "match": True, "score": True},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "rule_only",
                "confidence": 0.93,
                "expected_judgement": "accept",
                "predicted_judgement": "accept",
                "expected_human_review": False,
                "predicted_human_review": False,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            }
        ],
        "samples": {"fengtu_conflicts_pending_confirmation_top50": []},
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False), encoding="utf-8")
    try:
        page = client.get("/v1/governance/lab/coverage/view")
        assert page.status_code == 200
        html = page.text
        assert "All Cases Execution Statistics" in html
        assert "rows_total" in html
        assert "rows_total</b>: 6" in html
        assert "pass/fail" in html
        assert "4/2" in html
        assert "Coverage Metrics" in html
        assert "case_type_distribution" in html
        assert "integration" in html
        assert "e2e" in html
        assert "city_distribution_top20" in html
        assert "上海市" in html
        assert "北京市" in html
        assert "深圳市" in html
        assert "苏州市" in html
        assert "武汉市" in html
        assert "随州市" in html
    finally:
        if report_path.exists():
            report_path.unlink()


def test_lab_coverage_view_case_details_query_with_result_type_city_filters() -> None:
    client = TestClient(app)
    project_root = Path(__file__).resolve().parents[3]
    output_dir = project_root / "output" / "lab_mode"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "cn1300_module_coverage_29990101_030303.json"
    report_payload = {
        "dataset": "testdata/fixtures/lab-mode-phase1_5-中文地址测试用例-1300-2026-02-15.csv",
        "generated_at": "2026-02-15T12:10:00+00:00",
        "rows_total": 4,
        "module_coverage": {
            "normalize": {"hit_rate": 0.5},
            "parse": {"field_hit_rate": {"province": 1.0}},
            "match": {"hit_rate": 0.5},
            "dedup": {"dedup_exact_pass": True},
            "score": {"judgement_hit_rate": 0.75},
        },
        "case_summary": {
            "overall_result_distribution": {"pass": 2, "fail": 2},
            "case_type_distribution": {"integration": 2, "e2e": 2},
            "city_distribution_top20": {"上海市": 1, "武汉市": 2, "北京市": 1},
        },
        "case_details": [
            {
                "case_id": "CNADDR-T1",
                "case_type": "integration",
                "scenario_tag": "标准地址",
                "city": "上海市",
                "district": "浦东新区",
                "raw_text": "raw-t1",
                "normalized": "norm-t1",
                "expected_normalized": "norm-t1",
                "overall_result": "pass",
                "module_result": {"normalize": True, "parse": True, "match": True, "score": True},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "rule_only",
                "confidence": 0.95,
                "expected_judgement": "accept",
                "predicted_judgement": "accept",
                "expected_human_review": False,
                "predicted_human_review": False,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            },
            {
                "case_id": "CNADDR-T2",
                "case_type": "e2e",
                "scenario_tag": "疑难地址",
                "city": "武汉市",
                "district": "洪山区",
                "raw_text": "raw-t2-target",
                "normalized": "norm-t2",
                "expected_normalized": "norm-t2x",
                "overall_result": "fail",
                "module_result": {"normalize": False, "parse": True, "match": False, "score": True},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "match_dict",
                "confidence": 0.58,
                "expected_judgement": "needs-human",
                "predicted_judgement": "needs-human",
                "expected_human_review": True,
                "predicted_human_review": True,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            },
            {
                "case_id": "CNADDR-T3",
                "case_type": "e2e",
                "scenario_tag": "缺失字段",
                "city": "武汉市",
                "district": "武昌区",
                "raw_text": "raw-t3",
                "normalized": "norm-t3",
                "expected_normalized": "norm-t3x",
                "overall_result": "fail",
                "module_result": {"normalize": False, "parse": True, "match": True, "score": False},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "human_required",
                "confidence": 0.44,
                "expected_judgement": "reject",
                "predicted_judgement": "needs-human",
                "expected_human_review": True,
                "predicted_human_review": True,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            },
            {
                "case_id": "CNADDR-T4",
                "case_type": "integration",
                "scenario_tag": "标准地址",
                "city": "北京市",
                "district": "海淀区",
                "raw_text": "raw-t4",
                "normalized": "norm-t4",
                "expected_normalized": "norm-t4",
                "overall_result": "pass",
                "module_result": {"normalize": True, "parse": True, "match": True, "score": True},
                "parse_field_hits": {"province": True},
                "parse_missing_fields": [],
                "strategy": "rule_only",
                "confidence": 0.92,
                "expected_judgement": "accept",
                "predicted_judgement": "accept",
                "expected_human_review": False,
                "predicted_human_review": False,
                "status": "completed",
                "fengtu_conflict_pending": False,
                "fengtu_candidate": "",
            },
        ],
        "samples": {"fengtu_conflicts_pending_confirmation_top50": []},
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False), encoding="utf-8")
    try:
        # 过滤条件：fail + e2e + 武汉市 + module(match)=fail，应只剩 CNADDR-T2。
        page = client.get(
            "/v1/governance/lab/coverage/view?result=fail&case_type=e2e&city=武汉市&module=match&module_outcome=fail&status=completed&page_size=20"
        )
        assert page.status_code == 200
        html = page.text
        assert "Case Details Query" in html
        assert "filtered=1" in html
        assert "CNADDR-T2" in html
        assert "raw-t2-target" in html
        assert "CNADDR-T1" not in html
        assert "CNADDR-T3" not in html
        assert "CNADDR-T4" not in html

        # 数据接口也校验同样维度筛选。
        data = client.get(
            "/v1/governance/lab/coverage/data?result=fail&case_type=e2e&city=武汉市&module=match&module_outcome=fail&status=completed&page_size=20"
        )
        assert data.status_code == 200
        payload = data.json()
        assert payload["pagination"]["total_filtered"] == 1
        assert len(payload["rows"]) == 1
        assert payload["rows"][0]["case_id"] == "CNADDR-T2"
        assert set(payload["filters"]["case_types"]) >= {"integration", "e2e"}
        assert set(payload["filters"]["cities"]) >= {"上海市", "武汉市", "北京市"}
    finally:
        if report_path.exists():
            report_path.unlink()


def test_lab_observability_snapshot_api() -> None:
    client = TestClient(app)
    resp = client.get("/v1/governance/lab/observability/snapshot?env=dev")
    assert resp.status_code == 200
    data = resp.json()
    assert data["environment"] == "dev"
    assert "l1" in data and "l2" in data and "l3" in data
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


def test_lab_observability_stream_sse() -> None:
    client = TestClient(app)
    resp = client.get("/v1/governance/lab/observability/stream?env=dev&interval_sec=1&max_events=1")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
    assert "event: connected" in resp.text
    assert "event: snapshot" in resp.text


def test_lab_observability_live_view() -> None:
    client = TestClient(app)
    page = client.get("/v1/governance/lab/observability/view?env=dev")
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "")
    assert "系统可观测性管理看板" in page.text
    assert "SQL交互查询" in page.text


def test_lab_observability_management_data_contract() -> None:
    client = TestClient(app)
    resp = client.get("/v1/governance/lab/observability/management/data")
    assert resp.status_code == 200
    data = resp.json()
    assert "test_overview" in data
    assert "gate_layers" in data
    assert "failure_classification" in data
    assert "execution_process" in data
    assert "sql_capability" in data
    assert "timeline" in data["execution_process"]
    assert len(data["execution_process"]["timeline"]) >= 20
