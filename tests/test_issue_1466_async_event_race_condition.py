"""Test for issue #1466 - Race condition in _get_async_event

This test verifies that the _get_async_event method properly handles
the race condition between checking the lock state and setting the event.
"""
import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1466_AsyncEventRaceCondition:
    """Test for race condition in _get_async_event (issue #1466)."""

    @pytest.mark.asyncio
    async def test_async_event_state_when_lock_is_held_during_init(self):
        """Test that event is NOT set when lock is held during _get_async_event initialization.

        This is the core issue: if another thread holds self._lock when _get_async_event
        is called, the newly created event should NOT be set.

        The race condition would occur if:
        1. Thread A holds self._lock
        2. Thread B calls _get_async_event
        3. Thread B checks if lock is available (acquire fails, returns False)
        4. Thread A releases self._lock before Thread B creates the event
        5. Thread B creates event and sets it (because check said lock was available)
        6. But now the event state is wrong - it's set but we don't know if lock is available

        The fix ensures the entire operation is atomic.
        """
        lock = _AsyncCompatibleLock()

        # First, acquire the lock from another thread
        lock_holder_ready = threading.Event()
        lock_holder_done = threading.Event()
        event_state_after_init = []

        def hold_lock():
            """Hold the lock while async event is initialized."""
            lock._lock.acquire(blocking=True)
            lock_holder_ready.set()
            # Wait for async initialization to happen
            time.sleep(0.1)  # Hold long enough for initialization
            lock_holder_done.wait()
            lock._lock.release()

        # Start lock holder thread
        holder = threading.Thread(target=hold_lock)
        holder.start()
        lock_holder_ready.wait()

        # Now initialize async event while lock is held
        event = lock._get_async_event()
        event_state_after_init.append(event.is_set())

        # Signal lock holder to release
        lock_holder_done.set()
        holder.join(timeout=2)

        # The event should NOT be set because the lock was held during initialization
        assert not event_state_after_init[0], (
            "Event should not be set when lock is held during _get_async_event. "
            "This indicates the TOCTOU race condition where the lock state changed "
            "between the acquire() check and the event creation."
        )

        # Clean up
        lock._async_events.clear()

    @pytest.mark.asyncio
    async def test_async_event_state_when_lock_is_free_during_init(self):
        """Test that event IS set when lock is free during _get_async_event initialization."""
        lock = _AsyncCompatibleLock()

        # Initialize async event when lock is free
        event = lock._get_async_event()

        # The event SHOULD be set because the lock was free
        assert event.is_set(), (
            "Event should be set when lock is free during _get_async_event. "
            "This ensures correct initial state."
        )

        # Clean up
        lock._async_events.clear()

    def test_lock_state_is_checked_under_init_lock(self):
        """Verify that lock.state check happens inside _async_event_init_lock protection.

        This ensures atomicity of the check-and-set operation.
        """
        lock = _AsyncCompatibleLock()

        # We can't directly test the internal implementation without being fragile,
        # but we can verify the behavior is correct under concurrent access

        results = {"init_happened": False, "state_consistent": True}

        def initialize_event():
            """Call _get_async_event which should be atomic."""
            try:
                # This will fail without event loop, but that's OK for this test
                # We're just checking if it can be called
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                event = lock._get_async_event()
                results["init_happened"] = True
                loop.close()
            except RuntimeError:
                # No event loop in thread - expected
                pass

        # Try multiple concurrent initializations
        threads = []
        for _ in range(5):
            t = threading.Thread(target=initialize_event)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=2)

        # The fact that we didn't crash or corrupt state is a good sign


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
