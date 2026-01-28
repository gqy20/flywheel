"""Test lock timeout state consistency (Issue #1521).

This test verifies that when _AsyncCompatibleLock times out during __enter__,
the internal state remains consistent and the lock is NOT held.

The critical requirement is:
- When acquire(timeout=X) returns False or raises an exception,
  NO internal state should be modified (especially any _sync_locked flags
  or similar state tracking).

This test ensures that:
1. After a timeout, the underlying lock is NOT held
2. After a timeout, the lock can be successfully acquired by another context
3. The lock state remains consistent after timeout exceptions
"""

import threading
import time
from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


def test_lock_timeout_does_not_hold_lock():
    """Test that after timeout, the lock is NOT held.

    This is the critical test for Issue #1521. When __enter__ times out,
    it must ensure that:
    1. The underlying lock is NOT acquired
    2. No internal state flags are set
    3. Another thread can immediately acquire the lock
    """
    # Create a lock with a very short timeout
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # First, acquire the lock in one thread
    first_acquired = threading.Event()
    first_ready_to_release = threading.Event()

    def holder_thread():
        """Hold the lock for a while."""
        with lock:
            first_acquired.set()  # Signal that we acquired the lock
            # Wait until main thread is ready
            first_ready_to_release.wait(timeout=5.0)

    # Start the holder thread
    holder = threading.Thread(target=holder_thread)
    holder.start()

    # Wait for holder to acquire the lock
    first_acquired.wait(timeout=5.0)
    assert first_acquired.is_set(), "First thread should acquire lock"

    # Now try to acquire the same lock - it should timeout
    # and the lock should NOT be held after the exception
    try:
        with lock:
            # This should timeout and raise StorageTimeoutError
            pass
        # If we get here, the test fails (should have timed out)
        assert False, "Expected StorageTimeoutError but lock was acquired"
    except StorageTimeoutError as e:
        # Expected - lock acquisition timed out
        # CRITICAL: At this point, the lock must NOT be held by current thread
        pass

    # Signal the holder to release
    first_ready_to_release.set()
    holder.join(timeout=5.0)

    # Now try to acquire the lock again - should succeed immediately
    # This proves that the timeout didn't leave the lock in a bad state
    second_acquired = threading.Event()

    def second_thread():
        """Try to acquire the lock after timeout."""
        try:
            with lock:
                second_acquired.set()
        except Exception as e:
            # Should not happen - lock should be available
            raise AssertionError(f"Second thread failed to acquire lock: {e}")

    second = threading.Thread(target=second_thread)
    second.start()
    second.join(timeout=1.0)

    assert second_acquired.is_set(), (
        "Second thread should acquire lock immediately after timeout. "
        "This indicates the timeout left the lock in a bad state."
    )


def test_lock_timeout_state_consistency():
    """Test that internal state remains consistent after timeout.

    This verifies that no internal state flags (like _sync_locked, _async_locked)
    are incorrectly set when a timeout occurs.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # Snapshot initial state
    initial_lock = lock._lock
    initial_async_events = dict(lock._async_events)
    initial_timeout = lock._lock_timeout

    # Create a scenario where timeout will occur
    held = threading.Event()

    def hold_lock():
        with lock:
            held.set()
            time.sleep(2.0)  # Hold longer than timeout

    holder = threading.Thread(target=hold_lock)
    holder.start()
    held.wait(timeout=1.0)

    # Try to acquire - should timeout
    try:
        with lock:
            pass
        assert False, "Should have timed out"
    except StorageTimeoutError:
        pass

    # Wait for holder to complete
    holder.join(timeout=5.0)

    # Verify internal state is unchanged
    assert lock._lock is initial_lock, "Underlying lock object should not change"
    assert lock._async_events == initial_async_events, (
        "Async events dict should not be modified by timeout"
    )
    assert lock._lock_timeout == initial_timeout, (
        "Timeout value should not be modified"
    )

    # Most importantly: the lock should be usable
    # This proves state consistency
    final_acquired = threading.Event()

    def final_thread():
        with lock:
            final_acquired.set()

    final = threading.Thread(target=final_thread)
    final.start()
    final.join(timeout=1.0)

    assert final_acquired.is_set(), (
        "Lock should be usable after timeout - state is consistent"
    )


def test_multiple_timeouts_do_not_corrupt_state():
    """Test that multiple consecutive timeouts don't corrupt state.

    This simulates a high-contention scenario where multiple threads
    timeout trying to acquire the lock.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.1)

    # Hold the lock
    held = threading.Event()
    ready_to_release = threading.Event()

    def holder():
        with lock:
            held.set()
            ready_to_release.wait(timeout=10.0)

    holder_thread = threading.Thread(target=holder)
    holder_thread.start()
    held.wait(timeout=2.0)

    # Multiple threads try and timeout
    timeout_count = {"value": 0}
    threads = []

    def try_acquire():
        try:
            with lock:
                pass
        except StorageTimeoutError:
            timeout_count["value"] += 1

    # Launch multiple concurrent attempts
    for _ in range(5):
        t = threading.Thread(target=try_acquire)
        t.start()
        threads.append(t)

    # Wait for all to timeout
    for t in threads:
        t.join(timeout=5.0)

    assert timeout_count["value"] == 5, (
        f"Expected 5 timeouts, got {timeout_count['value']}"
    )

    # Release the holder
    ready_to_release.set()
    holder_thread.join(timeout=5.0)

    # Now verify lock is still functional
    acquired = threading.Event()

    def final_acquirer():
        with lock:
            acquired.set()

    final = threading.Thread(target=final_acquirer)
    final.start()
    final.join(timeout=1.0)

    assert acquired.is_set(), (
        "Lock should be functional after multiple timeouts"
    )


if __name__ == "__main__":
    print("Running test_lock_timeout_does_not_hold_lock...")
    try:
        test_lock_timeout_does_not_hold_lock()
        print("✓ test_lock_timeout_does_not_hold_lock PASSED")
    except AssertionError as e:
        print(f"✗ test_lock_timeout_does_not_hold_lock FAILED: {e}")

    print("\nRunning test_lock_timeout_state_consistency...")
    try:
        test_lock_timeout_state_consistency()
        print("✓ test_lock_timeout_state_consistency PASSED")
    except AssertionError as e:
        print(f"✗ test_lock_timeout_state_consistency FAILED: {e}")

    print("\nRunning test_multiple_timeouts_do_not_corrupt_state...")
    try:
        test_multiple_timeouts_do_not_corrupt_state()
        print("✓ test_multiple_timeouts_do_not_corrupt_state PASSED")
    except AssertionError as e:
        print(f"✗ test_multiple_timeouts_do_not_corrupt_state FAILED: {e}")
