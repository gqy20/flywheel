"""Test for async events cleanup to prevent memory leaks (Issue #1541)."""

import asyncio
import gc
import weakref

from flywheel.storage import _AsyncCompatibleLock


def test_async_events_cleaned_up_after_loop_closure():
    """Test that asyncio.Event objects are cleaned up when event loops are closed.

    This test verifies the fix for Issue #1541: When event loops are closed,
    the asyncio.Event objects stored in _async_events dictionary should be
    cleaned up to prevent memory leaks in long-running programs.

    The test creates multiple event loops, uses them with the lock, then closes
    them. It verifies that the events are properly cleaned up, preventing memory
    leaks.
    """
    lock = _AsyncCompatibleLock()

    # Keep weak references to event loops to verify they can be garbage collected
    loop_refs = []

    # Create and use multiple event loops
    for i in range(5):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Store weak reference to track garbage collection
        loop_refs.append(weakref.ref(loop))

        try:
            # Use the lock in this event loop, which will create an Event
            async def use_lock():
                async with lock:
                    await asyncio.sleep(0.01)

            loop.run_until_complete(use_lock())

            # Verify that an event was created for this loop
            current_loop = asyncio.get_running_loop()
            assert current_loop in lock._async_events, (
                f"Event not created for loop {i}"
            )
        finally:
            loop.close()

    # Force garbage collection
    gc.collect()

    # Check that all event loops have been garbage collected
    # If events hold strong references, this will fail
    for i, loop_ref in enumerate(loop_refs):
        assert loop_ref() is None, (
            f"Event loop {i} was not garbage collected. "
            "This indicates that _async_events holds strong references "
            "to closed event loops, causing a memory leak (Issue #1541)."
        )

    # Verify that _async_events is empty or contains only entries for dead loops
    # In the current implementation, it will still contain entries
    # After the fix, it should be cleaned up
    active_loops = [
        loop for loop in lock._async_events.keys()
        if not loop.is_closed()
    ]

    assert len(active_loops) == 0, (
        f"Found {len(active_loops)} active event loops in _async_events. "
        "All loops should be closed and cleaned up."
    )


def test_async_events_memory_leak_with_many_loops():
    """Test that creating and closing many event loops doesn't cause memory leak.

    This test simulates a long-running program that creates many event loops
    over time (e.g., a web server handling requests). Each loop should be
    properly cleaned up to prevent unbounded memory growth.
    """
    lock = _AsyncCompatibleLock()

    # Track how many events remain after creating and closing many loops
    initial_events_count = len(lock._async_events)

    # Create and close many event loops
    num_loops = 20
    loop_refs = []

    for i in range(num_loops):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_refs.append(weakref.ref(loop))

        try:
            # Use the lock to trigger event creation
            async def use_lock():
                async with lock:
                    await asyncio.sleep(0.001)

            loop.run_until_complete(use_lock())
        finally:
            loop.close()

    # Force garbage collection
    gc.collect()

    # All loops should be garbage collected
    live_loops = [ref() for ref in loop_refs if ref() is not None]
    assert len(live_loops) == 0, (
        f"{len(live_loops)} event loops were not garbage collected. "
        "This indicates a memory leak in _async_events cleanup (Issue #1541)."
    )

    # After the fix, _async_events should not accumulate entries indefinitely
    # The current implementation will have entries for all closed loops
    # The fix should clean up entries for closed loops
    events_after = len(lock._async_events)

    # This assertion will fail with the current implementation
    # After the fix, events should be cleaned up
    assert events_after == initial_events_count, (
        f"_async_events accumulated {events_after - initial_events_count} entries "
        f"after creating and closing {num_loops} event loops. "
        "This indicates a memory leak (Issue #1541). "
        "Events should be cleaned up when loops are closed."
    )


def test_cleanup_loop_method_works():
    """Test that the cleanup_loop() method properly removes event references.

    This test verifies that the existing cleanup_loop() method works correctly
    when called explicitly. The fix for Issue #1541 should ensure this cleanup
    happens automatically when loops are closed.
    """
    lock = _AsyncCompatibleLock()

    # Create an event loop and use the lock
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Use the lock to create an event
        async def use_lock():
            async with lock:
                await asyncio.sleep(0.01)

        loop.run_until_complete(use_lock())

        # Verify event was created
        assert loop in lock._async_events, "Event not created for loop"

        # Call cleanup_loop explicitly
        lock.cleanup_loop(loop)

        # Verify event was removed
        assert loop not in lock._async_events, (
            "Event not removed after cleanup_loop() call"
        )

    finally:
        loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
