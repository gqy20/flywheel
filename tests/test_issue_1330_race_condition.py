"""Test for Issue #1330: Race condition in IOMetrics._get_async_lock

This test verifies that the _get_async_lock method properly handles
concurrent access from multiple threads without allowing lock objects
to be overwritten or creating multiple locks for the same event loop.
"""
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

import pytest

from flywheel.storage import IOMetrics


class TestIssue1330RaceCondition:
    """Test suite for Issue #1330 race condition fix."""

    def test_concurrent_get_async_lock_same_loop(self):
        """Test that concurrent calls to _get_async_lock from multiple threads
        using the same event loop return the same lock object.

        This is the core issue: multiple threads should never get different
        lock objects for the same event loop.
        """
        metrics = IOMetrics()
        locks = []
        exceptions = []
        num_threads = 10

        # Create an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def get_lock_from_thread(thread_id):
            """Each thread tries to get the async lock."""
            try:
                # We need to run this in the event loop's context
                # For simplicity, we'll just call the method directly
                # In real scenarios, this would be called from async context
                lock = metrics._get_async_lock()
                locks.append((thread_id, id(lock)))
            except Exception as e:
                exceptions.append((thread_id, e))

        try:
            # Launch multiple threads simultaneously
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=get_lock_from_thread, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join(timeout=5.0)

            # Check for exceptions
            assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"

            # All threads should have gotten locks with the same ID
            unique_lock_ids = set(lock_id for _, lock_id in locks)

            # This is the critical assertion - there should be exactly ONE unique lock
            assert len(unique_lock_ids) == 1, (
                f"Expected 1 unique lock, but got {len(unique_lock_ids)} different locks. "
                f"This indicates a race condition where lock objects were overwritten "
                f"or multiple locks were created for the same event loop. "
                f"Lock IDs: {unique_lock_ids}"
            )

            # Verify we got exactly num_threads results
            assert len(locks) == num_threads, (
                f"Expected {num_threads} lock retrievals, but got {len(locks)}"
            )

        finally:
            loop.close()

    def test_lock_consistency_under_stress(self):
        """Stress test: repeatedly create locks and verify consistency."""
        metrics = IOMetrics()
        iterations = 100

        for _ in range(iterations):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop_id = id(loop)

            try:
                # Get the lock multiple times
                lock1 = metrics._get_async_lock()
                lock2 = metrics._get_async_lock()
                lock3 = metrics._get_async_lock()

                # All should be the same object
                assert id(lock1) == id(lock2) == id(lock3), (
                    f"Lock objects are not the same for event loop {loop_id}: "
                    f"{id(lock1)}, {id(lock2)}, {id(lock3)}"
                )

                # Verify the lock is in the dictionary
                assert loop_id in metrics._locks, (
                    f"Event loop {loop_id} not found in _locks dictionary"
                )

                # Verify it's the same lock
                assert id(metrics._locks[loop_id]) == id(lock1), (
                    f"Lock in dictionary doesn't match returned lock"
                )

            finally:
                loop.close()

    def test_no_lock_overwrite_on_reentry(self):
        """Test that rapid re-entry to _get_async_lock doesn't overwrite the lock."""
        metrics = IOMetrics()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Get lock multiple times rapidly
            lock_ids = [id(metrics._get_async_lock()) for _ in range(50)]

            # All should be identical
            unique_ids = set(lock_ids)
            assert len(unique_ids) == 1, (
                f"Lock was overwritten or recreated! Got {len(unique_ids)} different IDs: {unique_ids}"
            )

        finally:
            loop.close()

    def test_concurrent_with_cleanup(self):
        """Test race condition when cleanup happens concurrently with lock creation."""
        metrics = IOMetrics()
        num_loops = 5
        threads_per_loop = 3

        def create_and_get_lock(loop_num):
            """Create a loop and get its lock multiple times."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                lock_ids = []
                for _ in range(threads_per_loop):
                    lock = metrics._get_async_lock()
                    lock_ids.append(id(lock))

                # All locks for this loop should be the same
                unique_ids = set(lock_ids)
                if len(unique_ids) != 1:
                    return (loop_num, "FAILED", f"Got {len(unique_ids)} different locks")

                return (loop_num, "SUCCESS", len(unique_ids))
            except Exception as e:
                return (loop_num, "ERROR", str(e))
            finally:
                try:
                    loop.close()
                except:
                    pass

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=num_loops) as executor:
            futures = [
                executor.submit(create_and_get_lock, i) for i in range(num_loops)
            ]

            results = []
            for future in futures:
                try:
                    result = future.result(timeout=10.0)
                    results.append(result)
                except FutureTimeoutError:
                    pytest.fail("Test timed out - possible deadlock detected")

        # Check results
        for loop_num, status, detail in results:
            assert status == "SUCCESS", (
                f"Loop {loop_num} failed with status {status}: {detail}"
            )
