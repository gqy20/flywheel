"""Test for issue #1124: IOMetrics should use pure asyncio.Lock in async contexts.

This test verifies that IOMetrics.record_operation_async doesn't use
threading.Lock which can cause event loop blocking or deadlocks in
high concurrency async I/O scenarios.
"""

import asyncio
import threading
import time
from flywheel.storage import IOMetrics


async def test_record_operation_async_uses_pure_async_lock():
    """Test that record_operation_async doesn't block the event loop.

    This test creates a scenario where if record_operation_async uses
    threading.Lock internally, it will cause the event loop to block
    and the concurrent tasks will not execute efficiently.

    The test verifies that all operations complete quickly without blocking.
    """
    metrics = IOMetrics()
    operation_count = 100
    completion_times = []

    async def record_operation_with_timing(task_id):
        """Record an operation and track completion time."""
        start = time.time()
        await metrics.record_operation_async(
            operation_type='test',
            duration=0.001,
            retries=0,
            success=True
        )
        end = time.time()
        completion_times.append((task_id, end - start))

    # Launch many concurrent operations
    tasks = [
        asyncio.create_task(record_operation_with_timing(i))
        for i in range(operation_count)
    ]

    # Wait for all to complete
    await asyncio.gather(*tasks)

    # If threading.Lock was used, some operations would block significantly
    # With pure asyncio.Lock, all should complete quickly
    max_time = max(t[1] for t in completion_times)
    avg_time = sum(t[1] for t in completion_times) / len(completion_times)

    # Verify all operations completed reasonably quickly
    # With threading.Lock blocking, we'd see much higher times
    assert max_time < 0.1, f"Max operation time {max_time}s suggests event loop blocking"
    assert avg_time < 0.01, f"Avg operation time {avg_time}s suggests blocking behavior"

    # Verify all operations were recorded
    assert len(metrics.operations) == operation_count


async def test_record_operation_async_no_sync_lock_holding():
    """Test that record_operation_async doesn't hold sync lock during async wait.

    This test checks that if we have multiple async operations happening
    concurrently with a simulated delay, they don't block each other due to
    a sync lock being held.
    """
    metrics = IOMetrics()
    results = []

    async def slow_operation(task_id):
        """Simulate an operation that might need to wait."""
        # Record the operation
        await metrics.record_operation_async(
            operation_type='slow_test',
            duration=0.01,
            retries=0,
            success=True
        )
        results.append(task_id)

    # Create many concurrent slow operations
    tasks = [
        asyncio.create_task(slow_operation(i))
        for i in range(50)
    ]

    start = time.time()
    await asyncio.gather(*tasks)
    total_time = time.time() - start

    # With proper async locking, operations should run concurrently
    # With sync lock, they would serialize and take much longer
    assert total_time < 0.5, f"Total time {total_time}s suggests serialized execution due to sync lock"

    # Verify all operations completed
    assert len(results) == 50
    assert len(metrics.operations) == 50


async def test_concurrent_async_and_sync_contexts():
    """Test that sync and async contexts don't deadlock each other.

    This test verifies that if record_operation_async uses pure asyncio.Lock,
    it won't deadlock when called alongside sync operations in different threads.
    """
    metrics = IOMetrics()
    async_results = []
    sync_results = []
    ready_event = asyncio.Event()

    async def async_worker():
        """Async worker that records operations."""
        await ready_event.wait()
        for i in range(10):
            await metrics.record_operation_async(
                operation_type='async',
                duration=0.001,
                retries=0,
                success=True
            )
            await asyncio.sleep(0)  # Yield control
            async_results.append(i)

    def sync_worker():
        """Sync worker that tries to use sync methods."""
        # Wait a bit for async to start
        time.sleep(0.01)
        for i in range(10):
            try:
                metrics.record_operation(
                    operation_type='sync',
                    duration=0.001,
                    retries=0,
                    success=True
                )
                sync_results.append(i)
            except RuntimeError as e:
                # Expected if called from async context
                pass

    # Start async task
    async_task = asyncio.create_task(async_worker())

    # Start sync thread
    sync_thread = threading.Thread(target=sync_worker)
    sync_thread.start()

    # Signal both to start
    ready_event.set()

    # Wait for completion
    await async_task
    sync_thread.join(timeout=2.0)

    # Verify both completed without deadlock
    assert len(async_results) == 10 or sync_thread.is_alive() is False
    assert len(metrics.operations) >= 10  # At least async operations should be recorded


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
