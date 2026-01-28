"""Tests for Issue #1331 - _AsyncCompatibleLock multi-threaded asyncio.Lock safety.

This test verifies that _AsyncCompatibleLock can safely handle multiple threads
with different event loops without causing deadlocks or RuntimeErrors.
"""
import asyncio
import threading
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_async_lock_multi_thread_safety():
    """Test that _AsyncCompatibleLock works correctly with multiple event loops.

    This test creates a shared _AsyncCompatibleLock instance and uses it from
    multiple threads, each with its own event loop. The lock should handle this
    safely by using per-event-loop locks (similar to IOMetrics implementation).

    The test will FAIL with the current implementation because it uses a single
    self._async_lock that can cause RuntimeError when used across different
    event loops.
    """
    shared_lock = _AsyncCompatibleLock()
    errors = []
    results = []

    def worker_in_thread(thread_id):
        """Worker function that runs in its own thread with its own event loop."""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def async_work():
                # Try to use the shared lock in this thread's event loop
                async with shared_lock:
                    # Simulate some work
                    await asyncio.sleep(0.1)
                    results.append(f"Thread {thread_id} acquired lock")

            # Run the async work
            loop.run_until_complete(async_work())
            loop.close()

        except Exception as e:
            errors.append((thread_id, type(e).__name__, str(e)))

    # Create multiple threads, each with its own event loop
    threads = []
    num_threads = 3

    for i in range(num_threads):
        t = threading.Thread(target=worker_in_thread, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check that no errors occurred
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Check that all threads successfully acquired the lock
    assert len(results) == num_threads, f"Expected {num_threads} results, got {len(results)}"

    print("✓ All threads successfully acquired and released the lock")


def test_async_lock_same_event_loop_reuse():
    """Test that the same lock can be used multiple times in the same event loop."""
    lock = _AsyncCompatibleLock()

    async def reuse_lock():
        results = []

        # Use the lock multiple times in sequence
        for i in range(3):
            async with lock:
                await asyncio.sleep(0.01)
                results.append(i)

        return results

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        results = loop.run_until_complete(reuse_lock())
        assert results == [0, 1, 2], f"Expected [0, 1, 2], got {results}"
    finally:
        loop.close()


def test_async_lock_concurrent_same_loop():
    """Test concurrent usage of the same lock from multiple tasks in the same event loop."""
    lock = _AsyncCompatibleLock()

    async def concurrent_task(task_id):
        async with lock:
            await asyncio.sleep(0.05)
            return task_id

    async def run_concurrent():
        tasks = [concurrent_task(i) for i in range(3)]
        return await asyncio.gather(*tasks)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        results = loop.run_until_complete(run_concurrent())
        assert sorted(results) == [0, 1, 2], f"Expected [0, 1, 2], got {sorted(results)}"
    finally:
        loop.close()
