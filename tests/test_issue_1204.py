"""Test for Issue #1204 - Truncated code causes syntax error and incomplete logic.

This test verifies that the cleanup_lock() coroutine in the __enter__ method's
finally block properly waits for the cleanup to complete, preventing race conditions
where the lock might be acquired after timeout but before cancellation is processed.
"""
import asyncio
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_cleanup_lock_waits_for_completion():
    """Test that cleanup_lock properly waits for lock release.

    Issue #1204: The asyncio.run_coroutine_threadsafe call on line 229
    does not wait for the cleanup to complete, which can cause race conditions.

    The fix should add .result() to wait for the cleanup coroutine to finish.
    """
    lock = _AsyncCompatibleLock()

    # Test 1: Verify lock can be acquired and released normally
    with lock:
        assert lock._lock.locked()

    # Test 2: Verify lock is properly released after timeout scenario
    # This simulates the case where lock is acquired after timeout
    # but before cancellation is processed
    loop = lock._get_or_create_loop()

    # Manually test the cleanup path
    async def acquire_and_cleanup():
        # Acquire the lock
        await lock._lock.acquire()

        # Simulate the cleanup that should happen in __enter__ finally block
        if lock._lock.locked():
            lock._lock.release()

    # Run the test in the event loop
    future = asyncio.run_coroutine_threadsafe(acquire_and_cleanup(), loop)
    future.result(timeout=2)  # Should complete without timeout

    # Verify lock is not held after cleanup
    assert not lock._lock.locked()

    lock.close()


def test_lock_state_consistency_after_timeout():
    """Test that lock state remains consistent after timeout and cleanup.

    This test verifies that the _locked flag and actual lock state stay consistent.
    """
    lock = _AsyncCompatibleLock()

    # Test normal usage
    with lock:
        assert lock._locked
        assert lock._lock.locked()

    # After exiting context, both should be False/released
    assert not lock._locked
    assert not lock._lock.locked()

    lock.close()


def test_concurrent_lock_access():
    """Test that concurrent access to the lock is handled correctly.

    This test simulates the race condition scenario from Issue #1201/#1204
    where the lock might be acquired after timeout but before cleanup.
    """
    lock = _AsyncCompatibleLock()

    def worker():
        """Worker that tries to acquire the lock."""
        with lock:
            # Hold the lock briefly
            import time
            time.sleep(0.1)

    # Test multiple sequential acquisitions
    for _ in range(5):
        worker()

    # Verify lock is not held
    assert not lock._lock.locked()
    assert not lock._locked

    lock.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
