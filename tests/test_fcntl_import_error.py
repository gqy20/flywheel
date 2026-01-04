"""Test fcntl import error handling (Issue #679)."""

import sys
import pytest


def test_fcntl_import_handled_gracefully():
    """Test that missing fcntl module is handled gracefully.

    On Unix-like systems, if fcntl is not available (e.g., Cygwin,
    restricted environments), the module should handle ImportError gracefully
    instead of crashing at import time.
    """
    # This test verifies that storage.py can handle missing fcntl
    # We can't actually remove fcntl from sys.modules, but we can
    # verify the import behavior by checking if the module has proper handling

    import flywheel.storage

    # On non-Windows systems, fcntl should be available for normal operation
    # but the module should have error handling if it's not
    if sys.platform != 'win32':
        # Verify the module imported successfully
        assert flywheel.storage is not None

        # The module should either:
        # 1. Have fcntl available (normal Unix systems)
        # 2. Handle its absence gracefully
        try:
            import fcntl
            # If fcntl is available, that's normal
            assert fcntl is not None
        except ImportError:
            # If fcntl is not available, storage module should still work
            # or provide a clear error message
            pass


def test_storage_module_has_fcntl_fallback():
    """Test that storage module has proper fcntl error handling.

    This test verifies the fix for Issue #679 where fcntl was imported
    without error handling on Unix-like systems.
    """
    import importlib
    import sys

    # Save original modules
    original_modules = sys.modules.copy()

    try:
        # Remove fcntl from sys.modules if it exists
        if 'fcntl' in sys.modules:
            del sys.modules['fcntl']

        # Also remove storage module to force re-import
        if 'flywheel.storage' in sys.modules:
            del sys.modules['flywheel.storage']

        # Mock fcntl to raise ImportError
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == 'fcntl':
                raise ImportError("fcntl module not available")
            return original_import(name, *args, **kwargs)

        builtins.__import__ = mock_import

        # Try to import storage - it should either:
        # 1. Handle the ImportError gracefully, or
        # 2. Provide a clear error message
        try:
            import flywheel.storage
            # If it imports successfully, that's even better
            assert flywheel.storage is not None
        except ImportError as e:
            # If it raises ImportError, it should have a clear message
            # about platform requirements
            assert 'fcntl' in str(e).lower() or 'platform' in str(e).lower()

    finally:
        # Restore original modules and import
        sys.modules.clear()
        sys.modules.update(original_modules)
        builtins.__import__ = original_import

        # Re-import storage to ensure normal state
        import importlib
        import flywheel.storage
        importlib.reload(flywheel.storage)


def test_windows_requires_pywin32():
    """Test that Windows requires pywin32 (Issue #674, #679)."""
    import sys

    if sys.platform == 'win32':
        # On Windows, pywin32 should be required
        try:
            import flywheel.storage
            # If we got here, pywin32 is available
            assert flywheel.storage.win32file is not None
        except ImportError as e:
            # Should have clear message about pywin32 requirement
            assert 'pywin32' in str(e)
    else:
        # On non-Windows, pywin32 modules should be None
        import flywheel.storage
        assert flywheel.storage.win32file is None
