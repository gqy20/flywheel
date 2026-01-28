"""Test for Issue #1161: Race condition in IOMetrics._get_async_lock

This test verifies that creating asyncio.Lock while holding threading.Lock
is safe across different event loop contexts.
"""
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel.storage import IOMetrics


def test_get_async_lock_thread_safety():
    """Test that _get_async_lock is thread-safe when called from multiple threads.

    This test creates multiple threads, each with its own event loop,
    and verifies that locks are created safely without deadlocks.
    """
    metrics = IOMetrics()
    errors = []
    successful_threads = []
    loop_ids = []

    def create_lock_in_thread(thread_id):
        """Create a lock in a thread with its own event loop."""
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_ids.append(id(loop))

            # Try to get the async lock - this should not deadlock
            async def get_lock():
                lock = metrics._get_async_lock()
                # Verify the lock is associated with this thread's event loop
                current_loop = asyncio.get_running_loop()
                assert current_loop in metrics._locks
                return lock

            lock = loop.run_until_complete(get_lock())

            # Verify we got a valid lock
            assert lock is not None
            successful_threads.append(thread_id)

            # Clean up
            loop.close()

        except Exception as e:
            errors.append((thread_id, str(e)))

    # Run multiple threads concurrently
    num_threads = 5
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_lock_in_thread, i) for i in range(num_threads)]
        for future in futures:
            future.result()  # Wait for completion

    # Verify all threads succeeded
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(successful_threads) == num_threads

    # Verify each event loop got its own lock
    assert len(metrics._locks) == num_threads

    # Verify all locks are unique
    lock_objects = list(metrics._locks.values())
    assert len(lock_objects) == len(set(id(l) for l in lock_objects)), \
        "Each event loop should have its own unique lock"


def test_get_async_lock_concurrent_same_loop():
    """Test that _get_async_lock handles concurrent calls from the same event loop.

    This test verifies that multiple concurrent calls to _get_async_lock
    from the same event loop return the same lock instance.
    """
    metrics = IOMetrics()

    async def concurrent_lock_access():
        """Multiple coroutines trying to get the lock simultaneously."""
        tasks = [
            asyncio.create_task(metrics._get_async_lock())
            for _ in range(10)
        ]

        locks = await asyncio.gather(*tasks)

        # All locks should be the same instance for the same event loop
        first_lock = locks[0]
        for lock in locks:
            assert lock is first_lock, "All locks should be the same instance"

        return locks

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        locks = loop.run_until_complete(concurrent_lock_access())
        # Should have exactly one lock in the dictionary
        assert len(metrics._locks) == 1
        assert loop in metrics._locks
    finally:
        loop.close()


def test_get_async_lock_no_event_loop():
    """Test that _get_async_lock raises RuntimeError when called without event loop."""
    metrics = IOMetrics()

    # Make sure there's no running event loop
    try:
        asyncio.get_event_loop().close()
    except:
        pass

    with pytest.raises(RuntimeError, match="must be called from an async context"):
        # This should fail because there's no running event loop
        async def try_get_lock():
            # Cancel any existing loop first
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, which is what we want
                pass

            # Now try to get the lock without a running loop
            return metrics._get_async_lock()

        # Try to run without a proper loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)  # Clear the event loop
        with pytest.raises(RuntimeError):
            metrics._get_async_lock()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
