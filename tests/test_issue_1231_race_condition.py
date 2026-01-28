"""Tests for issue #1231 - Race condition in _get_or_create_loop.

The issue is that asyncio.get_running_loop() is called while holding
_loop_lock, which can cause unexpected behavior or deadlocks.
"""
import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestGetOrCreateLoopRaceCondition:
    """Test that _get_or_create_loop doesn't have race conditions."""

    def test_get_running_loop_outside_lock(self):
        """Test that get_running_loop is called outside the lock.

        This test verifies that the implementation calls
        asyncio.get_running_loop() BEFORE acquiring the loop lock,
        which prevents potential deadlocks.
        """
        # Create multiple locks concurrently to stress test the implementation
        locks = []
        threads = []
        results = []
        exceptions = []

        def create_lock_in_thread():
            """Create and use a lock in a separate thread."""
            try:
                lock = _AsyncCompatibleLock()
                # Access the event loop by acquiring the lock
                with lock:
                    # If there's a race condition/deadlock, this will hang
                    time.sleep(0.01)
                results.append(True)
            except Exception as e:
                exceptions.append(e)

        # Create multiple threads that each create a lock
        for _ in range(10):
            thread = threading.Thread(target=create_lock_in_thread)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)

        # If any thread is still alive, we have a deadlock
        alive_threads = [t for t in threads if t.is_alive()]
        assert len(alive_threads) == 0, (
            f"Deadlock detected: {len(alive_threads)} threads still running"
        )

        # No exceptions should have occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # All operations should have completed successfully
        assert len(results) == 10

    def test_async_context_reuses_running_loop(self):
        """Test that async context reuses the running loop efficiently."""
        async def async_test():
            lock1 = _AsyncCompatibleLock()
            loop1 = lock1._get_or_create_loop()

            # Should get the same running loop
            running_loop = asyncio.get_running_loop()
            assert loop1 is running_loop, (
                "In async context, should reuse the running loop"
            )

            # Create another lock, should also reuse the running loop
            lock2 = _AsyncCompatibleLock()
            loop2 = lock2._get_or_create_loop()
            assert loop2 is running_loop, (
                "Second lock should also reuse the running loop"
            )

        asyncio.run(async_test())

    def test_sync_context_creates_loop_efficiently(self):
        """Test that sync context creates a loop only when needed."""
        # In a sync context (no running loop)
        lock = _AsyncCompatibleLock()
        loop = lock._get_or_create_loop()

        assert loop is not None
        assert not loop.is_closed()

        # Multiple calls should return the same loop
        loop2 = lock._get_or_create_loop()
        assert loop is loop2

    def test_concurrent_access_thread_safety(self):
        """Test that concurrent access to _get_or_create_loop is thread-safe."""
        lock = _AsyncCompatibleLock()
        loops = []
        exceptions = []

        def access_loop():
            """Access the event loop from multiple threads."""
            try:
                for _ in range(100):
                    loop = lock._get_or_create_loop()
                    loops.append(loop)
                    time.sleep(0.0001)  # Small delay to increase contention
            except Exception as e:
                exceptions.append(e)

        threads = []
        for _ in range(5):
            thread = threading.Thread(target=access_loop)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        # No deadlocks or exceptions
        alive_threads = [t for t in threads if t.is_alive()]
        assert len(alive_threads) == 0, "Deadlock detected"
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

        # All loops should be the same instance
        assert len(loops) == 500  # 5 threads * 100 iterations
        assert all(loop is loops[0] for loop in loops), (
            "All accesses should return the same loop instance"
        )
