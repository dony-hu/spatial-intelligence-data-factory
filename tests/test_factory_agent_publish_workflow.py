from __future__ import annotations

from pathlib import Path

from packages.factory_agent.publish_workflow import WorkpackagePublishWorkflow


def test_publish_workflow_blocked_and_audited_when_bundle_missing(tmp_path) -> None:
    events: list[dict] = []
    persisted: list[dict] = []

    workflow = WorkpackagePublishWorkflow(
        bundle_root=tmp_path / "workpackages" / "bundles",
        output_root=tmp_path / "output" / "workpackages",
        extract_bundle_name=lambda _prompt: "missing-v1.0.0",
        execute_entrypoint=lambda **_kwargs: {"success": True, "return_code": 0, "report_path": "", "metrics_path": ""},
        persist_publish=lambda **kwargs: persisted.append(kwargs),
        log_blocked=lambda payload: events.append(payload),
    )
    result = workflow.run("发布 missing-v1.0.0 到 runtime")
    assert result["status"] == "blocked"
    assert result["reason"] == "workpackage_not_found"
    assert len(events) == 1
    assert events[0]["reason"] == "workpackage_not_found"
    assert persisted == []


def test_publish_workflow_success_should_persist_and_emit_evidence(tmp_path) -> None:
    events: list[dict] = []
    persisted: list[dict] = []
    bundle = tmp_path / "workpackages" / "bundles" / "demo-v1.0.0"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "workpackage.json").write_text('{"name":"demo","version":"v1.0.0"}', encoding="utf-8")
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    (bundle / "skills").mkdir(exist_ok=True)
    (bundle / "observability").mkdir(exist_ok=True)

    workflow = WorkpackagePublishWorkflow(
        bundle_root=tmp_path / "workpackages" / "bundles",
        output_root=tmp_path / "output" / "workpackages",
        extract_bundle_name=lambda _prompt: "demo-v1.0.0",
        execute_entrypoint=lambda **_kwargs: {
            "success": True,
            "return_code": 0,
            "report_path": str(bundle / "observability" / "publish_execution_report.json"),
            "metrics_path": str(bundle / "observability" / "line_metrics.json"),
        },
        persist_publish=lambda **kwargs: persisted.append(kwargs),
        log_blocked=lambda payload: events.append(payload),
    )
    result = workflow.run("发布 demo-v1.0.0 到 runtime")
    assert result["status"] == "ok"
    assert result["runtime"]["status"] == "published"
    assert Path(result["runtime"]["evidence_ref"]).exists()
    assert len(persisted) == 1
    assert persisted[0]["status"] == "published"
    assert events == []
