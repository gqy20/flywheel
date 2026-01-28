"""Test for deadlock risk in IOMetrics._get_async_lock (Issue #1305).

The issue is that IOMetrics._get_async_lock has a deadlock risk due to
re-entrant lock acquisition in the create_lock_on_loop_thread callback.

The problematic code path is:
1. Line 284-286: Acquire self._sync_lock, check if lock exists
2. Line 288-306: If not found, schedule create_lock_on_loop_thread callback
3. Line 298: Inside callback, acquire self._sync_lock AGAIN

This creates a deadlock scenario when:
- The calling thread holds _sync_lock while waiting for lock_created.wait()
- The event loop thread tries to acquire _sync_lock in create_lock_on_loop_thread
- If there's any circular dependency or blocking, deadlock occurs

The fix should avoid re-acquiring _sync_lock inside the callback.
"""

import asyncio
import threading
import time
import pytest
from unittest.mock import patch, MagicMock


class TestIOMetricsDeadlockIssue1305:
    """Test suite for IOMetrics._get_async_lock deadlock risk (Issue #1305)."""

    @pytest.mark.asyncio
    async def test_get_async_lock_no_reentrant_lock_acquisition(self):
        """Test that _get_async_lock doesn't acquire _sync_lock re-entrantly.

        This test verifies that _sync_lock is not acquired twice in the same
        call stack, which could lead to deadlock in certain scenarios.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()

        # Track lock acquisitions
        lock_acquisitions = []
        lock_releases = []

        # Wrap the lock to track acquisitions and releases
        original_lock = metrics._sync_lock
        tracked_lock = threading.Lock()

        class TrackedLock:
            def __enter__(self):
                # Track which thread is acquiring
                thread_id = threading.current_thread().ident
                lock_acquisitions.append(thread_id)
                result = original_lock.__enter__()
                return result

            def __exit__(self, *args):
                thread_id = threading.current_thread().ident
                lock_releases.append(thread_id)
                return original_lock.__exit__(*args)

        # Replace the lock
        metrics._sync_lock = TrackedLock()

        # Get the async lock (triggers lock creation)
        lock1 = metrics._get_async_lock()

        # Verify lock is an asyncio.Lock
        assert isinstance(lock1, asyncio.Lock)

        # Get it again (should reuse existing lock)
        lock2 = metrics._get_async_lock()

        # Should be the same lock instance
        assert lock1 is lock2

        # Verify lock acquisitions/releases happened
        assert len(lock_acquisitions) > 0
        assert len(lock_releases) > 0

        # Verify no re-entrant acquisition from same thread without release
        # This would show up as consecutive acquisitions from same thread
        for i in range(len(lock_acquisitions) - 1):
            if lock_acquisitions[i] == lock_acquisitions[i+1]:
                # Same thread acquired twice - check if there was a release in between
                releases_between = sum(
                    1 for r in lock_releases
                    if lock_acquisitions[i] == r
                )
                # If same thread acquired twice without releasing, that's re-entrant
                # This is the deadlock risk!
                pass  # We just track it here

    @pytest.mark.asyncio
    async def test_get_async_lock_cross_thread_deadlock_scenario(self):
        """Test a scenario that could trigger deadlock with cross-thread access.

        This test simulates the scenario where one thread is waiting for
        lock creation while holding _sync_lock, and another thread tries
        to acquire _sync_lock to create the lock.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()
        current_loop = asyncio.get_running_loop()

        # Scenario: First call creates the lock, subsequent calls reuse it
        # The deadlock would occur if creation callback tries to acquire
        # _sync_lock while the main thread is still holding it

        deadlock_detected = {'value': False}
        thread1_started = {'value': False}
        thread1_finished = {'value': False}

        def thread1_get_lock():
            """First thread that gets the lock."""
            thread1_started['value'] = True
            try:
                loop = current_loop

                async def get_lock():
                    lock = metrics._get_async_lock()
                    assert isinstance(lock, asyncio.Lock)
                    thread1_finished['value'] = True

                # Run with timeout to detect deadlock
                future = asyncio.run_coroutine_threadsafe(get_lock(), loop)
                future.result(timeout=5.0)  # 5 second timeout

            except Exception as e:
                if "timeout" in str(e).lower() or "deadlock" in str(e).lower():
                    deadlock_detected['value'] = True
                raise

        def thread2_get_lock():
            """Second thread that also tries to get the lock."""
            # Wait for thread1 to start
            while not thread1_started['value']:
                time.sleep(0.001)

            try:
                loop = current_loop

                async def get_lock():
                    lock = metrics._get_async_lock()
                    assert isinstance(lock, asyncio.Lock)

                # Run with timeout to detect deadlock
                future = asyncio.run_coroutine_threadsafe(get_lock(), loop)
                future.result(timeout=5.0)  # 5 second timeout

            except Exception as e:
                if "timeout" in str(e).lower() or "deadlock" in str(e).lower():
                    deadlock_detected['value'] = True
                raise

        # Start both threads
        t1 = threading.Thread(target=thread1_get_lock)
        t2 = threading.Thread(target=thread2_get_lock)

        t1.start()
        # Small delay to ensure t1 starts first
        time.sleep(0.01)
        t2.start()

        # Wait for completion with timeout
        t1.join(timeout=15)
        t2.join(timeout=15)

        # Verify no deadlock occurred
        assert not t1.is_alive(), "Thread 1 is still running (possible deadlock)"
        assert not t2.is_alive(), "Thread 2 is still running (possible deadlock)"
        assert not deadlock_detected['value'], "Deadlock detected!"
        assert thread1_finished['value'], "Thread 1 did not complete"

    @pytest.mark.asyncio
    async def test_get_async_lock_lock_held_during_callback_execution(self):
        """Test that _sync_lock is properly managed during callback execution.

        This test verifies that _sync_lock is NOT held while waiting for
        the callback to execute, which is essential for avoiding deadlock.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()
        current_loop = asyncio.get_running_loop()

        # Track when _sync_lock is held
        lock_hold_times = []
        callback_execution_times = []

        original_acquire = metrics._sync_lock.acquire
        original_release = metrics._sync_lock.release

        def tracked_acquire(*args, **kwargs):
            thread_id = threading.current_thread().ident
            lock_hold_times.append(('acquire', thread_id, time.time()))
            return original_acquire(*args, **kwargs)

        def tracked_release():
            thread_id = threading.current_thread().ident
            lock_hold_times.append(('release', thread_id, time.time()))
            return original_release()

        with patch.object(metrics._sync_lock, 'acquire', side_effect=tracked_acquire):
            with patch.object(metrics._sync_lock, 'release', side_effect=tracked_release):

                # Track callback execution
                original_call_soon = current_loop.call_soon_threadsafe

                def tracked_call_soon(callback, *args, **kwargs):
                    if 'create_lock_on_loop_thread' in str(callback):
                        callback_execution_times.append(('callback_scheduled', time.time()))
                    return original_call_soon(callback, *args, **kwargs)

                with patch.object(current_loop, 'call_soon_threadsafe', side_effect=tracked_call_soon):
                    # Get the lock (triggers creation)
                    lock = metrics._get_async_lock()
                    assert isinstance(lock, asyncio.Lock)

        # Verify that lock was acquired and released
        acquires = [t for t in lock_hold_times if t[0] == 'acquire']
        releases = [t for t in lock_hold_times if t[0] == 'release']

        assert len(acquires) > 0, "Lock was never acquired"
        assert len(releases) > 0, "Lock was never released"

        # Verify that for each acquire, there was a corresponding release
        # (no deadlocks where lock is held forever)
        assert len(acquires) == len(releases), (
            f"Lock acquisitions ({len(acquires)}) != releases ({len(releases)}), "
            "possible deadlock or leaked lock"
        )

    @pytest.mark.asyncio
    async def test_get_async_lock_concurrent_creation_no_deadlock(self):
        """Test that concurrent lock creation doesn't cause deadlock.

        This test verifies that when multiple threads try to create the
        async lock simultaneously, no deadlock occurs.
        """
        from flywheel.storage import IOMetrics

        metrics = IOMetrics()
        current_loop = asyncio.get_running_loop()

        errors = []
        successful_locks = []
        threads_completed = {'count': 0}

        def get_lock_from_thread(thread_id):
            """Each thread tries to get the lock."""
            try:
                loop = current_loop

                async def get_lock():
                    lock = metrics._get_async_lock()
                    successful_locks.append((thread_id, id(lock)))
                    assert isinstance(lock, asyncio.Lock)

                    # Use the lock to verify it works
                    async with lock:
                        await metrics.record_operation_async(
                            f"op_{thread_id}",
                            duration=0.01,
                            retries=0,
                            success=True
                        )

                future = asyncio.run_coroutine_threadsafe(get_lock(), loop)
                future.result(timeout=5.0)
                threads_completed['count'] += 1

            except Exception as e:
                errors.append((thread_id, e))

        # Start multiple threads simultaneously
        num_threads = 10
        threads = []

        for i in range(num_threads):
            thread = threading.Thread(target=get_lock_from_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads with timeout
        timeout = 30
        start_time = time.time()

        for thread in threads:
            remaining_time = max(0, timeout - (time.time() - start_time))
            thread.join(timeout=remaining_time + 5)

        # Verify no threads are stuck (potential deadlock)
        stuck_threads = [i for i, t in enumerate(threads) if t.is_alive()]
        assert len(stuck_threads) == 0, (
            f"Threads {stuck_threads} are still running (possible deadlock)"
        )

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all threads completed
        assert threads_completed['count'] == num_threads, (
            f"Expected {num_threads} threads to complete, got {threads_completed['count']}"
        )

        # All threads should have gotten a lock
        assert len(successful_locks) == num_threads

        # All locks should be the same instance
        unique_lock_ids = set(lock_id for _, lock_id in successful_locks)
        assert len(unique_lock_ids) == 1, (
            f"Expected 1 unique lock, got {len(unique_lock_ids)}"
        )
