import os


from services.governance_api.app.repositories.governance_repository import REPOSITORY
from services.governance_worker.app.jobs.governance_job import run


class _RuntimeResultStub:
    def model_dump(self) -> dict:
        return {
            "strategy": "auto_accept",
            "confidence": 0.92,
            "evidence": {"items": [{"runtime": "ut"}]},
        }


class _RuntimeStub:
    def run_task(self, task_context: dict, ruleset: dict):
        return _RuntimeResultStub()


def test_governance_job_run_updates_task_status(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.governance_worker.app.jobs.governance_job.get_runtime",
        lambda: _RuntimeStub(),
    )
    task_id = "task_unit_flow"
    REPOSITORY.create_task(
        task_id=task_id,
        batch_name="unit-batch",
        ruleset_id="default",
        status="PENDING",
        queue_backend="test",
        queue_message="unit",
    )
    payload = {
        "task_id": task_id,
        "ruleset_id": "default",
        "records": [{"raw_id": "r1", "raw_text": "深圳市南山区科技园"}],
    }
    result = run(payload)
    assert result["status"] == "SUCCEEDED"
    assert REPOSITORY.get_task(task_id)["status"] == "SUCCEEDED"
