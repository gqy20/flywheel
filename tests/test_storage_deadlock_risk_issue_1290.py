"""Test for deadlock risk in _AsyncCompatibleLock (Issue #1290).

The issue is that _AsyncCompatibleLock uses asyncio.Lock which is tied to
a specific event loop. When different threads try to acquire the lock, they
might end up using different event loops, which breaks mutual exclusion because
asyncio.Lock is per-event-loop, not a true cross-thread lock.

This test creates a scenario where multiple threads try to acquire the lock
concurrently and verifies that true mutual exclusion is maintained.
"""

import asyncio
import threading
import time
from unittest.mock import patch

from flywheel.storage import _AsyncCompatibleLock


def test_async_lock_mutual_exclusion_with_shared_resource():
    """Test that the lock provides true mutual exclusion across threads.

    This test verifies that when two threads try to access a shared resource
    protected by _AsyncCompatibleLock, they don't interfere with each other.
    If asyncio.Lock doesn't provide proper mutual exclusion across different
    event loops, this test will fail by detecting race conditions.
    """
    lock = _AsyncCompatibleLock()

    # Shared counter that should be protected by the lock
    counter = {'value': 0}
    # Track if race condition was detected
    race_detected = {'detected': False}
    # Track operations for debugging
    operations = []

    def increment_counter(thread_id, num_increments=100):
        """Increment the counter multiple times with lock protection.

        Each increment should be atomic - if the lock works properly,
        the final value should be exactly thread_id * num_increments.
        """
        for i in range(num_increments):
            with lock:
                # Read current value
                current = counter['value']
                operations.append(f"Thread {thread_id}: read {current}")

                # Simulate some work while holding the lock
                time.sleep(0.0001)

                # Write new value
                new_value = current + 1
                counter['value'] = new_value
                operations.append(f"Thread {thread_id}: wrote {new_value}")

                # Check for race condition: if another thread modified the counter
                # between our read and write, we'd have a problem
                # (This is a simplified check - real race conditions might be more subtle)

    # Create multiple threads that will increment the counter
    num_threads = 5
    num_increments = 50
    threads = []

    for thread_id in range(num_threads):
        thread = threading.Thread(
            target=increment_counter,
            args=(thread_id, num_increments)
        )
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join(timeout=30)

    # Expected final value
    expected_value = num_threads * num_increments
    actual_value = counter['value']

    # Verify mutual exclusion was maintained
    assert actual_value == expected_value, (
        f"Race condition detected! Expected counter={expected_value}, "
        f"but got {actual_value}. This indicates that _AsyncCompatibleLock "
        f"does not provide proper mutual exclusion across threads. "
        f"This is likely because asyncio.Lock is tied to specific event "
        f"loops, and different threads may be using different loops."
    )


def test_async_lock_no_deadlock_with_cross_thread_access():
    """Test that the lock doesn't cause deadlocks with cross-thread access.

    This test creates a scenario where one thread holds the lock and another
    thread tries to acquire it. If the implementation uses asyncio.Lock
    improperly, this could lead to deadlocks.
    """
    lock = _AsyncCompatibleLock()

    # Track state
    thread1_acquired = {'value': False}
    thread2_acquired = {'value': False}
    thread1_done = {'value': False}
    deadlock_detected = {'value': False}

    def thread1_func():
        """First thread that holds the lock for a while."""
        nonlocal thread1_acquired, thread1_done
        with lock:
            thread1_acquired['value'] = True
            # Hold the lock for a bit
            time.sleep(0.5)
            thread1_done['value'] = True

    def thread2_func():
        """Second thread that tries to acquire the lock."""
        nonlocal thread2_acquired, deadlock_detected
        # Wait for thread1 to acquire the lock
        while not thread1_acquired['value']:
            time.sleep(0.01)

        # Try to acquire the lock (should block until thread1 releases it)
        # Use a timeout to detect potential deadlocks
        start_time = time.time()
        with lock:
            wait_time = time.time() - start_time

            # If we had to wait more than 2 seconds, something is wrong
            if wait_time > 2.0:
                deadlock_detected['value'] = True

            thread2_acquired['value'] = True

    # Start thread1
    t1 = threading.Thread(target=thread1_func)
    t1.start()

    # Start thread2 (it should block until thread1 releases)
    t2 = threading.Thread(target=thread2_func)
    t2.start()

    # Wait for both threads with timeout
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Verify both threads completed successfully
    assert thread1_done['value'], "Thread 1 did not complete"
    assert thread2_acquired['value'], "Thread 2 did not acquire the lock"
    assert not deadlock_detected['value'], (
        "Potential deadlock detected - thread2 took too long to acquire lock"
    )

    # Verify threads are actually done
    assert not t1.is_alive(), "Thread 1 is still running"
    assert not t2.is_alive(), "Thread 2 is still running"


def test_async_lock_single_event_loop_across_threads():
    """Test that the lock uses a single event loop across all threads.

    This test verifies the fix for Issue #1290: all threads should use
    the same event loop for lock synchronization.
    """
    lock = _AsyncCompatibleLock()

    # Track event loops used by different threads
    event_loops = []
    errors = []

    def get_loop_in_thread():
        """Each thread gets the event loop used by the lock."""
        try:
            # Get the event loop by triggering lock acquisition
            loop = lock._get_or_create_loop()
            event_loops.append(loop)
        except Exception as e:
            errors.append(e)

    # Create multiple threads
    num_threads = 10
    threads = []

    for _ in range(num_threads):
        thread = threading.Thread(target=get_loop_in_thread)
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join(timeout=10)

    # Verify no errors
    assert not errors, f"Errors occurred: {errors}"

    # All threads should have gotten the same event loop
    assert len(event_loops) == num_threads, (
        f"Expected {num_threads} event loops, got {len(event_loops)}"
    )

    first_loop = event_loops[0]
    for loop in event_loops[1:]:
        assert loop is first_loop, (
            "Different threads are using different event loops! "
            "This breaks mutual exclusion because asyncio.Lock is "
            "tied to a specific event loop."
        )


def test_async_lock_stress_test_concurrent_access():
    """Stress test the lock with heavy concurrent access.

    This test creates a scenario with many threads performing many
    lock acquisitions to verify that the lock remains stable and
    provides consistent mutual exclusion.
    """
    lock = _AsyncCompatibleLock()

    # Shared resource
    counter = {'value': 0}
    # Track errors
    errors = []

    def increment_many_times(thread_id):
        """Increment the counter many times."""
        try:
            for _ in range(100):
                with lock:
                    current = counter['value']
                    time.sleep(0.00001)  # Tiny delay to increase contention
                    counter['value'] = current + 1
        except Exception as e:
            errors.append((thread_id, e))

    # Create many threads
    num_threads = 20
    threads = []

    for thread_id in range(num_threads):
        thread = threading.Thread(
            target=increment_many_times,
            args=(thread_id,)
        )
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join(timeout=60)

    # Verify no errors
    assert not errors, f"Errors occurred: {errors}"

    # Verify final counter value
    expected_value = num_threads * 100
    actual_value = counter['value']

    assert actual_value == expected_value, (
        f"Stress test failed! Expected {expected_value}, got {actual_value}. "
        f"This indicates that the lock does not provide reliable mutual "
        f"exclusion under high contention."
    )
