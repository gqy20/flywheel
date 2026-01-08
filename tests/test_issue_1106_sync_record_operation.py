"""Tests for Issue #1106 - record_operation should be sync (no I/O)."""

import asyncio
import pytest

from flywheel.storage import IOMetrics


class TestIssue1106SyncRecordOperation:
    """Test that record_operation can be called synchronously.

    Issue #1106: record_operation is a simple dict append with no I/O blocking,
    so it should be synchronous. This allows it to be called from both sync and
    async contexts without needing await.
    """

    @pytest.mark.asyncio
    async def test_record_operation_is_sync_method(self):
        """Test that record_operation can be called synchronously (without await)."""
        metrics = IOMetrics()

        # record_operation should be callable synchronously
        # If it's async, calling it like this will return a coroutine instead of recording
        metrics.record_operation("test", 0.1, 0, True, None)

        # Verify the operation was recorded
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert len(ops) == 1
        assert ops[0]['operation_type'] == 'test'
        assert ops[0]['duration'] == 0.1
        assert ops[0]['success'] is True

    @pytest.mark.asyncio
    async def test_track_operation_calls_sync_record_operation(self):
        """Test that track_operation context manager works with sync record_operation."""
        metrics = IOMetrics()

        # The context manager should work without issues
        async with metrics.track_operation("test_operation"):
            await asyncio.sleep(0.01)

        # Verify the operation was recorded
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert len(ops) == 1
        assert ops[0]['operation_type'] == 'test_operation'
        assert ops[0]['success'] is True

    @pytest.mark.asyncio
    async def test_multiple_sync_record_operations(self):
        """Test multiple synchronous calls to record_operation."""
        metrics = IOMetrics()

        # Call record_operation multiple times synchronously
        metrics.record_operation("op1", 0.1, 0, True)
        metrics.record_operation("op2", 0.2, 1, True)
        metrics.record_operation("op3", 0.3, 0, False, "Error")

        # All should be recorded
        assert metrics.total_operation_count() == 3
        ops = metrics.operations
        assert ops[0]['operation_type'] == 'op1'
        assert ops[1]['operation_type'] == 'op2'
        assert ops[2]['operation_type'] == 'op3'
        assert ops[2]['success'] is False
        assert ops[2]['error_type'] == 'Error'
