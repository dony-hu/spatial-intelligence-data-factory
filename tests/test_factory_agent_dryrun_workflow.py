from __future__ import annotations

from pathlib import Path

from packages.factory_agent.dryrun_workflow import WorkpackageDryrunWorkflow


def test_dryrun_workflow_blocked_when_workpackage_missing(tmp_path) -> None:
    workflow = WorkpackageDryrunWorkflow(
        bundle_root=tmp_path / "workpackages" / "bundles",
        extract_bundle_name=lambda _prompt: "missing-v1.0.0",
        execute_entrypoint=lambda **_kwargs: {"success": True, "return_code": 0, "report_path": "", "metrics_path": ""},
    )
    result = workflow.run("试运行 missing-v1.0.0")
    assert result["status"] == "blocked"
    assert result["reason"] == "workpackage_not_found"


def test_dryrun_workflow_success_returns_summary(tmp_path) -> None:
    bundle = tmp_path / "workpackages" / "bundles" / "demo-v1.0.0"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "workpackage.json").write_text(
        '{"name":"demo","version":"v1.0.0","sources":["gaode","baidu"]}',
        encoding="utf-8",
    )
    (bundle / "entrypoint.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    workflow = WorkpackageDryrunWorkflow(
        bundle_root=tmp_path / "workpackages" / "bundles",
        extract_bundle_name=lambda _prompt: "demo-v1.0.0",
        execute_entrypoint=lambda **_kwargs: {
            "success": True,
            "return_code": 0,
            "report_path": str(bundle / "observability" / "dryrun_report.json"),
            "metrics_path": str(bundle / "observability" / "line_metrics.json"),
        },
    )
    result = workflow.run("试运行 demo-v1.0.0")
    assert result["status"] == "ok"
    assert result["action"] == "dryrun_workpackage"
    assert result["dryrun"]["status"] == "success"
    assert result["dryrun"]["output_summary"]["result_count"] == 2
