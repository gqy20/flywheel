"""
Test for Issue #1196: Race condition in _get_or_create_loop

This test verifies thread safety of the _AsyncCompatibleLock implementation.
The current code is thread-safe, but this test documents and verifies
the expected behavior under concurrent access.
"""
import asyncio
import threading
import time

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_concurrent_get_or_create_loop_thread_safety():
    """
    Test that verifies thread safety when multiple threads
    call _get_or_create_loop concurrently.

    This test ensures that all accesses to _event_loop and
    _event_loop_thread_id are properly protected by the lock,
    preventing race conditions.
    """
    lock = _AsyncCompatibleLock()
    loops = []
    thread_ids = []
    exceptions = []

    def get_loop_info():
        """Get loop and thread ID from a different thread"""
        try:
            loop = lock._get_or_create_loop()
            thread_id = lock._event_loop_thread_id
            loops.append(loop)
            thread_ids.append(thread_id)
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads that will all try to create/get the loop
    threads = [threading.Thread(target=get_loop_info) for _ in range(10)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # No exceptions should have been raised
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # All threads should have gotten a loop
    assert len(loops) == 10

    # All loops should be the same instance (same event loop)
    first_loop = loops[0]
    assert all(loop is first_loop for loop in loops), \
        "All threads should get the same event loop instance"

    # All thread IDs should be the same (the thread that created the loop)
    first_thread_id = thread_ids[0]
    assert all(tid == first_thread_id for tid in thread_ids), \
        f"All thread IDs should be the same, got: {thread_ids}"


def test_concurrent_sync_lock_acquisition():
    """
    Test that verifies thread safety when multiple threads
    try to acquire the sync lock concurrently.

    This test ensures the lock properly handles concurrent access
    without race conditions or deadlocks.
    """
    lock = _AsyncCompatibleLock()
    counter = [0]  # Use list for mutable shared state
    exceptions = []

    def increment_counter():
        """Increment counter with lock protection"""
        try:
            for _ in range(100):
                with lock:
                    # Critical section - only one thread at a time
                    current = counter[0]
                    time.sleep(0.0001)  # Simulate some work
                    counter[0] = current + 1
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads
    threads = [threading.Thread(target=increment_counter) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # No exceptions should have occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # Counter should equal total increments (5 threads * 100 increments each)
    assert counter[0] == 500, f"Expected counter to be 500, got {counter[0]}"


def test_event_loop_state_consistency_under_concurrent_access():
    """
    Test that verifies _event_loop and _event_loop_thread_id
    remain consistent under concurrent access.

    This test ensures that the lock properly protects the internal state
    from race conditions when multiple threads access it concurrently.
    """
    lock = _AsyncCompatibleLock()
    results = []
    exceptions = []

    def access_loop_state():
        """Access loop state from a different thread"""
        try:
            loop = lock._get_or_create_loop()
            thread_id = lock._event_loop_thread_id
            results.append({
                'loop': loop,
                'thread_id': thread_id,
                'has_loop': loop is not None,
                'loop_closed': loop.is_closed()
            })
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads that will all try to access the loop state
    threads = [threading.Thread(target=access_loop_state) for _ in range(10)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # No exceptions should have occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # All threads should successfully get a loop
    assert len(results) == 10
    assert all(r['has_loop'] for r in results)

    # All should have the same loop
    assert all(r['loop'] is results[0]['loop'] for r in results)

    # All should have the same thread ID
    assert all(r['thread_id'] == results[0]['thread_id'] for r in results)

    # Loop should not be closed
    assert all(not r['loop_closed'] for r in results)


def test_no_data_race_on_event_loop_thread_id():
    """
    Test that verifies there's no data race when accessing
    _event_loop_thread_id from multiple threads.

    This test ensures that even though _event_loop_thread_id is read
    outside the lock in some places, the access is still thread-safe
    because the value is stable and only written once.
    """
    lock = _AsyncCompatibleLock()
    thread_ids = []
    exceptions = []

    def read_thread_id():
        """Read thread ID from a different thread"""
        try:
            # First create/get the loop
            loop = lock._get_or_create_loop()
            # Then read the thread ID multiple times
            for _ in range(100):
                thread_id = lock._event_loop_thread_id
                thread_ids.append(thread_id)
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads
    threads = [threading.Thread(target=read_thread_id) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # No exceptions should have occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # All thread IDs should be the same
    assert len(thread_ids) > 0
    first_thread_id = thread_ids[0]
    assert all(tid == first_thread_id for tid in thread_ids), \
        f"All thread IDs should be the same, got unique values: {set(thread_ids)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
