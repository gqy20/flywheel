"""Test for _AsyncCompatibleLock.__enter__ syntax error (Issue #1222).

This test verifies that the __enter__ method of _AsyncCompatibleLock
can be used without syntax errors.
"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import _AsyncCompatibleLock


def test_async_compatible_lock_sync_context_manager():
    """Test that _AsyncCompatibleLock can be used as a sync context manager.

    This test verifies that:
    1. The __enter__ method has no syntax errors (specifically checking for
       the truncated 'self._locked = Tr' bug mentioned in issue #1222)
    2. The lock properly sets _locked flag to True after entering
    3. The lock properly sets _locked flag to False after exiting

    Reference: Issue #1222
    """
    lock = _AsyncCompatibleLock()

    # Test that we can enter the context (this will fail if there's a syntax error)
    with lock:
        # Verify that _locked is set to True after entering
        assert lock._locked is True, "Lock should be marked as acquired after __enter__"

        # Verify we can acquire the lock again (it's reentrant through the same lock instance)
        assert lock._locked is True

    # Verify that _locked is set to False after exiting
    assert lock._locked is False, "Lock should be marked as released after __exit__"


def test_async_compatible_lock_multiple_entries():
    """Test that _AsyncCompatibleLock can be entered and exited multiple times.

    This ensures the syntax error doesn't prevent proper lock state management.
    """
    lock = _AsyncCompatibleLock()

    for i in range(3):
        with lock:
            assert lock._locked is True, f"Iteration {i}: Lock should be marked as acquired"
        assert lock._locked is False, f"Iteration {i}: Lock should be marked as released"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
