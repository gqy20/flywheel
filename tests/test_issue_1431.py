"""Test for Issue #1431: __exit__ should signal events while holding _async_event_init_lock

This test verifies that __exit__ method properly acquires _async_event_init_lock
before iterating over _async_events to prevent race conditions.
"""
import asyncio
import threading
import pytest
import time
from flywheel.storage import _AsyncCompatibleLock


def _get_async_event_for_lock(lock, loop):
    """Helper function to get or create event for a specific loop."""
    existing = lock._async_events.get(loop)
    if existing is not None:
        return existing

    with lock._async_event_init_lock:
        existing = lock._async_events.get(loop)
        if existing is not None:
            return existing
        new_event = asyncio.Event(loop=loop)
        lock._async_events[loop] = new_event
        return new_event


def test_exit_should_hold_async_event_init_lock_during_iteration():
    """Test that __exit__ holds _async_event_init_lock while iterating over _async_events.

    This test verifies the fix for Issue #1431. The __exit__ method should acquire
    _async_event_init_lock before iterating over _async_events to prevent race
    conditions where another thread might modify the dictionary during iteration.

    The current implementation fails this test because it iterates over
    self._async_events without holding _async_event_init_lock.
    """
    lock = _AsyncCompatibleLock()
    race_detected = [False]
    iteration_started = threading.Event()
    iteration_completed = threading.Event()
    thread_started = threading.Event()

    # Create an event loop and associated event
    loop = asyncio.new_event_loop()
    event = _get_async_event_for_lock(lock, loop)
    event.clear()

    # Monkey-patch the __exit__ method to detect the race
    original_exit = lock.__exit__

    def patched_exit(exc_type, exc_val, exc_tb):
        # Signal that iteration is about to start
        iteration_started.set()

        # Small delay to allow the other thread to try accessing _async_events
        time.sleep(0.01)

        # Check if _async_event_init_lock is held during iteration
        is_lock_held = lock._async_event_init_lock.locked()

        # Call original implementation
        result = original_exit(exc_type, exc_val, exc_tb)

        iteration_completed.set()

        if not is_lock_held:
            race_detected[0] = True

        return result

    lock.__exit__ = patched_exit

    # Thread that tries to modify _async_events during __exit__
    def try_modify_events_during_exit():
        thread_started.set()
        # Wait for iteration to start
        iteration_started.wait(timeout=2)

        # Try to acquire _async_event_init_lock and add a new event
        # If the __exit__ method holds the lock properly, this will block
        # until __exit__ completes. If not, this will run concurrently
        # with the iteration, potentially causing a race condition.
        acquired = lock._async_event_init_lock.acquire(timeout=0.001)

        if acquired:
            # If we acquired the lock immediately, it means __exit__ wasn't holding it
            try:
                # Create a new event loop and event
                new_loop = asyncio.new_event_loop()
                new_event = asyncio.Event(loop=new_loop)
                lock._async_events[new_loop] = new_event
            finally:
                lock._async_event_init_lock.release()

    # Start the thread
    thread = threading.Thread(target=try_modify_events_during_exit)
    thread.start()
    thread_started.wait(timeout=1)

    # Enter and exit the lock
    with lock:
        pass

    # Wait for thread to complete
    thread.join(timeout=2)
    iteration_completed.wait(timeout=2)

    # Clean up
    loop.close()

    # This assertion should fail with the current implementation
    # because __exit__ doesn't hold _async_event_init_lock during iteration
    assert not race_detected[0], \
        "Race condition detected: __exit__ did not hold _async_event_init_lock " \
        "while iterating over _async_events"


def test_exit_prevents_runtime_error_during_iteration():
    """Test that __exit__ prevents RuntimeError when _async_events is modified during iteration.

    Without holding _async_event_init_lock, concurrent modifications to _async_events
    can cause RuntimeError: dictionary changed size during iteration.
    """
    lock = _AsyncCompatibleLock()
    errors = []

    # Create initial event
    loop1 = asyncio.new_event_loop()
    event1 = _get_async_event_for_lock(lock, loop1)
    event1.clear()

    # Thread that tries to modify _async_events during __exit__
    def modify_events_during_exit():
        for _ in range(100):
            try:
                new_loop = asyncio.new_event_loop()
                with lock._async_event_init_lock:
                    new_event = asyncio.Event(loop=new_loop)
                    lock._async_events[new_loop] = new_event
                time.sleep(0.001)
            except Exception as e:
                errors.append(e)

    thread = threading.Thread(target=modify_events_during_exit)
    thread.start()

    # Perform multiple enter/exit cycles
    for _ in range(50):
        with lock:
            pass

    thread.join(timeout=3)

    # Clean up
    loop1.close()

    # Check if any RuntimeError occurred
    runtime_errors = [e for e in errors if isinstance(e, RuntimeError)]
    assert len(runtime_errors) == 0, \
        f"RuntimeError detected during iteration: {runtime_errors}"


def test_exit_signals_events_correctly():
    """Test that __exit__ correctly signals all events."""
    lock = _AsyncCompatibleLock()

    # Create multiple event loops with events
    event_loops = []
    events = []

    for _ in range(3):
        loop = asyncio.new_event_loop()
        event_loops.append(loop)
        events.append(_get_async_event_for_lock(lock, loop))

    # Set all events to unset state
    for event in events:
        event.clear()

    # Enter and exit the context
    with lock:
        pass

    # Verify all events were signaled
    for event in events:
        assert event.is_set(), "All events should be set after __exit__"

    # Clean up event loops
    for loop in event_loops:
        loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
