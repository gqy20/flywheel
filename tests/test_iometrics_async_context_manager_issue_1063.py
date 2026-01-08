"""Tests for IOMetrics async context manager (Issue #1063)."""

import asyncio
import pytest

from flywheel.storage import IOMetrics


class TestIOMetricsAsyncContextManager:
    """Test async context manager functionality for IOMetrics."""

    @pytest.mark.asyncio
    async def test_track_operation_context_manager_basic(self):
        """Test basic async context manager for tracking operations."""
        metrics = IOMetrics()

        # Test that track_operation method exists and returns an async context manager
        async with metrics.track_operation("test_operation") as tracker:
            # Simulate some work
            await asyncio.sleep(0.01)
            # The tracker should have recorded start time
            assert tracker.start_time is not None

        # After context exits, operation should be recorded
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert len(ops) == 1
        assert ops[0]['operation_type'] == 'test_operation'
        assert ops[0]['success'] is True
        assert ops[0]['duration'] > 0
        assert ops[0]['retries'] == 0

    @pytest.mark.asyncio
    async def test_track_operation_context_manager_with_exception(self):
        """Test async context manager captures exceptions."""
        metrics = IOMetrics()

        with pytest.raises(ValueError, match="Test error"):
            async with metrics.track_operation("failing_operation"):
                raise ValueError("Test error")

        # Operation should still be recorded but marked as failed
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert len(ops) == 1
        assert ops[0]['operation_type'] == 'failing_operation'
        assert ops[0]['success'] is False
        assert ops[0]['error_type'] == 'ValueError'

    @pytest.mark.asyncio
    async def test_track_operation_simplifies_code(self):
        """Test that context manager simplifies tracking code."""
        metrics = IOMetrics()

        # Old way (manual tracking with try/except)
        start_time = asyncio.get_event_loop().time()
        try:
            await asyncio.sleep(0.01)
            success = True
            error_type = None
        except Exception as e:
            success = False
            error_type = type(e).__name__
        duration = asyncio.get_event_loop().time() - start_time
        await metrics.record_operation("manual", duration, 0, success, error_type)

        # New way (with context manager)
        async with metrics.track_operation("automatic"):
            await asyncio.sleep(0.01)

        # Both should result in recorded operations
        assert metrics.total_operation_count() == 2
        assert metrics.operations[0]['operation_type'] == 'manual'
        assert metrics.operations[1]['operation_type'] == 'automatic'

    @pytest.mark.asyncio
    async def test_track_operation_custom_retries(self):
        """Test context manager with custom retry count."""
        metrics = IOMetrics()

        async with metrics.track_operation("retry_operation", retries=3):
            await asyncio.sleep(0.01)

        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert ops[0]['retries'] == 3

    @pytest.mark.asyncio
    async def test_track_operation_multiple_sequential(self):
        """Test multiple sequential operations can be tracked."""
        metrics = IOMetrics()

        async with metrics.track_operation("op1"):
            await asyncio.sleep(0.01)

        async with metrics.track_operation("op2"):
            await asyncio.sleep(0.01)

        async with metrics.track_operation("op3"):
            await asyncio.sleep(0.01)

        assert metrics.total_operation_count() == 3
        assert [op['operation_type'] for op in metrics.operations] == ['op1', 'op2', 'op3']
