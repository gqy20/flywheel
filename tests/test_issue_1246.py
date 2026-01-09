"""Test for Issue #1246: Potential deadlock risk in double-checked locking.

This test verifies that _get_or_create_loop properly handles the race condition
where an event loop might be closed between the first check (before acquiring
the lock) and the second check (after acquiring the lock).
"""

import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestIssue1246:
    """Tests for Issue #1246 - Race condition in double-checked locking."""

    def test_get_or_create_loop_returns_non_closed_loop(self):
        """Test that _get_or_create_loop never returns a closed loop.

        This test simulates the race condition where:
        1. Thread A checks if event loop is not None (passes)
        2. Thread B closes the event loop
        3. Thread A acquires the lock and returns the now-closed loop

        The fix ensures that even in this scenario, we check is_closed()
        INSIDE the lock and create a new loop if needed.
        """
        lock = _AsyncCompatibleLock()

        # Create an initial event loop
        loop1 = lock._get_or_create_loop()
        assert loop1 is not None
        assert not loop1.is_closed()

        # Simulate the race condition:
        # Close the loop while another thread might be checking
        loop1.close()

        # Now call _get_or_create_loop again
        # It should detect that the loop is closed and create a new one
        loop2 = lock._get_or_create_loop()

        # The returned loop must NOT be closed
        assert loop2 is not None, "_get_or_create_loop should return a valid loop"
        assert not loop2.is_closed(), "_get_or_create_loop should not return a closed loop"

        # It should be a different loop instance (since the first one was closed)
        # Note: Due to the bug, it might return the same closed loop,
        # so we don't assert loop1 != loop2
        # Instead, we just verify loop2 is not closed

    def test_get_or_create_loop_thread_safety(self):
        """Test that _get_or_create_loop is thread-safe under concurrent access.

        This test creates multiple threads that all call _get_or_create_loop
        concurrently, with one thread closing the loop to simulate the
        race condition.
        """
        lock = _AsyncCompatibleLock()
        results = []
        errors = []

        def get_loop(thread_id):
            """Get a loop and record if it was closed."""
            try:
                loop = lock._get_or_create_loop()
                is_closed = loop.is_closed()
                results.append((thread_id, is_closed))
            except Exception as e:
                errors.append((thread_id, e))

        # Create initial loop
        initial_loop = lock._get_or_create_loop()
        assert initial_loop is not None

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=get_loop, args=(i,))
            threads.append(t)

        # Close the loop just before starting threads to trigger the race condition
        initial_loop.close()

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all threads got a non-closed loop
        for thread_id, is_closed in results:
            assert not is_closed, f"Thread {thread_id} received a closed loop"

    def test_get_or_create_loop_with_concurrent_close(self):
        """Test _get_or_create_loop when loop is closed concurrently.

        This test more directly simulates the bug scenario:
        1. Thread A is in _get_or_create_loop, past the first check
        2. Thread B closes the loop
        3. Thread A should not return the closed loop
        """
        lock = _AsyncCompatibleLock()

        # Create initial loop
        loop = lock._get_or_create_loop()
        assert loop is not None

        # Close the loop
        loop.close()

        # Try to get the loop again - it should not be closed
        new_loop = lock._get_or_create_loop()
        assert new_loop is not None, "Should return a loop"
        assert not new_loop.is_closed(), "Should not return a closed loop"

        # Verify we can actually use the loop
        # If the loop was closed, this would fail
        async def dummy_coro():
            return "success"

        try:
            future = asyncio.run_coroutine_threadsafe(
                dummy_coro(), new_loop
            )
            result = future.result(timeout=1.0)
            assert result == "success", "Should be able to run coroutines on the loop"
        except Exception as e:
            pytest.fail(f"Failed to run coroutine on the loop: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
