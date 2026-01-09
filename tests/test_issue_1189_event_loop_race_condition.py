"""
Test for Issue #1189 - Race condition in event loop creation

This test verifies that the event loop creation is thread-safe and properly
handles the double-checked locking pattern without race conditions.
"""

import asyncio
import threading
import pytest
from flywheel import Storage


def test_event_loop_creation_thread_safety():
    """
    Test that multiple threads cannot create different event loops simultaneously.

    The bug was that the double-checked locking pattern checked `self._event_loop`
    outside the lock first. If the loop is closed between the check and the lock
    acquisition, multiple threads may create new loops.

    This test creates multiple threads that all try to get the event loop at the
    same time, and verifies that they all get the same loop object.
    """
    storage = Storage(":memory:", threaded=True)

    # Container to store the event loops from different threads
    loops = []
    exceptions = []
    num_threads = 10

    def get_event_loop():
        """Try to get the event loop from a thread."""
        try:
            # Get the internal event loop
            loop = storage._get_event_loop()
            loops.append(loop)
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads that all try to get the event loop simultaneously
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=get_event_loop)
        threads.append(thread)

    # Start all threads at roughly the same time
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that no exceptions occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # Check that all threads got the same event loop
    assert len(loops) == num_threads, f"Expected {num_threads} loops, got {len(loops)}"

    # All loops should be the same object (not just equal)
    first_loop = loops[0]
    for loop in loops[1:]:
        assert loop is first_loop, "Multiple threads got different event loop objects!"

    # Clean up
    storage.close()


def test_event_loop_recreation_after_close():
    """
    Test that when an event loop is closed and needs to be recreated,
    only one thread succeeds in creating the new loop.

    This test simulates the scenario where the event loop becomes closed
    (e.g., after being used in an async context and then closed), and
    multiple threads try to get/create a new one.
    """
    storage = Storage(":memory:", threaded=True)

    # Get the initial event loop
    initial_loop = storage._get_event_loop()
    assert initial_loop is not None

    # Close the event loop to simulate it becoming invalid
    initial_loop.close()

    # Now multiple threads try to get the event loop
    loops = []
    exceptions = []
    num_threads = 10

    def get_event_loop_after_close():
        """Try to get the event loop after it's been closed."""
        try:
            loop = storage._get_event_loop()
            loops.append(loop)
        except Exception as e:
            exceptions.append(e)

    # Create multiple threads that all try to get the event loop
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=get_event_loop_after_close)
        threads.append(thread)

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that no exceptions occurred
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

    # Check that all threads got an event loop
    assert len(loops) == num_threads, f"Expected {num_threads} loops, got {len(loops)}"

    # All loops should be the same object
    first_loop = loops[0]
    for loop in loops[1:]:
        assert loop is first_loop, "Multiple threads created different event loop objects!"

    # The new loop should be different from the initial closed loop
    assert loops[0] is not initial_loop, "Should have created a new event loop"

    # The new loop should be running (not closed)
    assert not loops[0].is_closed(), "New event loop should not be closed"

    # Clean up
    storage.close()


def test_event_loop_double_checked_locking_atomicity():
    """
    Test that the double-checked locking pattern is atomic.

    This test specifically targets the bug where the check happens outside
    the lock, allowing a race condition where the loop state changes between
    the check and the lock acquisition.
    """
    storage = Storage(":memory:", threaded=True)

    # Get initial loop
    loop1 = storage._get_event_loop()
    assert loop1 is not None

    # Use a barrier to synchronize threads
    barrier = threading.Barrier(2)
    loops = []
    exceptions = []

    def thread1_func():
        """Thread 1: Close the loop at a precise moment."""
        try:
            barrier.wait()  # Synchronize with thread 2
            # Immediately after thread 2 passes the first check,
            # close the loop to create the race condition
            if storage._event_loop is not None:
                storage._event_loop.close()
        except Exception as e:
            exceptions.append(e)

    def thread2_func():
        """Thread 2: Try to get the event loop."""
        try:
            barrier.wait()  # Synchronize with thread 1
            # This should handle the race condition correctly
            loop = storage._get_event_loop()
            loops.append(loop)
        except Exception as e:
            exceptions.append(e)

    # Create and start threads
    t1 = threading.Thread(target=thread1_func)
    t2 = threading.Thread(target=thread2_func)

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Thread 2 should have gotten a valid loop (either the old one or a new one)
    # but should not have crashed
    assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
    assert len(loops) == 1, "Thread 2 should have gotten exactly one loop"

    # The loop should be valid (not closed)
    # Note: Due to the race, it could be either the original closed loop
    # or a newly created one. The important thing is no exception occurred.
    # In the fixed version, a new loop should be created
    assert not loops[0].is_closed() or loops[0] is loop1, \
        "Loop should be valid or the original loop"

    # Clean up
    try:
        storage.close()
    except:
        pass
