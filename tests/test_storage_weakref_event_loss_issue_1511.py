"""Test for issue #1511: WeakKeyDictionary may cause event loss

This test verifies that using WeakKeyDictionary for storing asyncio.Event
objects can cause events to be lost when the event loop object doesn't have
strong references elsewhere, potentially causing coroutines waiting for the
loop to block forever.
"""
import asyncio
import gc
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_weakref_keydictionary_event_loss():
    """Test that WeakKeyDictionary can lose events when loop has no strong references.

    This test demonstrates the bug described in issue #1511. When an event loop
    is created and only stored in a WeakKeyDictionary, it can be garbage collected
    if there are no other strong references to it, causing the Event to be lost.

    Expected behavior: The test should fail initially (RED phase) because the
    WeakKeyDictionary allows the event loop to be garbage collected, losing the event.
    After the fix, the test should pass (GREEN phase) because we use a regular dict.
    """
    lock = _AsyncCompatibleLock()

    # Create a new event loop (not the running one)
    loop = asyncio.new_event_loop()

    # Simulate creating an async event for this loop
    # This should store the event in _async_events
    try:
        asyncio.set_event_loop(loop)
        event = lock._get_async_event()
        assert event is not None, "Event should be created"

        # Verify the event is stored
        assert loop in lock._async_events, "Event should be stored in _async_events"

        # Now simulate a scenario where the loop loses its strong reference
        # In a real application, this could happen if:
        # 1. A temporary event loop is created
        # 2. The loop is stored in WeakKeyDictionary
        # 3. The loop variable goes out of scope
        # 4. GC runs and collects the loop
        # 5. The event is lost from WeakKeyDictionary

        # Save reference to verify later
        loop_ref = loop
        event_ref = event

        # Delete the strong reference
        del loop
        del event

        # Force garbage collection
        gc.collect()

        # After fix: The event loop should still be in the dictionary
        # Before fix: With WeakKeyDictionary, the loop might have been GC'd
        # and the event would be lost
        assert loop_ref in lock._async_events, (
            "Event loop should still be in _async_events after GC "
            "(this will FAIL with WeakKeyDictionary but PASS with regular dict)"
        )

        # Verify we can still retrieve the event
        retrieved_event = lock._async_events.get(loop_ref)
        assert retrieved_event is not None, "Event should still be retrievable"
        assert retrieved_event is event_ref, "Retrieved event should match original"

    finally:
        # Clean up
        loop.close()


def test_weakref_keydictionary_multiple_loops():
    """Test that multiple event loops can be tracked without loss.

    This test verifies that when multiple event loops are used,
    they are all properly tracked and not lost due to weak references.
    """
    lock = _AsyncCompatibleLock()

    loops = []
    events = []

    # Create multiple event loops and events
    for i in range(3):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            event = lock._get_async_event()
            loops.append(loop)
            events.append(event)

            # Verify each is stored
            assert loop in lock._async_events, f"Loop {i} should be stored"
        finally:
            asyncio.set_event_loop(None)

    # Now delete references to some loops and force GC
    # Keep only the first loop
    first_loop = loops[0]
    first_event = events[0]

    # Delete references to other loops
    del loops[1:]
    del events[1:]

    # Force garbage collection
    gc.collect()

    # After fix: All loops should still be in the dictionary
    # Before fix: Some loops might have been GC'd from WeakKeyDictionary
    for i, loop in enumerate([first_loop]):
        assert loop in lock._async_events, f"Loop {i} should still be in _async_events"

    # Verify we can still retrieve the event for the first loop
    retrieved_event = lock._async_events.get(first_loop)
    assert retrieved_event is not None, "Event for first loop should still be retrievable"
    assert retrieved_event is first_event, "Retrieved event should match original"

    # Clean up
    first_loop.close()


def test_weakref_keydictionary_event_persistence_during_wait():
    """Test that events persist when a coroutine is waiting.

    This test simulates a real-world scenario where a coroutine is waiting
    for an event, and we need to ensure the event doesn't get garbage collected
    due to weak references.
    """
    lock = _AsyncCompatibleLock()

    async def wait_for_lock():
        """Simulate a coroutine waiting for the lock."""
        async with lock:
            await asyncio.sleep(0.01)
            return True

    # Create a new event loop
    loop = asyncio.new_event_loop()

    try:
        asyncio.set_event_loop(loop)

        # Start a task that will wait for the lock
        task = loop.create_task(wait_for_lock())

        # Give it a moment to start waiting
        loop.run_until_complete(asyncio.sleep(0.001))

        # The event loop should be in _async_events now
        assert loop in lock._async_events, "Event loop should be stored"

        # Simulate potential GC pressure
        # In a real application, the loop reference might be temporary
        loop_ref = loop

        # Run the task to completion
        result = loop.run_until_complete(task)
        assert result is True, "Task should complete successfully"

        # After task completes, the event should still be available
        assert loop_ref in lock._async_events, "Event loop should still be stored after task completes"

    finally:
        # Clean up
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        loop.close()
