"""
Test for Issue #1221: Background event loop thread cannot be stopped cleanly.

This test verifies that the background event loop thread created in
_get_or_create_loop can be properly shut down using the stop event mechanism.
"""

import threading
import time
import asyncio
from unittest.mock import patch

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_event_loop_thread_stops_cleanly_with_stop_event():
    """
    Test that the background event loop thread stops when stop event is set.

    This test verifies the fix for Issue #1221. The problem was that
    the background thread used `loop.run_until_complete(asyncio.sleep(0.1))`
    in a while loop, which cannot be interrupted by `loop.stop()` because
    `run_until_complete` will restart the loop if the future isn't done.

    The fix uses `loop.run_forever()` and calls `loop.call_soon_threadsafe(loop.stop)`
    when the stop event is set.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock in a sync context to trigger event loop creation
    with lock:
        # Verify that a background thread was created
        assert lock._loop_thread is not None
        assert lock._loop_thread_stop_event is not None
        assert lock._loop_thread.is_alive()

        # Get the thread reference for later testing
        thread_ref = lock._loop_thread
        stop_event_ref = lock._loop_thread_stop_event
        loop_ref = lock._event_loop

    # After exiting the context, the thread should still be alive
    # (it's a daemon thread that runs until the lock is garbage collected)
    assert thread_ref.is_alive()

    # Now set the stop event to signal the thread to stop
    stop_event_ref.set()

    # Give the thread a moment to stop
    # With the bug, this would timeout because the thread cannot be stopped
    thread_ref.join(timeout=2.0)

    # Verify the thread has stopped
    # With the bug, this assertion would fail
    assert not thread_ref.is_alive(), "Background event loop thread did not stop when stop event was set"


def test_event_loop_thread_can_be_stopped_multiple_times():
    """
    Test that setting the stop event multiple times doesn't cause issues.

    This ensures the stop mechanism is idempotent and handles edge cases.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock to create the background thread
    with lock:
        thread_ref = lock._loop_thread
        stop_event_ref = lock._loop_thread_stop_event

    # Set the stop event multiple times
    stop_event_ref.set()
    stop_event_ref.set()
    stop_event_ref.set()

    # The thread should stop normally
    thread_ref.join(timeout=2.0)
    assert not thread_ref.is_alive()


def test_event_loop_thread_respects_stop_event_immediately():
    """
    Test that the event loop thread checks the stop event promptly.

    This test ensures that once the stop event is set, the thread
    exits the loop and terminates without unnecessary delays.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock to create the background thread
    with lock:
        thread_ref = lock._loop_thread
        stop_event_ref = lock._loop_thread_stop_event

    # Record the time before setting the stop event
    start_time = time.time()

    # Set the stop event
    stop_event_ref.set()

    # Wait for the thread to stop
    thread_ref.join(timeout=2.0)

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # The thread should stop within a reasonable time (< 1 second)
    # With the bug, this would take much longer or timeout
    assert not thread_ref.is_alive()
    assert elapsed_time < 1.0, f"Thread took {elapsed_time:.2f}s to stop, expected < 1.0s"


def test_event_loop_thread_stops_with_pending_tasks():
    """
    Test that the event loop thread stops even when there are pending tasks.

    This verifies that the stop mechanism works correctly even when
    the event loop has pending tasks scheduled.
    """
    lock = _AsyncCompatibleLock()

    # Use the lock to create the background thread
    with lock:
        loop_ref = lock._event_loop
        thread_ref = lock._loop_thread
        stop_event_ref = lock._loop_thread_stop_event

        # Schedule some tasks on the event loop
        async def dummy_task():
            await asyncio.sleep(10)  # This will be cancelled

        # Submit multiple tasks to the loop
        for _ in range(5):
            asyncio.run_coroutine_threadsafe(dummy_task(), loop_ref)

    # Now set the stop event
    # The thread should stop despite having pending tasks
    stop_event_ref.set()

    # Wait for the thread to stop
    thread_ref.join(timeout=2.0)

    # Verify the thread stopped
    assert not thread_ref.is_alive(), "Thread did not stop with pending tasks"


def test_multiple_locks_with_independent_threads():
    """
    Test that multiple locks have independent event loop threads.

    This verifies that stopping one lock's thread doesn't affect others.
    """
    lock1 = _AsyncCompatibleLock()
    lock2 = _AsyncCompatibleLock()

    # Use both locks to create independent threads
    with lock1:
        thread1 = lock1._loop_thread
        stop_event1 = lock1._loop_thread_stop_event

    with lock2:
        thread2 = lock2._loop_thread
        stop_event2 = lock2._loop_thread_stop_event

    # Both threads should be alive
    assert thread1.is_alive()
    assert thread2.is_alive()

    # Stop only the first thread
    stop_event1.set()
    thread1.join(timeout=2.0)

    # First thread should stop, second should still be alive
    assert not thread1.is_alive()
    assert thread2.is_alive()

    # Stop the second thread
    stop_event2.set()
    thread2.join(timeout=2.0)

    # Both should be stopped now
    assert not thread2.is_alive()
