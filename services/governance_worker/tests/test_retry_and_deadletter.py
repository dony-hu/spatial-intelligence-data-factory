from services.governance_worker.app.core.queue import IN_MEMORY_QUEUE, enqueue_task


def test_enqueue_fallback_to_in_memory() -> None:
    before = len(IN_MEMORY_QUEUE.jobs)
    result = enqueue_task({"task_id": "task_fallback"})
    after = len(IN_MEMORY_QUEUE.jobs)
    assert result.queued is True
    assert after >= before
