"""Verification test for Issue #1220 - code is already complete.

This test verifies that the issue reported in #1220 does not exist
in the current codebase. The __enter__, __exit__, __aenter__, and
__aexit__ methods are all properly implemented.
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import _AsyncCompatibleLock
import asyncio


def test_async_compatible_lock_enter_method_complete():
    """Verify that __enter__ method is complete and returns self.

    This test disproves the claim in Issue #1220 that the __enter__
    method was truncated at 'self._locked = Tr'.

    Reference: Issue #1220
    """
    lock = _AsyncCompatibleLock()

    # Test that __enter__ returns self (basic functionality)
    result = lock.__enter__()
    assert result is lock, "__enter__ should return self"
    assert lock._locked is True, "Lock should be marked as acquired"

    # Test that __exit__ properly releases
    lock.__exit__(None, None, None)
    assert lock._locked is False, "Lock should be marked as released"


@pytest.mark.asyncio
async def test_async_compatible_lock_async_methods_complete():
    """Verify that __aenter__ and __aexit__ methods exist and work.

    This test disproves the claim in Issue #1220 that these methods
    were missing.

    Reference: Issue #1220
    """
    lock = _AsyncCompatibleLock()

    # Test that __aenter__ returns self
    result = await lock.__aenter__()
    assert result is lock, "__aenter__ should return self"
    assert lock._locked is True, "Lock should be marked as acquired"

    # Test that __aexit__ properly releases
    await lock.__aexit__(None, None, None)
    assert lock._locked is False, "Lock should be marked as released"


def test_async_compatible_lock_context_manager():
    """Verify that the lock works as a synchronous context manager.

    Reference: Issue #1220
    """
    lock = _AsyncCompatibleLock()

    with lock:
        assert lock._locked is True

    assert lock._locked is False


@pytest.mark.asyncio
async def test_async_compatible_lock_async_context_manager():
    """Verify that the lock works as an asynchronous context manager.

    Reference: Issue #1220
    """
    lock = _AsyncCompatibleLock()

    async with lock:
        assert lock._locked is True

    assert lock._locked is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
