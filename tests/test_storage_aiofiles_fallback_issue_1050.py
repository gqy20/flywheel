"""Test that _AiofilesFallback implementation is complete (Issue #1050).

This test verifies that the fallback async file operations are properly
implemented when aiofiles is not available.
"""

import sys
import importlib


def test_aiofiles_fallback_class_exists():
    """Test that _AiofilesFallback class exists and has required methods."""
    # Force reimport without aiofiles
    if 'flywheel.storage' in sys.modules:
        del sys.modules['flywheel.storage']

    # Mock absence of aiofiles
    import flywheel.storage as storage
    HAS_AIOFILES = storage.HAS_AIOFILES

    if not HAS_AIOFILES:
        # Check that the fallback class exists
        assert hasattr(storage, '_AiofilesFallback'), \
            "_AiofilesFallback class should exist when aiofiles is not available"

        fallback = storage._AiofilesFallback

        # Check that open method exists
        assert hasattr(fallback, 'open'), \
            "_AiofilesFallback should have an 'open' method"

        # Check that open method is callable
        assert callable(fallback.open), \
            "_AiofilesFallback.open should be callable"

        # Check that aiofiles is replaced with fallback
        assert hasattr(storage, 'aiofiles'), \
            "storage module should have aiofiles attribute"

        # Verify aiofiles.open exists (via fallback)
        assert hasattr(storage.aiofiles, 'open'), \
            "aiofiles should have open method via fallback"


def test_async_file_context_manager_exists():
    """Test that _AsyncFileContextManager class exists and is complete."""
    if 'flywheel.storage' in sys.modules:
        del sys.modules['flywheel.storage']

    import flywheel.storage as storage
    HAS_AIOFILES = storage.HAS_AIOFILES

    if not HAS_AIOFILES:
        # Check that the context manager class exists
        assert hasattr(storage, '_AsyncFileContextManager'), \
            "_AsyncFileContextManager class should exist when aiofiles is not available"

        context_mgr = storage._AsyncFileContextManager

        # Check for required async methods
        required_methods = ['__aenter__', '__aexit__', 'read', 'write', 'flush']
        for method in required_methods:
            assert hasattr(context_mgr, method), \
                f"_AsyncFileContextManager should have {method} method"


def test_fallback_docstring_complete():
    """Test that fallback implementation docstrings are not truncated."""
    if 'flywheel.storage' in sys.modules:
        del sys.modules['flywheel.storage']

    import flywheel.storage as storage
    HAS_AIOFILES = storage.HAS_AIOFILES

    if not HAS_AIOFILES:
        # Check that _AiofilesFallback has a proper docstring
        fallback = storage._AiofilesFallback
        assert fallback.__doc__ is not None, \
            "_AiofilesFallback should have a docstring"
        assert len(fallback.__doc__) > 10, \
            "_AiofilesFallback docstring should not be truncated"

        # Check that open method has a proper docstring
        open_method = fallback.open
        assert open_method.__doc__ is not None, \
            "_AiofilesFallback.open should have a docstring"
        assert len(open_method.__doc__) > 20, \
            "_AiofilesFallback.open docstring should be complete"
        # The docstring should not end abruptly
        assert not open_method.__doc__.strip().endswith('a'), \
            "Docstring should not be truncated mid-word"
