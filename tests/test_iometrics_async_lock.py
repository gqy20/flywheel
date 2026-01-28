"""Test for IOMetrics asyncio safety (Issue #1080).

This test verifies that IOMetrics uses asyncio.Lock instead of threading.Lock
to prevent race conditions when used in async contexts.
"""

import asyncio
import pytest

from flywheel.storage import IOMetrics


@pytest.mark.asyncio
async def test_iometrics_concurrent_operations_safety():
    """Test that concurrent async operations don't cause race conditions.

    This test creates multiple concurrent coroutines that all use the
    IOMetrics.track_operation() async context manager. With threading.Lock,
    this can cause race conditions because multiple coroutines can interleave
    their execution within the locked block.

    With asyncio.Lock, the operations are properly serialized and the test
    should pass consistently.
    """
    metrics = IOMetrics()
    num_concurrent = 100

    # Create multiple concurrent operations
    async def record_op(op_id):
        async with metrics.track_operation("test_op"):
            # Simulate some async work
            await asyncio.sleep(0.001)
            return op_id

    # Run many operations concurrently
    tasks = [record_op(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks)

    # Verify all operations completed
    assert len(results) == num_concurrent
    assert results == list(range(num_concurrent))

    # Verify all operations were recorded
    assert metrics.total_operation_count() == num_concurrent

    # Verify no operations were lost or corrupted
    successful_ops = sum(1 for op in metrics.operations if op['success'])
    assert successful_ops == num_concurrent


@pytest.mark.asyncio
async def test_iometrics_record_operation_thread_safety():
    """Test that record_operation is safe for concurrent async access.

    Directly test record_operation with multiple concurrent calls.
    """
    metrics = IOMetrics()
    num_concurrent = 50

    async def record_multiple():
        for i in range(10):
            metrics.record_operation(
                "test",
                duration=0.001,
                retries=0,
                success=True
            )
            await asyncio.sleep(0)  # Yield to event loop

    # Run multiple coroutines concurrently
    tasks = [record_multiple() for _ in range(num_concurrent)]
    await asyncio.gather(*tasks)

    # Verify all operations were recorded
    expected_count = num_concurrent * 10
    assert metrics.total_operation_count() == expected_count

    # Verify no corruption
    successful_ops = sum(1 for op in metrics.operations if op['success'])
    assert successful_ops == expected_count


@pytest.mark.asyncio
async def test_iometrics_reset_concurrent_safety():
    """Test that reset() is safe for concurrent async access.

    Verify that reset() doesn't cause issues when called concurrently
    with record_operation.
    """
    metrics = IOMetrics()

    async def record_and_reset():
        for i in range(5):
            metrics.record_operation("test", 0.001, 0, True)
            await asyncio.sleep(0.001)
        metrics.reset()

    # Run multiple coroutines that both record and reset
    tasks = [record_and_reset() for _ in range(10)]
    await asyncio.gather(*tasks)

    # The final state should be consistent (all ended with reset)
    assert metrics.total_operation_count() == 0
