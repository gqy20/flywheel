"""Tests for Issue #1078 - Add 'reset' method to IOMetrics."""

import pytest
import threading
import time

from flywheel.storage import IOMetrics


class TestIssue1078:
    """Test that IOMetrics has a reset method that clears metrics."""

    @pytest.mark.asyncio
    async def test_reset_clears_operations(self):
        """Test that reset() clears all recorded operations."""
        metrics = IOMetrics()

        # Record some operations
        await metrics.record_operation("read", 0.1, 0, True)
        await metrics.record_operation("write", 0.2, 1, True)
        await metrics.record_operation("flush", 0.05, 0, False, "ENOENT")

        # Verify operations were recorded
        assert metrics.total_operation_count() == 3
        assert len(metrics.operations) == 3

        # Reset the metrics
        metrics.reset()

        # Verify operations are cleared
        assert metrics.total_operation_count() == 0
        assert len(metrics.operations) == 0

    @pytest.mark.asyncio
    async def test_reset_after_multiple_operations(self):
        """Test that reset() works after many operations."""
        metrics = IOMetrics()

        # Record many operations
        for i in range(100):
            await metrics.record_operation(f"op_{i}", 0.01, 0, True)

        assert metrics.total_operation_count() == 100

        # Reset
        metrics.reset()

        # Verify cleared
        assert metrics.total_operation_count() == 0
        assert len(metrics.operations) == 0

    @pytest.mark.asyncio
    async def test_reset_can_be_called_multiple_times(self):
        """Test that reset() can be called multiple times without error."""
        metrics = IOMetrics()

        # Record some operations
        await metrics.record_operation("read", 0.1, 0, True)

        # Reset multiple times
        metrics.reset()
        metrics.reset()
        metrics.reset()

        # Should still be empty
        assert metrics.total_operation_count() == 0

    @pytest.mark.asyncio
    async def test_reset_on_empty_metrics(self):
        """Test that reset() works on empty metrics."""
        metrics = IOMetrics()

        # Reset without any operations
        metrics.reset()

        # Should still be empty
        assert metrics.total_operation_count() == 0
        assert len(metrics.operations) == 0

    @pytest.mark.asyncio
    async def test_reset_thread_safety(self):
        """Test that reset() is thread-safe using existing lock."""
        import asyncio
        metrics = IOMetrics()
        errors = []

        async def record_operations():
            """Record operations in a task."""
            try:
                for i in range(50):
                    await metrics.record_operation("thread_op", 0.01, 0, True)
                    await asyncio.sleep(0.0001)  # Small delay to increase contention
            except Exception as e:
                errors.append(e)

        async def reset_metrics():
            """Reset metrics in a task."""
            try:
                for i in range(10):
                    metrics.reset()
                    await asyncio.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append(e)

        # Start tasks
        tasks = []
        for _ in range(3):
            tasks.append(asyncio.create_task(record_operations()))

        for _ in range(2):
            tasks.append(asyncio.create_task(reset_metrics()))

        # Wait for completion
        await asyncio.gather(*tasks)

        # Should not have any errors
        assert len(errors) == 0, f"Thread-safety errors: {errors}"

        # Metrics should be in a valid state
        assert metrics.total_operation_count() >= 0
        assert len(metrics.operations) >= 0

    @pytest.mark.asyncio
    async def test_reset_allows_fresh_tracking(self):
        """Test that reset() allows tracking fresh metrics after clearing."""
        metrics = IOMetrics()

        # Record initial operations
        await metrics.record_operation("read", 0.1, 0, True)
        await metrics.record_operation("write", 0.2, 0, True)

        assert metrics.total_operation_count() == 2
        initial_duration = metrics.total_duration()
        assert initial_duration > 0

        # Reset
        metrics.reset()

        # Record new operations
        await metrics.record_operation("read", 0.05, 0, True)
        await metrics.record_operation("flush", 0.03, 0, True)

        # Should only have new operations
        assert metrics.total_operation_count() == 2
        new_duration = metrics.total_duration()
        assert new_duration < initial_duration
        assert abs(new_duration - 0.08) < 0.001  # 0.05 + 0.03
