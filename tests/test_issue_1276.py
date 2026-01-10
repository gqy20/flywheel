"""Tests for Issue #1276 - Resource leak: uncleaned background thread and event loop.

Note: This issue was previously fixed in Issue #1185 and Issue #1211.
The _AsyncCompatibleLock class already has both close() and __del__() methods
implemented for proper resource cleanup.

These tests verify that the cleanup functionality works correctly.
"""
import threading
import gc
import time

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockCleanup:
    """Test that _AsyncCompatibleLock properly cleans up resources."""

    def test_lock_has_cleanup_method(self):
        """Test that _AsyncCompatibleLock has a cleanup method."""
        lock = _AsyncCompatibleLock()
        # Trigger event loop creation by using the lock
        with lock:
            pass

        # Check if cleanup method exists
        assert hasattr(lock, 'close') or hasattr(lock, '__del__'), \
            "_AsyncCompatibleLock should have a close() or __del__() method for cleanup"

    def test_background_thread_is_cleaned(self):
        """Test that background threads are properly cleaned up."""
        # Get initial thread count
        initial_thread_count = threading.active_count()

        # Create and use multiple locks
        locks = []
        for _ in range(5):
            lock = _AsyncCompatibleLock()
            with lock:
                pass
            locks.append(lock)

        # Clean up locks if they have a close method
        for lock in locks:
            if hasattr(lock, 'close'):
                lock.close()

        # Force garbage collection
        del locks
        gc.collect()
        time.sleep(0.1)  # Give time for threads to clean up

        # After cleanup, thread count should be close to initial
        # We allow some tolerance for system threads
        final_thread_count = threading.active_count()
        assert final_thread_count <= initial_thread_count + 2, \
            f"Background threads not cleaned up: started with {initial_thread_count}, " \
            f"ended with {final_thread_count}"

    def test_event_loop_is_closed(self):
        """Test that event loops are properly closed."""
        lock = _AsyncCompatibleLock()

        # Trigger event loop creation
        with lock:
            pass

        # Get the event loop
        loop = lock._event_loop
        assert loop is not None, "Event loop should be created"

        # Clean up if method exists
        if hasattr(lock, 'close'):
            lock.close()

        # After cleanup, the loop should be closed
        # or the reference should be cleared
        if hasattr(lock, 'close'):
            assert loop.is_closed() or lock._event_loop is None, \
                "Event loop should be closed after cleanup"

    def test_cleanup_can_be_called_multiple_times(self):
        """Test that cleanup methods are idempotent."""
        lock = _AsyncCompatibleLock()

        # Trigger event loop creation
        with lock:
            pass

        # If close method exists, it should be safe to call multiple times
        if hasattr(lock, 'close'):
            lock.close()
            lock.close()  # Should not raise an exception

    def test_stop_event_is_set_on_cleanup(self):
        """Test that the stop event is properly set during cleanup."""
        lock = _AsyncCompatibleLock()

        # Trigger event loop creation
        with lock:
            pass

        # Get the stop event
        stop_event = lock._loop_thread_stop_event
        assert stop_event is not None, "Stop event should exist"

        # Clean up if method exists
        if hasattr(lock, 'close'):
            lock.close()

            # Stop event should be set
            assert stop_event.is_set(), "Stop event should be set after cleanup"
