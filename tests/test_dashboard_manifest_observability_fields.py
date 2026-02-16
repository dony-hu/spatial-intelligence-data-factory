from scripts.dashboard_data_lib import build_manifest


def test_dashboard_manifest_exposes_observability_fields() -> None:
    manifest = build_manifest()
    fields = manifest.get("observability_fields", {})
    assert "test_overview" in fields
    assert "execution_process" in fields
    assert "failure_classification" in fields
    assert "sql_panel" in fields
    assert "gate_decision" in fields["test_overview"]
    assert "quality_score" in fields["test_overview"]
    assert "task_batch_id" in fields["execution_process"]
    assert "failure_type" in fields["failure_classification"]
    assert "readonly_select_with_only" in fields["sql_panel"]
