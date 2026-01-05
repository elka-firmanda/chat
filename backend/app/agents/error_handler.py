"""
Error Handling System with Retry Logic and User Intervention

Implements:
- Error classification (API, timeout, validation)
- Automatic retry with exponential backoff (max 3 attempts)
- User intervention handling (retry, skip, abort)
- Error logging in working memory
- SSE event emission for error states
"""

import asyncio
import functools
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from dataclasses import dataclass, field
import traceback

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Classification of error types for appropriate handling."""

    # API-related errors
    API_ERROR = "api_error"  # Generic API error
    API_AUTH = "api_auth"  # Authentication/authorization failed
    API_RATE_LIMIT = "api_rate_limit"  # Rate limited
    API_TIMEOUT = "api_timeout"  # API request timed out
    API_UNAVAILABLE = "api_unavailable"  # Service unavailable

    # Network errors
    NETWORK_ERROR = "network_error"  # Network connectivity issue
    CONNECTION_TIMEOUT = "connection_timeout"  # Connection establishment timeout

    # Validation errors
    VALIDATION_ERROR = "validation_error"  # Input validation failed
    SCHEMA_ERROR = "schema_error"  # Response schema mismatch

    # Execution errors
    EXECUTION_TIMEOUT = "execution_timeout"  # Code execution timeout
    EXECUTION_ERROR = "execution_error"  # Code execution failed
    MEMORY_ERROR = "memory_error"  # Out of memory

    # Data errors
    DATA_NOT_FOUND = "data_not_found"  # Required data missing
    DATA_CORRUPTION = "data_corruption"  # Data integrity issue

    # System errors
    SYSTEM_ERROR = "system_error"  # Internal system error
    UNKNOWN_ERROR = "unknown_error"  # Unclassified error


class InterventionAction(str, Enum):
    """User intervention actions."""

    RETRY = "retry"  # Retry the failed operation
    SKIP = "skip"  # Skip this step and continue
    ABORT = "abort"  # Abort the entire workflow


@dataclass
class AgentError(Exception):
    """Structured error information for agents."""

    error_type: ErrorType
    message: str
    original_exception: Optional[Exception] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    step_info: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "step_info": self.step_info,
            "context": self.context,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "can_retry": self.can_retry,
            "can_skip": self._can_skip(),
        }

    @property
    def can_retry(self) -> bool:
        """Check if this error can be retried."""
        return self.retry_count < self.max_retries and self._is_retryable()

    def _is_retryable(self) -> bool:
        """Determine if this error type is retryable."""
        non_retryable = {
            ErrorType.VALIDATION_ERROR,
            ErrorType.SCHEMA_ERROR,
            ErrorType.DATA_NOT_FOUND,
            ErrorType.DATA_CORRUPTION,
            ErrorType.API_AUTH,
        }
        return self.error_type not in non_retryable

    def _can_skip(self) -> bool:
        """Determine if this error allows skipping the step."""
        # Most errors can be skipped except critical system errors
        non_skipable = {
            ErrorType.SYSTEM_ERROR,
            ErrorType.MEMORY_ERROR,
        }
        return self.error_type not in non_skipable

    def get_retry_delay(self) -> float:
        """Get delay in seconds before next retry (exponential backoff)."""
        base_delay = 1.0  # 1 second base
        # Different base delays for different error types
        type_delays = {
            ErrorType.API_RATE_LIMIT: 5.0,
            ErrorType.API_TIMEOUT: 2.0,
            ErrorType.CONNECTION_TIMEOUT: 2.0,
            ErrorType.NETWORK_ERROR: 3.0,
        }
        base = type_delays.get(self.error_type, base_delay)
        # Exponential backoff: delay * 2^retry_count
        return base * (2**self.retry_count)

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        step_info: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> "AgentError":
        """Create AgentError from an exception."""
        error_type = cls._classify_exception(exception)
        message = cls._get_error_message(exception, error_type)

        return cls(
            error_type=error_type,
            message=message,
            original_exception=exception,
            step_info=step_info,
            context=context or {},
        )

    @staticmethod
    def _classify_exception(exception: Exception) -> ErrorType:
        """Classify an exception into an ErrorType."""
        exception_type = type(exception).__name__
        exception_str = str(exception).lower()

        # Check for common patterns (more specific first)
        if "auth" in exception_str or "401" in exception_str or "403" in exception_str:
            return ErrorType.API_AUTH
        elif "rate limit" in exception_str or "429" in exception_str:
            return ErrorType.API_RATE_LIMIT
        elif "connection refused" in exception_str:
            return ErrorType.CONNECTION_TIMEOUT
        elif "connection timeout" in exception_str:
            return ErrorType.CONNECTION_TIMEOUT
        elif "connection" in exception_str or "network" in exception_str:
            return ErrorType.NETWORK_ERROR
        elif "timeout" in exception_str or "504" in exception_str:
            return ErrorType.API_TIMEOUT
        elif "validation" in exception_str or "validate" in exception_str:
            return ErrorType.VALIDATION_ERROR
        elif "not found" in exception_str or "404" in exception_str:
            return ErrorType.DATA_NOT_FOUND
        elif "schema" in exception_str or "parse" in exception_str:
            return ErrorType.SCHEMA_ERROR
        elif "timeout" in exception_str or "execution time" in exception_str:
            return ErrorType.EXECUTION_TIMEOUT
        elif "memory" in exception_str or "out of memory" in exception_str:
            return ErrorType.MEMORY_ERROR
        elif "unavailable" in exception_str or "503" in exception_str:
            return ErrorType.API_UNAVAILABLE
        elif exception_type in ("AttributeError", "TypeError", "KeyError"):
            return ErrorType.VALIDATION_ERROR
        elif exception_type in ("RuntimeError", "SystemError"):
            return ErrorType.SYSTEM_ERROR

        return ErrorType.UNKNOWN_ERROR

    @staticmethod
    def _get_error_message(exception: Exception, error_type: ErrorType) -> str:
        """Get a human-readable error message."""
        base_messages = {
            ErrorType.API_ERROR: "API request failed",
            ErrorType.API_AUTH: "Authentication failed",
            ErrorType.API_RATE_LIMIT: "Rate limit exceeded",
            ErrorType.API_TIMEOUT: "API request timed out",
            ErrorType.API_UNAVAILABLE: "Service unavailable",
            ErrorType.NETWORK_ERROR: "Network error occurred",
            ErrorType.CONNECTION_TIMEOUT: "Connection timed out",
            ErrorType.VALIDATION_ERROR: "Validation error",
            ErrorType.SCHEMA_ERROR: "Schema validation failed",
            ErrorType.EXECUTION_TIMEOUT: "Execution timed out",
            ErrorType.EXECUTION_ERROR: "Execution failed",
            ErrorType.MEMORY_ERROR: "Out of memory",
            ErrorType.DATA_NOT_FOUND: "Required data not found",
            ErrorType.DATA_CORRUPTION: "Data corruption detected",
            ErrorType.SYSTEM_ERROR: "System error",
            ErrorType.UNKNOWN_ERROR: "Unknown error",
        }

        base = base_messages.get(error_type, "Error occurred")
        # Add exception message if available
        exception_msg = str(exception)
        if exception_msg and exception_msg not in base.lower():
            return f"{base}: {exception_msg}"
        return base


class UserInterventionState:
    """Tracks user intervention state for error recovery."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.pending_error: Optional[AgentError] = None
        self.awaiting_response: bool = False
        self.action: Optional[InterventionAction] = None
        self.response_time: Optional[str] = None
        self._event_loop: Optional[asyncio.Event] = None

    def set_pending_error(self, error: AgentError) -> None:
        """Set a pending error awaiting user intervention."""
        self.pending_error = error
        self.awaiting_response = True
        self.action = None
        self._event_loop = asyncio.Event()
        logger.info(f"Error pending for user intervention: {error.message}")

    async def wait_for_response(
        self, timeout: float = 300.0
    ) -> Optional[InterventionAction]:
        """Wait for user intervention response."""
        if not self._event_loop:
            self._event_loop = asyncio.Event()

        try:
            await asyncio.wait_for(self._event_loop.wait(), timeout=timeout)
            return self.action
        except asyncio.TimeoutError:
            logger.warning(f"User intervention timeout for session {self.session_id}")
            self.awaiting_response = False
            return None

    def set_response(self, action: InterventionAction) -> None:
        """Set the user's intervention response."""
        self.action = action
        self.awaiting_response = False
        self.response_time = datetime.utcnow().isoformat()
        if self._event_loop:
            self._event_loop.set()
        logger.info(f"User selected intervention: {action.value}")

    def clear(self) -> None:
        """Clear the intervention state."""
        self.pending_error = None
        self.awaiting_response = False
        self.action = None
        self.response_time = None
        self._event_loop = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "pending_error": self.pending_error.to_dict()
            if self.pending_error
            else None,
            "awaiting_response": self.awaiting_response,
            "action": self.action.value if self.action else None,
            "response_time": self.response_time,
        }


