"""
Test for Issue #1599: Lock timeout logic bypasses user-provided `lock_timeout` when `timeout_range` is provided

This test verifies that when both `lock_timeout` and `timeout_range` are provided,
the explicit `lock_timeout` parameter takes precedence over the calculated midpoint
from `timeout_range`.
"""
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_lock_timeout_takes_precedence_over_timeout_range():
    """
    Test that when both lock_timeout and timeout_range are provided,
    lock_timeout takes precedence.

    This is the failing test for Issue #1599. The current implementation
    silently ignores lock_timeout when timeout_range is present.
    """
    # Create lock with BOTH lock_timeout and timeout_range
    lock = _AsyncCompatibleLock(
        lock_timeout=5.0,
        timeout_range=(10.0, 20.0)
    )

    # The explicit lock_timeout (5.0) should be used, NOT the midpoint (15.0)
    # This test will fail with the current implementation because
    # it calculates (10.0 + 20.0) / 2 = 15.0 instead of using 5.0
    assert lock._lock_timeout == 5.0, (
        f"Expected lock_timeout (5.0) to take precedence, "
        f"but got {lock._lock_timeout}"
    )


def test_lock_timeout_with_none_timeout_range():
    """
    Test that lock_timeout works correctly when timeout_range is explicitly None.
    """
    lock = _AsyncCompatibleLock(
        lock_timeout=8.0,
        timeout_range=None
    )

    assert lock._lock_timeout == 8.0


def test_timeout_range_without_lock_timeout():
    """
    Test that timeout_range midpoint is used when lock_timeout is None.
    """
    lock = _AsyncCompatibleLock(
        lock_timeout=None,
        timeout_range=(10.0, 20.0)
    )

    # Should use midpoint when lock_timeout is None
    assert lock._lock_timeout == 15.0  # (10.0 + 20.0) / 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
