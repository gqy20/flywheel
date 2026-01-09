"""Test for issue #1154: Race condition in IOMetrics._get_async_lock

This test verifies that _get_async_lock is thread-safe and doesn't create
multiple locks for the same event loop when called concurrently.
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from flywheel.storage import IOMetrics


def test_get_async_lock_thread_safety():
    """Test that _get_async_lock doesn't have race conditions.

    This test creates multiple threads that simultaneously call _get_async_lock
    in the same event loop. The test verifies that:
    1. Only one lock is created for the event loop
    2. All threads receive the same lock instance
    3. No exceptions occur during concurrent access
    """
    metrics = IOMetrics()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    locks = []
    exceptions = []
    num_threads = 10

    def get_lock_from_thread():
        """Each thread tries to get the async lock."""
        try:
            # Small delay to increase chance of race condition
            time.sleep(0.001)
            lock = metrics._get_async_lock()
            locks.append(lock)
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads that will try to get the lock simultaneously
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=get_lock_from_thread)
        threads.append(t)

    # Start all threads at roughly the same time
    for t in threads:
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Check that no exceptions occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # Check that all threads got the same lock instance
    assert len(locks) == num_threads, f"Expected {num_threads} locks, got {len(locks)}"

    # All locks should be the same instance (same object identity)
    first_lock = locks[0]
    for lock in locks[1:]:
        assert lock is first_lock, "Different lock instances were created for the same event loop"

    # Verify that only one lock was created for this event loop
    assert len(metrics._locks) == 1, f"Expected 1 lock in _locks dict, got {len(metrics._locks)}"
    assert loop in metrics._locks, "Event loop not found in _locks dict"
    assert metrics._locks[loop] is first_lock, "Lock in _locks dict doesn't match returned lock"

    loop.close()


def test_get_async_lock_different_loops():
    """Test that _get_async_lock creates different locks for different event loops.

    This test verifies that when called from different event loops (in different
    threads), _get_async_lock correctly creates and returns different locks.
    """
    metrics = IOMetrics()

    results = {}
    exceptions = []

    def run_in_loop(loop_id):
        """Run an async task in a new event loop."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            lock = metrics._get_async_lock()
            results[loop_id] = (loop, lock)

            loop.close()
        except Exception as e:
            exceptions.append((loop_id, e))

    # Create multiple threads, each with its own event loop
    threads = []
    for i in range(5):
        t = threading.Thread(target=run_in_loop, args=(i,))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Check that no exceptions occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # Check that we got locks for all threads
    assert len(results) == 5, f"Expected 5 results, got {len(results)}"

    # Check that each event loop got its own lock
    loops_and_locks = list(results.values())
    for i, (loop1, lock1) in enumerate(loops_and_locks):
        for loop2, lock2 in loops_and_locks[i + 1:]:
            # Different event loops should have different locks
            assert loop1 is not loop2, "Event loops should be different"
            assert lock1 is not lock2, "Locks should be different for different event loops"

    # Verify that _locks dict contains all the correct locks
    assert len(metrics._locks) == 5, f"Expected 5 locks in _locks dict, got {len(metrics._locks)}"
    for loop, lock in results.values():
        assert loop in metrics._locks, "Event loop not found in _locks dict"
        assert metrics._locks[loop] is lock, "Lock in _locks dict doesn't match returned lock"


def test_get_async_lock_double_checked_locking():
    """Test that the double-checked locking pattern is correctly implemented.

    This test verifies that the lock is acquired before checking if the lock
    exists, preventing race conditions.
    """
    metrics = IOMetrics()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # First call should create a new lock
    lock1 = metrics._get_async_lock()
    assert lock1 is not None
    assert len(metrics._locks) == 1
    assert loop in metrics._locks
    assert metrics._locks[loop] is lock1

    # Second call should return the same lock
    lock2 = metrics._get_async_lock()
    assert lock2 is lock1
    assert len(metrics._locks) == 1

    loop.close()
