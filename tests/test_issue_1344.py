"""Test for Issue #1344: Race condition in lock state management.

This test verifies that the lock state is managed atomically and correctly
in the _AsyncCompatibleLock.__enter__ method to prevent race conditions.
"""

import threading
import time
from flywheel.storage import _AsyncCompatibleLock


def test_lock_state_consistency_under_stress():
    """Test that lock state remains consistent under concurrent stress.

    This test creates multiple threads that repeatedly acquire and release
    the lock to verify that _sync_locked is always consistent with the actual
    lock state.

    The race condition in the original code:
        1. self._lock.acquire() succeeds
        2. Signal/interrupt occurs before self._sync_locked = True
        3. __exit__ checks _sync_locked and doesn't release the lock
        4. Lock is permanently held

    The fix ensures that state update is atomic with lock acquisition.
    """
    lock = _AsyncCompatibleLock()
    errors = []
    success_count = [0]  # Use list for mutable share across threads

    def worker():
        """Worker that acquires and releases lock multiple times."""
        try:
            for _ in range(100):
                with lock:
                    # Simulate some work
                    time.sleep(0.0001)
                success_count[0] += 1
        except Exception as e:
            errors.append(e)

    # Launch multiple threads to create contention
    threads = []
    for _ in range(10):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    # Wait for all threads to complete
    for t in threads:
        t.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Verify all operations completed successfully
    assert success_count[0] == 1000, f"Expected 1000 successful operations, got {success_count[0]}"

    # Verify final state is consistent
    assert lock._sync_locked is False, "Lock should not be held after all contexts exit"
    assert lock._lock.locked() is False, "Internal RLock should not be locked"


def test_lock_state_after_exception_in_context():
    """Test that lock state is consistent even if exception occurs in context.

    This verifies that __exit__ properly cleans up even when an exception
    occurs within the with block.
    """
    lock = _AsyncCompatibleLock()

    try:
        with lock:
            assert lock._sync_locked is True
            assert lock._lock.locked() is True
            raise ValueError("Test exception")
    except ValueError:
        pass

    # State should be clean after exception
    assert lock._sync_locked is False, "_sync_locked should be False after exception"
    assert lock._lock.locked() is False, "Lock should be released after exception"


def test_reentrant_lock_state_consistency():
    """Test that reentrant acquisition maintains consistent state.

    RLock allows the same thread to acquire the lock multiple times.
    This test verifies that state tracking works correctly with reentrancy.
    """
    lock = _AsyncCompatibleLock()

    # First acquisition
    with lock:
        assert lock._sync_locked is True
        assert lock._lock.locked() is True

        # Second acquisition (reentrant)
        with lock:
            assert lock._sync_locked is True
            assert lock._lock.locked() is True

        # Still locked after inner context exits
        assert lock._sync_locked is True
        assert lock._lock.locked() is True

    # Fully released after outer context exits
    assert lock._sync_locked is False
    assert lock._lock.locked() is False


def test_no_double_release():
    """Test that lock cannot be released twice.

    This test verifies that calling __exit__ without __enter__ (or multiple
    __exit__ calls) doesn't cause errors.
    """
    lock = _AsyncCompatibleLock()

    # Direct __exit__ without __enter__ should not cause issues
    lock.__exit__(None, None, None)
    assert lock._sync_locked is False

    # Normal usage
    with lock:
        assert lock._sync_locked is True

    # Double __exit__ should be safe
    lock.__exit__(None, None, None)
    assert lock._sync_locked is False
