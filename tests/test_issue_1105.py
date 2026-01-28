"""Test cases for Issue #1105 - Don't create new event loop in sync context manager."""

import asyncio
import threading
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockNoNewEventLoop:
    """Test that _AsyncCompatibleLock doesn't create new event loops in sync context.

    Issue #1105: Creating a new event loop in a synchronous context manager breaks
    existing async contexts and can cause deadlocks or state inconsistency.
    """

    def test_sync_context_does_not_create_event_loop(self):
        """Test that using sync context manager doesn't create a new event loop.

        The fix should use threading.Lock for sync contexts instead of creating
        a new event loop, which can break existing async contexts.
        """
        lock = _AsyncCompatibleLock()

        # Get the current event loop before using the lock
        loop_before = None
        try:
            loop_before = asyncio.get_event_loop()
        except RuntimeError:
            pass

        # Use the lock in a sync context
        with lock:
            # Inside the lock, check if event loop was changed
            loop_inside = None
            try:
                loop_inside = asyncio.get_event_loop()
            except RuntimeError:
                pass

            # The event loop should not have been changed
            # If a new loop was created and closed, loop_inside might be None
            # or different from loop_before
            assert loop_inside is loop_before, (
                "Event loop should not be changed by sync context manager"
            )

        # After exiting the lock, the event loop state should be preserved
        loop_after = None
        try:
            loop_after = asyncio.get_event_loop()
        except RuntimeError:
            pass

        assert loop_after is loop_before, (
            "Event loop state should be preserved after using sync context manager"
        )

    def test_sync_context_with_async_running_loop(self):
        """Test that sync context manager raises error in async context.

        When there's a running event loop, using sync context manager should
        raise a RuntimeError instead of creating a new loop.
        """
        lock = _AsyncCompatibleLock()
        error_raised = False

        async def try_sync_in_async():
            nonlocal error_raised
            try:
                # This should raise RuntimeError because there's a running loop
                with lock:
                    pass
            except RuntimeError as e:
                error_raised = True
                assert "Cannot use synchronous context manager" in str(e)

        # Run in async context
        asyncio.run(try_sync_in_async())

        assert error_raised, "Should raise RuntimeError when using sync context in async"

    def test_async_context_still_works(self):
        """Test that async context manager still works correctly."""
        lock = _AsyncCompatibleLock()

        async def use_async_lock():
            async with lock:
                # Lock should be acquired
                assert lock._async_lock.locked()
                # Do some work
                await asyncio.sleep(0.01)

            # Lock should be released
            assert not lock._async_lock.locked()

        asyncio.run(use_async_lock())

    def test_sync_context_with_threading_lock(self):
        """Test that sync context manager can be used in multiple threads.

        If using threading.Lock internally, the lock should work correctly
        across different threads without creating event loops.
        """
        lock = _AsyncCompatibleLock()
        results = []

        def worker(thread_id):
            """Worker function that uses the lock."""
            try:
                with lock:
                    # Simulate some work
                    import time
                    time.sleep(0.01)
                    results.append(thread_id)
            except Exception as e:
                results.append(f"Thread {thread_id} error: {e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All threads should have completed successfully
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # Check that no errors occurred
        for result in results:
            assert not isinstance(result, str) or "error" not in result.lower(), (
                f"Thread error occurred: {result}"
            )
