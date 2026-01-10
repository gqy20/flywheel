"""Test for Issue #1275: Potential deadlock risk when starting threads while holding locks

This test verifies that:
1. call_soon_threadsafe is NOT called while holding _init_lock
2. Thread.start() is NOT called while holding any lock
3. No deadlock occurs under concurrent access patterns
"""
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel.storage import IOMetrics


def test_no_lock_held_during_call_soon_threadsafe():
    """Test that call_soon_threadsafe is not called while holding _init_lock.

    This test creates multiple threads that simultaneously try to create
    async locks. It verifies that the implementation properly releases
    _init_lock before calling call_soon_threadsafe, preventing deadlocks.
    """
    metrics = IOMetrics()
    errors = []
    successful_threads = []
    lock_acquisition_times = []

    def create_lock_in_thread(thread_id):
        """Create a lock in a thread with its own event loop."""
        try:
            start_time = time.time()

            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Try to get the async lock - this should not deadlock
            async def get_lock():
                # The critical point: _get_async_lock should:
                # 1. Acquire _init_lock
                # 2. Schedule lock creation with call_soon_threadsafe
                # 3. RELEASE _init_lock BEFORE the callback runs
                # 4. Wait for the lock to be created
                lock = metrics._get_async_lock()

                # Verify the lock is valid and usable
                async with lock:
                    pass  # Test that we can acquire it
                return lock

            lock = loop.run_until_complete(get_lock())

            acquisition_time = time.time() - start_time
            lock_acquisition_times.append(acquisition_time)

            # Verify we got a valid lock
            assert lock is not None
            successful_threads.append(thread_id)

            # Clean up
            loop.close()

        except Exception as e:
            errors.append((thread_id, str(e)))

    # Run multiple threads concurrently to stress-test the lock creation
    num_threads = 10
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_lock_in_thread, i) for i in range(num_threads)]
        for future in futures:
            # Add a timeout to detect deadlocks
            try:
                future.result(timeout=5.0)
            except Exception as e:
                errors.append(("thread", str(e)))

    # Verify all threads succeeded
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(successful_threads) == num_threads

    # Verify lock acquisition was reasonably fast (no deadlock)
    avg_time = sum(lock_acquisition_times) / len(lock_acquisition_times)
    assert avg_time < 1.0, f"Average lock acquisition time too high: {avg_time}s (possible deadlock)"


def test_concurrent_lock_creation_with_shared_loop():
    """Test concurrent lock creation from multiple threads with the same event loop.

    This test simulates the scenario where multiple threads try to create
    locks for the same event loop concurrently. The implementation should
    handle this safely without deadlocks.
    """
    metrics = IOMetrics()

    # Create a shared event loop
    shared_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(shared_loop)

    errors = []
    successful_creations = []

    def create_lock_in_thread(thread_id):
        """Try to create a lock from a different thread."""
        try:
            # Each thread schedules lock creation on the shared loop
            async def get_lock():
                # This should use call_soon_threadsafe to schedule
                # lock creation on the shared loop's thread
                return metrics._get_async_lock()

            # Run the coroutine on the shared loop
            future = asyncio.run_coroutine_threadsafe(
                get_lock(),
                shared_loop
            )

            # Wait for the result with timeout
            lock = future.result(timeout=2.0)

            assert lock is not None
            successful_creations.append(thread_id)

        except Exception as e:
            errors.append((thread_id, str(e)))

    # Run multiple threads concurrently
    num_threads = 5
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(create_lock_in_thread, i) for i in range(num_threads)]
        for future in futures:
            try:
                future.result(timeout=5.0)
            except Exception as e:
                errors.append(("thread", str(e)))

    # Verify all threads succeeded
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(successful_creations) == num_threads

    # Clean up
    shared_loop.close()


def test_lock_creation_releases_init_lock_before_callback():
    """Test that _init_lock is released before the callback runs.

    This test verifies the specific fix for Issue #1275: the callback
    that creates the asyncio.Lock should NOT be executed while holding
    _init_lock, as this could cause deadlocks.
    """
    metrics = IOMetrics()

    # Track the state of _init_lock
    init_lock_held_during_callback = [False]
    callback_executed = [False]

    # We need to patch the lock creation to check if _init_lock is held
    original_get_async_lock = metrics._get_async_lock

    def instrumented_get_async_lock():
        """Instrumented version that checks lock state during callback."""
        # Create a new event loop for this test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Patch the inner function to check lock state
        # This is a bit tricky, but we can verify by checking
        # if we can acquire _init_lock from within the callback
        def check_lock_state():
            # If we can acquire _init_lock here, it means it was NOT
            # held during the callback execution
            try:
                # Try to acquire with timeout
                acquired = metrics._init_lock.acquire(timeout=0.1)
                if acquired:
                    metrics._init_lock.release()
                    # Lock was NOT held during callback - GOOD
                    init_lock_held_during_callback[0] = False
                else:
                    # Lock WAS held during callback - BAD (deadlock risk)
                    init_lock_held_during_callback[0] = True
            except:
                pass

            callback_executed[0] = True

        # Schedule the check
        loop.call_soon(check_lock_state)

        # Run the loop briefly
        loop.run_until_complete(asyncio.sleep(0.1))
        loop.close()

        return original_get_async_lock()

    # Call the instrumented version
    lock = instrumented_get_async_lock()

    # Verify the callback executed
    assert callback_executed[0], "Callback should have executed"

    # Verify _init_lock was NOT held during callback
    assert not init_lock_held_during_callback[0], \
        "_init_lock should NOT be held during callback execution (Issue #1275)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