# Global intervention state manager
_intervention_states: Dict[str, UserInterventionState] = {}


def get_intervention_state(session_id: str) -> UserInterventionState:
    """Get or create intervention state for a session."""
    if session_id not in _intervention_states:
        _intervention_states[session_id] = UserInterventionState(session_id)
    return _intervention_states[session_id]


def clear_intervention_state(session_id: str) -> None:
    """Clear intervention state for a session."""
    if session_id in _intervention_states:
        _intervention_states[session_id].clear()
        del _intervention_states[session_id]


T = TypeVar("T", bound=Callable[..., Any])


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
):
    """
    Decorator to add retry logic with exponential backoff to async functions.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds before first retry
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)

                except asyncio.CancelledError:
                    # Don't retry on cancellation
                    raise

                except Exception as e:
                    last_error = e
                    error = AgentError.from_exception(e)

                    # Determine if we should retry
                    if not error.can_retry:
                        logger.warning(f"Non-retryable error: {error.error_type.value}")
                        raise

                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (exponential_base**attempt), max_delay)
                        # Add jitter (random variation)
                        import random

                        delay = delay * (0.5 + random.random())

                        logger.info(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} "
                            f"after {delay:.1f}s delay. Error: {error.message}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        # Max retries exceeded
                        logger.error(f"Max retries exceeded for {func.__name__}")
                        raise

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            raise Exception("Retry logic failed")

        return wrapper  # type: ignore

    return decorator


async def execute_with_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    error_context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Any:
    """
    Execute a function with retry logic and error tracking.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_retries: Maximum retry attempts
        error_context: Additional context for error logging
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Raises:
        AgentError: After all retries exhausted
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            last_error = e
            error = AgentError.from_exception(
                exception=e,
                context=error_context,
            )

            if not error.can_retry:
                logger.warning(f"Non-retryable error: {error.error_type.value}")
                raise

            if attempt < max_retries:
                delay = error.get_retry_delay()
                logger.info(
                    f"Retry attempt {attempt + 1}/{max_retries} after {delay:.1f}s. "
                    f"Error: {error.message}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Max retries exceeded. Final error: {error.message}")
                raise AgentError(
                    error_type=error.error_type,
                    message=f"Failed after {max_retries + 1} attempts: {error.message}",
                    original_exception=e,
                    context=error_context,
                    retry_count=attempt,
                    max_retries=max_retries,
                )

    if last_error:
        raise last_error
    raise Exception("Execution failed")


