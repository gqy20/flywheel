"""Test for Issue #1444: Verify _AsyncCompatibleLock methods are complete.

This test verifies that the issue #1444 report is inaccurate - the code
is NOT truncated and all methods (__exit__, __aenter__, __aexit__) are
properly implemented and functional.
"""

import asyncio
import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_async_compatible_lock_exit_method_complete():
    """Test that __exit__ method is complete and functional."""
    lock = _AsyncCompatibleLock()

    # Verify __exit__ method exists and is callable
    assert hasattr(lock, '__exit__'), "_AsyncCompatibleLock should have __exit__ method"
    assert callable(lock.__exit__), "__exit__ should be callable"

    # Verify __exit__ has proper docstring
    assert lock.__exit__.__doc__ is not None, "__exit__ should have docstring"
    assert "Release lock" in lock.__exit__.__doc__, "Docstring should describe releasing lock"

    # Test that __exit__ actually works
    assert not lock._lock.locked(), "Lock should not be held initially"
    with lock:
        assert lock._lock.locked(), "Lock should be held inside context"
    assert not lock._lock.locked(), "Lock should be released after exiting"


@pytest.mark.asyncio
async def test_async_compatible_lock_aenter_method_complete():
    """Test that __aenter__ method is complete and functional."""
    lock = _AsyncCompatibleLock()

    # Verify __aenter__ method exists and is callable
    assert hasattr(lock, '__aenter__'), "_AsyncCompatibleLock should have __aenter__ method"
    assert callable(lock.__aenter__), "__aenter__ should be callable"
    assert asyncio.iscoroutinefunction(lock.__aenter__), "__aenter__ should be async"

    # Verify __aenter__ has proper docstring
    assert lock.__aenter__.__doc__ is not None, "__aenter__ should have docstring"
    assert "asynchronous context manager" in lock.__aenter__.__doc__

    # Test that __aenter__ actually works
    assert not lock._lock.locked(), "Lock should not be held initially"
    async with lock:
        assert lock._lock.locked(), "Lock should be held inside context"
    assert not lock._lock.locked(), "Lock should be released after exiting"


@pytest.mark.asyncio
async def test_async_compatible_lock_aexit_method_complete():
    """Test that __aexit__ method is complete and functional."""
    lock = _AsyncCompatibleLock()

    # Verify __aexit__ method exists and is callable
    assert hasattr(lock, '__aexit__'), "_AsyncCompatibleLock should have __aexit__ method"
    assert callable(lock.__aexit__), "__aexit__ should be callable"
    assert asyncio.iscoroutinefunction(lock.__aexit__), "__aexit__ should be async"

    # Verify __aexit__ has proper docstring
    assert lock.__aexit__.__doc__ is not None, "__aexit__ should have docstring"
    assert "Release lock" in lock.__aexit__.__doc__, "Docstring should describe releasing lock"

    # Test that __aexit__ actually works
    assert not lock._lock.locked(), "Lock should not be held initially"
    async with lock:
        assert lock._lock.locked(), "Lock should be held inside context"
    assert not lock._lock.locked(), "Lock should be released after exiting"


@pytest.mark.asyncio
async def test_async_compatible_lock_all_context_managers_work():
    """Comprehensive test that all context manager methods work correctly."""
    lock = _AsyncCompatibleLock()

    # Test sync context manager (__enter__ and __exit__)
    with lock:
        assert lock._lock.locked(), "Sync: Lock should be held"
    assert not lock._lock.locked(), "Sync: Lock should be released"

    # Test async context manager (__aenter__ and __aexit__)
    async with lock:
        assert lock._lock.locked(), "Async: Lock should be held"
    assert not lock._lock.locked(), "Async: Lock should be released"

    # Test multiple sequential uses
    for _ in range(3):
        with lock:
            assert lock._lock.locked(), "Sequential sync: Lock should be held"
        async with lock:
            assert lock._lock.locked(), "Sequential async: Lock should be held"


def test_async_compatible_lock_methods_have_correct_signatures():
    """Test that all context manager methods have correct signatures."""
    import inspect

    lock = _AsyncCompatibleLock()

    # Check __exit__ signature: (self, exc_type, exc_val, exc_tb)
    exit_sig = inspect.signature(lock.__exit__)
    exit_params = list(exit_sig.parameters.keys())
    assert exit_params == ['exc_type', 'exc_val', 'exc_tb'], f"__exit__ params: {exit_params}"

    # Check __aenter__ signature: (self)
    aenter_sig = inspect.signature(lock.__aenter__)
    aenter_params = list(aenter_sig.parameters.keys())
    assert aenter_params == [], f"__aenter__ params: {aenter_params}"

    # Check __aexit__ signature: (self, exc_type, exc_val, exc_tb)
    aexit_sig = inspect.signature(lock.__aexit__)
    aexit_params = list(aexit_sig.parameters.keys())
    assert aexit_params == ['exc_type', 'exc_val', 'exc_tb'], f"__aexit__ params: {aexit_params}"
