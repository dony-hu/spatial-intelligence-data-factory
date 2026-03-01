from services.governance_worker.app.core.queue import enqueue_task


def test_enqueue_without_queue_mode_fails_fast(monkeypatch) -> None:
    monkeypatch.delenv("GOVERNANCE_QUEUE_MODE", raising=False)
    result = enqueue_task({"task_id": "task_no_mode"})
    assert result.queued is False
    assert result.backend == "none"
    assert result.message == "queue_mode_unset"


def test_enqueue_unknown_mode_is_unsupported(monkeypatch) -> None:
    monkeypatch.setenv("GOVERNANCE_QUEUE_MODE", "unsupported")
    result = enqueue_task({"task_id": "task_mode_unsupported"})
    assert result.queued is False
    assert result.backend == "unsupported"
    assert result.message == "queue_mode_unsupported"


def test_enqueue_rq_mode_returns_error_when_rq_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("GOVERNANCE_QUEUE_MODE", "rq")
    result = enqueue_task({"task_id": "task_rq_unavailable"})
    assert result.queued is False
    assert result.backend == "rq"
    assert result.message.startswith("enqueue_failed:")
