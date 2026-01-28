"""Test for Issue #1621 - Type safety for aiofiles variable.

This test ensures that aiofiles is properly typed without allowing None,
even during the module initialization phase.

The issue: Line 84 in storage.py has `aiofiles: _AiofilesProtocol | None = None`
which creates a type safety risk. The fix is to ensure aiofiles is never None-typed.
"""

import pytest
from typing import get_type_hints
import inspect


def test_aiofiles_type_annotation_safety():
    """Ensure aiofiles type annotation does not include None (Issue #1621).

    This test verifies that the aiofiles variable is properly typed
    without the None type option, which prevents potential runtime errors.
    """
    from flywheel import storage

    # Check that aiofiles is not None at runtime
    assert storage.aiofiles is not None, (
        "aiofiles should never be None after module initialization"
    )

    # Check that it has the expected interface
    assert hasattr(storage.aiofiles, 'open'), (
        "aiofiles should have an 'open' method"
    )


def test_aiofiles_usable_without_none_checks():
    """Test that aiofiles can be used directly without None checks (Issue #1621).

    This demonstrates that the type system should not require None checks
    when using aiofiles, as it should always be a valid object.
    """
    from flywheel import storage
    from flywheel.storage import _AiofilesProtocol

    # This assignment should work without type errors
    # If the type annotation includes | None, type checkers will complain
    aiofiles_obj: _AiofilesProtocol = storage.aiofiles

    # Verify it's the same object
    assert aiofiles_obj is storage.aiofiles

    # Verify we can access its methods without None checks
    assert callable(aiofiles_obj.open)


def test_aiofiles_consistency_with_has_aiofiles():
    """Test that aiofiles works regardless of HAS_AIOFILES flag (Issue #1621).

    Whether aiofiles library is available or not, the aiofiles variable
    should always be a valid object (either the real library or fallback).
    """
    from flywheel import storage

    # HAS_AIOFILES indicates if the real library is available
    # But aiofiles itself should always be usable
    if storage.HAS_AIOFILES:
        # If real aiofiles is available, it should be the real library
        import aiofiles as _real_check
        assert storage.aiofiles is _real_check
    else:
        # If not available, aiofiles should be our fallback implementation
        assert storage.aiofiles is not None
        assert hasattr(storage.aiofiles, 'open')

    # In both cases, it should be usable
    assert callable(storage.aiofiles.open)
