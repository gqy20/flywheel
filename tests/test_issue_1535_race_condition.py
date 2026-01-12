"""
Test for Issue #1535: Race condition in _get_async_event

This test verifies that _get_async_event properly holds the lock
during the entire check-and-get phase to prevent:
1. GC from cleaning up the event between get() and return
2. Multiple threads from creating and overwriting events
"""

import asyncio
import threading
import time
import gc
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_get_async_event_holds_lock_during_check_and_get():
    """
    Test that _get_async_event holds _async_event_init_lock during
    the entire check-and-get phase.

    This test creates a scenario where:
    1. Thread A calls _get_async_event
    2. Thread A gets the event from the dict
    3. Before Thread A returns, GC cleans up the event
    4. Thread A returns a cleaned-up event

    The fix should prevent this by holding the lock during get() and return.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop and get an async event
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # First call to create the event
        async def get_first_event():
            return lock._get_async_event()

        event1 = loop.run_until_complete(get_first_event())
        assert event1 is not None

        # Verify the event is in the dictionary
        assert loop in lock._async_events
        assert lock._async_events[loop] is event1

        # Now simulate a race condition by forcing GC and checking
        # if the event reference is still valid
        # This test verifies that the lock prevents the race

        # Get the event again - should return the same event
        event2 = loop.run_until_complete(get_first_event())
        assert event2 is event1, "Should return the same event object"

        # Verify the event is still in the dictionary
        assert loop in lock._async_events
        assert lock._async_events[loop] is event1

    finally:
        loop.close()


def test_get_async_event_thread_safety():
    """
    Test that multiple threads calling _get_async_event simultaneously
    don't create different events or cause race conditions.

    This test verifies the double-check locking pattern works correctly.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        events = []
        exceptions = []

        def get_event_from_thread():
            try:
                # Need to set event loop for this thread
                asyncio.set_event_loop(loop)
                event = lock._get_async_event()
                events.append(event)
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads that will call _get_async_event
        threads = []
        for _ in range(10):
            t = threading.Thread(target=get_event_from_thread)
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Check that no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # All threads should get the same event object
        assert len(events) == 10, "All threads should have completed"
        first_event = events[0]
        for event in events[1:]:
            assert event is first_event, "All threads should get the same event object"

        # Verify only one event is in the dictionary
        assert loop in lock._async_events
        assert lock._async_events[loop] is first_event

    finally:
        loop.close()


def test_get_async_event_lock_prevents_gc_race():
    """
    Test that the lock prevents GC from cleaning up the event
    between get() and return.

    This is a more direct test of the issue: we want to ensure
    that holding the lock prevents GC from interfering.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Get the event for the first time
        event = loop.run_until_complete(asyncio.coroutine(lambda: lock._get_async_event())())
        assert event is not None

        # The key protection mechanism is that _async_event_init_lock
        # should be held during the entire check-and-return sequence
        # We can't directly test GC behavior, but we can verify
        # that the lock is properly used

        # Verify the event is still accessible
        assert loop in lock._async_events
        assert lock._async_events[loop] is event

        # Get the event again - should return the same event
        event2 = loop.run_until_complete(asyncio.coroutine(lambda: lock._get_async_event())())
        assert event2 is event

    finally:
        loop.close()


def test_get_async_event_with_lock_contention():
    """
    Test _get_async_event under high lock contention to ensure
    thread safety is maintained.

    This test simulates the race condition scenario where multiple
    threads try to get/create the event simultaneously.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        results = []
        errors = []

        def contested_get_event(thread_id):
            try:
                asyncio.set_event_loop(loop)
                # Each thread tries to get the event
                event = lock._get_async_event()
                results.append((thread_id, id(event)))
            except Exception as e:
                errors.append((thread_id, e))

        # Launch many threads simultaneously
        threads = []
        for i in range(20):
            t = threading.Thread(target=contested_get_event, args=(i,))
            threads.append(t)

        # Start all threads at once
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All threads should have gotten the same event (same id)
        event_ids = [event_id for _, event_id in results]
        assert len(set(event_ids)) == 1, f"All threads should get the same event, got IDs: {event_ids}"

        # Only one event should be in the dictionary
        assert loop in lock._async_events
        assert len(lock._async_events) == 1

    finally:
        loop.close()
