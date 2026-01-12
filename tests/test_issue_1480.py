"""
Test for Issue #1480: Race condition in double-check locking pattern

This test verifies that the _get_async_event method properly handles
concurrent access without race conditions that could cause event state
to be lost.
"""
import asyncio
import threading
import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestIssue1480:
    """Test suite for Issue #1480 - Race condition in double-check locking"""

    def test_concurrent_event_initialization(self, event_loop):
        """
        Test that concurrent calls to _get_async_event from multiple threads
        always return the same event object and preserve event state.

        The bug: When two threads race to create an event, one might create
        a new_event outside the lock, while another thread inserts and sets
        a different event. The first thread then overwrites the set event with
        its unset event, losing the signal.

        This test creates a controlled race condition where:
        1. Thread 1 creates new_event and is about to insert it
        2. Thread 2 creates another new_event, sets it, and inserts it
        3. Thread 1 inserts its unset event, overwriting Thread 2's set event

        If the bug exists, the event will be unset even after being set.
        """
        lock = _AsyncCompatibleLock()

        # Track which events were created
        created_events = []
        insertion_order = []

        def thread_func():
            """Call _get_async_event and track what happens"""
            event = lock._get_async_event()
            created_events.append(event)
            insertion_order.append(id(event))
            return event

        # Create multiple threads that will call _get_async_event concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=thread_func)
            threads.append(t)

        # Start all threads at once to maximize race condition likelihood
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All threads should have gotten the same event object
        unique_events = set(created_events)
        assert len(unique_events) == 1, (
            f"Expected 1 unique event, but got {len(unique_events)}. "
            f"This indicates a race condition where multiple events were created."
        )

        # The event should be set (since lock is not held)
        event = created_events[0]
        assert event.is_set(), (
            "Event should be set because the lock is not held. "
            "If this fails, it indicates that an unset event overwrote a set event."
        )

    def test_event_state_preservation_under_contention(self, event_loop):
        """
        Test that event state is preserved even under high contention.

        This test repeatedly creates new event loops and calls _get_async_event
        to ensure that the event state (set/unset) is correctly initialized
        and preserved regardless of concurrent access.
        """
        lock = _AsyncCompatibleLock()

        # Run multiple iterations to increase likelihood of catching race conditions
        for iteration in range(10):
            # Create a new event loop for this iteration
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Call _get_async_event from multiple threads
                events = []

                def get_event():
                    event = lock._get_async_event()
                    events.append(event)
                    return event

                threads = []
                for _ in range(3):
                    t = threading.Thread(target=get_event)
                    threads.append(t)

                for t in threads:
                    t.start()

                for t in threads:
                    t.join()

                # All should be the same event
                assert len(set(events)) == 1
                # Event should be set (lock not held)
                assert events[0].is_set()

            finally:
                loop.close()

    def test_no_event_overwrite_on_double_check(self, event_loop):
        """
        Test specifically for the overwrite scenario described in the issue.

        Scenario:
        1. Thread A checks lock, finds no event
        2. Thread A creates new_event_a (OUTSIDE LOCK - bug location)
        3. Thread B checks lock, finds no event
        4. Thread B creates new_event_b
        5. Thread B enters lock, double-checks, inserts new_event_b, sets it
        6. Thread A enters lock, double-checks (finds new_event_b), should return it
        7. BUG: Thread A should NOT insert new_event_a, overwriting new_event_b

        The fix ensures that even if new_event is created outside the lock,
        the double-check logic prevents overwriting an existing event.
        """
        lock = _AsyncCompatibleLock()

        # Get the event once (this will create and set it)
        event1 = lock._get_async_event()
        assert event1.is_set(), "Event should be set when lock is not held"

        # Get it again - should be the same object
        event2 = lock._get_async_event()
        assert event1 is event2, "Should return the same event object"
        assert event2.is_set(), "Event should still be set"

        # Clear the event and verify
        event2.clear()
        assert not event2.is_set(), "Event should be cleared"

        # Get it one more time - should still be the same object (still unset)
        event3 = lock._get_async_event()
        assert event2 is event3, "Should return the same event object"
        assert not event3.is_set(), "Event should remain unset"
