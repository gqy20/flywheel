"""
Test for Issue #1386: Inconsistent lock state management in __exit__.

This test verifies that __exit__ correctly releases the underlying lock
even when the _sync_locked flag is inconsistent with the actual lock state.
"""

import threading
import time
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_exit_releases_lock_when_flag_is_inconsistent():
    """
    Test that __exit__ releases the lock even if _sync_locked flag is False
    but the lock is actually held.

    This simulates a scenario where __enter__ succeeded (acquired the lock)
    but _sync_locked was not set to True due to some unexpected condition.
    """
    lock = _AsyncCompatibleLock()

    # Manually acquire the lock (simulating __enter__ acquiring but flag not set)
    lock._lock.acquire()
    # Ensure the flag is False (simulating the inconsistent state)
    lock._sync_locked = False

    # Verify lock is held
    assert lock._lock.locked()

    # Call __exit__ directly
    result = lock.__exit__(None, None, None)

    # After __exit__, the lock should be released even though flag was False
    # Current implementation will NOT release the lock, causing this test to fail
    assert not lock._lock.locked(), "Lock should be released after __exit__"
    assert result is False


def test_exit_handles_locked_flag_correctly():
    """
    Test that __exit__ works correctly when flag is properly set.
    """
    lock = _AsyncCompatibleLock()

    # Normal case: __enter__ sets flag correctly
    lock._lock.acquire()
    lock._sync_locked = True

    assert lock._lock.locked()
    assert lock._sync_locked is True

    # Call __exit__
    lock.__exit__(None, None, None)

    # Lock should be released and flag cleared
    assert not lock._lock.locked()
    assert lock._sync_locked is False


def test_exit_is_idempotent():
    """
    Test that calling __exit__ multiple times doesn't cause errors.
    """
    lock = _AsyncCompatibleLock()

    # Normal usage
    lock._lock.acquire()
    lock._sync_locked = True

    # First __exit__
    lock.__exit__(None, None, None)

    # Second __exit__ should not raise any errors
    lock.__exit__(None, None, None)

    assert not lock._lock.locked()
    assert lock._sync_locked is False


def test_concurrent_access_with_inconsistent_state():
    """
    Test that inconsistent lock state doesn't cause deadlock in concurrent scenarios.
    """
    lock = _AsyncCompatibleLock()
    results = {"acquired": False, "errors": []}

    def worker():
        try:
            # Try to acquire lock with timeout
            with lock:
                results["acquired"] = True
                time.sleep(0.01)
        except Exception as e:
            results["errors"].append(str(e))

    # Manually create inconsistent state
    lock._lock.acquire()
    lock._sync_locked = False

    # Try to acquire from another thread
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=1.0)

    # Clean up
    if lock._lock.locked():
        lock._lock.release()

    # The worker should either acquire the lock or timeout cleanly
    assert thread.is_alive() is False, "Thread should have completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
