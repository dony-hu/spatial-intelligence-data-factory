from services.governance_worker.app.core.queue import IN_MEMORY_QUEUE, enqueue_task


def test_enqueue_fallback_to_in_memory_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ALLOW_IN_MEMORY_QUEUE", "1")
    before = len(IN_MEMORY_QUEUE.jobs)
    result = enqueue_task({"task_id": "task_fallback"})
    after = len(IN_MEMORY_QUEUE.jobs)
    assert result.queued is True
    assert after >= before


def test_enqueue_strict_mode_blocks_fallback_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_IN_MEMORY_QUEUE", raising=False)
    result = enqueue_task({"task_id": "task_no_fallback"})
    assert result.queued is False
    assert result.backend == "rq"
    assert result.message.startswith("enqueue_failed:")
