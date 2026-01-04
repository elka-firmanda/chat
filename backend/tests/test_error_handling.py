"""
Test script for Phase 5 error handling with retry and user intervention.

Tests the error classification, retry logic, and intervention flow.
"""

import asyncio
import sys
import os

# Add the backend to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.agents.error_handler import (
    AgentError,
    ErrorType,
    InterventionAction,
    UserInterventionState,
    get_intervention_state,
    clear_intervention_state,
    create_error_sse_event,
    create_retry_sse_event,
    execute_with_retry,
)


async def test_error_classification():
    """Test that errors are classified correctly."""
    print("Testing error classification...")

    # Test API errors
    api_error = AgentError.from_exception(
        Exception("API request failed with 429 rate limit")
    )
    assert api_error.error_type == ErrorType.API_RATE_LIMIT
    print(f"✓ API rate limit error classified correctly: {api_error.error_type.value}")

    # Test timeout errors
    timeout_error = AgentError.from_exception(Exception("Connection timeout after 30s"))
    assert timeout_error.error_type == ErrorType.CONNECTION_TIMEOUT
    print(
        f"✓ Connection timeout error classified correctly: {timeout_error.error_type.value}"
    )

    # Test validation errors
    validation_error = AgentError.from_exception(
        Exception("Validation failed: field required")
    )
    assert validation_error.error_type == ErrorType.VALIDATION_ERROR
    print(
        f"✓ Validation error classified correctly: {validation_error.error_type.value}"
    )

    # Test authentication errors
    auth_error = AgentError.from_exception(
        Exception("401 Unauthorized: Invalid API key")
    )
    assert auth_error.error_type == ErrorType.API_AUTH
    print(f"✓ Authentication error classified correctly: {auth_error.error_type.value}")

    print("✓ All error classification tests passed!")


async def test_retry_logic():
    """Test retry logic with exponential backoff."""
    print("\nTesting retry logic...")

    # Create a retryable error
    error = AgentError(
        error_type=ErrorType.API_TIMEOUT,
        message="API request timed out",
        retry_count=0,
        max_retries=3,
    )

    # Test retry eligibility
    assert error.can_retry == True
    print(f"✓ Error can be retried initially")

    # Test retry delay calculation
    delay_1 = error.get_retry_delay()
    error.retry_count = 1
    delay_2 = error.get_retry_delay()
    error.retry_count = 2
    delay_3 = error.get_retry_delay()

    assert delay_2 > delay_1  # Exponential backoff
    assert delay_3 > delay_2
    print(
        f"✓ Exponential backoff working: delays = {delay_1:.1f}s, {delay_2:.1f}s, {delay_3:.1f}s"
    )

    # Test non-retryable errors
    validation_error = AgentError(
        error_type=ErrorType.VALIDATION_ERROR,
        message="Invalid input data",
        retry_count=0,
        max_retries=3,
    )
    assert validation_error.can_retry == False
    print(
        f"✓ Non-retryable error correctly identified: {validation_error.error_type.value}"
    )

    # Test max retries exceeded
    error.max_retries = 3
    error.retry_count = 3
    assert error.can_retry == False
    print(f"✓ Max retries correctly prevents further retries")

    print("✓ All retry logic tests passed!")


async def test_execute_with_retry():
    """Test the execute_with_retry function."""
    print("\nTesting execute_with_retry...")

    call_count = 0

    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return "Success!"

    # Test successful execution after retries
    result = await execute_with_retry(
        flaky_function,
        max_retries=3,
        error_context={"test": "value"},
    )
    assert result == "Success!"
    assert call_count == 3
    print(f"✓ Function succeeded after {call_count} attempts")

    # Test failure after max retries
    call_count = 0

    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise Exception("Always fails")

    try:
        await execute_with_retry(
            always_fails,
            max_retries=2,
            error_context={"test": "value"},
        )
        assert False, "Should have raised an error"
    except AgentError as e:
        assert e.retry_count == 2
        assert "Always fails" in e.message
        print(f"✓ Correctly raised AgentError after {call_count} attempts")

    print("✓ All execute_with_retry tests passed!")


async def test_user_intervention():
    """Test user intervention state machine."""
    print("\nTesting user intervention...")

    session_id = "test-session-123"

    # Clear any existing state
    clear_intervention_state(session_id)

    # Get intervention state
    state = get_intervention_state(session_id)
    assert state.awaiting_response == False
    print("✓ Initial intervention state is clean")

    # Create and set pending error
    error = AgentError(
        error_type=ErrorType.API_TIMEOUT,
        message="API request timed out",
        retry_count=3,
        max_retries=3,
    )
    state.set_pending_error(error)

    assert state.awaiting_response == True
    assert state.pending_error == error
    print("✓ Error state set correctly")

    # Test intervention options
    assert error.can_retry == False  # Max retries exceeded
    assert error._can_skip() == True
    print("✓ Intervention options calculated correctly")

    # Clear state
    clear_intervention_state(session_id)
    state = get_intervention_state(session_id)
    assert state.awaiting_response == False
    print("✓ State cleared correctly")

    print("✓ All user intervention tests passed!")


async def test_sse_events():
    """Test SSE event creation."""
    print("\nTesting SSE event creation...")

    error = AgentError(
        error_type=ErrorType.API_RATE_LIMIT,
        message="Rate limit exceeded. Please wait before making more requests.",
        retry_count=1,
        max_retries=3,
    )

    step_info = {
        "type": "research",
        "description": "Searching for information",
        "step_number": 2,
    }

    # Test error event
    error_event = create_error_sse_event(error, step_info)
    assert error_event["event_type"] == "error"
    assert error_event["error"]["error_type"] == "api_rate_limit"
    assert error_event["intervention_options"]["retry"] == True
    print("✓ Error event created correctly")

    # Test retry event
    retry_event = create_retry_sse_event(
        retry_count=2,
        max_retries=3,
        delay=4.0,
        step_info=step_info,
    )
    assert retry_event["event_type"] == "retry"
    assert retry_event["retry_count"] == 2
    assert retry_event["delay"] == 4.0
    print("✓ Retry event created correctly")

    print("✓ All SSE event tests passed!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 5 Error Handling Tests")
    print("=" * 60)

    try:
        await test_error_classification()
        await test_retry_logic()
        await test_execute_with_retry()
        await test_user_intervention()
        await test_sse_events()

        print("\n" + "=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
