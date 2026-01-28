"""Test for Issue #1065 - Verify deque is used for O(1) circular buffer performance.

This test verifies that the IOMetrics class uses collections.deque instead of list
for efficient O(1) circular buffer operations.
"""

import time
import unittest
from collections import deque

from flywheel.storage import IOMetrics


class TestDequePerformance(unittest.TestCase):
    """Test that IOMetrics uses deque for O(1) performance."""

    def test_operations_is_deque(self):
        """Test that operations attribute is a deque with maxlen."""
        metrics = IOMetrics()

        # Verify operations is a deque
        self.assertIsInstance(metrics.operations, deque,
                            "operations should be a deque for O(1) performance")

        # Verify maxlen is set to MAX_OPERATIONS
        self.assertEqual(metrics.operations.maxlen, IOMetrics.MAX_OPERATIONS,
                        f"deque maxlen should be {IOMetrics.MAX_OPERATIONS}")

    @pytest.mark.asyncio
    async def test_circular_buffer_auto_discard(self):
        """Test that deque automatically discards oldest when full."""
        metrics = IOMetrics()

        # Fill the buffer beyond MAX_OPERATIONS
        for i in range(IOMetrics.MAX_OPERATIONS + 100):
            await metrics.record_operation('test_op', 0.001, 0, True)

        # Verify size is at most MAX_OPERATIONS
        self.assertLessEqual(len(metrics.operations), IOMetrics.MAX_OPERATIONS,
                            "Deque should automatically maintain max size")

        # Verify it's exactly at max (deque property)
        self.assertEqual(len(metrics.operations), IOMetrics.MAX_OPERATIONS,
                        "Deque should be at max capacity")

    @pytest.mark.asyncio
    async def test_performance_benefit(self):
        """Test that using deque provides O(1) performance for large N."""
        metrics = IOMetrics()

        # Record many operations - should be fast with deque
        iterations = 10000
        start_time = time.time()

        for i in range(iterations):
            await metrics.record_operation('test_op', 0.001, 0, True)

        elapsed = time.time() - start_time

        # With deque, this should complete very quickly (< 1 second)
        # With list.pop(0), this would be O(N*M) and much slower
        self.assertLess(elapsed, 1.0,
                       f"Recording {iterations} operations should take < 1s with deque, took {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_thread_safety_maintained(self):
        """Test that thread safety is maintained with deque."""
        import asyncio

        metrics = IOMetrics()
        errors = []

        async def record_ops():
            try:
                for i in range(100):
                    await metrics.record_operation('test_op', 0.001, 0, True)
            except Exception as e:
                errors.append(e)

        tasks = [asyncio.create_task(record_ops()) for _ in range(10)]
        await asyncio.gather(*tasks)

        self.assertEqual(len(errors), 0, "No errors should occur in concurrent access")
        self.assertEqual(metrics.total_operation_count(), 1000,
                        "All operations should be recorded")


if __name__ == '__main__':
    unittest.main()
