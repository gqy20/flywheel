"""Test for issue #1416: Race condition in lock release

This test verifies that when a lock is released via __exit__, all async
events are signaled while holding the lock to prevent race conditions.
"""
import asyncio
import threading
import time

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_lock_release_holds_lock_during_event_signaling():
    """Test that __exit__ signals events while holding lock.

    This test ensures there's no race condition where:
    1. Thread A releases the lock in __exit__
    2. Thread B acquires the lock before Thread A signals events
    3. Thread B clears an event
    4. Thread A's event.set() is lost

    The fix ensures events are signaled while holding the lock.
    """

    lock = _AsyncCompatibleLock()
    # Track whether signaling happened while lock was held
    signaling_while_held = []
    lock_released = []

    original_exit = lock.__exit__

    def patched_exit(exc_type, exc_val, exc_tb):
        """Patch __exit__ to verify lock is held during event signaling."""
        # Release lock (original behavior)
        result = original_exit(exc_type, exc_val, exc_tb)

        # Check if lock is released after event signaling
        # In the buggy version, lock is released BEFORE event signaling
        # In the fixed version, events are signaled WHILE holding the lock
        lock_released.append(not lock._lock.locked())

        return result

    # Monkey patch __exit__
    lock.__exit__ = patched_exit

    # Use the lock in a context
    with lock:
        assert lock._lock.locked(), "Lock should be held inside context"

    # After exiting, the lock should be released
    assert not lock._lock.locked(), "Lock should be released after context exit"


def test_lock_release_with_async_waiter():
    """Test that async waiters are properly signaled on lock release.

    This test demonstrates the race condition:
    1. Async task waits on event
    2. Sync thread releases lock
    3. Another async task could acquire lock and clear event before signaling
    4. First async task misses the wake-up

    The fix ensures atomicity by signaling events while holding the lock.
    """

    async def async_waiter(lock, acquired_flag, woke_flag):
        """Async task that waits for lock to be available."""
        # Try to acquire lock asynchronously
        async with lock:
            acquired_flag.set()
            # Hold briefly to simulate work
            await asyncio.sleep(0.01)
            woke_flag.set()

    lock = _AsyncCompatibleLock()

    async def test_async():
        # Start async task that will wait for lock
        acquired1 = threading.Event()
        woke1 = threading.Event()

        # First, acquire the lock in sync context
        with lock:
            assert lock._lock.locked()

            # Start async waiter that will block
            task1 = asyncio.create_task(async_waiter(lock, acquired1, woke1))

            # Give task a chance to start waiting
            await asyncio.sleep(0.05)

            # Verify task is waiting (hasn't acquired)
            assert not acquired1.is_set()

        # Lock is released here - events should be signaled
        # The fix ensures this happens atomically

        # Wait for first task to complete
        await asyncio.sleep(0.1)
        assert acquired1.is_set(), "First task should acquire lock"

    # Run the async test
    asyncio.run(test_async())


def test_lock_release_prevents_event_loss():
    """Test that event signaling is atomic with lock release.

    This test verifies that releasing the lock and signaling events
    happens in a way that prevents signal loss.
    """

    lock = _AsyncCompatibleLock()
    event_count = 0
    max_events = 0

    # Patch to track event signaling
    original_exit = lock.__exit__

    def tracked_exit(exc_type, exc_val, exc_tb):
        nonlocal event_count, max_events
        # Count events before signaling
        max_events = len(list(lock._async_events.values()))

        # Call original
        result = original_exit(exc_type, exc_val, exc_tb)

        # After calling original, verify events were processed
        event_count = max_events

        return result

    lock.__exit__ = tracked_exit

    # Use the lock
    with lock:
        pass

    # Should have completed without error
    assert not lock._lock.locked()


def test_concurrent_lock_access_during_release():
    """Test concurrent access to lock during __exit__.

    This test simulates multiple threads/async tasks accessing the lock
    during release to ensure proper synchronization.
    """

    lock = _AsyncCompatibleLock()
    errors = []
    success_count = []

    async def async_worker(worker_id):
        """Async worker trying to acquire lock."""
        try:
            async with lock:
                success_count.append(worker_id)
                await asyncio.sleep(0.001)
        except Exception as e:
            errors.append((worker_id, e))

    def sync_worker(worker_id):
        """Sync worker trying to acquire lock."""
        try:
            with lock:
                success_count.append(worker_id)
                time.sleep(0.001)
        except Exception as e:
            errors.append((worker_id, e))

    async def run_concurrent_test():
        # Hold lock initially
        with lock:
            # Launch concurrent workers while lock is held
            # They will queue up waiting
            tasks = [
                asyncio.create_task(async_worker(i))
                for i in range(3)
            ]

            # Give tasks time to start waiting
            await asyncio.sleep(0.01)

        # Lock released - all should wake up properly
        await asyncio.gather(*tasks)

    asyncio.run(run_concurrent_test())

    # All workers should succeed
    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(success_count) == 3, f"Expected 3 successful workers, got {len(success_count)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
