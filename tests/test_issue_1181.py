"""Test for Issue #1181: Unsafe lock release in _AsyncCompatibleLock.__exit__

This test verifies that releasing an asyncio.Lock without holding it doesn't cause
RuntimeError. If __enter__ timed out or failed, the lock wasn't acquired, but __exit__
might still be called (e.g., in a finally block).
"""
import asyncio
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_exit_without_enter_should_not_raise():
    """Test that __exit__ without __enter__ doesn't raise RuntimeError.

    This simulates the case where __enter__ times out or fails, but __exit__
    is still called (e.g., in a finally block). The lock should track whether
    it was acquired to avoid unsafe release.
    """
    lock = _AsyncCompatibleLock()

    # Call __exit__ without calling __enter__
    # This should not raise RuntimeError: Lock is not acquired
    try:
        lock.__exit__(None, None, None)
    except RuntimeError as e:
        if "Lock is not acquired" in str(e) or "not acquired" in str(e).lower():
            pytest.fail(f"__exit__ raised unsafe lock release error: {e}")


def test_exit_after_timeout_should_not_raise():
    """Test that __exit__ after __enter__ timeout doesn't raise RuntimeError.

    This simulates a real scenario where __enter__ times out (e.g., due to deadlock),
    and the cleanup code in finally block calls __exit__.
    """
    lock = _AsyncCompatibleLock()

    # Acquire the lock in a way that will cause timeout on another attempt
    # First, acquire it properly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Acquire the lock in this thread
        future = asyncio.run_coroutine_threadsafe(lock._lock.acquire(), loop)
        future.result(timeout=1)

        # Now try to use the lock with context manager - it will timeout
        # because the lock is already held
        try:
            with lock:
                pass
        except TimeoutError:
            # Expected - the lock acquisition timed out
            pass

        # The __exit__ should have been called despite timeout
        # It should not raise RuntimeError for releasing an unacquired lock

    finally:
        loop.call_soon_threadsafe(lock._lock.release)
        loop.close()


def test_normal_context_manager_usage():
    """Test that normal context manager usage still works correctly."""
    lock = _AsyncCompatibleLock()

    with lock:
        # Lock should be held here
        assert lock._lock.locked()

    # Lock should be released here
    assert not lock._lock.locked()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
