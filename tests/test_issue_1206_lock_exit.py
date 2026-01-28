"""Test for Issue #1206: Verify __exit__ and __aexit__ methods exist and work.

This test verifies that _AsyncCompatibleLock has both __exit__ and __aexit__
methods properly implemented to prevent lock leaks.
"""

import asyncio
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_async_compatible_lock_has_exit_methods():
    """Test that _AsyncCompatibleLock has __exit__ and __aexit__ methods."""
    lock = _AsyncCompatibleLock()

    # Verify __exit__ method exists
    assert hasattr(lock, '__exit__'), "_AsyncCompatibleLock should have __exit__ method"
    assert callable(lock.__exit__), "__exit__ should be callable"

    # Verify __aexit__ method exists
    assert hasattr(lock, '__aexit__'), "_AsyncCompatibleLock should have __aexit__ method"
    assert callable(lock.__aexit__), "__aexit__ should be callable"


def test_sync_context_manager_releases_lock():
    """Test that sync context manager properly releases lock via __exit__."""
    lock = _AsyncCompatibleLock()

    # Lock should not be held initially
    assert not lock._lock.locked(), "Lock should not be held initially"

    # Use sync context manager
    with lock:
        # Lock should be held inside context
        assert lock._lock.locked(), "Lock should be held inside context"

    # Lock should be released after exiting context
    assert not lock._lock.locked(), "Lock should be released after exiting context"


def test_sync_context_manager_releases_lock_on_exception():
    """Test that sync context manager releases lock even when exception occurs."""
    lock = _AsyncCompatibleLock()

    try:
        with lock:
            assert lock._lock.locked(), "Lock should be held inside context"
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Lock should be released even after exception
    assert not lock._lock.locked(), "Lock should be released after exception"


@pytest.mark.asyncio
async def test_async_context_manager_releases_lock():
    """Test that async context manager properly releases lock via __aexit__."""
    lock = _AsyncCompatibleLock()

    # Lock should not be held initially
    assert not lock._lock.locked(), "Lock should not be held initially"

    # Use async context manager
    async with lock:
        # Lock should be held inside context
        assert lock._lock.locked(), "Lock should be held inside context"

    # Lock should be released after exiting context
    assert not lock._lock.locked(), "Lock should be released after exiting context"


@pytest.mark.asyncio
async def test_async_context_manager_releases_lock_on_exception():
    """Test that async context manager releases lock even when exception occurs."""
    lock = _AsyncCompatibleLock()

    try:
        async with lock:
            assert lock._lock.locked(), "Lock should be held inside context"
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Lock should be released even after exception
    assert not lock._lock.locked(), "Lock should be released after exception"


def test_multiple_sync_context_entries():
    """Test that lock can be acquired and released multiple times."""
    lock = _AsyncCompatibleLock()

    for i in range(5):
        with lock:
            assert lock._lock.locked(), f"Lock should be held in iteration {i}"
        assert not lock._lock.locked(), f"Lock should be released in iteration {i}"


@pytest.mark.asyncio
async def test_multiple_async_context_entries():
    """Test that lock can be acquired and released multiple times in async context."""
    lock = _AsyncCompatibleLock()

    for i in range(5):
        async with lock:
            assert lock._lock.locked(), f"Lock should be held in iteration {i}"
        assert not lock._lock.locked(), f"Lock should be released in iteration {i}"


@pytest.mark.asyncio
async def test_mixed_sync_and_async_usage():
    """Test that lock works correctly with mixed sync and async usage.

    Note: This test verifies that the same lock instance can be used
    in both sync and async contexts sequentially (not concurrently).
    """
    lock = _AsyncCompatibleLock()

    # Use in sync context
    with lock:
        assert lock._lock.locked(), "Lock should be held in sync context"

    # Use in async context
    async with lock:
        assert lock._lock.locked(), "Lock should be held in async context"

    # Use in sync context again
    with lock:
        assert lock._lock.locked(), "Lock should be held in sync context again"

    # Verify lock is released
    assert not lock._lock.locked(), "Lock should be finally released"
