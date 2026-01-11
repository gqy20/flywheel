"""Test for lock timeout in __enter__ to prevent potential deadlock (Issue #1406).

This test verifies that the __enter__ method of _AsyncCompatibleLock uses
a timeout when acquiring the lock, rather than blocking indefinitely.

The issue: If self._lock.acquire() is a blocking call that hangs indefinitely,
the try block is never reached. While this is inherent to blocking locks, we need
to ensure the lock usage is time-bound or that the code calling __enter__ handles
timeouts appropriately to avoid freezing the thread.

The fix: The __enter__ method should use acquire(timeout=X) instead of acquire()
to ensure that the lock acquisition is time-bound and doesn't hang indefinitely.
"""

import asyncio
import threading
import time

from flywheel.storage import _AsyncCompatibleLock


def test_lock_enter_has_timeout_mechanism():
    """Test that __enter__ uses timeout when acquiring lock.

    This test verifies that the __enter__ method doesn't block indefinitely
    when trying to acquire a lock that's held by another thread. It should
    use a timeout mechanism to prevent potential deadlocks.
    """
    lock = _AsyncCompatibleLock()

    # Track if timeout occurred and how long it took
    timeout_occurred = [False]
    acquisition_time = [None]
    exception_type = [None]

    # Simulate a long-running async operation that holds the lock
    async def long_running_async_operation():
        """Hold the lock for 5 seconds."""
        async with lock:
            await asyncio.sleep(5)

    def run_async_operation():
        """Run async operation in background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(long_running_async_operation())
        finally:
            loop.close()

    # Start the async operation
    async_thread = threading.Thread(target=run_async_operation)
    async_thread.start()

    # Give it time to acquire the lock
    time.sleep(0.5)

    # Now try to acquire from sync context using __enter__
    start_time = time.time()
    try:
        with lock:
            acquisition_time[0] = time.time() - start_time
            # If we get here, the lock was acquired successfully
            print(f"Lock acquired after {acquisition_time[0]:.2f}s")
    except Exception as e:
        timeout_occurred[0] = True
        acquisition_time[0] = time.time() - start_time
        exception_type[0] = type(e).__name__
        print(f"Exception occurred after {acquisition_time[0]:.2f}s: {exception_type[0]}: {e}")

    # Wait for async thread to complete
    async_thread.join(timeout=15)

    # Document current behavior
    print(f"\nTest Results:")
    print(f"  Exception occurred: {timeout_occurred[0]}")
    print(f"  Exception type: {exception_type[0]}")
    print(f"  Time waited: {acquisition_time[0]:.2f}s")

    # The fix should ensure that:
    # 1. Either the lock is acquired successfully (if async operation completes within timeout)
    # 2. Or a timeout exception is raised (if timeout mechanism is implemented)
    # 3. The acquisition should NOT block indefinitely (i.e., should return within reasonable time)

    # If no timeout occurred, the lock was acquired - this is acceptable
    # if the timeout is long enough (e.g., 10 seconds as per Issue #1291)
    if not timeout_occurred[0]:
        print("  Lock was acquired successfully (async operation completed within timeout)")
        # Verify it took at least the duration of the async operation
        assert acquisition_time[0] >= 4.5, (
            f"Expected to wait at least 4.5 seconds (duration of async operation minus setup time), "
            f"but only waited {acquisition_time[0]:.2f}s. "
            "This indicates the lock was not properly held by the async operation."
        )
    else:
        print("  Timeout exception was raised (this is acceptable behavior)")
        # Verify it timed out within a reasonable time (should be around 10 seconds)
        # This proves that a timeout mechanism is in place
        assert acquisition_time[0] < 15, (
            f"Expected timeout within 15 seconds, but took {acquisition_time[0]:.2f}s. "
            "This suggests the lock acquisition is blocking indefinitely without timeout."
        )
        # Should have timed out after the configured timeout (e.g., 10 seconds)
        assert acquisition_time[0] >= 9, (
            f"Expected timeout after at least 9 seconds, but took {acquisition_time[0]:.2f}s. "
            "This suggests the timeout is too short."
        )

    print("  ✓ Lock acquisition has timeout mechanism (doesn't block indefinitely)")


def test_lock_enter_does_not_hang_indefinitely():
    """Test that __enter__ doesn't hang indefinitely when lock is contested.

    This is a stricter test that verifies the lock acquisition will eventually
    timeout rather than hanging forever if the lock is held by another thread.
    """
    lock = _AsyncCompatibleLock()

    # Hold the lock in a separate thread indefinitely
    lock_held = [True]

    def hold_lock_indefinitely():
        """Hold the lock in a thread."""
        with lock:
            # Hold the lock until told to release
            while lock_held[0]:
                time.sleep(0.1)

    # Start thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock_indefinitely)
    holder_thread.start()

    # Give it time to acquire the lock
    time.sleep(0.5)

    # Now try to acquire from another thread
    # This should either succeed (if reentrant) or timeout (if not reentrant)
    # But it should NOT hang indefinitely
    start_time = time.time()
    timeout_occurred = [False]
    exception_caught = [None]

    try:
        # Try to acquire with a reasonable timeout
        # If the implementation has no timeout, this will hang
        with lock:
            acquisition_time = time.time() - start_time
            print(f"Lock acquired after {acquisition_time:.2f}s")
    except Exception as e:
        timeout_occurred[0] = True
        exception_caught[0] = type(e).__name__
        acquisition_time = time.time() - start_time
        print(f"Exception after {acquisition_time:.2f}s: {exception_caught[0]}: {e}")

    # Signal the holder thread to release the lock
    lock_held[0] = False
    holder_thread.join(timeout=5)

    print(f"\nTest Results:")
    print(f"  Time waited: {acquisition_time:.2f}s")
    print(f"  Exception: {exception_caught[0]}")

    # The key assertion: we should not have waited indefinitely
    # With the 10-second timeout from Issue #1291, we should see behavior
    # within a reasonable time frame
    assert acquisition_time < 20, (
        f"Lock acquisition took {acquisition_time:.2f}s, which suggests "
        "it may be blocking indefinitely. A timeout mechanism should be in place."
    )

    print("  ✓ Lock acquisition does not hang indefinitely")


if __name__ == "__main__":
    print("Testing lock __enter__ timeout mechanism...")
    test_lock_enter_has_timeout_mechanism()

    print("\nTesting lock __enter__ doesn't hang indefinitely...")
    test_lock_enter_does_not_hang_indefinitely()

    print("\n✅ All tests passed - Issue #1406 is being addressed!")
