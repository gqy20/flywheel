"""Test explicit cleanup of asyncio.Event objects in _AsyncCompatibleLock.

This test verifies the enhancement requested in Issue #1493:
- Add a cleanup_loop(loop) method to explicitly remove Event objects
- Test that the method properly cleans up events for closed event loops
- Ensure the cleanup is thread-safe and doesn't interfere with active loops
"""

import asyncio
import threading
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncEventCleanupIssue1493:
    """Test explicit cleanup of asyncio.Event objects (Issue #1493)."""

    def test_cleanup_loop_method_exists(self):
        """Test that cleanup_loop method exists on _AsyncCompatibleLock."""
        lock = _AsyncCompatibleLock()
        assert hasattr(lock, 'cleanup_loop'), (
            "_AsyncCompatibleLock should have cleanup_loop method"
        )
        assert callable(lock.cleanup_loop), (
            "cleanup_loop should be a callable method"
        )

    async def test_cleanup_loop_removes_event(self):
        """Test that cleanup_loop removes event for specific loop."""
        lock = _AsyncCompatibleLock()
        loop = asyncio.get_running_loop()

        # Create an event by using async context
        async with lock:
            # Event should be created now
            assert loop in lock._async_events, (
                "Event should be created after async context usage"
            )

        # Cleanup the loop
        lock.cleanup_loop(loop)

        # Event should be removed
        assert loop not in lock._async_events, (
            "Event should be removed after cleanup_loop is called"
        )

    async def test_cleanup_loop_with_nonexistent_loop(self):
        """Test that cleanup_loop handles nonexistent loops gracefully."""
        lock = _AsyncCompatibleLock()

        # Create a dummy loop that's not in the dictionary
        dummy_loop = asyncio.new_event_loop()
        try:
            # Should not raise an exception
            lock.cleanup_loop(dummy_loop)
        finally:
            dummy_loop.close()

    async def test_cleanup_loop_multiple_times(self):
        """Test that cleanup_loop can be called multiple times safely."""
        lock = _AsyncCompatibleLock()
        loop = asyncio.get_running_loop()

        # Create an event
        async with lock:
            pass

        # Cleanup multiple times - should not raise
        lock.cleanup_loop(loop)
        lock.cleanup_loop(loop)
        lock.cleanup_loop(loop)

    async def test_cleanup_loop_does_not_affect_other_loops(self):
        """Test that cleanup_loop for one loop doesn't affect other loops."""
        lock = _AsyncCompatibleLock()
        current_loop = asyncio.get_running_loop()

        # Create event in current loop
        async with lock:
            pass

        # Create another loop and use it
        other_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(other_loop)
            async def use_lock_in_other_loop():
                async with lock:
                    pass
            await other_loop.run_until_complete(use_lock_in_other_loop())

            # Both loops should have events
            assert current_loop in lock._async_events
            assert other_loop in lock._async_events

            # Cleanup current loop
            lock.cleanup_loop(current_loop)

            # Only current loop should be removed
            assert current_loop not in lock._async_events
            assert other_loop in lock._async_events
        finally:
            other_loop.close()
            asyncio.set_event_loop(current_loop)

    async def test_cleanup_loop_with_weakref_fallback(self):
        """Test that cleanup_loop complements WeakKeyDictionary garbage collection."""
        lock = _AsyncCompatibleLock()

        # Create event and cleanup explicitly
        loop = asyncio.get_running_loop()
        async with lock:
            pass

        # Explicit cleanup
        lock.cleanup_loop(loop)

        # Even without explicit cleanup, WeakKeyDictionary would handle this
        # but explicit cleanup is more predictable
        assert loop not in lock._async_events

    def test_cleanup_loop_thread_safety(self):
        """Test that cleanup_loop is thread-safe."""
        lock = _AsyncCompatibleLock()
        results = []
        errors = []

        def cleanup_in_thread():
            """Cleanup a loop from a different thread."""
            try:
                # Create a new event loop in this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Use the lock in this loop
                    async def use_lock():
                        async with lock:
                            await asyncio.sleep(0.01)
                    loop.run_until_complete(use_lock())

                    # Verify event exists
                    assert loop in lock._async_events

                    # Cleanup
                    lock.cleanup_loop(loop)
                    results.append(True)
                finally:
                    loop.close()
            except Exception as e:
                errors.append(e)

        # Run in multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=cleanup_in_thread)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

    async def test_async_lock_still_works_after_cleanup(self):
        """Test that async lock functionality still works after cleanup."""
        lock = _AsyncCompatibleLock()
        loop = asyncio.get_running_loop()

        # Use lock and cleanup
        async with lock:
            pass

        lock.cleanup_loop(loop)

        # Lock should still work - new event should be created
        async with lock:
            # Event should be recreated
            assert loop in lock._async_events
