"""Tests for Issue #1341 - _AsyncCompatibleLock multi-loop memory leak."""
import asyncio
import gc
import threading
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_async_locks_cleanup_after_loop_close():
    """Test that _async_locks dictionary doesn't leak memory after event loops are closed.

    This test verifies that locks are properly cleaned up when event loops are destroyed,
    preventing memory leaks and potential ID conflicts.
    """
    lock = _AsyncCompatibleLock()

    # Track created event loops for cleanup
    loops = []

    async def use_lock_in_loop():
        """Use the async lock in current event loop."""
        async with lock:
            await asyncio.sleep(0.001)

    def run_in_new_thread():
        """Run an event loop in a separate thread."""
        loop = asyncio.new_event_loop()
        loops.append(loop)
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(use_lock_in_loop())
        finally:
            # Close the loop to simulate cleanup
            loop.close()
            asyncio.set_event_loop(None)

    # Create multiple event loops in threads and close them
    for _ in range(5):
        thread = threading.Thread(target=run_in_new_thread)
        thread.start()
        thread.join()

    # Force garbage collection
    gc.collect()

    # Check that _async_locks doesn't accumulate entries for destroyed loops
    # After closing loops and garbage collection, the dictionary should be empty
    # or only contain entries for currently active loops
    assert len(lock._async_locks) == 0, (
        f"_async_locks should be empty after all event loops are closed, "
        f"but contains {len(lock._async_locks)} entries. "
        f"This indicates a memory leak."
    )


def test_async_locks_multiple_concurrent_loops():
    """Test that _AsyncCompatibleLock works correctly with multiple concurrent event loops."""
    lock = _AsyncCompatibleLock()

    results = []

    async def use_lock_in_loop(loop_id):
        """Use the async lock and record success."""
        async with lock:
            await asyncio.sleep(0.01)
            results.append(loop_id)

    def run_in_thread(loop_id):
        """Run an event loop with the given ID."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(use_lock_in_loop(loop_id))
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    # Run multiple loops concurrently
    threads = [
        threading.Thread(target=run_in_thread, args=(i,))
        for i in range(3)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    # All threads should have completed successfully
    assert len(results) == 3
    assert set(results) == {0, 1, 2}


def test_async_locks_no_stale_references():
    """Test that destroyed event loops don't leave stale references in _async_locks."""
    lock = _AsyncCompatibleLock()

    # Weak references to track event loops
    loop_refs = []

    async def use_lock():
        """Use the lock to create an entry in _async_locks."""
        async with lock:
            await asyncio.sleep(0.001)

    def create_and_destroy_loop():
        """Create a loop, use lock, then destroy it."""
        loop = asyncio.new_event_loop()
        loop_refs.append(weakref.ref(loop))
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(use_lock())
            # At this point, lock._async_locks should have an entry
            current_loop_id = id(loop)
            assert current_loop_id in lock._async_locks
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    # Create and destroy several loops
    for _ in range(3):
        create_and_destroy_loop()

    # Force garbage collection
    gc.collect()

    # All event loops should be destroyed
    for ref in loop_refs:
        assert ref() is None, "Event loop should be destroyed"

    # The dictionary should be empty (or close to it) after cleanup
    # Note: This is the key assertion - we expect the dictionary to clean up
    # stale entries, not just keep accumulating them forever
    assert len(lock._async_locks) < len(loop_refs), (
        f"_async_locks has {len(lock._async_locks)} entries after "
        f"{len(loop_refs)} event loops were destroyed. "
        f"This suggests stale entries are not being cleaned up."
    )
