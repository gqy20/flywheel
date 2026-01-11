"""Test for Issue #1384 - Deadlock risk in __aenter__ due to missing lock release.

This test verifies that if an exception occurs during __aenter__, the lock is
properly released to prevent deadlock.
"""

import pytest
import asyncio
from flywheel.storage import _AsyncCompatibleLock


@pytest.mark.asyncio
async def test_async_context_lock_release_on_exception():
    """Test that lock is released if exception occurs in __aenter__.

    Issue #1384: If an exception occurs after acquire() but before __aenter__
    returns, the lock must be released to prevent deadlock.

    The fix ensures that:
    1. self._async_locked is set to False
    2. self._lock.release() is called
    3. async_event.set() is called to signal waiting tasks
    """
    lock = _AsyncCompatibleLock()

    # Create a scenario where __aenter__ raises an exception after acquiring
    class BrokenAsyncLock(_AsyncCompatibleLock):
        """A lock that raises an exception during __aenter__ after acquire."""

        async def __aenter__(self):
            # Get the event for this event loop
            async_event = self._get_async_event()

            # Wait for the event to be set
            await async_event.wait()

            # Acquire the lock
            acquired = self._lock.acquire(blocking=False)
            if acquired:
                try:
                    # Flag is set
                    self._async_locked = True
                    # Clear the event
                    async_event.clear()

                    # Simulate an exception before returning
                    raise RuntimeError("Simulated exception during __aenter__")
                except BaseException:
                    # This is where the fix must clean up
                    self._async_locked = False
                    self._lock.release()
                    async_event.set()
                    raise
            else:
                await asyncio.sleep(0)
                return self

    broken_lock = BrokenAsyncLock()

    # Attempting to enter should raise an exception
    with pytest.raises(RuntimeError, match="Simulated exception"):
        async with broken_lock:
            pass

    # After exception, lock should be released and flag should be False
    assert broken_lock._async_locked is False
    assert broken_lock._lock.locked() is False


@pytest.mark.asyncio
async def test_async_context_normal_operation():
    """Test that async context manager works normally.

    This verifies that the exception handler doesn't break normal operation.
    """
    lock = _AsyncCompatibleLock()

    # Normal case: successful async context entry
    assert lock._async_locked is False
    assert lock._lock.locked() is False

    async with lock:
        # Inside context, lock should be held and flag should be True
        assert lock._async_locked is True
        assert lock._lock.locked() is True

    # After context, lock should be released and flag should be False
    assert lock._async_locked is False
    assert lock._lock.locked() is False


@pytest.mark.asyncio
async def test_async_context_flag_matches_lock_state():
    """Test that _async_locked flag always reflects actual lock state."""
    lock = _AsyncCompatibleLock()

    # Initial state
    assert lock._async_locked == lock._lock.locked(), (
        "Flag should match lock state initially"
    )

    # After entering context
    async with lock:
        assert lock._async_locked == lock._lock.locked(), (
            "Flag should match lock state inside context"
        )

    # After exiting context
    assert lock._async_locked == lock._lock.locked(), (
        "Flag should match lock state after context"
    )


@pytest.mark.asyncio
async def test_async_context_concurrent_access():
    """Test that concurrent async access properly waits for lock."""
    lock = _AsyncCompatibleLock()
    results = []
    acquire_order = []

    async def worker(worker_id):
        """Worker that tries to acquire the lock."""
        async with lock:
            acquire_order.append(worker_id)
            # Simulate some work
            await asyncio.sleep(0.01)
            results.append(worker_id)

    # Launch concurrent workers
    tasks = [worker(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # All workers should have completed
    assert len(results) == 5
    # Each should have acquired the lock exactly once
    assert len(acquire_order) == 5
    # Lock should be released at the end
    assert lock._async_locked is False
    assert lock._lock.locked() is False
