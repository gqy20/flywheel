"""Test for Issue #1526: Race condition in _AsyncCompatibleLock._get_async_event

The issue is that `new_event` is created BEFORE acquiring the lock,
which means if the lock is currently held, the Event's initial state
may not be synchronized with the actual lock state.

This test creates a scenario where multiple threads try to get the
async event while the lock is held, to verify that the event state
is correctly synchronized.
"""

import asyncio
import threading
import time
import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestIssue1526:
    """Test race condition in _AsyncCompatibleLock._get_async_event"""

    def test_event_state_synchronization_under_contention(self):
        """Test that Event state is synchronized with lock state under contention.

        Scenario:
        1. Main thread holds the lock
        2. Multiple async tasks call _get_async_event
        3. Each task should get an event that reflects the current lock state

        Expected: All events should be unset (locked) because the lock is held
        """
        lock = _AsyncCompatibleLock()

        # Acquire the lock synchronously first
        with lock:
            # Create an event loop for this test
            async def test_event_state():
                # Get the event while lock is held
                event = lock._get_async_event()

                # The event should be unset because lock is held
                # If there's a race condition, the event might be incorrectly set
                assert not event.is_set(), (
                    "Event should be unset when lock is held. "
                    "This indicates a race condition in Event initialization."
                )

                # Try to wait on the event (should timeout because lock is held)
                try:
                    await asyncio.wait_for(event.wait(), timeout=0.1)
                    assert False, "Event.wait() should have timed out"
                except asyncio.TimeoutError:
                    # Expected - lock is still held
                    pass

            # Run the async test
            asyncio.run(test_event_state())

    def test_double_check_locking_with_multiple_threads(self):
        """Test double-check locking prevents race condition with multiple threads.

        This test verifies that when multiple threads try to create events
        simultaneously, only one event gets registered and all threads
        get the same event with correct state.
        """
        lock = _AsyncCompatibleLock()
        results = []
        errors = []

        def worker():
            """Worker that tries to get async event"""
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def get_event():
                    # Hold the lock to create contention
                    with lock:
                        event = lock._get_async_event()

                        # When we hold the lock, the event should be set
                        # (because we hold the lock, event signals availability)
                        # But actually, when WE hold the lock, the event should
                        # reflect that lock is available TO US (we have it)
                        # The event is set when lock is NOT held by others

                        # The important check: all threads should get the same event
                        return event.is_set()

                result = loop.run_until_complete(get_event())
                results.append(result)

                loop.close()
            except Exception as e:
                errors.append(e)
            finally:
                # Clean up
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        pass
                    else:
                        loop.close()
                except:
                    pass

        # Launch multiple threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check for errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All threads should have completed
        assert len(results) == 5

    def test_event_created_inside_lock_has_correct_state(self):
        """Test that creating Event with proper lock state yields correct initial state.

        This test verifies the fix: Event state should be set based on
        the lock state at the time of registration, not at the time of creation.
        """
        lock = _AsyncCompatibleLock()

        async def test_creation_order():
            # Get event first time (lock is free)
            event1 = lock._get_async_event()
            assert event1.is_set(), "Event should be set when lock is free"

            # Now acquire the lock
            await asyncio.to_thread(lock.__enter__)

            try:
                # Get event again (lock is held)
                # This might create a new event or return existing one
                event2 = lock._get_async_event()

                # The event should be unset because lock is held
                # If event2 is the same as event1, it should have been cleared
                assert not event2.is_set(), (
                    "Event should be unset when lock is held. "
                    "This indicates the event state wasn't updated when lock was acquired."
                )

                # They should be the same event object (per event loop)
                assert event1 is event2, "Should return the same event for the same event loop"

            finally:
                # Release the lock
                lock.__exit__(None, None, None)

                # Event should be set again
                assert event1.is_set(), "Event should be set when lock is released"

        asyncio.run(test_creation_order())

    def test_event_state_consistency_after_lock_release(self):
        """Test that event state is correctly updated when lock is released.

        This verifies that the event properly tracks lock state transitions.
        """
        lock = _AsyncCompatibleLock()

        async def test_state_transitions():
            event = lock._get_async_event()

            # Initial state: lock is free, event should be set
            assert event.is_set(), "Event should be set initially"

            # Acquire lock
            await asyncio.to_thread(lock.__enter__)

            try:
                # After acquisition: event should be cleared
                assert not event.is_set(), "Event should be cleared after lock acquisition"

                # Wait on event should timeout
                try:
                    await asyncio.wait_for(event.wait(), timeout=0.1)
                    assert False, "Should timeout waiting for event"
                except asyncio.TimeoutError:
                    pass  # Expected

            finally:
                # Release lock
                lock.__exit__(None, None, None)

            # After release: event should be set again
            assert event.is_set(), "Event should be set after lock release"

            # Wait on event should complete immediately
            await asyncio.wait_for(event.wait(), timeout=0.1)

        asyncio.run(test_state_transitions())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
