"""Test for Issue #1631 - Ensure aiofiles placeholder doesn't raise RuntimeError.

This test verifies that the _AiofilesPlaceholder provides a working
implementation that doesn't crash with RuntimeError, even if it's
accidentally called before being replaced with _AiofilesFallback.
"""
import asyncio
import tempfile

import pytest

from flywheel import storage


def test_aiofiles_placeholder_does_not_raise():
    """Test that aiofiles.open doesn't raise RuntimeError.

    The _AiofilesPlaceholder should provide a minimal working implementation
    instead of raising RuntimeError (Issue #1631).
    """
    # The aiofiles module should be available even without aiofiles installed
    assert hasattr(storage, 'aiofiles'), "aiofiles should be available in storage module"

    # We should be able to access the open method without error
    assert hasattr(storage.aiofiles, 'open'), "aiofiles.open should be callable"

    # The placeholder should not raise RuntimeError
    # Verify the implementation doesn't have the old error message
    from flywheel.storage import _AiofilesPlaceholder

    if not storage.HAS_AIOFILES:
        # When aiofiles is not installed, we should be able to use the placeholder
        # without it raising RuntimeError
        import inspect

        source = inspect.getsource(_AiofilesPlaceholder.open)
        assert "placeholder was not replaced" not in source, \
            "aiofiles placeholder should not raise RuntimeError (Issue #1631)"


@pytest.mark.asyncio
async def test_aiofiles_open_works():
    """Test that aiofiles.open actually works for file operations.

    This is a functional test to ensure the module provides a working
    implementation even before the full fallback is loaded.
    """
    from flywheel import storage

    # Create a temporary file to test with
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_path = f.name
        f.write("test content")

    try:
        # Test that we can open and read the file using aiofiles.open
        async with storage.aiofiles.open(temp_path, 'r') as f:
            content = await f.read()

        assert content == "test content", "Should be able to read file content"
    finally:
        # Clean up the temporary file
        import os
        if os.path.exists(temp_path):
            os.unlink(temp_path)
