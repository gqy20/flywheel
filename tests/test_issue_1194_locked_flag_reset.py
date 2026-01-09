"""Test for Issue #1194: Deadlock risk in __exit__ due to missing reset of _locked flag.

This test verifies that the _locked flag is properly reset even when
future.result() times out during lock release in __exit__.
"""
import asyncio
import threading
import time
import unittest
from unittest.mock import patch, MagicMock

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1194LockedFlagReset(unittest.TestCase):
    """Test that _locked flag is reset correctly even when timeout occurs."""

    def test_locked_flag_reset_after_timeout_in_exit(self):
        """Test that _locked flag is reset to False even when future.result times out.

        This test simulates a timeout scenario in __exit__ where the lock release
        future times out. The _locked flag should still be set to False to prevent
        state inconsistency.
        """
        lock = _AsyncCompatibleLock()

        # Simulate acquiring the lock normally
        loop = lock._get_or_create_loop()

        # Acquire the lock using run_coroutine_threadsafe
        future = asyncio.run_coroutine_threadsafe(lock._lock.acquire(), loop)
        future.result(timeout=1)
        lock._locked = True  # Mark as locked

        # Verify lock is acquired
        self.assertTrue(lock._locked)
        self.assertTrue(lock._lock.locked())

        # Mock run_coroutine_threadsafe to simulate timeout
        original_run_coroutine_threadsafe = asyncio.run_coroutine_threadsafe
        timeout_simulated = threading.Event()

        def mock_run_coroutine_threadsafe(coro, loop):
            """Mock that creates a future that will timeout."""
            if not timeout_simulated.is_set():
                timeout_simulated.set()
                # Create a future that never completes
                never_completes = asyncio.Future()
                return never_completes
            return original_run_coroutine_threadsafe(coro, loop)

        with patch('asyncio.run_coroutine_threadsafe',
                   side_effect=mock_run_coroutine_threadsafe):
            # Call __exit__ which should handle timeout
            lock.__exit__(None, None, None)

        # CRITICAL ASSERTION: _locked flag should be False even after timeout
        # This is the bug fix - if _locked remains True after timeout,
        # the next __exit__ call might skip releasing the actual lock
        self.assertFalse(
            lock._locked,
            "_locked flag should be False after __exit__ even when timeout occurs. "
            "If this flag remains True, it creates state inconsistency where "
            "_locked=True but the underlying asyncio lock might not be held."
        )

    def test_locked_flag_consistency_with_actual_lock(self):
        """Test that _locked flag state matches actual lock state after timeout.

        This test verifies that even when a timeout occurs, the _locked flag
        should reflect the correct state to prevent deadlocks on subsequent use.
        """
        lock = _AsyncCompatibleLock()

        # Acquire the lock
        loop = lock._get_or_create_loop()
        future = asyncio.run_coroutine_threadsafe(lock._lock.acquire(), loop)
        future.result(timeout=1)
        lock._locked = True

        # Verify lock is acquired
        self.assertTrue(lock._locked)

        # Simulate timeout in __exit__
        timeout_occurred = False

        original_result_method = asyncio.Future.result

        def mock_result(self, timeout=None):
            """Mock result method that raises TimeoutError."""
            nonlocal timeout_occurred
            if not timeout_occurred:
                timeout_occurred = True
                raise TimeoutError("Simulated timeout")
            return original_result_method(self, timeout=timeout)

        with patch.object(asyncio.Future, 'result', side_effect=mock_result):
            # Call __exit__ - should handle timeout gracefully
            lock.__exit__(None, None, None)

        # After __exit__, _locked should be False regardless of timeout
        self.assertFalse(
            lock._locked,
            "After __exit__ completes (even with timeout), _locked must be False "
            "to prevent state mismatch on next __enter__/__exit__ cycle."
        )

        # Additional verification: try to acquire the lock again
        # This should work without deadlock
        try:
            future = asyncio.run_coroutine_threadsafe(lock._lock.acquire(), loop)
            # First try to release the original lock (if still held)
            try:
                asyncio.run_coroutine_threadsafe(lock._lock.release(), loop).result(timeout=0.1)
            except:
                pass
            # Now try to acquire
            acquired = future.result(timeout=0.5)
            if acquired:
                lock._lock.release()
            # If we get here without deadlock, the fix is working
        except Exception as e:
            # If there's a deadlock or other issue, fail the test
            self.fail(f"Should be able to use lock after timeout in __exit__: {e}")

    def test_no_state_inconsistency_after_timeout(self):
        """Test that timeout doesn't create state inconsistency between _locked and actual lock.

        The bug is that if _locked remains True after timeout, but the actual
        lock might be released later by the event loop, creating a state where:
        - _locked = True
        - actual lock = not held

        This causes __exit__ to skip releasing on next use, while the lock
        might actually be held by someone else.
        """
        lock = _AsyncCompatibleLock()

        # First, acquire and release to establish baseline
        loop = lock._get_or_create_loop()

        # Scenario 1: Normal acquisition
        with lock:
            self.assertTrue(lock._locked)

        self.assertFalse(lock._locked)

        # Scenario 2: Acquisition followed by timeout on release
        future = asyncio.run_coroutine_threadsafe(lock._lock.acquire(), loop)
        future.result(timeout=1)
        lock._locked = True

        # Simulate timeout
        timeout_happened = False

        def slow_release(*args, **kwargs):
            """A release that will timeout."""
            async def never_completes():
                await asyncio.sleep(100)  # Long sleep to cause timeout
                return True

            nonlocal timeout_happened
            timeout_happened = True
            return asyncio.run_coroutine_threadsafe(never_completes(), loop)

        original_rcts = asyncio.run_coroutine_threadsafe

        with patch('asyncio.run_coroutine_threadsafe', side_effect=slow_release):
            lock.__exit__(None, None, None)

        # Verify timeout was simulated
        self.assertTrue(timeout_happened, "Timeout should have been simulated")

        # CRITICAL: After __exit__ with timeout, _locked must be False
        # Otherwise, next __exit__ might think lock is already released
        # (because _locked is True) and skip releasing, causing deadlock
        self.assertFalse(
            lock._locked,
            "_locked flag must be False after __exit__ even with timeout. "
            "This ensures consistent state and prevents deadlock on reuse."
        )


if __name__ == '__main__':
    unittest.main()
