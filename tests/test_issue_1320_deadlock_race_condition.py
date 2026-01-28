"""Test for Issue #1320 - IOMetrics._get_async_lock deadlock and race condition.

This test verifies that there's a fundamental conflict between:
1. Issue #1296: All checks must be inside lock for atomicity
2. Issue #1161: Cannot create asyncio.Lock while holding threading.Lock

The current implementation tries to satisfy both but has a race condition:
- Thread A: checks in lock, sets sentinel, releases lock
- Thread B: checks in lock, sees sentinel, waits for event
- Thread A: calls call_soon_threadsafe (AFTER releasing lock)
- Thread B: waits for event that hasn't been set yet
- If event creation is delayed, Thread B might timeout or see inconsistent state

This test will expose the race condition by having multiple threads
contending for lock creation simultaneously.
"""

import asyncio
import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from flywheel.storage import IOMetrics


def test_multiple_threads_single_event_loop_race_condition():
    """Test that multiple threads accessing the same event loop don't cause race conditions.

    This test creates multiple threads that all try to get the async lock
    for the same event loop. The race condition occurs when:
    1. Thread A creates the sentinel and releases the lock
    2. Thread B sees the sentinel and waits for the event
    3. Thread A schedules the lock creation (not immediate)
    4. Thread B times out waiting for the event

    With the fix, this should pass without timeouts.
    """
    metrics = IOMetrics()
    num_threads = 10
    results = []
    errors = []

    def run_async_in_thread(thread_id):
        """Run async code in a thread with an event loop."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def get_lock():
                # Try to get the async lock - this should trigger lazy initialization
                lock = metrics._get_async_lock()
                # Verify it's a valid asyncio.Lock
                assert isinstance(lock, asyncio.Lock)
                return lock

            # Run the async function
            lock = loop.run_until_complete(get_lock())
            results.append((thread_id, id(lock)))

            # Clean up
            loop.close()

        except Exception as e:
            errors.append((thread_id, e))

    # Run multiple threads concurrently
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(run_async_in_thread, i) for i in range(num_threads)]

        # Wait for all threads to complete with timeout
        for future in futures:
            try:
                future.result(timeout=5.0)
            except FutureTimeoutError:
                pytest.fail("Thread timed out - possible deadlock or race condition")
            except Exception as e:
                errors.append(("thread", e))

    # Check for errors
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # All threads should have successfully acquired a lock
    assert len(results) == num_threads

    # Note: Each thread has its own event loop, so locks will be different
    # This is expected behavior


def test_same_event_loop_multiple_threads_race_condition():
    """Test race condition when multiple threads share the same event loop.

    This is the critical test for issue #1320. When multiple threads
    share an event loop, they should all get the same lock safely.

    The race condition in the current implementation:
    1. Thread A: enters _get_async_lock, acquires _init_lock
    2. Thread A: checks if lock exists (no), creates sentinel
    3. Thread A: creates event, releases _init_lock
    4. Thread A: schedules lock creation via call_soon_threadsafe
    5. Thread B: enters _get_async_lock, acquires _init_lock
    6. Thread B: checks if lock exists (yes, it's None sentinel)
    7. Thread B: waits for event (but event might not be set yet!)
    8. Thread A: the callback runs and sets the event
    9. Thread B: wakes up and returns the lock

    The problem is between step 7 and 8: if the event loop is busy,
    the callback might be delayed, causing Thread B to timeout.
    """
    metrics = IOMetrics()

    # Create a shared event loop
    main_loop = asyncio.new_event_loop()

    num_threads = 5
    results = []
    errors = []
    lock_ids = []

    def access_lock_from_thread(thread_id):
        """Access the async lock from a thread using the shared event loop."""
        try:
            # This simulates accessing the lock from a different thread
            # than the event loop's thread

            def get_lock_in_thread():
                # Get the current event loop (which is the main_loop)
                loop = asyncio.get_event_loop()
                return metrics._get_async_lock()

            # We need to call this from a thread that's not the event loop thread
            # to trigger the call_soon_threadsafe path
            if threading.current_thread() is threading.main_thread():
                # Run in a separate thread
                t = threading.Thread(
                    target=lambda: lock_ids.append(id(get_lock_in_thread()))
                )
                t.start()
                t.join(timeout=2.0)
                if t.is_alive():
                    raise RuntimeError("Thread deadlock - possible issue #1320")
            else:
                lock = get_lock_in_thread()
                lock_ids.append(id(lock))

            results.append(thread_id)

        except Exception as e:
            errors.append((thread_id, e))

    # Run multiple threads accessing the same event loop
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=access_lock_from_thread, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join(timeout=5.0)
        if t.is_alive():
            pytest.fail(f"Thread {t} is still running - possible deadlock")

    # Check for errors
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # All threads should have completed
    assert len(results) == num_threads

    # All threads should get the same lock (same event loop)
    assert len(lock_ids) == num_threads
    assert len(set(lock_ids)) == 1, "All threads should get the same lock for the same event loop"


def test_concurrent_initialization_stress_test():
    """Stress test for concurrent lock initialization.

    This test creates heavy concurrent load to expose any race conditions
    in the lock initialization logic.
    """
    metrics = IOMetrics()

    num_iterations = 20
    num_threads_per_iteration = 5
    errors = []

    def stress_test(iteration_id):
        """Run a stress test iteration."""
        try:
            for i in range(num_threads_per_iteration):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def access_lock():
                    lock = metrics._get_async_lock()
                    assert isinstance(lock, asyncio.Lock)
                    return lock

                lock = loop.run_until_complete(access_lock())
                loop.close()

        except Exception as e:
            errors.append((iteration_id, e))

    # Run multiple iterations
    threads = []
    for i in range(num_iterations):
        t = threading.Thread(target=stress_test, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join(timeout=10.0)
        if t.is_alive():
            pytest.fail(f"Stress test thread {t} timed out - possible deadlock")

    # Check for errors
    assert len(errors) == 0, f"Errors occurred during stress test: {errors}"


def test_lock_creation_event_timeout():
    """Test that the lock creation event properly synchronizes threads.

    This test specifically checks that the event mechanism works correctly
    and threads don't timeout waiting for lock creation.
    """
    metrics = IOMetrics()

    # Create an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def first_access():
        """First thread to access the lock."""
        lock = metrics._get_async_lock()
        assert isinstance(lock, asyncio.Lock)
        return lock

    # First access (creates the lock)
    lock1 = loop.run_until_complete(first_access())
    lock1_id = id(lock1)

    # Subsequent accesses should return the same lock
    for i in range(10):
        async def subsequent_access():
            lock = metrics._get_async_lock()
            assert isinstance(lock, asyncio.Lock)
            assert id(lock) == lock1_id, "Should return the same lock"
            return lock

        lock2 = loop.run_until_complete(subsequent_access())
        assert id(lock2) == lock1_id

    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
