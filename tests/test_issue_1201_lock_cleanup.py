"""Test for incomplete cancellation logic in __enter__ exception handler (Issue #1201)."""

import asyncio
import threading
import time
from unittest.mock import Mock, patch

from flywheel.storage import _AsyncCompatibleLock


def test_lock_released_after_timeout_with_delayed_acquisition():
    """Test that lock is properly released when timeout occurs but lock is acquired shortly after.

    This test verifies the fix for Issue #1201: When a TimeoutError occurs during
    lock acquisition, future.cancel() is called. However, if the lock is acquired
    *after* the timeout but *before* the cancellation is processed, the lock will
    be held forever because __exit__ will not be called.

    The fix ensures that even in this race condition, the lock is properly released
    by checking if it's locked in the finally block and releasing it if necessary.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Track if lock was acquired and released
        lock_acquired = threading.Event()
        lock_should_acquire = threading.Event()
        lock_released = threading.Event()

        # Store original acquire method
        original_acquire = lock._lock.acquire

        async def delayed_acquire():
            """Simulate lock acquisition that happens after timeout."""
            # Wait for the signal to proceed with acquisition
            lock_should_acquire.wait(timeout=5)
            # Acquire the lock (simulating it happening after timeout)
            result = await original_acquire()
            lock_acquired.set()
            return result

        # Mock the acquire method
        lock._lock.acquire = delayed_acquire

        # Track the actual asyncio.Lock state
        actual_lock = asyncio.Lock()

        # Replace the internal lock with one we can check
        lock._lock = actual_lock

        # First acquire the lock in the event loop to block subsequent acquisition
        async def hold_lock_briefly():
            """Hold the lock initially, then release it after delay."""
            await actual_lock.acquire()
            # Signal that the test can try to acquire (will block)
            lock_should_acquire.set()
            # Wait a bit longer than the timeout
            await asyncio.sleep(1.5)
            # Now release the lock (simulating delayed acquisition)
            actual_lock.release()
            # Give time for acquisition to complete
            await asyncio.sleep(0.1)

        # Start the lock holder in a task
        lock_holder = asyncio.create_task(hold_lock_briefly())

        # Try to acquire with sync context manager (should timeout)
        with patch.object(lock, '_lock', actual_lock):
            # Wait a bit for the lock holder to acquire
            time.sleep(0.1)

            try:
                # This should timeout
                with lock:
                    pass
            except TimeoutError:
                # This is expected - timeout occurred
                pass

        # Wait for the background task to complete
        try:
            loop.run_until_complete(asyncio.wait_for(lock_holder, timeout=5))
        except asyncio.TimeoutError:
            pass

        # Give time for any pending operations
        time.sleep(0.5)

        # The critical check: the lock should NOT be held
        # If the bug exists, the lock was acquired after timeout but never released
        assert not actual_lock.locked(), (
            "Lock is still held after timeout! This indicates the bug from Issue #1201: "
            "The lock was acquired after timeout but before cancellation was processed, "
            "and was never released because __exit__ was not called."
        )

    finally:
        loop.close()


def test_lock_state_consistent_after_timeout():
    """Test that lock's internal state is consistent after a timeout.

    This test verifies that the _locked flag is properly reset after a timeout,
    preventing state inconsistency.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Acquire the lock first to block subsequent acquisition
        async def hold_lock():
            await lock._lock.acquire()
            await asyncio.sleep(2)  # Hold longer than timeout

        lock_holder = asyncio.create_task(hold_lock())

        # Give time for lock to be acquired
        time.sleep(0.2)

        # Try to acquire with sync context manager (should timeout)
        try:
            with lock:
                pass
        except TimeoutError:
            # Expected - timeout occurred
            pass

        # Wait for holder to complete
        try:
            loop.run_until_complete(asyncio.wait_for(lock_holder, timeout=5))
        except asyncio.TimeoutError:
            pass

        # The _locked flag should be False (reset in finally block)
        assert not lock._locked, (
            "_locked flag is still True after timeout. This indicates state inconsistency "
            "where the internal flag doesn't match the actual lock state."
        )

        # The actual lock should not be held
        assert not lock._lock.locked(), (
            "Actual lock is still held after timeout."
        )

    finally:
        loop.close()


def test_no_lock_leak_on_concurrent_timeout():
    """Test that multiple timeout attempts don't cause lock leaks.

    This test verifies that even with multiple timeout scenarios, the lock
    is properly cleaned up each time.
    """
    lock = _AsyncCompatibleLock()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Track how many times we timeout
        timeout_count = [0]

        async def hold_lock():
            """Hold the lock to force timeouts."""
            await lock._lock.acquire()
            await asyncio.sleep(3)  # Hold longer than timeout

        # Try multiple acquisitions that should timeout
        for i in range(3):
            lock_holder = asyncio.create_task(hold_lock())

            # Give time for lock to be acquired
            time.sleep(0.1)

            try:
                with lock:
                    pass
            except TimeoutError:
                timeout_count[0] += 1

            # Wait for holder to complete or timeout
            try:
                loop.run_until_complete(asyncio.wait_for(lock_holder, timeout=5))
            except asyncio.TimeoutError:
                pass

            # Small delay between attempts
            time.sleep(0.1)

        # All three attempts should have timed out
        assert timeout_count[0] == 3, f"Expected 3 timeouts, got {timeout_count[0]}"

        # The lock should not be held
        assert not lock._lock.locked(), (
            "Lock is still held after multiple timeout attempts. "
            "This indicates a lock leak due to incomplete cleanup."
        )

        # The _locked flag should be False
        assert not lock._locked, (
            "_locked flag is still True after multiple timeout attempts."
        )

    finally:
        loop.close()
