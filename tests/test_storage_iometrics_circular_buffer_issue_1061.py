"""Tests for IOMetrics circular buffer implementation (Issue #1061).

This test ensures that the IOMetrics operations list uses a circular buffer
to prevent unbounded memory growth in long-running processes.
"""

import pytest


class TestIOMetricsCircularBufferIssue1061:
    """Test suite for IOMetrics circular buffer (Issue #1061)."""

    @pytest.mark.asyncio
    async def test_operations_list_has_max_size_limit(self):
        """Test that operations list has a maximum size limit to prevent unbounded growth."""
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Record more operations than the max buffer size
        # Assuming we want to limit to around 1000 operations
        for i in range(10000):
            await metrics.record_operation(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )

        # The operations list should be bounded
        # This will fail initially because the list grows unbounded
        assert metrics.total_operation_count() <= 1000, \
            f"Operations list should be bounded to 1000, but has {metrics.total_operation_count()} items"

    @pytest.mark.asyncio
    async def test_old_operations_are_evicted_when_buffer_full(self):
        """Test that old operations are evicted when the circular buffer is full."""
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Record operations with identifiable data
        for i in range(1500):
            await metrics.record_operation(
                f"operation_{i}",
                duration=float(i),
                retries=0,
                success=True
            )

        # Should only keep the most recent 1000 operations
        assert metrics.total_operation_count() <= 1000

        # The oldest operations should have been evicted
        # The first operation in the list should be operation_500 or later
        first_op_type = metrics.operations[0]['operation_type']
        assert first_op_type not in ['operation_0', 'operation_1', 'operation_10'], \
            f"Oldest operations should be evicted, but found {first_op_type}"

    @pytest.mark.asyncio
    async def test_metrics_remain_accurate_with_circular_buffer(self):
        """Test that metrics remain accurate even with circular buffer eviction."""
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Record many operations
        for i in range(2000):
            await metrics.record_operation(
                "read",
                duration=0.1,
                retries=0,
                success=True
            )

        # Metrics should still work correctly
        assert metrics.total_operation_count() <= 1000
        assert metrics.total_duration() > 0

        # New operations should still be recorded
        await metrics.record_operation("write", duration=0.5, retries=1, success=True)
        assert metrics.total_operation_count() <= 1000
