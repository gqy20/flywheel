"""Tests for _AsyncCompatibleLock thread cleanup (issue #1230).

This test verifies that the _AsyncCompatibleLock properly cleans up
the background event loop thread when the lock is destroyed or closed.
"""

import pytest
import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_async_lock_cleanup_background_thread():
    """Test that _AsyncCompatibleLock properly cleans up background thread.

    This test verifies that when a lock is used in a sync context (which
    creates a background event loop thread), the thread is properly
    cleaned up when close() is called or when the object is destroyed.
    """
    # Track threads before creating the lock
    threads_before = set(threading.enumerate())
    thread_count_before = len(threads_before)

    # Create a lock
    lock = _AsyncCompatibleLock()

    # Use the lock in a sync context (this will create a background thread)
    with lock:
        pass

    # After using the lock, there should be a new thread (the event loop thread)
    threads_after_use = set(threading.enumerate())
    thread_count_after_use = len(threads_after_use)

    # The background thread should exist
    assert thread_count_after_use > thread_count_before, \
        "A background thread should have been created"

    # Close the lock
    lock.close()

    # Give some time for the thread to finish
    time.sleep(0.5)

    # After closing, the background thread should be gone
    threads_after_close = set(threading.enumerate())
    thread_count_after_close = len(threads_after_close)

    # The thread count should be back to the original count
    assert thread_count_after_close == thread_count_before, \
        f"Background thread should be cleaned up after close(). " \
        f"Before: {thread_count_before}, After use: {thread_count_after_use}, " \
        f"After close: {thread_count_after_close}"


def test_async_lock_destructor_cleanup():
    """Test that _AsyncCompatibleLock.__del__ properly cleans up.

    This test verifies that the __del__ method properly cleans up
    the background event loop thread when the lock object is destroyed.
    """
    # Track threads before creating the lock
    threads_before = set(threading.enumerate())
    thread_count_before = len(threads_before)

    # Create a lock in a local scope
    def create_and_destroy_lock():
        lock = _AsyncCompatibleLock()
        # Use the lock in a sync context
        with lock:
            pass
        # lock goes out of scope here, __del__ should be called
        return

    create_and_destroy_lock()

    # Give some time for cleanup
    time.sleep(0.5)

    # After destruction, the background thread should be gone
    threads_after = set(threading.enumerate())
    thread_count_after = len(threads_after)

    # The thread count should be back to the original count
    assert thread_count_after == thread_count_before, \
        f"Background thread should be cleaned up after destruction. " \
        f"Before: {thread_count_before}, After: {thread_count_after}"


def test_async_lock_close_idempotent():
    """Test that close() can be called multiple times safely."""
    lock = _AsyncCompatibleLock()

    # Use the lock to create a background thread
    with lock:
        pass

    # close() should be idempotent
    lock.close()
    lock.close()  # Should not raise an error

    # After closing, _event_loop should be None
    assert lock._event_loop is None
    assert lock._loop_thread is None
    assert lock._loop_thread_stop_event is None


def test_async_lock_attributes_after_close():
    """Test that all internal attributes are properly cleaned up."""
    lock = _AsyncCompatibleLock()

    # Use the lock to create a background thread
    with lock:
        pass

    # Close the lock
    lock.close()

    # All internal attributes should be None
    assert lock._event_loop is None, \
        "_event_loop should be None after close()"
    assert lock._event_loop_thread_id is None, \
        "_event_loop_thread_id should be None after close()"
    assert lock._loop_thread is None, \
        "_loop_thread should be None after close()"
    assert lock._loop_thread_stop_event is None, \
        "_loop_thread_stop_event should be None after close()"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
