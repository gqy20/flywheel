"""Tests for Issue #1074 - __aexit__ method incomplete implementation."""

import asyncio
import pytest

from flywheel.storage import IOMetrics


class TestIssue1074:
    """Test that __aexit__ method properly completes execution."""

    @pytest.mark.asyncio
    async def test_aexit_returns_none_on_success(self):
        """Test that __aexit__ returns None (or False) on successful operation."""
        metrics = IOMetrics()

        # The context manager should return None from __aexit__ to allow normal exception propagation
        async with metrics.track_operation("test_operation"):
            pass

        # Verify operation was recorded
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert len(ops) == 1
        assert ops[0]['operation_type'] == 'test_operation'
        assert ops[0]['success'] is True

    @pytest.mark.asyncio
    async def test_aexit_records_operation_on_success(self):
        """Test that __aexit__ calls record_operation with correct parameters on success."""
        metrics = IOMetrics()

        async with metrics.track_operation("successful_op"):
            await asyncio.sleep(0.01)

        # Verify record_operation was called
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert ops[0]['operation_type'] == 'successful_op'
        assert ops[0]['success'] is True
        assert ops[0]['error_type'] is None
        assert ops[0]['duration'] > 0

    @pytest.mark.asyncio
    async def test_aexit_records_operation_on_failure(self):
        """Test that __aexit__ calls record_operation with correct parameters on failure."""
        metrics = IOMetrics()

        with pytest.raises(ValueError):
            async with metrics.track_operation("failing_op"):
                await asyncio.sleep(0.01)
                raise ValueError("Test error")

        # Verify record_operation was called with failure info
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert ops[0]['operation_type'] == 'failing_op'
        assert ops[0]['success'] is False
        assert ops[0]['error_type'] == 'ValueError'
        assert ops[0]['duration'] > 0

    @pytest.mark.asyncio
    async def test_aexit_does_not_suppress_exceptions(self):
        """Test that __aexit__ returns None/False to allow exceptions to propagate."""
        metrics = IOMetrics()

        # If __aexit__ returns True, it would suppress the exception
        # We want to ensure exceptions are NOT suppressed
        with pytest.raises(RuntimeError):
            async with metrics.track_operation("op_with_error"):
                raise RuntimeError("This should propagate")

        # Exception should have been recorded
        assert metrics.total_operation_count() == 1
        ops = metrics.operations
        assert ops[0]['success'] is False
        assert ops[0]['error_type'] == 'RuntimeError'
