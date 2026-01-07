"""Error handler stub for backward compatibility.

This module is deprecated. The new MasterAgent uses simple error handling.
These stubs are kept for existing subagent compatibility until they are rewritten.
"""

from enum import Enum
from typing import Any


class ErrorType(str, Enum):
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class AgentError(Exception):
    def __init__(
        self,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        message: str = "",
        **kwargs: Any,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.retry_count = kwargs.get("retry_count", 0)
        self.can_retry = kwargs.get("can_retry", True)
        self.timestamp = kwargs.get("timestamp", "")

    @classmethod
    def from_exception(cls, exception: Exception, **kwargs: Any) -> "AgentError":
        return cls(
            error_type=ErrorType.UNKNOWN_ERROR,
            message=str(exception),
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "retry_count": self.retry_count,
        }

    def get_retry_delay(self) -> float:
        return 1.0 * (2**self.retry_count)


class InterventionAction(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


class UserInterventionState:
    def __init__(self):
        self.pending_error: AgentError | None = None
        self.awaiting_response: bool = False
        self._response: InterventionAction | None = None

    def set_pending_error(self, error: AgentError) -> None:
        self.pending_error = error
        self.awaiting_response = True

    def set_response(self, action: InterventionAction) -> None:
        self._response = action
        self.awaiting_response = False

    def get_response(self) -> InterventionAction | None:
        return self._response


_intervention_states: dict[str, UserInterventionState] = {}


def get_intervention_state(session_id: str) -> UserInterventionState:
    if session_id not in _intervention_states:
        _intervention_states[session_id] = UserInterventionState()
    return _intervention_states[session_id]


def clear_intervention_state(session_id: str) -> None:
    if session_id in _intervention_states:
        del _intervention_states[session_id]


def create_error_sse_event(error: AgentError, step_info: Any = None) -> dict[str, Any]:
    return {"error": error.to_dict(), "step_info": step_info}


def create_retry_sse_event(**kwargs: Any) -> dict[str, Any]:
    return kwargs


def create_intervention_sse_event(**kwargs: Any) -> dict[str, Any]:
    return kwargs


async def execute_with_retry(func: Any, *args: Any, **kwargs: Any) -> Any:
    return await func(*args, **kwargs)
