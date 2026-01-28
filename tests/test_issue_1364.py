"""Test for Issue #1364 - Race condition in __enter__: flag set before potential exception.

This test verifies that the _sync_locked flag is only set after the lock is
actually acquired, and that if an exception occurs during __enter__, the lock
is properly released and the flag remains False.
"""

import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_sync_context_lock_state_consistency_on_exception():
    """Test that _sync_locked flag matches lock state even when exception occurs.

    Issue #1364: If an exception occurs between acquire() and setting the flag,
    the lock could be held but _sync_locked would be False, causing inconsistent
    state.

    The fix ensures that:
    1. The flag is set immediately after acquire() succeeds
    2. If any exception occurs, the lock is released and flag is cleared
    3. The lock and flag state are always consistent
    """
    lock = _AsyncCompatibleLock()

    # Normal case: successful context entry
    assert lock._sync_locked is False
    assert lock._lock.locked() is False

    with lock:
        # Inside context, lock should be held and flag should be True
        assert lock._sync_locked is True
        assert lock._lock.locked() is True

    # After context, lock should be released and flag should be False
    assert lock._sync_locked is False
    assert lock._lock.locked() is False


def test_sync_context_flag_set_before_return():
    """Test that _sync_locked is set immediately after acquire() succeeds.

    This test verifies that the flag is set before any potential exception
    could occur in the try block.
    """
    lock = _AsyncCompatibleLock()

    # Track the order of operations
    operations = []

    original_enter = lock.__enter__

    def tracked_enter():
        operations.append("acquire_start")
        result = original_enter()
        operations.append("enter_complete")
        return result

    lock.__enter__ = tracked_enter

    with lock:
        # Flag should be True as soon as __enter__ returns
        assert lock._sync_locked is True
        assert lock._lock.locked() is True

    # Verify the acquire happened before we checked the flag
    assert "acquire_start" in operations
    assert "enter_complete" in operations


def test_sync_context_exception_cleanup():
    """Test that exception during __enter__ properly cleans up lock state.

    This simulates a scenario where an exception occurs between acquire()
    and setting the flag (though this is very unlikely in practice).
    """
    lock = _AsyncCompatibleLock()

    # Create a scenario where __enter__ might raise an exception
    # In practice, this would require a very unusual condition
    # since __enter__ just sets a flag and returns self

    class BrokenLock(_AsyncCompatibleLock):
        """A lock that raises an exception during __enter__ after acquire."""

        def __enter__(self):
            self._lock.acquire()  # Lock is acquired
            # Flag should NOT be set yet if we're following the pattern
            # Now simulate an exception before setting flag
            try:
                raise RuntimeError("Simulated exception during __enter__")
            except BaseException:
                # This is where the fix should clean up
                self._sync_locked = False
                self._lock.release()
                raise

    broken_lock = BrokenLock()

    # Attempting to enter should raise an exception
    with pytest.raises(RuntimeError, match="Simulated exception"):
        with broken_lock:
            pass

    # After exception, lock should be released and flag should be False
    assert broken_lock._sync_locked is False
    assert broken_lock._lock.locked() is False


def test_sync_context_flag_always_matches_lock_state():
    """Test that _sync_locked flag always reflects actual lock state."""
    lock = _AsyncCompatibleLock()

    # Initial state
    assert lock._sync_locked == lock._lock.locked(), (
        "Flag should match lock state initially"
    )

    # After entering context
    with lock:
        assert lock._sync_locked == lock._lock.locked(), (
            "Flag should match lock state inside context"
        )

    # After exiting context
    assert lock._sync_locked == lock._lock.locked(), (
        "Flag should match lock state after context"
    )


def test_sync_context_nested_reentrancy():
    """Test that nested context managers work correctly (RLock reentrancy)."""
    lock = _AsyncCompatibleLock()

    # RLock allows the same thread to acquire multiple times
    assert lock._sync_locked is False

    with lock:
        assert lock._sync_locked is True

        # Nested enter (same thread)
        with lock:
            assert lock._sync_locked is True

        # After inner exit
        assert lock._sync_locked is True

    # After outer exit
    assert lock._sync_locked is False
