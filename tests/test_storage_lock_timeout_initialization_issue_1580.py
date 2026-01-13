"""Test for Issue #1580: Verify _timeout_range is properly initialized when using explicit lock_timeout.

This test ensures that when _AsyncCompatibleLock is initialized with an explicit lock_timeout
parameter, the _timeout_range attribute is properly set to None.

Issue: https://github.com/example/flywheel/issues/1580
"""

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_timeout_range_initialization_with_lock_timeout():
    """Test that _timeout_range is initialized to None when lock_timeout is explicitly provided."""
    # Create lock with explicit lock_timeout
    lock = _AsyncCompatibleLock(lock_timeout=5.0)

    # Verify _timeout_range is initialized to None
    assert lock._timeout_range is None
    # Verify _lock_timeout is set to the provided value
    assert lock._lock_timeout == 5.0


def test_timeout_range_initialization_with_timeout_range():
    """Test that _timeout_range is initialized when timeout_range is provided."""
    # Create lock with timeout_range
    lock = _AsyncCompatibleLock(timeout_range=(3.0, 7.0))

    # Verify _timeout_range is initialized to the provided range
    assert lock._timeout_range == (3.0, 7.0)
    # Verify _lock_timeout is set to the midpoint
    assert lock._lock_timeout == 5.0


def test_timeout_range_initialization_with_default():
    """Test that _timeout_range is initialized to None when using default timeout."""
    # Create lock with default parameters
    lock = _AsyncCompatibleLock()

    # Verify _timeout_range is initialized to None
    assert lock._timeout_range is None
    # Verify _lock_timeout is set to default
    assert lock._lock_timeout == 10.0
