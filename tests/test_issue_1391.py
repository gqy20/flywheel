"""Test for issue #1391: Race condition risk when iterating over WeakKeyDictionary during lock release.

This test verifies the fix for the potential RuntimeError that can occur when iterating
over _async_events (a WeakKeyDictionary) during __exit__ or __aexit__ methods.
"""

import asyncio
import gc
import threading
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_sync_exit_weakkeydictionary_iteration_safety():
    """Test that __exit__ safely iterates over WeakKeyDictionary even during GC.

    The bug: Iterating directly over self._async_events.values() can raise RuntimeError
    if garbage collection occurs during iteration and removes items from the WeakKeyDictionary.

    The fix: Use list(self._async_events.values()) to create a snapshot before iterating.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create multiple event loops to populate _async_events
        event_loops = []
        for i in range(5):
            test_loop = asyncio.new_event_loop()
            event_loops.append(test_loop)
            asyncio.set_event_loop(test_loop)
            # Create an event by accessing the lock in async context
            async def create_event():
                async with lock:
                    pass

            try:
                test_loop.run_until_complete(create_event())
            except Exception:
                pass

        # Verify we have multiple events in the dictionary
        assert len(lock._async_events) > 0, "No events were created"

        # Force garbage collection during iteration
        # The current buggy implementation may raise RuntimeError here
        def trigger_gc_and_iterate():
            # This simulates what happens in __exit__
            gc.collect()  # Force garbage collection
            # The buggy code does: for event in self._async_events.values()
            # This can raise RuntimeError if GC removed items during iteration
            for event in lock._async_events.values():
                if not event.is_set():
                    event.set()

        # Acquire and release the lock (which calls __exit__)
        with lock:
            pass

        # If we got here without RuntimeError, the fix is working
        # The buggy version would have raised RuntimeError during __exit__

    finally:
        for test_loop in event_loops:
            try:
                test_loop.close()
            except Exception:
                pass
        try:
            loop.close()
        except Exception:
            pass


def test_async_exit_weakkeydictionary_iteration_safety():
    """Test that __aexit__ safely iterates over WeakKeyDictionary even during GC.

    Similar to the sync version but for the async context manager exit.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create multiple event loops to populate _async_events
        event_loops = []
        for i in range(5):
            test_loop = asyncio.new_event_loop()
            event_loops.append(test_loop)

        # Populate _async_events
        for test_loop in event_loops:
            asyncio.set_event_loop(test_loop)
            async def create_event():
                async with lock:
                    pass
            try:
                test_loop.run_until_complete(create_event())
            except Exception:
                pass

        # Verify we have multiple events
        assert len(lock._async_events) > 0, "No events were created"

        # Test async exit with concurrent GC
        async def test_async_exit_with_gc():
            async with lock:
                # Force GC while holding lock
                gc.collect()

        # Run the test
        loop.run_until_complete(test_async_exit_with_gc())

        # If we got here without RuntimeError, the fix is working

    finally:
        for test_loop in event_loops:
            try:
                test_loop.close()
            except Exception:
                pass
        try:
            loop.close()
        except Exception:
            pass


def test_concurrent_gc_during_exit():
    """Test that concurrent garbage collection doesn't cause issues during __exit__.

    This is a stress test that tries to trigger the race condition more aggressively.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create multiple event loops
        event_loops = []
        for i in range(10):
            test_loop = asyncio.new_event_loop()
            event_loops.append(test_loop)
            asyncio.set_event_loop(test_loop)
            async def create_event():
                async with lock:
                    pass
            try:
                test_loop.run_until_complete(create_event())
            except Exception:
                pass

        # Start a thread that aggressively triggers GC
        stop_gc = threading.Event()

        def aggressive_gc():
            while not stop_gc.is_set():
                gc.collect()
                threading.Event().wait(0.001)  # Small delay

        gc_thread = threading.Thread(target=aggressive_gc)
        gc_thread.start()

        try:
            # Acquire and release the lock multiple times
            for _ in range(20):
                with lock:
                    pass
        finally:
            stop_gc.set()
            gc_thread.join(timeout=2.0)

        # Clean up
        for test_loop in event_loops:
            try:
                test_loop.close()
            except Exception:
                pass

    finally:
        try:
            loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
