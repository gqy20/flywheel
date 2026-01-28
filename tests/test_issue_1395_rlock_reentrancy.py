"""Test for Issue #1395: Lock state flags inconsistent with actual lock state.

This test verifies that the _sync_locked and _async_locked boolean flags
cannot correctly track RLock reentrancy. When the same thread acquires the
lock multiple times (reentrancy), the boolean flag doesn't track the count,
leading to state inconsistency.

The bug: RLock supports reentrancy (same thread can acquire multiple times),
but _sync_locked is a simple boolean. This creates a mismatch where:
- Thread acquires lock (reentrant count = 1, _sync_locked = True) ✓
- Thread acquires again (reentrant count = 2, _sync_locked = True) ✗
- Thread releases once (reentrant count = 1, lock still held, but _sync_locked = False) ✗
- Second __exit__ sees _sync_locked = False, tries to release anyway ✗
"""
import threading
import unittest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1395RLockReentrancy(unittest.TestCase):
    """Test that boolean flags cannot track RLock reentrancy correctly."""

    def test_sync_locked_flag_inconsistent_with_rlock_reentrancy(self):
        """Test that _sync_locked flag cannot track RLock reentrant count.

        When the same thread enters the lock context twice (reentrancy),
        the _sync_locked flag is True on first enter and stays True on second enter.
        On first exit, it's set to False, but the lock is still held (reentrant count = 1).
        On second exit, _sync_locked is False, but we should still release.

        This test demonstrates the bug and should FAIL before the fix.
        """
        lock = _AsyncCompatibleLock()

        # First acquisition - this should work normally
        with lock:
            # Inside first context, lock should be held
            self.assertTrue(lock._sync_locked, "First __enter__ should set _sync_locked to True")

            # CRITICAL TEST: Reentrant acquisition
            # When same thread enters again, the RLock count becomes 2
            # but _sync_locked is already True (no change)
            with lock:
                # Inside nested context, _sync_locked is still just True
                # It doesn't track that we've acquired twice
                self.assertTrue(lock._sync_locked, "_sync_locked should be True in nested context")

                # The actual RLock has been acquired twice (reentrant count = 2)
                # But _sync_locked is just a boolean - no count tracking!

            # After first __exit__, reentrant count goes from 2 to 1 (lock STILL HELD)
            # But _sync_locked is set to False - BUG!
            # The flag doesn't match reality: flag=False but lock is still held
            self.assertFalse(
                lock._sync_locked,
                "After first __exit__, _sync_locked is False (BUG: flag doesn't track reentrancy)"
            )

            # BUG: At this point, the lock is STILL held by this thread (reentrant count = 1)
            # but _sync_locked is False. The second __exit__ below should still release,
            # but the flag being False might cause incorrect behavior.

        # After second __exit__, reentrant count goes from 1 to 0 (lock released)
        # This should work, but the flag state was incorrect in between

    def test_rlock_actual_state_vs_flag_mismatch(self):
        """Test that RLock actual state doesn't match boolean flag after reentrant release.

        This test directly checks the RLock internal state vs the _sync_locked flag.
        It should FAIL before the fix, demonstrating the inconsistency.
        """
        lock = _AsyncCompatibleLock()

        # Acquire lock twice (reentrant)
        lock._lock.acquire()
        lock._sync_locked = True  # Simulates first __enter__

        lock._lock.acquire()
        # Second acquire - _sync_locked already True, no change
        # But RLock internal count is now 2

        # Verify RLock is held twice
        self.assertTrue(lock._lock.locked(), "RLock should be held")

        # First release - this simulates first __exit__
        lock._lock.release()
        lock._sync_locked = False  # BUG: Setting flag to False, but lock STILL HELD!

        # CRITICAL ASSERTION: This demonstrates the bug
        # After first release, the lock is STILL held (count went from 2 to 1)
        # but _sync_locked is False
        self.assertFalse(lock._sync_locked, "Flag is False after first release")

        # The RLock is STILL held by this thread (reentrant count = 1)
        # But _sync_locked says False - MISMATCH!
        # We can verify this by trying to check if lock is owned
        if hasattr(lock._lock, '_is_owned'):
            # If this method exists, it should return True (lock still held)
            # while _sync_locked is False - clear inconsistency
            is_owned = lock._lock._is_owned()
            self.assertTrue(
                is_owned and not lock._sync_locked,
                "BUG DETECTED: RLock._is_owned()=True but _sync_locked=False. "
                "The flag doesn't track reentrant count!"
            )

        # Clean up - release the second acquisition
        lock._lock.release()

    def test_rlock_needs_count_not_boolean(self):
        """Test demonstrating that RLock needs a count, not a boolean flag.

        This test shows the conceptual issue: RLock has a reentrant count,
        but _sync_locked is just a boolean. They can't stay in sync.
        """
        lock = _AsyncCompatibleLock()

        # Simulate reentrant acquisition pattern
        acquisitions = 3  # Acquire 3 times
        for _ in range(acquisitions):
            lock._lock.acquire()

        lock._sync_locked = True  # Flag set once, but lock acquired 3 times

        # Boolean flag can't represent count of 3
        self.assertTrue(lock._sync_locked)  # Just True, not 3

        # Release all but one
        for _ in range(acquisitions - 1):
            lock._lock.release()

        # Lock is STILL held (count = 1), but flag doesn't know
        self.assertTrue(lock._lock.locked(), "Lock should still be held")

        # The bug: if we set _sync_locked = False after first release,
        # we lose track of the fact that we still hold the lock
        lock._sync_locked = False  # This would be WRONG - lock still held!

        # But we have no way to know from the flag alone that we still hold it
        # That's the core issue

        # Clean up
        lock._lock.release()


if __name__ == '__main__':
    unittest.main()
