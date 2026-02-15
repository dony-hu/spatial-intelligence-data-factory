from services.governance_worker.app.core.task_state import TaskState, can_transition


def test_valid_state_transition() -> None:
    assert can_transition(TaskState.PENDING, TaskState.RUNNING) is True


def test_invalid_state_transition() -> None:
    assert can_transition(TaskState.SUCCEEDED, TaskState.RUNNING) is False
