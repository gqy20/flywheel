"""Tests for Issue #1470 - Potential deadlock in _get_async_event

The issue is that creating asyncio.Event() and calling set() while holding
_async_event_init_lock could cause deadlock.
"""

import asyncio
import threading
import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestIssue1470:
    """Test that _get_async_event doesn't cause deadlock."""

    @pytest.mark.asyncio
    async def test_get_async_event_no_deadlock_with_concurrent_calls(self):
        """Test that concurrent calls to _get_async_event don't deadlock.

        This test creates multiple event loops and tries to initialize async events
        concurrently to ensure there's no deadlock when holding _async_event_init_lock.
        """
        lock = _AsyncCompatibleLock()

        # Helper function to get async event in a thread with its own event loop
        def get_event_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Get event from within the event loop
                event = lock._get_async_event()
                return event.is_set()
            finally:
                loop.close()

        # Create multiple threads that will each create their own event loop
        # and call _get_async_event concurrently
        threads = []
        results = []

        for _ in range(5):
            result_container = [None]

            def thread_func():
                result_container[0] = get_event_in_thread()

            t = threading.Thread(target=thread_func)
            threads.append((t, result_container))
            t.start()

        # Wait for all threads to complete
        for t, _ in threads:
            t.join(timeout=5)

        # Collect results
        for _, result_container in threads:
            results.append(result_container[0])

        # All threads should have completed without deadlock
        assert len(results) == 5
        # Each result should be a boolean (event state)
        for result in results:
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_async_event_with_lock_held(self):
        """Test _get_async_event when the lock is already held.

        This ensures that creating and setting the Event doesn't block
        even when _async_event_init_lock is held.
        """
        lock = _AsyncCompatibleLock()

        # Acquire the main lock first
        with lock._lock:
            # Now try to get async event
            # This should work without deadlock even though _lock is held
            event = lock._get_async_event()

            # Event should not be set since lock is held
            assert not event.is_set()

        # After releasing lock, we can verify the event was created
        assert event is not None

    @pytest.mark.asyncio
    async def test_get_async_event_without_lock_held(self):
        """Test _get_async_event when no lock is held.

        Event should be set immediately since lock is available.
        """
        lock = _AsyncCompatibleLock()
        event = lock._get_async_event()

        # Event should be set since lock is not held
        assert event.is_set()

    @pytest.mark.asyncio
    async def test_multiple_get_async_event_calls_same_loop(self):
        """Test that multiple calls to _get_async_event return the same event.

        This verifies the caching behavior works correctly.
        """
        lock = _AsyncCompatibleLock()

        event1 = lock._get_async_event()
        event2 = lock._get_async_event()
        event3 = lock._get_async_event()

        # All should return the same Event object
        assert event1 is event2
        assert event2 is event3

        # And should be set since lock is not held
        assert event1.is_set()
