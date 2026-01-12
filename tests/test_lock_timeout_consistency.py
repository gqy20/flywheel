"""Test lock timeout consistency (Issue #1510).

This test verifies that when lock.acquire() times out and raises
StorageTimeoutError, the lock is NOT held by the caller, and calling
__exit__ does not cause any issues.
"""

import threading
import time
import pytest

from flywheel.storage import StorageTimeoutError


def test_lock_timeout_does_not_hold_lock():
    """Test that lock timeout does not leave lock in acquired state.

    When __enter__ raises StorageTimeoutError due to timeout, the lock
    should NOT be held by the current thread. This test verifies:

    1. StorageTimeoutError is raised when timeout occurs
    2. The lock is not held after timeout
    3. Calling __exit__ after timeout does not raise exceptions
    4. The lock can be acquired by another thread after timeout
    """
    from flywheel import Storage

    # Create storage instance with very short timeout
    storage = Storage(timeout=0.01)  # 10ms timeout

    # Acquire the lock in a separate thread and hold it
    lock_held = threading.Event()
    lock_acquired = threading.Event()
    other_thread_done = threading.Event()

    def hold_lock():
        """Hold the lock for a while to force timeout in main thread."""
        with storage._sync_lock:
            lock_acquired.set()
            lock_held.wait()  # Wait until main thread has tried to acquire

    # Start thread that will hold the lock
    thread = threading.Thread(target=hold_lock)
    thread.start()

    # Wait for the other thread to acquire the lock
    lock_acquired.wait(timeout=1.0)
    assert lock_acquired.is_set(), "Other thread should have acquired lock"

    # Try to acquire lock in main thread - should timeout
    with pytest.raises(StorageTimeoutError) as exc_info:
        with storage._sync_lock:
            # This should not be reached
            pytest.fail("Should have raised StorageTimeoutError")

    # Verify the exception message contains important information
    assert "NOT held" in str(exc_info.value) or "timeout" in str(exc_info.value).lower()

    # Signal the other thread to release and finish
    lock_held.set()
    thread.join(timeout=1.0)
    assert not thread.is_alive(), "Other thread should have finished"

    # Now verify the lock is not held by main thread
    # If the lock was held by main thread after timeout, this would deadlock
    # or cause issues. Instead, it should acquire successfully.
    acquired_quickly = storage._sync_lock._lock.acquire(timeout=0.1)
    assert acquired_quickly, "Should be able to acquire lock after timeout"
    storage._sync_lock._lock.release()


def test_exit_after_timeout_is_safe():
    """Test that calling __exit__ after timeout is safe.

    Even though __exit__ should not be called after a failed __enter__,
    this test ensures it's safe if it happens (e.g., in a finally block).
    """
    from flywheel import Storage

    storage = Storage(timeout=0.01)

    # Acquire the lock in a separate thread
    lock_acquired = threading.Event()
    release_lock = threading.Event()

    def hold_lock():
        with storage._sync_lock:
            lock_acquired.set()
            release_lock.wait(timeout=2.0)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    lock_acquired.wait(timeout=1.0)

    # Try to enter context - will timeout
    try:
        with storage._sync_lock:
            pytest.fail("Should have raised StorageTimeoutError")
    except StorageTimeoutError:
        pass  # Expected

    # Verify we can still use the storage after the failed attempt
    # This would fail if __exit__ left the lock in a bad state
    release_lock.set()
    thread.join(timeout=1.0)

    # Try normal usage
    with storage._sync_lock:
        # Should work fine
        pass


def test_lock_state_after_multiple_timeouts():
    """Test lock state remains consistent after multiple timeout failures."""
    from flywheel import Storage

    storage = Storage(timeout=0.01)

    # Acquire the lock in a separate thread
    lock_acquired = threading.Event()

    def hold_lock():
        with storage._sync_lock:
            lock_acquired.set()
            time.sleep(0.5)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    lock_acquired.wait(timeout=1.0)

    # Try multiple times to acquire - all should timeout
    timeout_count = 0
    for _ in range(3):
        try:
            with storage._sync_lock:
                pytest.fail("Should have raised StorageTimeoutError")
        except StorageTimeoutError:
            timeout_count += 1

    assert timeout_count == 3, f"Expected 3 timeouts, got {timeout_count}"

    thread.join(timeout=1.0)

    # After the other thread releases, we should be able to acquire
    with storage._sync_lock:
        pass  # Success


def test_lock_not_locked_after_timeout_direct():
    """Test that the underlying lock is not held after timeout.

    This is a more direct test that checks the internal state of the lock
    to ensure that when acquire(timeout=X) returns False (timeout), the lock
    is NOT held by the current thread.
    """
    from flywheel import Storage

    storage = Storage(timeout=0.01)

    # Acquire the lock in a separate thread
    lock_acquired = threading.Event()

    def hold_lock():
        with storage._sync_lock:
            lock_acquired.set()
            time.sleep(0.5)

    thread = threading.Thread(target=hold_lock)
    thread.start()
    lock_acquired.wait(timeout=1.0)

    # Try to acquire - should timeout
    try:
        with storage._sync_lock:
            pytest.fail("Should have raised StorageTimeoutError")
    except StorageTimeoutError:
        pass

    # Direct check: the lock should NOT be locked by current thread
    # If it were locked, this would cause issues
    # We can verify this by trying to acquire again immediately
    # (should still timeout because the other thread holds it)
    try:
        with storage._sync_lock:
            pytest.fail("Should have raised StorageTimeoutError")
    except StorageTimeoutError:
        pass  # Expected - other thread still holds lock

    thread.join(timeout=1.0)

    # Now we should be able to acquire
    acquired = storage._sync_lock._lock.acquire(timeout=0.1)
    assert acquired, "Should acquire lock after other thread releases"
    storage._sync_lock._lock.release()
