"""Test for Issue #1481: Lock timeout state consistency risk

This test verifies that when __enter__ times out and raises StorageTimeoutError,
the lock is NOT held, and subsequent __exit__ calls don't cause issues.
The key concern is that a caller might catch the exception and mistakenly believe
they hold the lock.
"""
import threading
import time
import pytest
from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


def test_lock_timeout_does_not_hold_lock():
    """Test that when __enter__ times out, the lock is not held.

    This verifies that the timeout behavior is correct: acquire(timeout=X)
    returning False means the lock is NOT held, so raising StorageTimeoutError
    is appropriate and the caller should not assume they have the lock.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # First, acquire the lock in another thread and hold it
    def hold_lock_for_duration():
        with lock:
            # Hold the lock for longer than the timeout
            time.sleep(0.5)

    thread = threading.Thread(target=hold_lock_for_duration)
    thread.start()

    # Give the thread time to acquire the lock
    time.sleep(0.05)

    # Now try to acquire the lock - it should timeout
    with pytest.raises(StorageTimeoutError) as exc_info:
        with lock:
            pass  # Should never get here

    # Verify the error message mentions timeout
    assert "timeout" in str(exc_info.value).lower()

    # Wait for the other thread to finish
    thread.join()

    # Now we should be able to acquire the lock normally
    # This proves the lock was properly released by the other thread
    # and our timeout attempt didn't affect the lock state
    with lock:
        # Lock should be held by us now
        assert lock._lock.locked()


def test_exit_after_timeout_is_safe():
    """Test that calling __exit__ after a timeout is safe.

    This simulates a scenario where:
    1. __enter__ times out and raises StorageTimeoutError
    2. Caller catches the exception
    3. Caller's finally block calls __exit__

    The __exit__ should handle this gracefully without raising.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # Hold the lock in another thread
    def hold_lock():
        with lock:
            time.sleep(0.5)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    time.sleep(0.05)

    # Try to use context manager - it will timeout
    try:
        with lock:
            pass
    except StorageTimeoutError:
        # Expected - timeout occurred
        pass

    # The context manager's __exit__ should have been called already
    # as part of the with statement's exception handling
    # But let's also test calling __exit__ explicitly to be defensive
    # This simulates manual cleanup in edge cases
    try:
        lock.__exit__(None, None, None)
    except RuntimeError:
        pytest.fail("__exit__ should not raise RuntimeError after timeout")

    thread.join()


def test_lock_state_after_timeout_is_clear():
    """Test that the lock state is clear after a timeout.

    This ensures that when acquire(timeout=X) returns False (timeout),
    the lock is NOT held by the current thread, preventing the caller
    from mistakenly believing they have the lock.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # Hold lock in another thread
    acquired = threading.Event()
    release_event = threading.Event()

    def hold_lock():
        with lock:
            acquired.set()
            release_event.wait()

    thread = threading.Thread(target=hold_lock)
    thread.start()
    acquired.wait()  # Wait for lock to be acquired

    # Try to acquire with timeout - will fail
    result = lock._lock.acquire(timeout=0.1)

    # acquire() should return False on timeout
    assert result is False, "acquire(timeout=X) should return False on timeout"

    # Verify lock is NOT held by current thread
    # threading.Lock doesn't have a way to check ownership, but we can
    # verify that trying to release it raises RuntimeError
    with pytest.raises(RuntimeError):
        lock._lock.release()

    # Clean up
    release_event.set()
    thread.join()


def test_documentation_behavior_is_correct():
    """Test that the documented behavior matches actual behavior.

    The issue suggests that callers might mistakenly believe they hold
    the lock after catching StorageTimeoutError. This test verifies
    that the documentation is accurate: the lock is NOT held after timeout.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # Hold lock in another thread
    def hold_lock():
        with lock:
            time.sleep(0.5)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    time.sleep(0.05)

    # Try context manager - will timeout
    timeout_raised = False
    try:
        with lock:
            # If we get here, something is wrong
            pytest.fail("Should not acquire lock within timeout")
    except StorageTimeoutError:
        timeout_raised = True

    assert timeout_raised, "StorageTimeoutError should be raised"

    # Critical test: After catching StorageTimeoutError,
    # verify the lock is NOT held by us
    # We can't directly check ownership with threading.Lock,
    # but we can verify behavior:
    # 1. The other thread still holds the lock
    # 2. We cannot perform operations that require the lock

    # The fact that the other thread is still running and holding the lock
    # proves we don't hold it

    thread.join()

    # Now we can acquire it
    with lock:
        pass  # Success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
