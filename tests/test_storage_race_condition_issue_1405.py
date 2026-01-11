"""Test for race condition in async lock acquisition (Issue #1405).

This test verifies that the __aenter__ method of _AsyncCompatibleLock properly
handles the race condition between lock acquisition failure and event waiting.

The issue: There is a potential race condition between self._lock.acquire(blocking=False)
failing and await event.wait(). If the lock is released after acquire() fails but before
wait() starts, the event might be set and then cleared before wait() consumes it, or
wait() might wait indefinitely if the event was already set and cleared.

The fix: Use a while loop: `while not self._lock.acquire(blocking=False): await event.wait()`
This ensures that if we miss the event notification, we'll loop back and try again.
"""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


async def test_race_condition_in_lock_acquisition():
    """Test that async lock acquisition handles race condition properly.

    This test simulates the race condition where:
    1. Task A tries to acquire the lock but fails (it's held by another thread)
    2. Task B releases the lock
    3. Task A calls event.wait()

    Without proper looping, Task A might miss the notification if the event
    was already set and cleared before wait() was called.
    """
    lock = _AsyncCompatibleLock()

    # Track whether the async task successfully acquired the lock
    async_task_acquired = [False]
    async_task_started = [False]

    # Task that holds the lock briefly in sync context
    def hold_lock_briefly():
        """Hold the lock for a very short time in a sync context."""
        with lock:
            # Hold the lock for a very short time
            time.sleep(0.05)

    # Async task that tries to acquire the lock
    async def async_acquire_lock():
        """Try to acquire the lock from async context."""
        async_task_started[0] = True
        async with lock:
            async_task_acquired[0] = True
            # Hold the lock briefly
            await asyncio.sleep(0.01)

    # Start the sync thread that will hold the lock
    sync_thread = threading.Thread(target=hold_lock_briefly)

    # Start the async task
    async_task = asyncio.create_task(async_acquire_lock())

    # Give the async task a moment to start
    await asyncio.sleep(0.01)

    # Now start the sync thread which will briefly hold and release the lock
    # This creates a race condition where the lock might be released while
    # the async task is in the middle of its acquisition logic
    sync_thread.start()

    # Wait for both to complete
    await async_task
    sync_thread.join(timeout=5)

    # Verify the async task successfully acquired the lock
    assert async_task_acquired[0], (
        "Async task failed to acquire the lock. "
        "This suggests a race condition where the event notification was missed."
    )

    print("✓ Async task successfully acquired the lock despite race condition")


async def test_concurrent_async_lock_acquisition():
    """Test that multiple async tasks can correctly compete for the lock.

    This test verifies that the while loop in __aenter__ properly handles
    multiple async tasks trying to acquire the same lock.
    """
    lock = _AsyncCompatibleLock()

    # Track which tasks acquired the lock and in what order
    acquisition_order = []
    tasks_completed = [0]

    async def acquire_lock_with_id(task_id):
        """Try to acquire the lock with a specific task ID."""
        async with lock:
            acquisition_order.append(task_id)
            # Hold the lock briefly
            await asyncio.sleep(0.01)
        tasks_completed[0] += 1

    # Start multiple async tasks competing for the same lock
    num_tasks = 5
    tasks = [asyncio.create_task(acquire_lock_with_id(i)) for i in range(num_tasks)]

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)

    # Verify all tasks completed
    assert tasks_completed[0] == num_tasks, (
        f"Expected {num_tasks} tasks to complete, but only {tasks_completed[0]} did. "
        "This suggests some tasks are stuck waiting for the lock."
    )

    # Verify all tasks acquired the lock exactly once
    assert len(acquisition_order) == num_tasks, (
        f"Expected {num_tasks} acquisitions, but got {len(acquisition_order)}. "
        "This suggests the lock acquisition logic is not working correctly."
    )

    print(f"✓ All {num_tasks} async tasks successfully acquired the lock")


async def test_lock_release_during_wait():
    """Test the specific race condition: lock released during wait() call.

    This test verifies that if the lock is released between a failed
    acquire() and the next wait() call, the task still acquires the lock.
    """
    lock = _AsyncCompatibleLock()

    lock_acquired = [False]
    test_completed = [False]

    # Sync task that holds the lock
    def hold_lock():
        """Hold the lock for a short time."""
        with lock:
            time.sleep(0.1)

    # Async task that tries to acquire
    async def async_acquire():
        """Try to acquire from async context."""
        nonlocal lock_acquired, test_completed
        async with lock:
            lock_acquired[0] = True
        test_completed[0] = True

    # Start the sync thread
    sync_thread = threading.Thread(target=hold_lock)
    sync_thread.start()

    # Give it time to acquire the lock
    time.sleep(0.01)

    # Start async task (will fail to acquire initially)
    async_task = asyncio.create_task(async_acquire())

    # The lock will be released while the async task is in its acquisition loop
    # This tests the race condition handling

    # Wait for completion
    await async_task
    sync_thread.join(timeout=5)

    assert lock_acquired[0], (
        "Async task failed to acquire the lock. "
        "The race condition handling may be broken."
    )
    assert test_completed[0], "Test did not complete"

    print("✓ Lock successfully acquired even when released during wait()")


def test_sync_async_interleaved_acquisition():
    """Test interleaved sync and async lock acquisitions.

    This test verifies that the lock correctly handles rapid changes
    between sync and async contexts, which can trigger race conditions.
    """
    lock = _AsyncCompatibleLock()

    results = []
    errors = []

    def sync_acquire(task_id):
        """Acquire lock in sync context."""
        try:
            with lock:
                results.append(('sync', task_id))
                time.sleep(0.02)
        except Exception as e:
            errors.append(('sync', task_id, str(e)))

    async def async_acquire(task_id):
        """Acquire lock in async context."""
        try:
            async with lock:
                results.append(('async', task_id))
                await asyncio.sleep(0.02)
        except Exception as e:
            errors.append(('async', task_id, str(e)))

    async def run_test():
        """Run the interleaved test."""
        # Start multiple sync and async tasks
        tasks = []

        # Create sync threads
        sync_threads = []
        for i in range(3):
            t = threading.Thread(target=sync_acquire, args=(i,))
            sync_threads.append(t)
            t.start()

        # Create async tasks
        for i in range(3):
            task = asyncio.create_task(async_acquire(i))
            tasks.append(task)

        # Wait for all async tasks
        await asyncio.gather(*tasks)

        # Wait for all sync threads
        for t in sync_threads:
            t.join(timeout=10)

    # Run the async test
    asyncio.run(run_test())

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify all acquisitions completed
    assert len(results) == 6, (
        f"Expected 6 acquisitions (3 sync, 3 async), got {len(results)}"
    )

    print(f"✓ All {len(results)} interleaved sync/async acquisitions completed successfully")


if __name__ == "__main__":
    print("Testing race condition in async lock acquisition (Issue #1405)...\n")

    print("Test 1: Race condition between acquire failure and wait...")
    asyncio.run(test_race_condition_in_lock_acquisition())

    print("\nTest 2: Concurrent async lock acquisition...")
    asyncio.run(test_concurrent_async_lock_acquisition())

    print("\nTest 3: Lock released during wait()...")
    asyncio.run(test_lock_release_during_wait())

    print("\nTest 4: Interleaved sync/async acquisition...")
    test_sync_async_interleaved_acquisition()

    print("\n✅ All tests passed - Issue #1405 is being addressed!")
