class OrchestratorError(Exception):
    """Base error for orchestrator runtime."""


class InvalidTransitionError(OrchestratorError):
    """Raised when a state transition is invalid."""


class NotFoundError(OrchestratorError):
    """Raised when task state is missing."""
