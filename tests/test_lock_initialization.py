"""Tests for _AsyncCompatibleLock initialization safety.

This test ensures that locks are properly initialized per-instance
to avoid race conditions from shared class-level locks.

Issue #1609
"""
import threading
import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestLockInitialization:
    """Test that each _AsyncCompatibleLock instance has its own locks."""

    def test_each_instance_has_own_lock(self):
        """Each instance should have a unique lock object."""
        lock1 = _AsyncCompatibleLock()
        lock2 = _AsyncCompatibleLock()

        # Verify that each instance has its own lock
        assert lock1._lock is not lock2._lock, \
            "Each instance should have its own lock to prevent race conditions"

    def test_locks_initialized_in_init(self):
        """Locks should be instance attributes, not class attributes."""
        lock = _AsyncCompatibleLock()

        # Verify lock is an instance attribute
        assert hasattr(lock, '_lock'), "Instance should have _lock attribute"
        assert hasattr(lock, '_async_events'), "Instance should have _async_events attribute"
        assert hasattr(lock, '_async_event_init_lock'), "Instance should have _async_event_init_lock attribute"
        assert hasattr(lock, '_stats_lock'), "Instance should have _stats_lock attribute"

        # Verify they are actual Lock objects
        assert isinstance(lock._lock, threading.Lock), "_lock should be a threading.Lock"
        assert isinstance(lock._async_event_init_lock, threading.Lock), "_async_event_init_lock should be a threading.Lock"
        assert isinstance(lock._stats_lock, threading.Lock), "_stats_lock should be a threading.Lock"

    def test_multiple_instances_dont_share_lock_state(self):
        """Multiple instances should not interfere with each other."""
        lock1 = _AsyncCompatibleLock()
        lock2 = _AsyncCompatibleLock()

        # Acquire lock1
        lock1._lock.acquire()

        # lock2 should still be acquireable since it's a different lock
        acquired = lock2._lock.acquire(blocking=False)
        assert acquired, "lock2 should be acquireable even though lock1 is held"

        # Cleanup
        lock1._lock.release()
        lock2._lock.release()

    def test_atexit_handler_does_not_leak(self):
        """atexit handlers should not cause memory leaks.

        The current implementation registers an atexit handler for each instance.
        This test verifies that instances can be garbage collected properly.

        Issue #1609: Potential memory leak from atexit handlers holding references.
        """
        import gc
        import weakref
        import atexit

        # Get initial handler count
        initial_count = len(atexit._exithandlers)

        # Create a lock and get a weak reference to it
        lock = _AsyncCompatibleLock()
        weak_ref = weakref.ref(lock)

        # The handler should have been registered
        current_count = len(atexit._exithandlers)
        assert current_count > initial_count, \
            "atexit handler should be registered for each instance"

        # Delete the lock
        del lock
        gc.collect()

        # The weak reference should now be dead (garbage collected)
        # This test will FAIL if the atexit handler prevents garbage collection
        assert weak_ref() is None, \
            "Lock instance should be garbage collected even with atexit handler registered. " \
            "If this fails, it indicates a memory leak from the atexit handler."

    def test_stats_initialized_per_instance(self):
        """Statistics should be initialized separately for each instance."""
        lock1 = _AsyncCompatibleLock()
        lock2 = _AsyncCompatibleLock()

        # Both should start with zero stats
        assert lock1._acquire_count == 0
        assert lock2._acquire_count == 0

        # Modify stats for lock1
        with lock1._stats_lock:
            lock1._acquire_count = 10

        # lock2 stats should be unaffected
        assert lock2._acquire_count == 0, \
            "Each instance should have its own statistics"
