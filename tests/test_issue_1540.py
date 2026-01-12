"""Test for Issue #1540: Lock timeout race condition

This test verifies that when a lock acquisition times out, the lock is NOT
held and no additional acquire() calls are made that could cause indefinite blocking.

The issue describes a potential race condition where if acquire(timeout=...) returns
False (timeout), the code must ensure no subsequent acquire() calls that could block
indefinitely are made.
"""

import threading
import time
import pytest
from src.flywheel.storage import StorageTimeoutError, _AsyncCompatibleLock


def test_lock_timeout_does_not_hold_lock():
    """Test that when lock acquisition times out, the lock is NOT held.

    This is the core issue: if acquire(timeout=X) returns False (timeout),
    the lock must NOT be held by the current thread.
    """
    # Create a lock with a very short timeout
    lock = _AsyncCompatibleLock(lock_timeout=0.01)

    # Acquire the lock in a separate thread and hold it
    def hold_lock():
        with lock:
            # Hold the lock long enough for timeout
            time.sleep(0.5)

    holder_thread = threading.Thread(target=hold_lock)
    holder_thread.start()

    # Give the holder thread time to acquire the lock
    time.sleep(0.02)

    # Try to acquire the lock - this should timeout
    with pytest.raises(StorageTimeoutError):
        with lock:
            pass

    # Wait for holder thread to complete
    holder_thread.join()

    # Now verify the lock can be acquired normally
    # If the lock was held after timeout, this would deadlock or timeout
    acquired = lock._lock.acquire(timeout=0.1)
    assert acquired, "Lock should be releasable after timeout"
    lock._lock.release()


def test_lock_timeout_no_indefinite_blocking():
    """Test that timeout doesn't cause indefinite blocking via subsequent acquire().

    This test ensures that after a timeout, the code path doesn't call
    acquire() without a timeout, which could cause indefinite blocking.
    """
    # Create a lock with very short timeout
    lock = _AsyncCompatibleLock(lock_timeout=0.01)

    # Acquire the lock in a separate thread
    def hold_lock():
        with lock:
            time.sleep(0.5)

    holder_thread = threading.Thread(target=hold_lock)
    holder_thread.start()
    time.sleep(0.02)  # Let holder acquire the lock

    # Try to acquire - should timeout quickly (within ~0.03s due to retries)
    start = time.time()
    with pytest.raises(StorageTimeoutError):
        with lock:
            pass
    elapsed = time.time() - start

    # Should complete within 0.1 seconds (3 retries * 0.01s timeout + small overhead)
    # If there's indefinite blocking, this would take much longer
    assert elapsed < 0.15, f"Timeout took {elapsed:.3f}s, possible indefinite blocking"

    holder_thread.join()


def test_lock_timeout_return_value_checked():
    """Test that acquire(timeout=X) return value is properly checked.

    This verifies that when acquire(timeout=X) returns False (timeout),
    the code doesn't proceed as if the lock was acquired.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.01)

    # Create a scenario where lock is held
    lock._lock.acquire()  # Acquire without timeout

    # Try to acquire with timeout - should return False and raise exception
    with pytest.raises(StorageTimeoutError) as exc_info:
        with lock:
            pass

    # Verify the exception message indicates lock is NOT held
    assert "NOT held" in str(exc_info.value)

    # Release the lock we held
    lock._lock.release()

    # Verify we can now acquire it
    acquired = lock._lock.acquire(timeout=0.1)
    assert acquired
    lock._lock.release()


def test_multiple_contested_locks_timeout():
    """Test multiple threads contesting for lock all timeout properly.

    This stress test ensures that under high contention, all threads that
    timeout do so correctly without holding the lock or causing deadlocks.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.01)
    results = {"successes": 0, "timeouts": 0, "errors": 0}

    def try_acquire_lock(thread_id):
        try:
            with lock:
                # If we got here, we acquired the lock
                results["successes"] += 1
                time.sleep(0.01)  # Hold briefly
        except StorageTimeoutError:
            results["timeouts"] += 1
        except Exception as e:
            results["errors"] += 1
            print(f"Thread {thread_id} unexpected error: {e}")

    # Create many threads that will contest for the lock
    threads = []
    for i in range(20):
        t = threading.Thread(target=try_acquire_lock, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join(timeout=2.0)  # Should complete within 2 seconds

    # Verify results
    assert results["errors"] == 0, f"Got errors: {results['errors']}"
    assert results["successes"] > 0, "At least one thread should succeed"
    assert results["timeouts"] > 0, "At least one thread should timeout"

    # Lock should be available now
    acquired = lock._lock.acquire(timeout=0.1)
    assert acquired, "Lock should be available after all threads complete"
    lock._lock.release()


def test_lock_timeout_preserves_retry_backoff():
    """Test that timeout mechanism respects retry backoff and doesn't block indefinitely.

    This ensures the exponential backoff doesn't cause indefinite blocking
    and that all acquire() calls use timeouts.
    """
    lock = _AsyncCompatibleLock(lock_timeout=0.01)

    # Hold the lock
    lock._lock.acquire()

    start = time.time()
    with pytest.raises(StorageTimeoutError):
        with lock:
            pass
    elapsed = time.time() - start

    # With 3 retries and exponential backoff, should complete quickly
    # Even with backoff delays, should be well under 1 second
    assert elapsed < 0.5, f"Timeout with backoff took {elapsed:.3f}s, may indicate indefinite blocking"

    lock._lock.release()
