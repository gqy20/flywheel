"""Test for Issue #1450: Lock release logic in __enter__ is unreachable and incorrect.

The issue is that the try-except block wrapping `return self` in __enter__ is
problematic because:
1. `return self` cannot raise an exception under normal circumstances
2. If an exception somehow occurs, the lock would be released, but then __exit__
   would be called and try to release it again, causing a RuntimeError
"""

import threading
import time
import pytest

from flywheel.storage import _AsyncCompatibleLock, StorageTimeoutError


def test_enter_lock_simple_acquisition():
    """Test that __enter__ simply acquires lock and returns self."""
    lock = _AsyncCompatibleLock()

    # Basic functionality: __enter__ should acquire the lock
    with lock:
        # Lock should be held inside the context
        assert lock._lock.locked()

    # Lock should be released after exiting
    assert not lock._lock.locked()


def test_enter_no_try_except_double_release():
    """Test that __enter__ doesn't have problematic try-except that could cause double release.

    The issue is that if __enter__ catches an exception and releases the lock,
    then __exit__ would be called by Python's context manager protocol and
    try to release it again, causing a RuntimeError.
    """
    lock = _AsyncCompatibleLock()

    # Normal case: should work fine
    with lock:
        assert lock._lock.locked()

    # Lock should be properly released
    assert not lock._lock.locked()

    # Should be able to acquire again
    with lock:
        assert lock._lock.locked()

    assert not lock._lock.locked()


def test_enter_returns_self_directly():
    """Test that __enter__ returns self without complex exception handling.

    The safest pattern for __enter__ is simply `acquire(); return self`.
    """
    lock = _AsyncCompatibleLock()

    # __enter__ should return the lock instance itself
    result = lock.__enter__()
    assert result is lock

    # Clean up
    lock.__exit__(None, None, None)


def test_enter_timeout_behavior():
    """Test that __enter__ properly handles timeout scenarios."""
    lock1 = _AsyncCompatibleLock()
    lock2 = _AsyncCompatibleLock()

    # Both locks should be able to acquire independently
    with lock1:
        assert lock1._lock.locked()

        # Different lock instances don't block each other
        with lock2:
            assert lock2._lock.locked()
            assert lock1._lock.locked()  # lock1 still held


def test_multiple_context_entries():
    """Test that the lock can be used multiple times in sequence."""
    lock = _AsyncCompatibleLock()

    for i in range(5):
        with lock:
            assert lock._lock.locked()
        assert not lock._lock.locked()


def test_context_manager_exception_handling():
    """Test that exceptions in the context body don't affect lock release."""
    lock = _AsyncCompatibleLock()

    # Exception in context body should still release the lock
    with pytest.raises(ValueError):
        with lock:
            assert lock._lock.locked()
            raise ValueError("Test exception")

    # Lock should be released despite the exception
    assert not lock._lock.locked()

    # Should be able to acquire again
    with lock:
        assert lock._lock.locked()


def test_lock_timeout_with_contested_lock():
    """Test that lock timeout works correctly with contested lock."""
    lock = _AsyncCompatibleLock(lock_timeout=0.1)  # Short timeout for testing

    # Acquire the lock in a thread
    def hold_lock():
        with lock:
            time.sleep(0.3)  # Hold longer than timeout

    thread = threading.Thread(target=hold_lock)
    thread.start()
    time.sleep(0.05)  # Let the thread acquire the lock

    # Try to acquire with timeout - should raise StorageTimeoutError
    with pytest.raises(StorageTimeoutError) as exc_info:
        with lock:
            pass

    assert "Could not acquire lock" in str(exc_info.value)

    thread.join()
