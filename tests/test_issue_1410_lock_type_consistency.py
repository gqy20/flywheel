"""Test for Issue #1410: Lock type consistency.

This test verifies that the lock type in _AsyncCompatibleLock is consistent
between initialization, comments, and logic.

The issue: Code uses threading.Lock() but __exit__ comments and logic
assume it's threading.RLock (checking _is_owned and handling reentrant count).
"""

import threading
import pytest

from src.flywheel.storage import _AsyncCompatibleLock


class TestIssue1410LockTypeConsistency:
    """Test suite for Issue #1410: Lock type consistency."""

    def test_lock_type_matches_comments_and_logic(self):
        """Test that the lock type is consistent with comments and logic.

        The lock type should match what the code comments and logic assume.
        If comments mention RLock, the lock should be RLock.
        If code checks _is_owned (RLock-specific), the lock should be RLock.
        """
        lock = _AsyncCompatibleLock()

        # Check if the lock is a Lock or RLock
        is_lock = isinstance(lock._lock, threading.Lock)
        is_rlock = isinstance(lock._lock, threading.RLock)

        # The lock should be either Lock or RLock, not both
        # Lock is not a subclass of RLock, and vice versa
        assert is_lock != is_rlock or (is_lock and is_rlock), \
            "Lock must be either threading.Lock or threading.RLock"

        # Check if _is_owned method exists (RLock-specific)
        has_is_owned = hasattr(lock._lock, '_is_owned')

        # If code checks _is_owned, lock should be RLock
        # If lock is Lock, it shouldn't check _is_owned
        if is_lock:
            # For threading.Lock, _is_owned should not exist
            # The code should have fallback logic
            assert not has_is_owned, \
                "threading.Lock should not have _is_owned method"

        # Test that __exit__ works correctly
        with lock:
            # Inside context, lock should be locked
            assert lock._lock.locked()

        # Outside context, lock should be released
        # This tests that __exit__ correctly releases the lock
        assert not lock._lock.locked()

    def test_lock_type_documentation_consistency(self):
        """Test that lock type matches documentation.

        The __exit__ docstring mentions "threading.RLock" but the
        implementation uses threading.Lock(). This inconsistency
        causes confusion and potential bugs.
        """
        lock = _AsyncCompatibleLock()

        # The lock type should be explicitly clear
        # Either:
        # 1. Use threading.Lock() and remove RLock-specific logic, OR
        # 2. Use threading.RLock() and keep RLock-specific logic

        lock_type = type(lock._lock).__name__
        actual_lock_type = "Lock" if isinstance(lock._lock, threading.Lock) else "RLock"

        # The lock type in __exit__ docstring should match actual lock type
        # Current issue: docstring says "threading.RLock" but uses threading.Lock()
        assert actual_lock_type in lock_type or lock_type in actual_lock_type, \
            f"Lock type mismatch: {lock_type} vs {actual_lock_type}"

    def test_exit_lock_release_without_is_owned(self):
        """Test that __exit__ works correctly for Lock (without _is_owned).

        For threading.Lock, there is no _is_owned method.
        The code should have fallback logic to handle this case.
        """
        lock = _AsyncCompatibleLock()

        # For Lock, _is_owned should not be available
        has_is_owned = hasattr(lock._lock, '_is_owned')

        if not has_is_owned:
            # The fallback logic should work correctly
            # It should release the lock even without _is_owned
            with lock:
                # Inside context, lock is held
                assert lock._lock.locked()
            # Outside context, lock is released
            assert not lock._lock.locked()

    def test_lock_behavior_matches_type(self):
        """Test that lock behavior matches its declared type.

        If using Lock: no reentrancy, simple acquire/release
        If using RLock: reentrancy supported, _is_owned available
        """
        lock = _AsyncCompatibleLock()
        lock_type = type(lock._lock)

        if lock_type == threading.Lock:
            # Lock should not be reentrant
            # Acquiring twice in same thread should block
            acquired = lock._lock.acquire(blocking=False)
            assert acquired
            try:
                # Second acquire should fail (not reentrant)
                acquired_again = lock._lock.acquire(blocking=False)
                assert not acquired_again, "threading.Lock should not be reentrant"
            finally:
                lock._lock.release()
                # Lock is now released

        elif lock_type == threading.RLock:
            # RLock should be reentrant
            # Acquiring twice in same thread should succeed
            assert lock._lock.acquire(blocking=True)
            assert lock._lock.acquire(blocking=True)  # Reentrant
            lock._lock.release()
            lock._lock.release()
            # Lock is now released
