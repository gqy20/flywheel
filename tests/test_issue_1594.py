"""
Test for Issue #1594: Inconsistent initialization of _lock_timeout attribute

This test verifies that _lock_timeout is always initialized correctly regardless
of which timeout parameters are provided to the _AsyncCompatibleLock constructor.

NOTE: Upon investigation, the issue description appears to be incorrect or refers
to an older version of the code. The current implementation (lines 218-241 in
storage.py) correctly handles all cases:
1. If timeout_range is provided: _lock_timeout is set to the midpoint
2. Else if lock_timeout is provided: _lock_timeout is set to that value
3. Else (both None): _lock_timeout is set to _DEFAULT_LOCK_TIMEOUT (10.0)

All tests pass, confirming that the bug does not exist in the current codebase.
"""
import pytest
from flywheel.storage import _AsyncCompatibleLock


def test_lock_timeout_initialization_with_timeout_range():
    """Test that _lock_timeout is initialized when timeout_range is provided."""
    # Create lock with timeout_range only
    lock = _AsyncCompatibleLock(
        timeout_range=(5.0, 15.0),
        lock_timeout=None
    )

    # Verify _lock_timeout is set to the midpoint
    assert hasattr(lock, '_lock_timeout')
    assert lock._lock_timeout == 10.0  # (5.0 + 15.0) / 2


def test_lock_timeout_initialization_with_lock_timeout():
    """Test that _lock_timeout is initialized when lock_timeout is provided."""
    # Create lock with lock_timeout only
    lock = _AsyncCompatibleLock(
        timeout_range=None,
        lock_timeout=7.5
    )

    # Verify _lock_timeout is set
    assert hasattr(lock, '_lock_timeout')
    assert lock._lock_timeout == 7.5


def test_lock_timeout_initialization_with_defaults():
    """Test that _lock_timeout is initialized with default when no timeout params provided."""
    # Create lock with no timeout parameters
    lock = _AsyncCompatibleLock(
        timeout_range=None,
        lock_timeout=None
    )

    # Verify _lock_timeout is set to default
    assert hasattr(lock, '_lock_timeout')
    # Default should be _DEFAULT_LOCK_TIMEOUT
    assert lock._lock_timeout == lock._DEFAULT_LOCK_TIMEOUT


def test_lock_timeout_accessible():
    """Test that _lock_timeout is accessible without AttributeError."""
    # Create lock with timeout_range
    lock = _AsyncCompatibleLock(
        timeout_range=(3.0, 9.0),
        lock_timeout=None
    )

    # Verify _lock_timeout can be accessed without AttributeError
    try:
        timeout = lock._lock_timeout
        assert timeout == 6.0  # (3.0 + 9.0) / 2
    except AttributeError as e:
        pytest.fail(f"_lock_timeout not accessible: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
