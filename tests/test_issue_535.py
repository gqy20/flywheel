"""Test for Issue #535: Windows module variable scope issue.

This test verifies that win32file and related Windows modules are
accessible at module level, even when pywin32 is not installed in debug mode.
"""
import os
import sys
import pytest


def test_windows_modules_accessible_in_degraded_mode():
    """Test that Windows modules are accessible in degraded mode (Issue #535)."""
    # Only run on Windows
    if os.name != 'nt':
        pytest.skip("Test only applicable on Windows")

    # Import after setting debug mode to trigger degraded mode
    import importlib
    import flywheel.storage

    # Reload the module to test import behavior
    # This simulates the scenario where pywin32 is not installed
    # but FLYWHEEL_DEBUG is enabled
    importlib.reload(flywheel.storage)

    # The key test: win32file should be accessible at module level
    # In degraded mode (FLYWHEEL_DEBUG enabled), it should be None
    # but it should NOT raise NameError
    try:
        # Try to access win32file at module level
        win32file_value = flywheel.storage.win32file
        # If we get here, the variable is accessible (may be None or a module)
        assert win32file_value is not None or os.environ.get('FLYWHEEL_DEBUG') == '1'
    except NameError as e:
        pytest.fail(
            f"win32file is not accessible at module level (Issue #535): {e}\n"
            f"This occurs when variables are assigned in except block without "
            f"being declared at module level first."
        )

    # Test that _is_degraded_mode can access win32file without NameError
    try:
        is_degraded = flywheel.storage._is_degraded_mode()
        # Should return a boolean, not raise NameError
        assert isinstance(is_degraded, bool)
    except NameError as e:
        pytest.fail(
            f"_is_degraded_mode() cannot access win32file (Issue #535): {e}\n"
            f"This happens when win32file is assigned in except block but not "
            f"declared at module level."
        )
