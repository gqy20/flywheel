"""Tests for Issue #1101 - Inconsistent lock usage.

This test verifies that total_operation_count and total_duration
are thread-safe by using locks consistently with record_operation.
"""

import asyncio
import pytest
from flywheel.storage import StorageMetrics


class TestIssue1101:
    """Test suite for Issue #1101 - Inconsistent lock usage."""

    @pytest.mark.asyncio
    async def test_total_operation_count_thread_safe(self):
        """Test that total_operation_count uses locks properly."""
        metrics = StorageMetrics(max_operations=1000)

        # Record some operations async
        tasks = []
        for i in range(100):
            task = metrics.record_operation_async(
                operation_type='read',
                duration=0.1,
                retries=0,
                success=True
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # total_operation_count should be async and use locks
        # This test will fail until we make it async
        count = await metrics.total_operation_count_async()
        assert count == 100

    @pytest.mark.asyncio
    async def test_total_duration_thread_safe(self):
        """Test that total_duration uses locks properly."""
        metrics = StorageMetrics(max_operations=1000)

        # Record operations with specific durations
        tasks = []
        for i in range(50):
            task = metrics.record_operation_async(
                operation_type='write',
                duration=0.5,
                retries=0,
                success=True
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        # total_duration should be async and use locks
        # This test will fail until we make it async
        duration = await metrics.total_duration_async()
        assert duration == 25.0  # 50 * 0.5

    @pytest.mark.asyncio
    async def test_concurrent_access_safety(self):
        """Test that concurrent access to metrics doesn't cause race conditions."""
        metrics = StorageMetrics(max_operations=1000)

        async def record_and_read():
            """Record operations and read metrics concurrently."""
            for _ in range(10):
                await metrics.record_operation_async(
                    operation_type='read',
                    duration=0.1,
                    retries=0,
                    success=True
                )
                # These should be async methods
                count = await metrics.total_operation_count_async()
                duration = await metrics.total_duration_async()
                assert count >= 0
                assert duration >= 0

        # Run multiple tasks concurrently
        tasks = [record_and_read() for _ in range(10)]
        await asyncio.gather(*tasks)

        # Verify final state
        final_count = await metrics.total_operation_count_async()
        assert final_count == 100  # 10 tasks * 10 operations

    @pytest.mark.asyncio
    async def test_sync_methods_work_in_sync_context(self):
        """Test that sync methods still work in non-async contexts."""
        metrics = StorageMetrics(max_operations=1000)

        # These should still work in sync context
        metrics.record_operation(
            operation_type='read',
            duration=0.1,
            retries=0,
            success=True
        )

        count = metrics.total_operation_count()
        assert count == 1

        duration = metrics.total_duration()
        assert duration == 0.1
