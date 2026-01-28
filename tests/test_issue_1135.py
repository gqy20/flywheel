"""Test for Issue #1135 - IOMetrics.record_operation should use threading.Lock

This test verifies that IOMetrics.record_operation works correctly in
both sync and async contexts without causing deadlocks or RuntimeError.

The issue: record_operation uses asyncio.run() to acquire asyncio.Lock
in sync context, which causes RuntimeError when called from a thread while
an event loop is already running.

The fix: Use threading.Lock for record_operation instead of asyncio.Lock,
which works in both pure sync contexts and when called from threads while
an event loop is running.
"""

import asyncio
import threading
import time
from flywheel.storage import IOMetrics


def test_record_operation_in_pure_sync_context():
    """Test that record_operation works in pure sync context without event loop."""
    metrics = IOMetrics()

    # This should work without raising any exceptions
    metrics.record_operation('read', 0.1, 0, True)

    # Verify it was recorded
    async with metrics._lock:
        count = len(metrics.operations)
    assert count == 1


def test_record_operation_multiple_sync_calls():
    """Test that multiple sync calls work without deadlock."""
    metrics = IOMetrics()

    # Multiple calls from sync context should work
    for i in range(10):
        metrics.record_operation('read', 0.1, 0, True)

    # Verify all were recorded
    async with metrics._lock:
        count = len(metrics.operations)
    assert count == 10


async def test_record_operation_async_in_async_context():
    """Test that record_operation_async works in async context."""
    metrics = IOMetrics()

    # This should work in async context
    await metrics.record_operation_async('read', 0.1, 0, True)

    async with metrics._lock:
        count = len(metrics.operations)
    assert count == 1


async def test_record_operation_from_thread_with_running_event_loop():
    """Test that record_operation works when called from a thread while event loop runs.

    This is the key test for Issue #1135. When record_operation is called
    from a thread while an event loop is already running in the main thread,
    it should NOT use asyncio.run() which would cause RuntimeError:
    "asyncio.run() cannot be called from a running event loop"

    Instead, it should use threading.Lock which works across threads.
    """
    metrics = IOMetrics()
    results = []
    errors = []

    async def async_operations():
        """Run async operations in the main event loop."""
        # Record some operations async
        for i in range(5):
            await metrics.record_operation_async('async_read', 0.1, 0, True)
            await asyncio.sleep(0.01)  # Small delay to allow thread to run
            results.append(('async', i))

    def sync_operations_from_thread():
        """Run sync operations from a separate thread."""
        # Simulate some work
        time.sleep(0.02)

        # This should NOT raise RuntimeError about asyncio.run()
        # It should use threading.Lock internally
        try:
            for i in range(5):
                metrics.record_operation('sync_read', 0.1, 0, True)
                time.sleep(0.01)
                results.append(('sync', i))
        except RuntimeError as e:
            errors.append(str(e))

    # Start async operations in the background
    async_task = asyncio.create_task(async_operations())

    # Start sync operations in a thread
    sync_thread = threading.Thread(target=sync_operations_from_thread)
    sync_thread.start()

    # Wait for both to complete
    await async_task
    sync_thread.join(timeout=5.0)

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify both async and sync operations completed
    assert len([r for r in results if r[0] == 'async']) == 5
    assert len([r for r in results if r[0] == 'sync']) == 5

    # Verify total operations recorded
    async with metrics._lock:
        total_ops = len(metrics.operations)
    assert total_ops == 10


async def test_concurrent_threads_and_async_operations():
    """Test heavy concurrency with multiple threads calling record_operation.

    This stress test verifies that threading.Lock is used correctly and
    there are no deadlocks or race conditions.
    """
    metrics = IOMetrics()
    num_threads = 5
    ops_per_thread = 10
    results = []
    errors = []

    async def async_worker():
        """Async worker recording operations."""
        for i in range(ops_per_thread):
            await metrics.record_operation_async('async_op', 0.01, 0, True)
            await asyncio.sleep(0.001)
            results.append(('async', i))

    def sync_worker(thread_id):
        """Sync worker in thread recording operations."""
        try:
            for i in range(ops_per_thread):
                metrics.record_operation(f'sync_op_{thread_id}', 0.01, 0, True)
                time.sleep(0.001)
                results.append((f'sync_{thread_id}', i))
        except Exception as e:
            errors.append((thread_id, str(e)))

    # Start async task
    async_task = asyncio.create_task(async_worker())

    # Start multiple sync threads
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=sync_worker, args=(i,))
        threads.append(thread)
        thread.start()

    # Wait for completion
    await async_task
    for thread in threads:
        thread.join(timeout=10.0)

    # Verify no errors
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify all operations completed
    expected_ops = ops_per_thread * (num_threads + 1)  # +1 for async worker
    async with metrics._lock:
        total_ops = len(metrics.operations)
    assert total_ops == expected_ops
