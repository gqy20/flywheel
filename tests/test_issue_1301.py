"""Tests for Issue #1301: _AsyncCompatibleLock blocking event loop.

This test verifies that _AsyncCompatibleLock doesn't block the event loop
when acquiring locks in async contexts.
"""
import asyncio
import threading
import time

import pytest

from flywheel.storage import _AsyncCompatibleLock


class TestAsyncCompatibleLockEventLoopBlocking:
    """Test suite for Issue #1301."""

    @pytest.mark.asyncio
    async def test_lock_does_not_block_event_loop_with_timeout(self):
        """Test that lock acquisition doesn't block the event loop indefinitely.

        This test simulates a scenario where the default thread pool executor
        might be exhausted, and verifies that we can still acquire the lock
        within a reasonable timeout.
        """
        lock = _AsyncCompatibleLock()
        lock_acquired = False
        task_completed = False

        async def acquire_lock():
            nonlocal lock_acquired, task_completed
            async with lock:
                lock_acquired = True
                # Simulate some async work
                await asyncio.sleep(0.01)
            task_completed = True

        # Create task with timeout to prevent indefinite blocking
        task = asyncio.create_task(acquire_lock())

        try:
            # Wait for task with timeout - if it blocks, this will raise TimeoutError
            await asyncio.wait_for(task, timeout=5.0)
            assert lock_acquired, "Lock should have been acquired"
            assert task_completed, "Task should have completed"
        except asyncio.TimeoutError:
            pytest.fail("Lock acquisition blocked the event loop beyond timeout")

    @pytest.mark.asyncio
    async def test_concurrent_lock_acquisitions(self):
        """Test that multiple concurrent async lock acquisitions work correctly.

        This test verifies that the lock properly serializes access while
        not blocking other tasks from making progress.
        """
        lock = _AsyncCompatibleLock()
        results = []
        execution_order = []

        async def worker(worker_id):
            """Worker that acquires lock and records execution order."""
            async with lock:
                execution_order.append(worker_id)
                # Simulate some work
                await asyncio.sleep(0.01)
                results.append(worker_id)

        # Create multiple concurrent workers
        tasks = [asyncio.create_task(worker(i)) for i in range(5)]

        # Wait for all tasks with timeout
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=10.0)
        except asyncio.TimeoutError:
            pytest.fail("Concurrent lock acquisitions blocked the event loop")

        # Verify all workers completed
        assert len(results) == 5, "All workers should have completed"
        assert len(execution_order) == 5, "All workers should have executed"

        # Verify lock provided mutual exclusion (execution order is sequential)
        assert execution_order == sorted(execution_order), \
            "Lock should have serialized execution"

    @pytest.mark.asyncio
    async def test_lock_with_dedicated_executor(self):
        """Test that lock can work with a dedicated executor.

        This test verifies the behavior when using a dedicated executor
        to avoid thread pool exhaustion.
        """
        lock = _AsyncCompatibleLock()
        lock_acquired = False

        # Create a dedicated executor with limited threads
        from concurrent.futures import ThreadPoolExecutor
        executor = ThreadPoolExecutor(max_workers=1)

        async def acquire_with_dedicated_executor():
            nonlocal lock_acquired
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, lambda: lock._lock.acquire())
            lock_acquired = True
            lock._lock.release()

        try:
            await asyncio.wait_for(acquire_with_dedicated_executor(), timeout=5.0)
            assert lock_acquired, "Lock should have been acquired with dedicated executor"
        except asyncio.TimeoutError:
            pytest.fail("Dedicated executor approach still blocked")
        finally:
            executor.shutdown(wait=True)

    @pytest.mark.asyncio
    async def test_lock_prevents_deadlock_under_load(self):
        """Test that lock doesn't cause deadlock under high concurrent load.

        This test simulates high load to ensure the lock implementation
        doesn't cause deadlocks or event loop blocking.
        """
        lock = _AsyncCompatibleLock()
        counter = 0
        num_tasks = 20

        async def increment_counter():
            nonlocal counter
            async with lock:
                # Simulate some async work while holding lock
                await asyncio.sleep(0.001)
                counter += 1

        # Create many concurrent tasks
        tasks = [asyncio.create_task(increment_counter()) for _ in range(num_tasks)]

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=15.0)
        except asyncio.TimeoutError:
            pytest.fail("Lock caused deadlock under load")

        # Verify all increments happened
        assert counter == num_tasks, \
            f"Expected {num_tasks} increments, got {counter}"
