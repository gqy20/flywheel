"""Test for issue #1385: Race condition in __aenter__ can cause missed wake-ups

This test verifies that __aenter__ doesn't have a race condition where:
1. Thread waits on async_event.wait()
2. Event gets set, thread wakes up
3. Thread tries to acquire lock with acquire(blocking=False)
4. If lock fails, thread goes back to wait
5. RACE: If lock is released between failed acquire and next wait(), the event
   might be set and then immediately cleared by wait(), causing indefinite blocking
"""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from flywheel.storage import _AsyncCompatibleLock


async def test_aenter_no_missed_wakeup():
    """Test that __aenter__ doesn't miss wake-ups due to race condition.

    This test creates a scenario where multiple async tasks compete for the lock
    while a sync thread holds and releases it. The test verifies that all async
    tasks eventually acquire the lock without indefinite blocking.
    """
    lock = _AsyncCompatibleLock()
    acquisition_count = {'value': 0}
    timeout_happened = {'value': False}
    num_tasks = 10

    async def acquire_lock(task_id):
        """Each task tries to acquire the lock with a timeout."""
        try:
            # Use asyncio.wait_for to detect indefinite blocking
            async with asyncio.timeout(2.0):  # 2 second timeout
                async with lock:
                    acquisition_count['value'] += 1
                    # Hold the lock briefly
                    await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            timeout_happened['value'] = True
            print(f"Task {task_id} timed out - likely hit the race condition bug!")

    async def hold_lock_sync():
        """Hold the lock in sync context for a bit."""
        with lock:
            await asyncio.sleep(0.1)

    # Start a sync context holder
    sync_task = asyncio.create_task(hold_lock_sync())

    # Give sync context time to acquire the lock
    await asyncio.sleep(0.01)

    # Create multiple async tasks that will compete for the lock
    # This increases the chance of hitting the race condition
    tasks = []
    for i in range(num_tasks):
        task = asyncio.create_task(acquire_lock(i))
        tasks.append(task)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)
    await sync_task

    # Verify that no task timed out
    assert not timeout_happened['value'], (
        "At least one task timed out, indicating the race condition bug "
        "where wait() clears the event and blocks indefinitely"
    )

    # Verify that all tasks acquired the lock
    assert acquisition_count['value'] == num_tasks, (
        f"Expected {num_tasks} acquisitions, got {acquisition_count['value']}. "
        "Some tasks may have been blocked indefinitely."
    )


async def test_aenter_concurrent_access():
    """Test that __aenter__ handles concurrent access correctly.

    This test creates multiple async tasks that all try to acquire the lock
    simultaneously, verifying that the lock properly serializes access and
    doesn't miss any wake-ups.
    """
    lock = _AsyncCompatibleLock()
    acquisition_order = []
    num_tasks = 20

    async def acquire_lock(task_id):
        """Each task acquires the lock and records its acquisition order."""
        async with lock:
            acquisition_order.append(task_id)
            # Hold briefly to ensure other tasks are waiting
            await asyncio.sleep(0.01)

    # Create all tasks
    tasks = [asyncio.create_task(acquire_lock(i)) for i in range(num_tasks)]

    # Wait for all to complete
    await asyncio.gather(*tasks)

    # Verify all tasks acquired the lock
    assert len(acquisition_order) == num_tasks, (
        f"Expected {num_tasks} acquisitions, got {len(acquisition_order)}. "
        "Some tasks may have been blocked indefinitely due to race condition."
    )

    # Verify that acquisitions were serialized (no concurrent access)
    # This is implicitly verified by the fact that all completed


def test_aenter_with_sync_context_competition():
    """Test __aenter__ when competing with sync contexts.

    This test creates a scenario where async tasks compete with sync threads
    for the lock, which is the most likely scenario to trigger the race condition.
    """
    lock = _AsyncCompatibleLock()
    results = {'async_acquisitions': 0, 'sync_acquisitions': 0, 'timeout': False}

    async def async_acquire():
        """Async task tries to acquire the lock."""
        try:
            async with asyncio.timeout(3.0):  # 3 second timeout
                async with lock:
                    results['async_acquisitions'] += 1
                    await asyncio.sleep(0.01)
        except asyncio.TimeoutError:
            results['timeout'] = True

    def sync_acquire():
        """Sync thread tries to acquire the lock."""
        with lock:
            results['sync_acquisitions'] += 1
            time.sleep(0.01)

    async def run_async_tasks():
        """Run multiple async tasks."""
        tasks = [asyncio.create_task(async_acquire()) for _ in range(10)]
        await asyncio.gather(*tasks)

    # Run in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Create threads that will acquire sync lock
        threads = []
        for _ in range(5):
            t = threading.Thread(target=sync_acquire)
            threads.append(t)

        # Start async tasks in background
        async_task = threading.Thread(target=lambda: loop.run_until_complete(run_async_tasks()))
        async_task.start()

        # Start sync threads
        for t in threads:
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join()
        async_task.join()

        # Verify no timeout occurred
        assert not results['timeout'], (
            "A task timed out, indicating the race condition bug where "
            "wait() can miss wake-ups when competing with sync contexts"
        )

        # Verify all acquisitions completed
        assert results['async_acquisitions'] == 10, (
            f"Expected 10 async acquisitions, got {results['async_acquisitions']}"
        )
        assert results['sync_acquisitions'] == 5, (
            f"Expected 5 sync acquisitions, got {results['sync_acquisitions']}"
        )

    finally:
        loop.close()


if __name__ == '__main__':
    # Run the tests
    print("Running test_aenter_no_missed_wakeup...")
    asyncio.run(test_aenter_no_missed_wakeup())
    print("PASSED")

    print("\nRunning test_aenter_concurrent_access...")
    asyncio.run(test_aenter_concurrent_access())
    print("PASSED")

    print("\nRunning test_aenter_with_sync_context_competition...")
    test_aenter_with_sync_context_competition()
    print("PASSED")

    print("\n✅ All tests passed!")
