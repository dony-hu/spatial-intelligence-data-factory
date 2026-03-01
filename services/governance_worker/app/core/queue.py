from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class QueueEnqueueResult:
    queued: bool
    backend: str
    message: str


def enqueue_task(task_payload: dict[str, Any]) -> QueueEnqueueResult:
    queue_mode = os.getenv("GOVERNANCE_QUEUE_MODE", "").strip().lower()

    if not queue_mode:
        return QueueEnqueueResult(queued=False, backend="none", message="queue_mode_unset")

    if queue_mode == "sync":
        from services.governance_worker.app.jobs.governance_job import run

        run(task_payload)
        return QueueEnqueueResult(queued=True, backend="sync", message="executed")

    if queue_mode != "rq":
        return QueueEnqueueResult(queued=False, backend=queue_mode, message="queue_mode_unsupported")

    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    queue_name = os.getenv("RQ_QUEUE", "governance")

    try:
        from redis import Redis
        from rq import Queue

        conn = Redis.from_url(redis_url)
        queue = Queue(name=queue_name, connection=conn)
        queue.enqueue("services.governance_worker.app.jobs.governance_job.run", task_payload)
        return QueueEnqueueResult(queued=True, backend="rq", message="queued")
    except Exception as exc:
        return QueueEnqueueResult(queued=False, backend="rq", message=f"enqueue_failed:{exc.__class__.__name__}")
