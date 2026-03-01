from __future__ import annotations

from packages.factory_agent.agent import FactoryAgent


def test_requirement_confirmation_emits_llm_observation_events(monkeypatch) -> None:
    agent = FactoryAgent()
    captured: list[dict] = []

    monkeypatch.setattr(
        agent,
        "_run_requirement_query",
        lambda _prompt: {
            "answer": '{"target":"地址治理","data_sources":["gaode"],"outputs":["workpackage"]}',
            "latency_ms": 123,
            "token_usage": {"prompt": 10, "completion": 8, "total": 18},
        },
    )
    monkeypatch.setattr(agent, "_record_observation_event", lambda **kwargs: captured.append(kwargs))

    result = agent._handle_requirement_confirmation("请确认 demo-v1.0.0 的地址治理需求")
    assert result["status"] == "ok"
    event_types = [str(item.get("event_type") or "") for item in captured]
    assert "llm_request" in event_types
    assert "llm_response" in event_types
    assert "requirements_confirmed" in event_types


def test_publish_workflow_emits_runtime_stages_with_metadata(monkeypatch) -> None:
    agent = FactoryAgent()
    captured: list[dict] = []

    class _StubPublishWorkflow:
        @staticmethod
        def run(_prompt: str):
            return {"status": "ok", "runtime": {"status": "published", "receipt_id": "receipt_demo"}}

    monkeypatch.setattr(agent, "_publish_workflow", _StubPublishWorkflow())
    monkeypatch.setattr(
        agent,
        "_collect_workpackage_metadata",
        lambda _bundle_name: {
            "version": "v1.0.0",
            "checksum": "demo-checksum",
            "skills_count": 5,
            "artifact_count": 9,
        },
    )
    monkeypatch.setattr(agent, "_record_observation_event", lambda **kwargs: captured.append(kwargs))

    result = agent._handle_publish_workpackage("发布 demo-v1.0.0 到 runtime")
    assert result["status"] == "ok"
    event_types = [str(item.get("event_type") or "") for item in captured]
    assert "workpackage_packaged" in event_types
    assert "runtime_submit_requested" in event_types
    assert "runtime_submit_accepted" in event_types
    assert "runtime_task_running" in event_types
    assert "runtime_task_finished" in event_types
    submit_evt = next(item for item in captured if str(item.get("event_type") or "") == "runtime_submit_requested")
    payload = submit_evt.get("payload") or {}
    assert payload.get("checksum") == "demo-checksum"
    assert int(payload.get("skills_count") or 0) == 5
    assert int(payload.get("artifact_count") or 0) == 9

