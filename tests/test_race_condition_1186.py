"""Test for Issue #1186: Race condition in _AsyncCompatibleLock initialization

This test verifies that the _AsyncCompatibleLock properly handles concurrent
initialization from multiple threads without race conditions.
"""

import asyncio
import threading
import pytest
from concurrent.futures import ThreadPoolExecutor

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockRaceCondition:
    """Tests for race conditions in _AsyncCompatibleLock initialization."""

    def test_concurrent_initialization_threads(self):
        """Test that concurrent initialization from multiple threads is safe.

        This test creates multiple threads that all try to acquire the lock
        simultaneously, potentially triggering a race condition in the
        _get_or_create_loop method if not properly synchronized.

        The race condition occurs when:
        1. Thread A checks self._event_loop.is_closed() and it's False
        2. Thread B checks self._event_loop.is_closed() and it's False
        3. Thread A creates a new event loop
        4. Thread B creates a new event loop
        5. Both threads think they have the same loop, but they don't

        With proper locking, only one thread should create the event loop.
        """
        lock = _AsyncCompatibleLock()
        errors = []
        results = []

        def try_acquire_lock(thread_id):
            """Try to acquire the lock from a thread."""
            try:
                # Each thread attempts to get the event loop
                loop = lock._get_or_create_loop()
                results.append((thread_id, id(loop)))

                # Try to use the lock
                with lock:
                    # Simulate some work
                    import time
                    time.sleep(0.01)

            except Exception as e:
                errors.append((thread_id, e))

        # Launch multiple threads concurrently
        num_threads = 10
        threads = []
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(try_acquire_lock, i)
                futures.append(future)

            # Wait for all threads to complete
            for future in futures:
                future.result()

        # Check that no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Check that all threads got the same event loop
        # This is the key test - if there's a race condition,
        # different threads might get different event loops
        unique_loops = set(loop_id for _, loop_id in results)
        assert len(unique_loops) == 1, (
            f"Race condition detected! Threads got {len(unique_loops)} "
            f"different event loops: {unique_loops}"
        )

    def test_concurrent_sync_and_async_usage(self):
        """Test concurrent sync and async lock usage.

        This test verifies that the lock properly handles being used
        from both sync and async contexts simultaneously.
        """
        lock = _AsyncCompatibleLock()
        errors = []

        async def async_worker(worker_id):
            """Worker that uses async with."""
            try:
                async with lock:
                    await asyncio.sleep(0.01)
            except Exception as e:
                errors.append((f"async-{worker_id}", e))

        def sync_worker(worker_id):
            """Worker that uses sync with."""
            try:
                with lock:
                    import time
                    time.sleep(0.01)
            except Exception as e:
                errors.append((f"sync-{worker_id}", e))

        async def run_async_workers():
            """Run multiple async workers concurrently."""
            tasks = [async_worker(i) for i in range(5)]
            await asyncio.gather(*tasks)

        def run_sync_workers():
            """Run multiple sync workers concurrently."""
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(sync_worker, i) for i in range(5)]
                for future in futures:
                    future.result()

        # Run async and sync workers concurrently
        import threading
        async_thread = threading.Thread(
            target=lambda: asyncio.run(run_async_workers())
        )
        sync_thread = threading.Thread(target=run_sync_workers)

        async_thread.start()
        sync_thread.start()

        async_thread.join()
        sync_thread.join()

        # Check that no errors occurred
        assert len(errors) == 0, f"Errors occurred during concurrent usage: {errors}"

    def test_event_loop_state_consistency(self):
        """Test that event loop state remains consistent under stress.

        This test repeatedly acquires and releases the lock from multiple
        threads to ensure the event loop reference remains stable.
        """
        lock = _AsyncCompatibleLock()

        def stress_test(iterations):
            """Run many acquire/release cycles."""
            for _ in range(iterations):
                with lock:
                    # Get the loop multiple times
                    loop1 = lock._get_or_create_loop()
                    loop2 = lock._get_or_create_loop()

                    # Must be the same loop
                    assert id(loop1) == id(loop2), (
                        "Event loop changed during single operation!"
                    )

        # Run stress test in multiple threads
        threads = []
        num_threads = 5
        iterations_per_thread = 100

        for _ in range(num_threads):
            thread = threading.Thread(
                target=stress_test, args=(iterations_per_thread,)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
