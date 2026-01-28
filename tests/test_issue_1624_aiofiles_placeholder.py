"""
Test for issue #1624: aiofiles placeholder should implement _AiofilesProtocol

This test ensures that the aiofiles placeholder object (used when aiofiles
is not available) implements the required protocol interface, specifically
having an 'open' method that can be called at runtime.
"""

import sys
from unittest.mock import patch

import pytest


def test_aiofiles_placeholder_has_open_method():
    """
    Test that aiofiles placeholder object has an 'open' method.

    When aiofiles is not available, a placeholder is assigned to the aiofiles
    variable. This placeholder must implement the _AiofilesProtocol interface,
    which requires an 'open' method. Without it, any runtime code that tries
    to use aiofiles.open() will fail with AttributeError.

    This test verifies that the aiofiles object (whether it's the real aiofiles
    or the fallback implementation) always has an 'open' method.
    """
    # Mock aiofiles as unavailable
    aiofiles_backup = sys.modules.get('aiofiles')
    if 'aiofiles' in sys.modules:
        del sys.modules['aiofiles']

    try:
        # Re-import storage module without aiofiles
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        from flywheel import storage

        # The critical check: aiofiles must have an 'open' method
        # This will fail if aiofiles is just object() placeholder
        assert hasattr(storage.aiofiles, 'open'), \
            "aiofiles placeholder must have 'open' method to implement _AiofilesProtocol"

        # Verify it's callable
        assert callable(storage.aiofiles.open), \
            "aiofiles.open must be callable"

    finally:
        # Restore aiofiles module
        if aiofiles_backup is not None:
            sys.modules['aiofiles'] = aiofiles_backup


def test_aiofiles_open_is_callable_at_import_time():
    """
    Test that aiofiles.open can be called immediately after module import.

    This is a stricter test that verifies the aiofiles object is properly
    initialized at import time, not lazily assigned later. This ensures
    type safety throughout the module lifecycle.
    """
    # Mock aiofiles as unavailable
    aiofiles_backup = sys.modules.get('aiofiles')
    if 'aiofiles' in sys.modules:
        del sys.modules['aiofiles']

    try:
        # Re-import storage module without aiofiles
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        from flywheel import storage

        # Try to access aiofiles.open - this should not raise AttributeError
        # If aiofiles is just object() placeholder, this will fail
        try:
            open_method = storage.aiofiles.open
            assert open_method is not None, "aiofiles.open should not be None"
        except AttributeError as e:
            pytest.fail(
                f"aiofiles placeholder does not implement 'open' method: {e}\n"
                "The placeholder at line 60 should be replaced with a proper "
                "_AiofilesProtocol implementation before module import completes."
            )

    finally:
        # Restore aiofiles module
        if aiofiles_backup is not None:
            sys.modules['aiofiles'] = aiofiles_backup


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
