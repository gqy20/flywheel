"""Tests for IOMetrics._get_async_lock race condition (Issue #1296).

This test ensures that IOMetrics._get_async_lock properly handles the race
condition described in issue #1296.

The bug is that there's a time window between:
1. The initial check: `if current_loop_id in self._locks: return self._locks[current_loop_id]` (lines 279-280)
2. The synchronized check inside create_lock_on_loop_thread: `if current_loop_id not in self._locks:` (line 293)

Multiple threads can pass the initial check simultaneously before any of them
acquires the lock and creates a new lock. This creates a race condition where:
- Thread A passes initial check (lock not in dict)
- Thread B passes initial check (lock not in dict)
- Both threads schedule lock creation
- Multiple locks may be created for the same event loop
- Or the second thread's call_soon_threadsafe may interfere with the first

The fix should ensure that only one lock is created per event loop, even when
multiple threads call _get_async_lock simultaneously.
"""

import asyncio
import threading
import pytest
import time
from unittest.mock import patch


class TestIOMetricsDoubleCheckRaceIssue1296:
    """Test suite for IOMetrics._get_async_lock race condition (Issue #1296)."""

    @pytest.mark.asyncio
    async def test_double_check_race_condition_same_loop(self):
        """Test that the double-check pattern prevents race condition.

        This test simulates the race condition where multiple threads call
        _get_async_lock for the same event loop simultaneously.

        The issue is that threads can pass the initial unsynchronized check
        before any of them acquires the synchronization lock.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)

        # Track how many times lock creation is attempted
        creation_attempts = [0]
        original_call_soon = current_loop.call_soon_threadsafe

        def tracked_call_soon(callback, *args, **kwargs):
            """Track call_soon_threadsafe calls."""
            if 'create_lock_on_loop_thread' in str(callback):
                creation_attempts[0] += 1
            return original_call_soon(callback, *args, **kwargs)

        with patch.object(current_loop, 'call_soon_threadsafe', side_effect=tracked_call_soon):
            errors = []
            locks = []

            def get_lock_from_thread(thread_id):
                """Each thread tries to get the lock."""
                try:
                    # Each thread uses the SAME event loop (current_loop)
                    # This simulates multiple async tasks calling from different threads
                    loop = current_loop

                    async def get_lock():
                        # This should all get the SAME lock instance
                        lock = metrics._get_async_lock()
                        locks.append((thread_id, id(lock)))
                        # Verify it's an asyncio.Lock
                        assert isinstance(lock, asyncio.Lock)
                        # Try to use it
                        async with lock:
                            await metrics.record_operation_async(
                                f"op_{thread_id}",
                                duration=0.01,
                                retries=0,
                                success=True
                            )

                    # Run on the main event loop
                    asyncio.run_coroutine_threadsafe(get_lock(), loop).result(timeout=2.0)

                except Exception as e:
                    errors.append(f"Thread {thread_id} error: {type(e).__name__}: {e}")

            # Start multiple threads simultaneously, all targeting the same event loop
            threads = []
            for i in range(5):
                thread = threading.Thread(target=get_lock_from_thread, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join(timeout=10.0)

            # Should not have any errors
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # All threads should have gotten a lock
            assert len(locks) == 5, f"Expected 5 locks, got {len(locks)}"

            # CRITICAL: All locks should be the SAME instance (same id)
            # If there's a race condition, different locks might be created
            unique_lock_ids = set(lock_id for _, lock_id in locks)
            assert len(unique_lock_ids) == 1, (
                f"Race condition detected! Expected 1 unique lock, "
                f"but got {len(unique_lock_ids)} different locks: {unique_lock_ids}"
            )

            # The lock should be in the metrics._locks dict for this event loop
            assert current_loop_id in metrics._locks
            assert metrics._locks[current_loop_id] is not None

            # Verify operations were recorded
            assert len(metrics.operations) == 5

    @pytest.mark.asyncio
    async def test_get_async_lock_returns_same_instance_on_concurrent_calls(self):
        """Test that concurrent calls to _get_async_lock return the same lock instance.

        This is a simpler test that verifies the basic requirement:
        multiple calls should return the exact same lock object for the same event loop.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Get the lock multiple times concurrently
        async def get_lock_multiple_times():
            locks = []
            for _ in range(10):
                lock = metrics._get_async_lock()
                locks.append(lock)
            return locks

        # Run multiple coroutines concurrently
        tasks = [get_lock_multiple_times() for _ in range(3)]
        all_locks = await asyncio.gather(*tasks)

        # Flatten the list of locks
        all_locks_flat = [lock for locks_list in all_locks for lock in locks_list]

        # All locks should be the exact same instance (same id)
        unique_lock_ids = set(id(lock) for lock in all_locks_flat)
        assert len(unique_lock_ids) == 1, (
            f"Expected 1 unique lock, got {len(unique_lock_ids)}: {unique_lock_ids}"
        )

    @pytest.mark.asyncio
    async def test_lock_initialization_is_atomic(self):
        """Test that lock initialization appears atomic to callers.

        Even with multiple threads calling _get_async_lock simultaneously,
        only one lock should be created and all callers should get that same lock.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Track lock creation calls
        lock_creation_count = [0]
        original_init = asyncio.Lock.__init__

        def tracked_init(self, *args, **kwargs):
            lock_creation_count[0] += 1
            return original_init(self, *args, **kwargs)

        with patch.object(asyncio.Lock, '__init__', tracked_init):
            # Simulate multiple threads trying to get the lock at the same time
            errors = []
            lock_ids = []

            def worker(worker_id):
                try:
                    loop = asyncio.get_running_loop()

                    async def get_lock():
                        lock = metrics._get_async_lock()
                        lock_ids.append((worker_id, id(lock)))

                    asyncio.run_coroutine_threadsafe(get_lock(), loop).result(timeout=2.0)

                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")

            threads = []
            for i in range(10):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join(timeout=10.0)

            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(lock_ids) == 10

            # All workers should get the same lock
            unique_ids = set(lock_id for _, lock_id in lock_ids)
            assert len(unique_ids) == 1, (
                f"Expected 1 unique lock, got {len(unique_ids)}. "
                f"Lock creation was called {lock_creation_count[0]} times."
            )

            # Lock should only be created once
            assert lock_creation_count[0] == 1, (
                f"Expected lock to be created once, but it was created {lock_creation_count[0]} times"
            )
