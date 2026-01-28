"""
Test for Issue #1476: Potential deadlock risk in _get_async_event

This test verifies that the _get_async_event method is thread-safe and
handles concurrent access correctly without race conditions.
"""
import asyncio
import threading
import weakref
from unittest.mock import patch

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1476:
    """Test suite for Issue #1476 - Potential deadlock risk."""

    def test_concurrent_event_creation_no_race_condition(self):
        """
        Test that concurrent calls to _get_async_event don't create
        duplicate events due to race conditions.

        This test verifies the fix for Issue #1476 which identified
        a 'Check-Then-Act' pattern that could be unsafe in concurrent
        environments.
        """
        lock = _AsyncCompatibleLock()
        events = []

        async def get_event():
            """Get the async event and store it."""
            event = lock._get_async_event()
            events.append(event)
            return event

        async def concurrent_access():
            """Simulate concurrent access from multiple coroutines."""
            # Create multiple tasks that will try to get the event
            tasks = [get_event() for _ in range(10)]
            await asyncio.gather(*tasks)

        # Run the concurrent access
        asyncio.run(concurrent_access())

        # All events should be the same (no duplicates created)
        assert len(events) == 10
        first_event = events[0]
        assert all(event is first_event for event in events), \
            "All events should be the same object"

    def test_event_initialization_with_double_check(self):
        """
        Test that the double-check pattern works correctly.

        This verifies that after checking for an existing event, creating
        a new one, and checking again before insertion, we don't create
        duplicate events.
        """
        lock = _AsyncCompatibleLock()

        async def test_double_check():
            # Get the first event
            event1 = lock._get_async_event()

            # Manually clear the events dict to simulate a race condition
            # where another thread might have created an event
            current_loop = asyncio.get_running_loop()
            lock._async_events.clear()

            # Get the event again - should create a new one
            event2 = lock._get_async_event()

            # Both should be valid Event objects
            assert isinstance(event1, asyncio.Event)
            assert isinstance(event2, asyncio.Event)

            # They might be different objects due to our manual clear,
            # but getting the event again should return event2
            event3 = lock._get_async_event()
            assert event3 is event2, "Should return the existing event"

        asyncio.run(test_double_check())

    def test_weakkeydictionary_cleanup_during_get(self):
        """
        Test that the method handles WeakKeyDictionary cleanup gracefully.

        WeakKeyDictionary can have entries removed at any time due to garbage
        collection. This test ensures the code handles this correctly.
        """
        lock = _AsyncCompatibleLock()

        async def test_gc_during_get():
            # Create an event loop and get its event
            loop = asyncio.get_running_loop()
            event1 = lock._get_async_event()

            # Verify it's stored
            assert loop in lock._async_events

            # Simulate GC by removing the loop reference
            # (In real scenario, the loop object would be garbage collected)
            del loop

            # Getting the event again should work fine
            event2 = lock._get_async_event()
            assert isinstance(event2, asyncio.Event)

        asyncio.run(test_gc_during_get())

    def test_no_lock_held_during_event_creation(self):
        """
        Test that the lock is NOT held during event creation.

        This is important to prevent potential deadlocks as mentioned
        in Issue #1470. The Event should be created outside the lock.
        """
        lock = _AsyncCompatibleLock()

        # Track if the lock is held during Event creation
        lock_held_during_creation = []

        original_event_init = asyncio.Event.__init__

        def patched_event_init(self, *args, **kwargs):
            """Check if lock is held during Event creation."""
            lock_held_during_creation.append(lock._async_event_init_lock.locked())
            return original_event_init(self, *args, **kwargs)

        async def test_lock_not_held():
            with patch.object(asyncio.Event, '__init__', patched_event_init):
                lock._get_async_event()

        asyncio.run(test_lock_not_held())

        # Assert that lock was NOT held during Event creation
        assert len(lock_held_during_creation) > 0, "Event should have been created"
        assert not any(lock_held_during_creation), \
            "Lock should not be held during Event creation to prevent deadlock"

    def test_thread_safety_of_event_init(self):
        """
        Test that event initialization is thread-safe.

        Multiple threads should be able to safely call _get_async_event
        without creating race conditions.
        """
        lock = _AsyncCompatibleLock()
        events = []
        exceptions = []

        def get_event_in_thread():
            """Get event from a thread using asyncio.run."""
            try:
                async def get_it():
                    return lock._get_async_event()

                event = asyncio.run(get_it())
                events.append(event)
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads
        threads = [
            threading.Thread(target=get_event_in_thread)
            for _ in range(5)
        ]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Should have no exceptions
        assert len(exceptions) == 0, f"Got exceptions: {exceptions}"

        # All events should be valid (might be different due to different event loops)
        assert len(events) == 5
        assert all(isinstance(e, asyncio.Event) for e in events)

    def test_check_act_pattern_safety(self):
        """
        Test that the check-act pattern is safe.

        This test specifically addresses Issue #1476's concern about
        the 'Check-Then-Act' pattern being unsafe in concurrent environments.
        The fix uses double-check locking to ensure safety.
        """
        lock = _AsyncCompatibleLock()

        async def simulate_race():
            """
            Simulate a potential race condition by manually checking
            and creating events.
            """
            # First call
            event1 = lock._get_async_event()

            # Verify it's in the dict
            current_loop = asyncio.get_running_loop()
            assert current_loop in lock._async_events

            # Second call should return the same event
            event2 = lock._get_async_event()

            # They should be the same object (no duplicate created)
            assert event1 is event2, \
                "Should return existing event, not create a new one"

            # Should only have one entry in the dict
            assert len(lock._async_events) == 1

        asyncio.run(simulate_race())

    def test_event_thread_safety_under_high_contention(self):
        """
        Test thread safety under high contention.

        This stress test specifically targets Issue #1476's concern about
        the 'Check-Then-Act' pattern. Under high contention, if the pattern
        is not correctly implemented, we could see duplicate events created.
        """
        lock = _AsyncCompatibleLock()
        events_set = set()
        errors = []

        async def get_and_track_event():
            """Get event and track unique instances."""
            try:
                event = lock._get_async_event()
                # Track by id to detect different instances
                events_set.add(id(event))
                return event
            except Exception as e:
                errors.append(e)
                raise

        async def high_contention_test():
            """Run many concurrent accesses."""
            # Create 100 concurrent tasks
            tasks = [get_and_track_event() for _ in range(100)]
            await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.run(high_contention_test())

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Should only have ONE unique event (all ids should be the same)
        assert len(events_set) == 1, \
            f"Expected 1 unique event, but got {len(events_set)}. " \
            "This indicates a race condition in event creation."
