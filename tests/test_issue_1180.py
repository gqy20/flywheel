"""Test for Issue #1180 - Potential deadlock in _AsyncCompatibleLock.__enter__

This test verifies that when a timeout occurs in __enter__, the underlying
acquire coroutine is properly cancelled to prevent deadlock.
"""
import asyncio
import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_lock_timeout_cancels_future():
    """Test that timeout in __enter__ cancels the acquire future.

    If the timeout occurs, future.result raises TimeoutError, but the
    underlying coroutine self._lock.acquire() is still scheduled on the loop.
    If the lock is eventually acquired in the background thread, it will
    remain locked forever (deadlock) because __exit__ will not be called
    to release it. The future must be cancelled if a timeout occurs.
    """
    lock = _AsyncCompatibleLock()

    # Create a function that holds the lock for a while
    def hold_lock():
        with lock:
            time.sleep(0.5)

    # Start a thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock)
    holder_thread.start()

    # Give the holder thread time to acquire the lock
    time.sleep(0.1)

    # Try to acquire the lock with a timeout
    # This should timeout because the holder thread has the lock
    start_time = time.time()
    with pytest.raises(TimeoutError, match="Failed to acquire lock"):
        with lock:
            pass  # Should timeout before reaching here
    elapsed = time.time() - start_time

    # Should have timed out quickly (around 1 second)
    assert 0.8 < elapsed < 1.5, f"Expected timeout around 1s, got {elapsed:.2f}s"

    # Wait for holder thread to complete
    holder_thread.join()

    # Now try to acquire the lock again
    # If the future was properly cancelled, this should succeed
    # If not, the lock might be stuck (deadlock)
    start_time = time.time()
    try:
        with lock:
            # Successfully acquired - no deadlock
            pass
        success = True
    except Exception as e:
        # Failed to acquire - potential deadlock
        success = False
        print(f"Failed to acquire lock after timeout: {e}")
    elapsed = time.time() - start_time

    # Should acquire quickly if the future was cancelled
    assert success, "Lock acquisition failed after timeout - potential deadlock"
    assert elapsed < 0.5, f"Lock acquisition took too long: {elapsed:.2f}s"


def test_lock_timeout_doesnt_deadlock_async_acquire():
    """Test that timeout in __enter__ doesn't prevent async acquisition.

    After a timeout in sync __enter__, the lock should still be usable
    with async with.
    """
    lock = _AsyncCompatibleLock()

    # Create a function that holds the lock
    def hold_lock():
        with lock:
            time.sleep(0.5)

    # Start a thread that holds the lock
    holder_thread = threading.Thread(target=hold_lock)
    holder_thread.start()

    # Give the holder thread time to acquire the lock
    time.sleep(0.1)

    # Try to acquire the lock with a timeout
    try:
        with lock:
            pass
    except TimeoutError:
        pass  # Expected to timeout

    # Wait for holder thread to complete
    holder_thread.join()

    # Now try async acquisition
    async def try_async_acquire():
        async with lock:
            return True

    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(try_async_acquire())
        assert result is True, "Async acquisition failed after sync timeout"
    finally:
        loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
