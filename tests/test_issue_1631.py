"""Test for Issue #1631 - Ensure aiofiles placeholder is properly replaced.

This test verifies that the _AiofilesPlaceholder is replaced with
_AiofilesFallback before any actual use, preventing RuntimeError.
"""
import pytest

from flywheel import storage


def test_aiofiles_placeholder_replaced():
    """Test that aiofiles.open does not raise RuntimeError.

    If _AiofilesPlaceholder is not properly replaced with _AiofilesFallback,
    calling aiofiles.open will raise a RuntimeError. This test ensures
    the replacement happens correctly during module initialization.
    """
    # The aiofiles module should be available even without aiofiles installed
    assert hasattr(storage, 'aiofiles'), "aiofiles should be available in storage module"

    # We should be able to access the open method without error
    assert hasattr(storage.aiofiles, 'open'), "aiofiles.open should be callable"

    # The placeholder should have been replaced, so we should not get
    # a RuntimeError when trying to use it
    # Note: We don't actually call open() here as it would require a real file,
    # but we verify the implementation is not the placeholder
    from flywheel.storage import _AiofilesPlaceholder, _AiofilesFallback

    if not storage.HAS_AIOFILES:
        # When aiofiles is not installed, it should be using the fallback
        assert isinstance(storage.aiofiles, _AiofilesFallback), \
            "aiofiles should use _AiofilesFallback when aiofiles package is not installed"
    else:
        # When aiofiles is installed, it should use the real aiofiles
        assert not isinstance(storage.aiofiles, _AiofilesPlaceholder), \
            "aiofiles should never be the placeholder implementation"


def test_aiofiles_open_is_callable():
    """Test that aiofiles.open is a callable that doesn't raise RuntimeError.

    This is a basic smoke test to ensure the module initialization
    completed successfully.
    """
    from flywheel import storage

    # Just accessing the open method should not raise an error
    open_func = storage.aiofiles.open
    assert callable(open_func), "aiofiles.open should be callable"

    # The open method should not be the placeholder's open method
    # (which would raise RuntimeError immediately)
    import inspect

    source_file = inspect.getsourcefile(open_func)
    # If it's the placeholder, it would raise RuntimeError on call
    # We verify it's not the placeholder by checking it doesn't have
    # the placeholder's error message in its source
    if not storage.HAS_AIOFILES:
        source = inspect.getsource(open_func)
        assert "placeholder was not replaced" not in source, \
            "aiofiles.open should not be the placeholder implementation"
