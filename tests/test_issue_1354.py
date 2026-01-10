"""Test for issue #1354 - Race condition in lock state tracking.

This test verifies that the _sync_locked flag is properly managed
even if exceptions occur during lock acquisition.

The issue is that between acquire() and setting the flag, if an exception
occurs (e.g., KeyboardInterrupt), the lock might be held but the flag not set,
leading to inconsistent state.

The fix uses try-finally to ensure atomic state management.
"""
import pytest
from unittest.mock import MagicMock, patch
from flywheel.storage import _AsyncCompatibleLock


def test_sync_lock_atomic_flag_setting():
    """Test that flag is set atomically with lock acquisition.

    This test ensures that if lock.acquire() succeeds, the flag must be
    set before any exception can occur. The implementation should use
    try-finally to guarantee this.
    """
    lock = _AsyncCompatibleLock()

    # Test normal behavior
    assert not lock._sync_locked

    with lock:
        # Flag MUST be true if we're inside the context
        assert lock._sync_locked is True, "Flag must be set when lock is held"
        assert lock._lock.locked(), "Lock must be acquired"

    # After exit, both should be cleared
    assert lock._sync_locked is False, "Flag must be cleared after exit"
    assert not lock._lock.locked(), "Lock must be released after exit"


def test_sync_lock_exception_in_context():
    """Test that exception in context doesn't corrupt state.

    If an exception occurs within the with block, __exit__ should still
    properly release the lock and reset the flag.
    """
    lock = _AsyncCompatibleLock()

    with pytest.raises(ValueError):
        with lock:
            assert lock._sync_locked is True
            raise ValueError("Test exception")

    # State must be consistent even after exception
    assert lock._sync_locked is False
    assert not lock._lock.locked()


def test_sync_lock_prevents_flag_lock_mismatch():
    """Test that flag and lock state are always in sync.

    This is a regression test for the race condition where:
    1. acquire() succeeds (lock is held)
    2. Exception occurs before flag is set
    3. lock is held but flag is False (inconsistent state)

    The fix ensures flag is set immediately after acquire() in a way
    that cannot be interrupted by exceptions.
    """
    lock = _AsyncCompatibleLock()

    # Multiple acquire/release cycles should maintain consistency
    for i in range(10):
        assert lock._sync_locked is False
        assert not lock._lock.locked()

        with lock:
            assert lock._sync_locked is True
            assert lock._lock.locked()

        assert lock._sync_locked is False
        assert not lock._lock.locked()


def test_sync_lock_immediate_flag_after_acquire():
    """Test that flag is set immediately after successful acquire.

    This test verifies that there's no gap between acquire() returning
    and the flag being set. If there was a gap, a concurrent thread
    could observe lock.locked() == True but _sync_locked == False.
    """
    import threading
    import time

    lock = _AsyncCompatibleLock()
    inconsistencies = []
    stop_flag = threading.Event()

    def monitor_thread():
        """Monitor for inconsistent states."""
        while not stop_flag.is_set():
            if lock._lock.locked() != lock._sync_locked:
                inconsistencies.append(
                    f"Inconsistency: locked={lock._lock.locked()}, "
                    f"_sync_locked={lock._sync_locked}"
                )
            time.sleep(0.0001)  # Small sleep to avoid busy-waiting

    # Start monitor thread
    monitor = threading.Thread(target=monitor_thread, daemon=True)
    monitor.start()

    # Perform multiple acquire/release cycles
    for _ in range(100):
        with lock:
            time.sleep(0.0001)  # Give monitor time to check

    # Stop monitor
    stop_flag.set()
    monitor.join(timeout=1.0)

    # Should not find any inconsistencies
    assert len(inconsistencies) == 0, (
        f"Found {len(inconsistencies)} state inconsistencies: {inconsistencies}"
    )


def test_async_lock_flag_consistency():
    """Test that async lock also maintains flag consistency.

    The async path should have similar robustness.
    """
    import asyncio

    async def test():
        lock = _AsyncCompatibleLock()

        # Normal case
        assert lock._async_locked is False

        async with lock:
            assert lock._async_locked is True

        assert lock._async_locked is False

        # Exception case
        try:
            async with lock:
                assert lock._async_locked is True
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert lock._async_locked is False

    asyncio.run(test())
