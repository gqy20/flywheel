"""Test Windows import compatibility when pywin32 is missing.

This test verifies that the storage module can be imported on Windows
even when pywin32 is not installed, allowing for degraded mode operation.
"""

import importlib
import sys
import unittest.mock as mock

import pytest


def test_module_import_on_windows_without_pywin32():
    """Test that storage module can be imported on Windows without pywin32.

    This test simulates the scenario where pywin32 is not installed on Windows.
    The module should still be importable, potentially with degraded functionality.
    """
    # Skip this test on actual Windows since we can't easily mock the platform check
    # and the actual pywin32 might be installed
    import os
    if os.name == 'nt':
        pytest.skip("Skipping on actual Windows - test is for simulated Windows environment")

    # Remove the storage module from sys.modules if it was already imported
    modules_to_remove = [k for k in sys.modules.keys() if k.startswith('flywheel.storage')]
    for module in modules_to_remove:
        del sys.modules[module]

    # Mock os.name to simulate Windows
    with mock.patch('os.name', 'nt'):
        # Mock the pywin32 import to fail
        import_side_effect = ImportError("No module named 'win32security'")

        def mock_import(name, *args, **kwargs):
            if name.startswith('win32') or name == 'pywintypes':
                raise import_side_effect
            return original_import(name, *args, **kwargs)

        original_import = __builtins__.__import__
        with mock.patch('builtins.__import__', side_effect=mock_import):
            # The module should be importable even without pywin32
            # It may have degraded functionality but should not raise ImportError at import time
            try:
                import flywheel.storage
                # If we get here, the module imported successfully
                # Verify that the module is in a degraded or safe state
                assert flywheel.storage is not None
            except ImportError as e:
                # If ImportError is raised, it should NOT be about pywin32 being required
                # The module should handle missing pywin32 gracefully
                error_msg = str(e).lower()
                if 'pywin32' in error_msg or 'win32' in error_msg:
                    pytest.fail(
                        f"Module should be importable without pywin32 for portability. "
                        f"Got ImportError: {e}"
                    )
                else:
                    # Some other ImportError - re-raise it
                    raise


def test_degraded_mode_function_returns_false():
    """Test that _is_degraded_mode returns False indicating pywin32 is required."""
    from flywheel.storage import _is_degraded_mode

    # According to the code comments, this function now always returns False
    # indicating degraded mode is no longer supported
    assert _is_degraded_mode() is False


def test_storage_module_imports_on_unix():
    """Test that storage module imports successfully on Unix systems."""
    import os
    if os.name == 'nt':
        pytest.skip("Skipping on Windows - Unix test only")

    # On Unix, the module should always import without issues
    from flywheel import storage
    assert storage is not None
