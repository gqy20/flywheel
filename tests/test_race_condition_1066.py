"""Test for race condition in IOMetrics.record_operation (Issue #1066)

This test verifies that the IOMetrics.record_operation method is async-safe
and can handle concurrent calls from multiple async tasks without data corruption.
"""

import pytest
import asyncio
from collections import Counter

from flywheel.storage import IOMetrics


@pytest.mark.asyncio
async def test_record_operation_thread_safety():
    """Test that record_operation is async-safe.

    This test creates multiple async tasks that all call record_operation
    concurrently. Without proper locking, this can lead to:
    - Race conditions in list append/pop operations
    - Corrupted list state
    - Index errors
    - Lost operations

    The test verifies:
    1. All operations are recorded (no lost operations)
    2. The operations list never exceeds MAX_OPERATIONS
    3. No exceptions are raised during concurrent access
    """
    metrics = IOMetrics()
    num_tasks = 10
    operations_per_task = 200

    # Track results from each task
    results = {'success': 0, 'errors': Counter()}
    errors = []

    async def worker(task_id):
        """Worker function that records operations concurrently."""
        try:
            for i in range(operations_per_task):
                await metrics.record_operation(
                    operation_type=f'op_{task_id}_{i}',
                    duration=0.001,
                    retries=0,
                    success=True
                )
                # Small sleep to increase chance of context switching
                await asyncio.sleep(0.0001)
            results['success'] += 1
        except Exception as e:
            errors.append((task_id, str(e)))
            results['errors'][type(e).__name__] += 1

    # Create and run all tasks concurrently
    tasks = [worker(i) for i in range(num_tasks)]
    await asyncio.gather(*tasks)

    # Verify no exceptions occurred
    assert len(errors) == 0, f"Errors occurred during concurrent operations: {errors}"

    # Verify all tasks completed successfully
    assert results['success'] == num_tasks, f"Some tasks failed: {results}"

    # Verify the operations list doesn't exceed maximum
    assert len(metrics.operations) <= IOMetrics.MAX_OPERATIONS, \
        f"Operations list exceeded MAX_OPERATIONS: {len(metrics.operations)} > {IOMetrics.MAX_OPERATIONS}"

    # Verify we recorded the expected number of operations
    # (capped at MAX_OPERATIONS due to circular buffer)
    expected_min = min(num_tasks * operations_per_task, IOMetrics.MAX_OPERATIONS)
    assert len(metrics.operations) >= expected_min, \
        f"Too few operations recorded: {len(metrics.operations)} < {expected_min}"

    # Verify data integrity - all operations should be valid dicts
    for op in metrics.operations:
        assert isinstance(op, dict), f"Invalid operation type: {type(op)}"
        assert 'operation_type' in op, "Missing operation_type"
        assert 'duration' in op, "Missing duration"
        assert 'retries' in op, "Missing retries"
        assert 'success' in op, "Missing success"


@pytest.mark.asyncio
async def test_record_operation_concurrent_append_and_pop():
    """Test concurrent append and pop operations on the circular buffer.

    This test specifically targets the race condition between append and pop
    operations when the buffer is full.
    """
    metrics = IOMetrics()
    num_tasks = 20
    operations_per_task = 100

    # Fill the buffer to near capacity first
    for i in range(IOMetrics.MAX_OPERATIONS - 50):
        await metrics.record_operation('init', 0.001, 0, True)

    errors = []

    async def worker(task_id):
        """Worker that performs rapid operations."""
        try:
            for i in range(operations_per_task):
                await metrics.record_operation(
                    operation_type=f'test_op',
                    duration=0.001,
                    retries=0,
                    success=True
                )
        except Exception as e:
            errors.append((task_id, type(e).__name__, str(e)))

    tasks = [worker(i) for i in range(num_tasks)]
    await asyncio.gather(*tasks)

    # Verify no exceptions
    assert len(errors) == 0, f"Race condition detected: {errors}"

    # Verify buffer integrity
    assert len(metrics.operations) <= IOMetrics.MAX_OPERATIONS, \
        f"Buffer overflow: {len(metrics.operations)} > {IOMetrics.MAX_OPERATIONS}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
