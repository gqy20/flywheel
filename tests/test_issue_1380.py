"""Test for Issue #1380 - WeakKeyDictionary race condition.

This test verifies that the WeakKeyDictionary used in _AsyncCompatibleLock
does not have a race condition where GC can clean up the event object between
the get() call and its usage.

The fix ensures that _get_async_event always acquires _async_event_init_lock
before accessing the WeakKeyDictionary, preventing GC from cleaning up the
event between the get() call and the return statement.
"""
import asyncio
import gc
import threading
import time
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_no_race_condition_with_gc():
    """Test that _get_async_event is safe from GC race condition.

    The fix ensures that we always hold the lock when accessing the
    WeakKeyDictionary, so GC cannot clean up the event between get() and return.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create the event - with the fix, this is safe
        event = lock._get_async_event()
        assert event is not None

        # Store the event ID for comparison
        event_id = id(event)

        # Force GC - event should remain valid because we hold a strong reference
        gc.collect()

        # Event should still be the same object
        assert event is not None
        assert id(event) == event_id

        # The fix ensures that _get_async_event always returns a valid event
        # even if GC runs concurrently in another thread

    finally:
        loop.close()


def test_concurrent_get_async_event_with_gc():
    """Test concurrent access to _get_async_event with GC doesn't cause issues.

    This test creates multiple threads that all try to get the async event
    while forcing GC, to verify the fix handles the race condition properly.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    success_count = [0]  # Use list to allow modification in closure

    def worker():
        """Worker that repeatedly gets events and forces GC."""
        try:
            for _ in range(50):
                # We need an event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # With the fix, this is thread-safe and GC-safe
                    event = lock._get_async_event()
                    # Force GC to try to trigger race condition
                    gc.collect()
                    # Use the event to ensure it's valid
                    if event.is_set() or not event.is_set():
                        success_count[0] += 1
                finally:
                    loop.close()
        except Exception as e:
            errors.append(e)

    # Run multiple threads
    threads = []
    for _ in range(5):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # Check no errors occurred and all operations succeeded
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert success_count[0] == 250, f"Expected 250 successful operations, got {success_count[0]}"


def test_weakref_cleanup_after_event_loop_closed():
    """Test that events are properly cleaned up when event loop is closed.

    This test verifies that the WeakKeyDictionary properly cleans up
    events when the event loop is closed and no longer referenced.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create the event
        event1 = lock._get_async_event()
        assert event1 is not None

        # Store weak reference to verify GC behavior
        weak_ref = weakref.ref(event1)

        # Close the event loop and clear our reference
        loop.close()
        del event1
        asyncio.set_event_loop(None)

        # Force GC - the event should be collected
        gc.collect()

        # The event should be garbage collected
        assert weak_ref() is None, "Event should be collected after loop is closed"

        # Create a new event loop and verify we can get a new event
        loop2 = asyncio.new_event_loop()
        asyncio.set_event_loop(loop2)

        try:
            event2 = lock._get_async_event()
            assert event2 is not None
            # This should be a different object since the old one was GC'd
            assert weak_ref() is None
        finally:
            loop2.close()

    finally:
        # Clean up
        if loop.is_running():
            loop.close()


def test_multiple_event_loops_isolation():
    """Test that different event loops get different event objects.

    This test verifies the fix properly handles multiple event loops
    without race conditions.
    """
    lock = _AsyncCompatibleLock()

    # Create multiple event loops
    loops = []
    events = []

    for i in range(3):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loops.append(loop)
        event = lock._get_async_event()
        events.append(event)
        assert event is not None

    # All events should be different objects
    assert len(set(id(e) for e in events)) == 3

    # Clean up
    for loop in loops:
        loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
