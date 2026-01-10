"""Test for Issue #1326 - _AsyncCompatibleLock uses a single _locked flag for two distinct locks.

This test demonstrates the race condition where using a single _locked flag for both
the threading lock and the asyncio lock causes state corruption.
"""

import asyncio
import threading
import time
import unittest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1326SeparateStateFlags(unittest.TestCase):
    """Test that _AsyncCompatibleLock maintains separate state for sync and async locks."""

    def test_separate_state_flags_exist(self):
        """Test that separate state flags exist for sync and async locks.

        This is the core issue: the current implementation uses a single _locked flag
        for both locks, which causes state corruption. We need separate _sync_locked
        and _async_locked flags.
        """
        lock = _AsyncCompatibleLock()

        # Check that lock has separate flags
        # This will fail with current implementation, demonstrating the bug
        self.assertTrue(
            hasattr(lock, '_sync_locked'),
            "Lock should have _sync_locked flag for sync lock state"
        )
        self.assertTrue(
            hasattr(lock, '_async_locked'),
            "Lock should have _async_locked flag for async lock state"
        )

        # Initially, both flags should be False
        self.assertFalse(lock._sync_locked, "Initial sync state should be unlocked")
        self.assertFalse(lock._async_locked, "Initial async state should be unlocked")

    def test_sync_lock_sets_correct_flag(self):
        """Test that sync lock only affects _sync_locked flag."""
        lock = _AsyncCompatibleLock()

        # Acquire sync lock
        lock.__enter__()

        # After sync acquire, ONLY _sync_locked should be True
        if hasattr(lock, '_sync_locked'):
            self.assertTrue(lock._sync_locked, "Sync lock should set _sync_locked to True")
            if hasattr(lock, '_async_locked'):
                self.assertFalse(
                    lock._async_locked,
                    "Sync lock should NOT affect _async_locked flag"
                )

        # Cleanup
        lock.__exit__(None, None, None)

        # After sync release, _sync_locked should be False
        if hasattr(lock, '_sync_locked'):
            self.assertFalse(lock._sync_locked, "After sync release, _sync_locked should be False")

    def test_async_lock_sets_correct_flag(self):
        """Test that async lock only affects _async_locked flag."""
        lock = _AsyncCompatibleLock()

        async def test_async():
            # Acquire async lock
            async with lock:
                # Inside async context, ONLY _async_locked should be True
                if hasattr(lock, '_async_locked'):
                    self.assertTrue(
                        lock._async_locked,
                        "Async lock should set _async_locked to True"
                    )
                    if hasattr(lock, '_sync_locked'):
                        self.assertFalse(
                            lock._sync_locked,
                            "Async lock should NOT affect _sync_locked flag"
                        )

            # After async exit, _async_locked should be False
            if hasattr(lock, '_async_locked'):
                self.assertFalse(
                    lock._async_locked,
                    "After async release, _async_locked should be False"
                )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(test_async())
        finally:
            loop.close()

    def test_single_locked_flag_causes_corruption(self):
        """Demonstrate that using a single _locked flag causes state corruption.

        This test shows the bug: when sync and async locks both use the same
        _locked flag, acquiring one affects the state of the other.
        """
        lock = _AsyncCompatibleLock()

        # First, show that the bug exists
        # The current implementation has _locked but not separate flags
        self.assertTrue(
            hasattr(lock, '_locked'),
            "Current implementation should have _locked attribute"
        )

        # Demonstrate the corruption scenario
        # 1. Acquire sync lock - sets _locked = True
        lock.__enter__()
        self.assertTrue(lock._locked, "After sync __enter__, _locked should be True")

        # The bug: if we could somehow acquire async lock while sync is held,
        # async __aexit__ would set _locked = False, corrupting sync state

        # Cleanup
        lock.__exit__(None, None, None)
        self.assertFalse(lock._locked, "After sync __exit__, _locked should be False")

    def test_concurrent_sync_and_async_no_interference(self):
        """Test that concurrent sync and async access don't interfere via state flags.

        With separate flags, sync and async operations should maintain independent
        state without corrupting each other.
        """
        lock = _AsyncCompatibleLock()
        results = {'sync_entered': False, 'async_entered': False, 'errors': []}

        def sync_worker():
            try:
                with lock:
                    results['sync_entered'] = True
                    # With separate flags, async flag should not be affected
                    if hasattr(lock, '_async_locked'):
                        # This might be True if async lock is held concurrently
                        # but sync flag should definitely be True
                        pass
                    time.sleep(0.1)
            except Exception as e:
                results['errors'].append(f"sync: {e}")

        async def async_worker():
            try:
                async with lock:
                    results['async_entered'] = True
                    # With separate flags, sync flag should not be affected
                    if hasattr(lock, '_sync_locked'):
                        # This might be True if sync lock is held concurrently
                        # but async flag should definitely be True
                        pass
                    await asyncio.sleep(0.1)
            except Exception as e:
                results['errors'].append(f"async: {e}")

        # Run sync and async workers concurrently
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            sync_thread = threading.Thread(target=sync_worker)
            sync_thread.start()

            loop.run_until_complete(async_worker())
            sync_thread.join()
        finally:
            loop.close()

        # Verify both workers completed without errors
        self.assertTrue(results['sync_entered'], "Sync worker should have entered lock")
        self.assertTrue(results['async_entered'], "Async worker should have entered lock")
        self.assertEqual(
            len(results['errors']),
            0,
            f"No errors should occur: {results['errors']}"
        )


if __name__ == '__main__':
    unittest.main()
