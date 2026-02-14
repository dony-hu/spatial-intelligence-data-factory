from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueueEnqueueResult:
    queued: bool
    backend: str
    message: str


@dataclass
class InMemoryQueue:
    jobs: list[dict[str, Any]] = field(default_factory=list)


IN_MEMORY_QUEUE = InMemoryQueue()


def enqueue_task(task_payload: dict[str, Any]) -> QueueEnqueueResult:
    queue_mode = os.getenv("GOVERNANCE_QUEUE_MODE", "rq").lower()

    if queue_mode == "sync":
        from services.governance_worker.app.jobs.governance_job import run

        run(task_payload)
        return QueueEnqueueResult(queued=True, backend="sync", message="executed")

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
        if os.getenv("ALLOW_IN_MEMORY_QUEUE", "0") != "1":
            return QueueEnqueueResult(queued=False, backend="rq", message=f"enqueue_failed:{exc.__class__.__name__}")
        IN_MEMORY_QUEUE.jobs.append(task_payload)
        return QueueEnqueueResult(queued=True, backend="in_memory", message=f"fallback:{exc.__class__.__name__}")


def run_in_memory_once() -> int:
    if not IN_MEMORY_QUEUE.jobs:
        return 0
    job = IN_MEMORY_QUEUE.jobs.pop(0)
    from services.governance_worker.app.jobs.governance_job import run

    run(job)
    return 1


def run_in_memory_all() -> int:
    count = 0
    while IN_MEMORY_QUEUE.jobs:
        count += run_in_memory_once()
    return count
