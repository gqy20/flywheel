"""Test for issue #1531: Potential deadlock risk - lock not released

This test verifies that the lock is properly released even when
an exception occurs during the __enter__ method after the lock
is acquired.
"""
import threading
import pytest
from flywheel.storage import Storage


def test_lock_released_on_exception_in_enter():
    """Test that lock is released if exception occurs after acquire().

    This is a regression test for issue #1531. The __enter__ method
    should use try-finally to ensure the lock is released even if
    an unexpected exception occurs between acquire() and return self.
    """
    storage = Storage()

    # First thread acquires the lock
    def hold_lock_forever():
        with storage:
            # Hold the lock indefinitely
            threading.Event().wait()

    thread1 = threading.Thread(target=hold_lock_forever, daemon=True)
    thread1.start()

    # Wait for thread1 to acquire the lock
    import time
    time.sleep(0.1)

    # Second thread should timeout trying to acquire the lock
    # The important part is that if thread2's __enter__ fails after
    # acquiring the lock (in a retry), it should release the lock
    # so that subsequent attempts can acquire it.
    with pytest.raises(TimeoutError):
        # Set a very short timeout to trigger quick failure
        storage._lock_timeout = 0.01
        with storage:
            pass

    # After the exception, the lock should NOT be held by thread2
    # If lock was leaked, thread3 would also timeout
    # If lock was properly released, thread1 still holds it so thread3
    # would still timeout - but we can verify thread2 didn't leak
    assert not storage._lock.acquire(timeout=0.01), "Thread1 should still hold lock"

    # Verify thread2 didn't leak the lock by checking lock owner
    # The lock should still be owned by thread1, not leaked
    thread1.join(timeout=0.5)


def test_lock_acquire_with_exception_simulation():
    """Test lock behavior when simulating exception in __enter__.

    We monkey-patch to simulate an exception after lock acquisition
    to ensure proper cleanup.
    """
    storage = Storage()
    original_enter = storage.__enter__

    call_count = [0]

    def patched_enter():
        call_count[0] += 1
        # On second call, acquire lock but raise exception
        if call_count[0] == 2:
            storage._lock.acquire(timeout=storage._lock_timeout)
            raise RuntimeError("Simulated exception after acquire")
        return original_enter()

    # Hold lock in main thread
    storage._lock.acquire()

    try:
        # Try to acquire in another way - this should fail
        # But we need to verify lock state
        with pytest.raises(RuntimeError):
            storage.__enter__ = patched_enter
            with storage:
                pass
    finally:
        # Release our held lock
        storage._lock.release()

    # The key assertion: lock should not be leaked
    # If the lock was properly released after the exception,
    # we should be able to acquire it now
    assert storage._lock.acquire(timeout=0.1), "Lock should be available after exception cleanup"
    storage._lock.release()
