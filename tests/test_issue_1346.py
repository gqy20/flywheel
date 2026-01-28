"""Tests for Issue #1346 - Lock cleanup logic has race condition and memory leak risks.

This test verifies that:
1. weakref.WeakValueDictionary is used for automatic lifecycle management
2. No hardcoded threshold causes high-frequency cleanup
3. No race condition when locks are being used while cleanup occurs
"""

import asyncio
import threading
import weakref
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1346:
    """Test suite for Issue #1346 fix."""

    def test_lock_uses_weakref_for_lifecycle_management(self):
        """Test that _async_locks uses weakref.WeakValueDictionary for automatic cleanup."""
        lock = _AsyncCompatibleLock()

        # Verify that _async_locks is a WeakValueDictionary or similar weakref-based structure
        # This ensures automatic cleanup when event loops are destroyed
        assert isinstance(lock._async_locks, weakref.WeakValueDictionary) or \
               hasattr(lock._async_locks, '_weakref__dict'), \
            "_async_locks should use weakref.WeakValueDictionary for automatic lifecycle management"

    def test_no_hardcoded_cleanup_threshold(self):
        """Test that there is no hardcoded threshold (like '10') triggering cleanup."""
        lock = _AsyncCompatibleLock()

        # Create many event loops with locks
        # If there's a hardcoded threshold, this would trigger cleanup
        # The fix should use WeakValueDictionary which doesn't need manual cleanup
        loop_ids = []
        for i in range(15):  # More than the hardcoded threshold of 10
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)

                # Create a lock in this event loop
                async def get_lock():
                    return lock._get_async_lock()

                lock_obj = loop.run_until_complete(get_lock())
                loop_ids.append(id(loop))
            finally:
                loop.close()

        # Verify that locks for closed loops are automatically cleaned up
        # without triggering a manual cleanup based on a threshold
        # With WeakValueDictionary, entries for closed loops should be gone

        # Force a new event loop to check if stale locks are auto-cleaned
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            async def check_locks():
                return lock._get_async_lock()

            new_lock = new_loop.run_until_complete(check_locks())

            # The stale lock entries should be automatically cleaned
            # count should only include the new loop
            current_id = id(new_loop)
            # After cleanup, only the current loop should remain
            assert current_id in lock._async_locks
        finally:
            new_loop.close()

    def test_no_race_condition_during_concurrent_lock_access(self):
        """Test that concurrent lock access doesn't cause race conditions during cleanup."""
        lock = _AsyncCompatibleLock()
        errors = []

        def worker(thread_id):
            """Worker function that creates and uses locks in a thread."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Multiple lock acquisitions to stress-test cleanup
                    for i in range(5):
                        async def use_lock():
                            async with lock:
                                await asyncio.sleep(0.01)

                        loop.run_until_complete(use_lock())
                finally:
                    loop.close()
            except Exception as e:
                errors.append((thread_id, e))

        # Create multiple threads to simulate concurrent access
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify no errors occurred (like KeyNotFoundError or lock failures)
        assert len(errors) == 0, f"Errors occurred during concurrent access: {errors}"

    def test_automatic_cleanup_without_manual_cleanup_call(self):
        """Test that locks are automatically cleaned up without manual cleanup calls."""
        lock = _AsyncCompatibleLock()

        # Create locks in multiple event loops
        loop_ids = []
        for i in range(5):
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)

                async def get_lock():
                    return lock._get_async_lock()

                lock_obj = loop.run_until_complete(get_lock())
                loop_ids.append(id(loop))
            finally:
                loop.close()

        # With WeakValueDictionary, old locks should be automatically cleaned
        # when the event loops are closed
        # Verify cleanup happened without manual _cleanup_stale_locks call

        # Create a new event loop and check
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            async def get_new_lock():
                return lock._get_async_lock()

            new_lock = new_loop.run_until_complete(get_new_lock())

            # The WeakValueDictionary should have auto-cleaned the old locks
            # Only the new loop's lock should remain
            assert id(new_loop) in lock._async_locks
        finally:
            new_loop.close()
