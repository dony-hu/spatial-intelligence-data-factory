from __future__ import annotations

from enum import Enum


class TaskState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"


VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.PENDING: {TaskState.RUNNING, TaskState.FAILED, TaskState.BLOCKED},
    TaskState.RUNNING: {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.BLOCKED},
    TaskState.BLOCKED: set(),
    TaskState.FAILED: {TaskState.RETRYING, TaskState.DEAD_LETTER},
    TaskState.RETRYING: {TaskState.RUNNING, TaskState.FAILED},
    TaskState.SUCCEEDED: set(),
    TaskState.DEAD_LETTER: set(),
}


def can_transition(current: TaskState, target: TaskState) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())
