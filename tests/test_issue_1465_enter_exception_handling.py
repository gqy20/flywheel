"""Test for Issue #1465: __enter__ method exception handling

This test verifies that the lock is properly managed even in edge cases,
preventing lock leaks through defensive programming.
"""
import threading
import pytest

from flywheel.storage import FileStorage
from flywheel.exceptions import StorageTimeoutError


class TestIssue1465:
    """Test that __enter__ and __exit__ properly handle edge cases to prevent lock leaks."""

    def test_normal_context_manager_behavior(self):
        """Test that normal context manager usage works correctly.

        This test verifies the basic functionality: lock is acquired in __enter__
        and released in __exit__.
        """
        storage = FileStorage(":memory:", timeout=5)

        # Before entering context, lock should not be held
        assert not storage._lock.locked()

        # Inside context, lock should be held
        with storage:
            assert storage._lock.locked()

        # After exiting context, lock should be released
        assert not storage._lock.locked()

    def test_multiple_context_entries_dont_leak_locks(self):
        """Test that multiple sequential context entries don't leak locks.

        This test verifies that the lock can be acquired and released multiple times
        without leaking, which would eventually cause deadlock.
        """
        storage = FileStorage(":memory:", timeout=5)

        # Use the context manager multiple times
        for _ in range(10):
            with storage:
                # Each time, lock should be held
                assert storage._lock.locked()

            # Each time, lock should be released
            assert not storage._lock.locked()

    def test_lock_state_after_failed_enter(self):
        """Test lock state when __enter__ fails due to timeout.

        When __enter__ fails to acquire the lock (timeout), the lock should
        not be held by the current thread.
        """
        storage = FileStorage(":memory:", timeout=0.1)

        # Acquire the lock in another thread to cause timeout
        def hold_lock():
            with storage:
                # Hold the lock for a while
                import time
                time.sleep(0.5)

        thread = threading.Thread(target=hold_lock)
        thread.start()

        # Give the other thread time to acquire the lock
        import time
        time.sleep(0.05)

        # Try to acquire - should timeout
        with pytest.raises(StorageTimeoutError):
            with storage:
                pass

        # Wait for other thread to complete
        thread.join()

        # Our thread should not hold the lock
        assert not storage._lock.locked()

    def test_exit_without_enter_does_not_crash(self):
        """Test that __exit__ handles being called without prior __enter__.

        This is a defensive test for Issue #1465. While this scenario shouldn't
        happen in normal usage, defensive programming should ensure that calling
        __exit__ without a successful __enter__ doesn't cause crashes or
        incorrect state.
        """
        storage = FileStorage(":memory:", timeout=5)

        # Call __exit__ without calling __enter__ first
        # This should not raise an exception or cause problems
        storage.__exit__(None, None, None)

        # Lock should not be held (we never acquired it)
        assert not storage._lock.locked()

    def test_manually_acquired_lock_is_released_by_exit(self):
        """Test that __exit__ properly releases a manually acquired lock.

        This test verifies defensive behavior: if someone manually acquires
        the lock (bypassing __enter__), __exit__ should still release it
        without crashing.
        """
        storage = FileStorage(":memory:", timeout=5)

        # Manually acquire the lock (simulating partial initialization)
        storage._lock.acquire()
        assert storage._lock.locked()

        # Call __exit__ - it should release the lock without error
        storage.__exit__(None, None, None)

        # Lock should be released
        assert not storage._lock.locked()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
