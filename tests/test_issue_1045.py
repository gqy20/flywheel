"""
Test for issue #1045: asyncio.TimeoutError handling bug in _retry_io_operation

The bug: When asyncio.wait_for times out, the code catches the exception,
re-raises it, and then tries to access e.errno in the outer IOError block,
which causes AttributeError since TimeoutError has no errno attribute.
"""

import asyncio
import pytest
from flywheel.storage import StorageTimeoutError, _retry_io_operation


async def test_timeout_error_does_not_raise_attribute_error():
    """
    Test that when a timeout occurs, it properly raises StorageTimeoutError
    without trying to access errno on the TimeoutError object.
    """

    async def slow_operation():
        """An operation that takes longer than the timeout."""
        await asyncio.sleep(10)  # Sleep longer than timeout
        return "should not reach here"

    # This should raise StorageTimeoutError, NOT AttributeError
    with pytest.raises(StorageTimeoutError) as exc_info:
        await _retry_io_operation(
            slow_operation,
            timeout=0.1,  # Very short timeout
            max_attempts=1
        )

    # Verify the error message contains the timeout information
    assert "timed out after" in str(exc_info.value)
    assert "0.1" in str(exc_info.value)


async def test_timeout_with_retry_does_not_cause_attribute_error():
    """
    Test that even with multiple retry attempts, timeout handling works correctly
    without causing AttributeError.
    """

    async def slow_operation():
        """An operation that times out."""
        await asyncio.sleep(5)
        return "should not reach here"

    # With multiple retry attempts, ensure no AttributeError occurs
    with pytest.raises(StorageTimeoutError) as exc_info:
        await _retry_io_operation(
            slow_operation,
            timeout=0.1,
            max_attempts=3,
            initial_backoff=0.01
        )

    assert "timed out after" in str(exc_info.value)