def create_error_sse_event(
    error: AgentError,
    step_info: Optional[Dict[str, Any]] = None,
    intervention_options: Optional[Dict[str, bool]] = None,
) -> Dict[str, Any]:
    """
    Create an SSE event payload for error notification with user-friendly details.

    Args:
        error: The error that occurred
        step_info: Information about the step that failed
        intervention_options: Available intervention options

    Returns:
        SSE event data dictionary with user-friendly messaging
    """
    from app.utils.user_friendly_errors import (
        get_user_friendly_error,
        get_suggested_actions,
    )

    friendly = get_user_friendly_error(
        error.error_type.value,
        error.message,
    )
    suggested_actions = get_suggested_actions(error.error_type.value)

    return {
        "event_type": "error",
        "error": error.to_dict(),
        "step_info": step_info or error.step_info,
        "intervention_options": intervention_options
        or {
            "retry": error.can_retry,
            "skip": error._can_skip(),
            "abort": True,
        },
        "timestamp": datetime.utcnow().isoformat(),
        "user_friendly": {
            "title": friendly.title,
            "description": friendly.description,
            "suggestion": friendly.suggestion,
            "severity": friendly.severity,
        },
        "suggested_actions": suggested_actions,
    }


def create_retry_sse_event(
    retry_count: int,
    max_retries: int,
    delay: float,
    step_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create an SSE event for retry notification.

    Args:
        retry_count: Current retry attempt number
        max_retries: Maximum retry attempts
        delay: Delay before retry
        step_info: Information about the step being retried

    Returns:
        SSE event data dictionary
    """
    return {
        "event_type": "retry",
        "retry_count": retry_count,
        "max_retries": max_retries,
        "delay": delay,
        "step_info": step_info,
        "timestamp": datetime.utcnow().isoformat(),
    }


def create_intervention_sse_event(
    action: InterventionAction,
    error: Optional[AgentError] = None,
) -> Dict[str, Any]:
    """
    Create an SSE event for user intervention.

    Args:
        action: The intervention action taken
        error: The error that prompted intervention

    Returns:
        SSE event data dictionary
    """
    return {
        "event_type": "intervention",
        "action": action.value,
        "error": error.to_dict() if error else None,
        "timestamp": datetime.utcnow().isoformat(),
    }
