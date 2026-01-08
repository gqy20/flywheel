"""Tests for sync record_operation in async context detection (Issue #1121).

This test ensures that calling the synchronous record_operation method
from an async context provides a clear error message directing users
to use record_operation_async instead.
"""

import asyncio

import pytest

from flywheel.storage import IOMetrics


class TestSyncRecordOperationInAsyncContextIssue1121:
    """Test suite for sync record_operation in async context (Issue #1121)."""

    @pytest.mark.asyncio
    async def test_record_operation_sync_in_async_context_raises_error(self):
        """Test that calling sync record_operation in async context raises RuntimeError.

        This test verifies that when record_operation (the sync method) is called
        from an async context, it raises a RuntimeError with a helpful message
        directing users to use record_operation_async instead.

        The current implementation will raise a RuntimeError from _AsyncCompatibleLock
        but with a generic message. The fix should provide a clearer message.
        """
        # Arrange
        metrics = IOMetrics()

        # Act & Assert
        # Calling the sync method from an async context should raise RuntimeError
        # with a message directing users to use the async version
        with pytest.raises(RuntimeError) as exc_info:
            metrics.record_operation(
                operation_type="read",
                duration=0.1,
                retries=0,
                success=True
            )

        # Verify the error message is helpful
        error_message = str(exc_info.value)
        # The error should mention using the async version
        assert "async" in error_message.lower() or "record_operation_async" in error_message, \
            f"Expected error message to mention async version, got: {error_message}"

    @pytest.mark.asyncio
    async def test_record_operation_async_works_in_async_context(self):
        """Test that record_operation_async works correctly in async context.

        This is the positive test - users should use record_operation_async
        in async contexts and it should work without issues.
        """
        # Arrange
        metrics = IOMetrics()

        # Act - this should work without raising any errors
        await metrics.record_operation_async(
            operation_type="read",
            duration=0.1,
            retries=0,
            success=True
        )

        # Assert - verify the operation was recorded
        assert len(metrics.operations) == 1, "Expected one operation to be recorded"
        assert metrics.operations[0]['operation_type'] == "read"
        assert metrics.operations[0]['duration'] == 0.1
        assert metrics.operations[0]['retries'] == 0
        assert metrics.operations[0]['success'] is True

    @pytest.mark.asyncio
    async def test_record_operation_sync_in_sync_context_works(self):
        """Test that record_operation works correctly in sync context.

        This verifies that the sync method still works in synchronous contexts,
        ensuring the fix doesn't break existing functionality.
        """
        # Arrange
        metrics = IOMetrics()

        # Act - call from a sync context (no running event loop)
        # We need to call this from outside an async function
        # So we'll use asyncio.create_task to run it in a separate thread
        # that doesn't have a running event loop

        def sync_call():
            """Call record_operation from a sync context."""
            metrics.record_operation(
                operation_type="write",
                duration=0.2,
                retries=1,
                success=True
            )

        # Run in a thread pool to avoid event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_call)

        # Assert - verify the operation was recorded
        assert len(metrics.operations) == 1, "Expected one operation to be recorded"
        assert metrics.operations[0]['operation_type'] == "write"
        assert metrics.operations[0]['duration'] == 0.2
        assert metrics.operations[0]['retries'] == 1
        assert metrics.operations[0]['success'] is True

    @pytest.mark.asyncio
    async def test_multiple_operations_in_async_context(self):
        """Test multiple async operations in sequence."""
        # Arrange
        metrics = IOMetrics()

        # Act - record multiple operations
        await metrics.record_operation_async("read", 0.1, 0, True)
        await metrics.record_operation_async("write", 0.2, 1, True)
        await metrics.record_operation_async("delete", 0.05, 0, False, "ENOENT")

        # Assert
        assert len(metrics.operations) == 3
        assert metrics.operations[0]['operation_type'] == "read"
        assert metrics.operations[1]['operation_type'] == "write"
        assert metrics.operations[2]['operation_type'] == "delete"
        assert metrics.operations[2]['success'] is False
        assert metrics.operations[2]['error_type'] == "ENOENT"
