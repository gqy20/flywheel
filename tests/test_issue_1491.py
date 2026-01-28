"""Test for Issue #1491 - asyncio.Event creation should happen outside lock.

This test verifies that the asyncio.Event() object is created outside
the threading.Lock to prevent potential deadlock when the event loop
is not running or is in a paused state.
"""
import asyncio
import threading
import time

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_asyncio_event_created_outside_lock():
    """Test that asyncio.Event is created outside the lock.

    This test verifies the fix for Issue #1491 which moves the
    asyncio.Event() creation outside the _async_event_init_lock
    to prevent potential deadlock.
    """
    lock = _AsyncCompatibleLock()

    # Track if Event creation was attempted inside the lock
    event_creation_inside_lock = []
    original_event_init = asyncio.Event.__init__

    def patched_event_init(self):
        # Check if we're holding the async_event_init_lock
        if lock._async_event_init_lock.locked():
            event_creation_inside_lock.append(True)
        original_event_init(self)

    # Patch asyncio.Event.__init__ to track creation timing
    asyncio.Event.__init__ = patched_event_init

    try:
        # Create an async context to trigger Event creation
        async def create_event():
            return lock._get_async_event()

        # Run in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            event = loop.run_until_complete(create_event())

            # Verify that Event was NOT created while holding the lock
            assert len(event_creation_inside_lock) == 0, (
                "asyncio.Event() was created inside _async_event_init_lock. "
                "This violates the fix for Issue #1491."
            )

            # Verify the event works correctly
            assert isinstance(event, asyncio.Event)
        finally:
            loop.close()
    finally:
        # Restore original __init__
        asyncio.Event.__init__ = original_event_init


def test_no_deadlock_with_multiple_threads():
    """Test that multiple threads can safely create events without deadlock.

    This test ensures that moving Event creation outside the lock doesn't
    introduce race conditions or deadlocks.
    """
    lock = _AsyncCompatibleLock()
    results = []
    errors = []

    def worker(thread_id):
        """Worker function that creates an async event in each thread."""
        try:
            # Each thread needs its own event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def get_event():
                return lock._get_async_event()

            try:
                event = loop.run_until_complete(get_event())
                results.append((thread_id, id(event)))
            finally:
                loop.close()
        except Exception as e:
            errors.append((thread_id, e))

    # Create multiple threads to simulate concurrent access
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=5)

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify all threads got an event
    assert len(results) == 5, f"Not all threads completed: {len(results)}/5"


def test_event_state_consistency():
    """Test that Event state remains consistent with the fix.

    This ensures that moving Event creation outside the lock doesn't
    break the initial state synchronization with the lock.
    """
    lock = _AsyncCompatibleLock()

    async def verify_event_state():
        # Get event when lock is not held
        event1 = lock._get_async_event()

        # Event should be set because lock is not held
        assert event1.is_set(), "Event should be set when lock is not held"

        # Acquire the lock
        await lock.acquire_async()

        try:
            # Get a new event reference while lock is held
            event2 = lock._get_async_event()

            # Event should be cleared because lock is held
            assert not event2.is_set(), "Event should be cleared when lock is held"
        finally:
            await lock.release_async()

        # After release, event should be set again
        event3 = lock._get_async_event()
        assert event3.is_set(), "Event should be set after lock release"

        # All should be the same event object
        assert event1 is event2 is event3, "Should return the same event object"

    # Run the test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(verify_event_state())
    finally:
        loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
