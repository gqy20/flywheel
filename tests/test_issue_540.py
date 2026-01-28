"""Test for Issue #540: Windows module variables NameError on Unix systems."""

import os
import sys
import pytest


def test_is_degraded_mode_on_unix():
    """Test that _is_degraded_mode works on Unix systems without NameError."""
    # Skip on Windows
    if os.name == 'nt':
        pytest.skip("This test is for Unix systems only")

    # Import the module fresh to avoid any cached state
    if 'flywheel.storage' in sys.modules:
        del sys.modules['flywheel.storage']

    from flywheel.storage import _is_degraded_mode

    # On Unix systems, win32file is not defined
    # This should NOT raise NameError
    # It should return False since we're not on Windows
    assert _is_degraded_mode() is False


def test_is_degraded_mode_on_windows_with_import_error():
    """Test that _is_degraded_mode handles ImportError gracefully on Windows."""
    # Skip on non-Windows systems
    if os.name != 'nt':
        pytest.skip("This test is for Windows systems only")

    from flywheel.storage import _is_degraded_mode

    # On Windows with pywin32 installed, should return False (not degraded)
    # If pywin32 is not installed, the import should have failed already
    # This test verifies the function doesn't crash with NameError
    try:
        result = _is_degraded_mode()
        # Should return a boolean, not raise NameError
        assert isinstance(result, bool)
    except NameError as e:
        pytest.fail(f"_is_degraded_mode raised NameError: {e}")


def test_win32file_variable_exists():
    """Test that win32file variable is accessible on all platforms."""
    from flywheel import storage

    # On Unix, win32file should be either:
    # 1. Defined as None (if we fix it by declaring it)
    # 2. Not defined at all (current bug - NameError)
    #
    # On Windows, it should be either the module or None (if import failed)

    if os.name == 'nt':
        # On Windows, win32file should exist (either as module or None)
        assert hasattr(storage, 'win32file'), "win32file should be defined on Windows"
    else:
        # On Unix, accessing win32file should not raise NameError
        # if the code properly handles it
        # Currently this will fail with NameError - that's the bug we're fixing
        try:
            _ = storage.win32file
        except AttributeError:
            # AttributeError is acceptable (variable not defined in module)
            # NameError is the bug we're fixing
            pass
        except NameError as e:
            pytest.fail(f"Accessing win32file raised NameError on Unix: {e}")
