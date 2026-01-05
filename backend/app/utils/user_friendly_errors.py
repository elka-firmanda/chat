"""
User-friendly error message utilities for backend.

Maps technical error types to user-friendly messages with suggestions.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ErrorType(str, Enum):
    API_TIMEOUT = "api_timeout"
    API_RATE_LIMIT = "api_rate_limit"
    API_AUTH = "api_auth"
    API_UNAVAILABLE = "api_unavailable"
    NETWORK_ERROR = "network_error"
    CONNECTION_TIMEOUT = "connection_timeout"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    SCHEMA_ERROR = "schema_error"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_ERROR = "execution_error"
    MEMORY_ERROR = "memory_error"
    DATA_NOT_FOUND = "data_not_found"
    DATA_CORRUPTION = "data_corruption"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class UserFriendlyError:
    title: str
    description: str
    suggestion: str
    severity: str  # 'info', 'warning', 'error'


ERROR_MESSAGES: Dict[ErrorType, UserFriendlyError] = {
    ErrorType.API_TIMEOUT: UserFriendlyError(
        title="AI Response Delayed",
        description="The AI is taking longer than expected to respond. This can happen during high-traffic periods.",
        suggestion="Try again in a few moments. If the issue persists, the service may be experiencing high demand.",
        severity="warning",
    ),
    ErrorType.API_RATE_LIMIT: UserFriendlyError(
        title="Too Many Requests",
        description="You've made too many requests in a short time. The service needs a moment to catch up.",
        suggestion="Please wait a moment before trying again. This helps ensure everyone gets a smooth experience.",
        severity="warning",
    ),
    ErrorType.API_AUTH: UserFriendlyError(
        title="Authentication Issue",
        description="There seems to be an issue with the API authentication. This is usually a configuration problem.",
        suggestion="Please check your API settings and ensure your API keys are correctly configured.",
        severity="error",
    ),
    ErrorType.API_UNAVAILABLE: UserFriendlyError(
        title="Service Temporarily Unavailable",
        description="The AI service is temporarily unavailable. This is usually a temporary issue on their end.",
        suggestion="Please wait a moment and try again. The service typically recovers quickly.",
        severity="error",
    ),
    ErrorType.NETWORK_ERROR: UserFriendlyError(
        title="Network Connection Issue",
        description="There was a problem connecting to the service. Your internet connection may be unstable.",
        suggestion="Check your internet connection and try again. If the problem continues, the service may be experiencing issues.",
        severity="warning",
    ),
    ErrorType.CONNECTION_TIMEOUT: UserFriendlyError(
        title="Connection Timed Out",
        description="The connection to the service took too long and was closed. This can happen during network issues.",
        suggestion="Check your internet connection and try again. Consider trying at a different time if issues persist.",
        severity="warning",
    ),
    ErrorType.API_ERROR: UserFriendlyError(
        title="Service Error",
        description="The AI service returned an unexpected error. This is usually a temporary issue.",
        suggestion="Try again in a few moments. If the problem persists, the service may be experiencing temporary difficulties.",
        severity="error",
    ),
    ErrorType.VALIDATION_ERROR: UserFriendlyError(
        title="Invalid Input",
        description="The request contained invalid data that could not be processed.",
        suggestion="Try rephrasing your request or removing special characters that might cause issues.",
        severity="error",
    ),
    ErrorType.SCHEMA_ERROR: UserFriendlyError(
        title="Data Processing Error",
        description="There was an error processing the response from the AI service.",
        suggestion="Try again. If the problem persists, the service may be experiencing temporary difficulties.",
        severity="error",
    ),
    ErrorType.EXECUTION_TIMEOUT: UserFriendlyError(
        title="Operation Took Too Long",
        description="The operation exceeded the maximum allowed time and was stopped.",
        suggestion="Try a simpler request or break it into smaller parts. Complex operations may need more time.",
        severity="warning",
    ),
    ErrorType.EXECUTION_ERROR: UserFriendlyError(
        title="Execution Failed",
        description="The requested operation could not be completed successfully.",
        suggestion="Review your request for any errors and try again. If this is code execution, check for syntax issues.",
        severity="error",
    ),
    ErrorType.MEMORY_ERROR: UserFriendlyError(
        title="Resource Limit Reached",
        description="The operation required more memory than available. This is a resource limitation.",
        suggestion="Try a simpler request or one that requires less processing. Complex operations may need to be broken down.",
        severity="error",
    ),
    ErrorType.DATA_NOT_FOUND: UserFriendlyError(
        title="Data Not Found",
        description="The requested data could not be found. It may have been removed or never existed.",
        suggestion="Verify the information you're looking for and try a different query. The data may need to be fetched again.",
        severity="info",
    ),
    ErrorType.DATA_CORRUPTION: UserFriendlyError(
        title="Data Integrity Issue",
        description="The data appears to be corrupted or incomplete.",
        suggestion="Try again. If the problem persists, the data may need to be refreshed or reloaded.",
        severity="error",
    ),
    ErrorType.SYSTEM_ERROR: UserFriendlyError(
        title="System Error",
        description="An unexpected error occurred in the system. This is not your fault.",
        suggestion="Please try again. If the problem persists, there may be a temporary system issue.",
        severity="error",
    ),
    ErrorType.UNKNOWN_ERROR: UserFriendlyError(
        title="Something Went Wrong",
        description="An unexpected error occurred. We're not sure what caused it.",
        suggestion="Try again. If the problem persists, please check your connection and try again later.",
        severity="error",
    ),
}


def get_user_friendly_error(
    error_type: str,
    original_message: Optional[str] = None,
) -> UserFriendlyError:
    """
    Get user-friendly error message for a technical error type.

    Args:
        error_type: Technical error type string
        original_message: Original error message to append

    Returns:
        UserFriendlyError with title, description, and suggestion
    """
    try:
        et = ErrorType(error_type)
        friendly = ERROR_MESSAGES[et]
    except ValueError:
        friendly = ERROR_MESSAGES[ErrorType.UNKNOWN_ERROR]

    if original_message and original_message not in friendly.description:
        return UserFriendlyError(
            title=friendly.title,
            description=f"{friendly.description} (Original: {original_message})",
            suggestion=friendly.suggestion,
            severity=friendly.severity,
        )

    return friendly


def get_suggested_actions(error_type: str) -> list:
    """Get suggested actions for an error type."""
    actions: Dict[ErrorType, list] = {
        ErrorType.API_TIMEOUT: [
            "Wait a moment and retry",
            "Try a simpler request",
            "Check if the service is experiencing issues",
        ],
        ErrorType.API_RATE_LIMIT: [
            "Wait before sending more requests",
            "Reduce the frequency of your requests",
            "Try again in a few minutes",
        ],
        ErrorType.API_AUTH: [
            "Check your API keys in settings",
            "Verify your API key is valid and has the required permissions",
            "Contact support if the issue persists",
        ],
        ErrorType.API_UNAVAILABLE: [
            "Wait and try again later",
            "Check service status pages",
            "Try an alternative provider if configured",
        ],
        ErrorType.NETWORK_ERROR: [
            "Check your internet connection",
            "Refresh the page",
            "Try again in a few moments",
        ],
        ErrorType.CONNECTION_TIMEOUT: [
            "Check your internet connection",
            "Try a simpler request",
            "Wait and retry",
        ],
        ErrorType.API_ERROR: [
            "Retry the request",
            "Try again in a few moments",
            "If persistent, check service status",
        ],
        ErrorType.VALIDATION_ERROR: [
            "Review your input for errors",
            "Remove special characters",
            "Try rephrasing your request",
        ],
        ErrorType.SCHEMA_ERROR: [
            "Retry the request",
            "Try a simpler query",
            "If persistent, contact support",
        ],
        ErrorType.EXECUTION_TIMEOUT: [
            "Try a simpler request",
            "Break complex tasks into smaller steps",
            "Reduce the scope of your request",
        ],
        ErrorType.EXECUTION_ERROR: [
            "Review your code for errors",
            "Check syntax and logic",
            "Try a simpler operation",
        ],
        ErrorType.MEMORY_ERROR: [
            "Try a simpler request",
            "Reduce the amount of data processed",
            "Break complex operations into smaller parts",
        ],
        ErrorType.DATA_NOT_FOUND: [
            "Verify the data exists",
            "Try a different query",
            "Check if the data needs to be reloaded",
        ],
        ErrorType.DATA_CORRUPTION: [
            "Try reloading the data",
            "Refresh the page",
            "Try again later",
        ],
        ErrorType.SYSTEM_ERROR: [
            "Refresh the page",
            "Try again in a few moments",
            "Contact support if the issue persists",
        ],
        ErrorType.UNKNOWN_ERROR: [
            "Try again",
            "Refresh the page",
            "Check your connection",
        ],
    }

    try:
        et = ErrorType(error_type)
        return actions.get(et, actions[ErrorType.UNKNOWN_ERROR])
    except ValueError:
        return actions[ErrorType.UNKNOWN_ERROR]
