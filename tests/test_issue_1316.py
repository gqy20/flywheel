"""Test for issue #1316: Thread lock in async context may block event loop.

This test verifies that the _AsyncCompatibleLock can handle high concurrency
without exhausting the dedicated thread pool executor.
"""
import asyncio
import pytest
from flywheel.storage import _AsyncCompatibleLock


class TestIssue1316:
    """Test suite for issue #1316."""

    @pytest.mark.asyncio
    async def test_high_concurrency_lock_contention(self):
        """Test that high concurrency doesn't exhaust thread pool.

        This test creates many concurrent lock acquisition attempts.
        With the old implementation using a thread pool executor with
        max_workers=4, this would fail or timeout under high contention.
        With asyncio.Lock, it should handle this gracefully.
        """
        lock = _AsyncCompatibleLock()
        completed_count = 0
        errors = []

        async def acquire_and_release(task_id):
            """Acquire lock, hold briefly, then release."""
            nonlocal completed_count
            try:
                async with lock:
                    # Simulate some async work while holding lock
                    await asyncio.sleep(0.01)
                    completed_count += 1
            except Exception as e:
                errors.append((task_id, str(e)))

        # Create many concurrent tasks (more than thread pool capacity)
        num_tasks = 20
        tasks = [acquire_and_release(i) for i in range(num_tasks)]

        # Run all tasks with a reasonable timeout
        # If thread pool is exhausted, this will timeout
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=10.0)
        except asyncio.TimeoutError:
            pytest.fail(
                "High concurrency test timed out - likely due to thread pool "
                "exhaustion. Consider using asyncio.Lock instead of threading.Lock."
            )

        # Verify all tasks completed successfully
        assert completed_count == num_tasks,
            f"Only {completed_count}/{num_tasks} tasks completed"

        assert len(errors) == 0,
            f"Errors occurred during concurrent lock operations: {errors}"

    @pytest.mark.asyncio
    async def test_lock_fairness_under_load(self):
        """Test that lock acquisition remains fair under high load.

        This test verifies that under high contention, all waiters
        eventually get the lock and no starvation occurs.
        """
        lock = AsyncLockWrapper()
        acquisition_order = []

        async def acquire_with_id(task_id):
            """Acquire lock and record acquisition order."""
            async with lock:
                acquisition_order.append(task_id)
                # Brief hold to ensure contention
                await asyncio.sleep(0.005)

        # Create many concurrent tasks
        num_tasks = 15
        tasks = [acquire_with_id(i) for i in range(num_tasks)]

        # Run all tasks with timeout
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=8.0)
        except asyncio.TimeoutError:
            pytest.fail(
                "Lock fairness test timed out - possible deadlock or "
                "thread pool exhaustion."
            )

        # Verify all tasks acquired the lock
        assert len(acquisition_order) == num_tasks,
            f"Only {len(acquisition_order)}/{num_tasks} tasks acquired lock"

        # Verify no duplicates (fairness)
        assert len(set(acquisition_order)) == num_tasks,
            "Some tasks acquired lock multiple times (unfair)"

    @pytest.mark.asyncio
    async def test_no_event_loop_blocking(self):
        """Test that lock operations don't block the event loop.

        This test verifies that while waiting for a lock, other async
        operations can still proceed.
        """
        lock = AsyncLockWrapper()
        other_task_completed = False

        async def hold_lock():
            """Hold the lock for a while."""
            async with lock:
                await asyncio.sleep(0.1)

        async def other_work():
            """Do other async work while lock is held."""
            nonlocal other_task_completed
            await asyncio.sleep(0.05)
            other_task_completed = True

        # Start a task holding the lock
        lock_holder = asyncio.create_task(hold_lock())

        # Wait a bit for lock to be acquired
        await asyncio.sleep(0.01)

        # Start other work - should complete even though lock is held
        worker = asyncio.create_task(other_work())

        # Wait for both to complete
        await asyncio.gather(lock_holder, worker)

        # Verify other work completed (proves event loop wasn't blocked)
        assert other_task_completed,
            "Event loop was blocked - other async work couldn't run"

    @pytest.mark.asyncio
    async def test_rapid_acquire_release_cycles(self):
        """Test rapid acquire/release cycles don't cause issues.

        This test simulates the pattern of many quick lock acquisitions
        and releases, which could stress a thread pool based implementation.
        """
        lock = AsyncLockWrapper()
        cycle_count = 50

        async def rapid_cycle(task_id):
            """Perform multiple rapid acquire/release cycles."""
            for _ in range(cycle_count):
                async with lock:
                    # Very brief hold - just a yield
                    await asyncio.sleep(0)

        # Run multiple tasks doing rapid cycles
        num_tasks = 10
        tasks = [rapid_cycle(i) for i in range(num_tasks)]

        # Should complete quickly without timeout
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=15.0)
        except asyncio.TimeoutError:
            pytest.fail(
                "Rapid cycle test timed out - thread pool may be exhausted"
            )

        # If we got here, the implementation handles rapid cycles well
        assert True
