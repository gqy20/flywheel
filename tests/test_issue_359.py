"""Test for Issue #359 - Windows security dependency check in __init__.

This test verifies that pywin32 dependency is checked during Storage initialization
on Windows, not deferred until _secure_directory is called.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage


class TestWindowsSecurityDependencyCheck:
    """Test that Windows checks for pywin32 during __init__."""

    def test_windows_checks_pywin32_in_init(self):
        """Test that Windows checks for pywin32 during __init__, not later.

        On Windows, if pywin32 is not available, the Storage.__init__ should
        raise RuntimeError immediately, rather than waiting for _secure_directory
        to be called.

        This test simulates Windows behavior even on non-Windows platforms.
        """
        # Save original os.name
        original_os_name = os.name

        try:
            # Mock os.name to simulate Windows
            os.name = 'nt'

            # Create a temporary directory for the test
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = Path(tmpdir) / "todos.json"

                # Create a failing import for win32security modules
                # We need to make sure they're not already imported
                modules_to_clear = ['win32security', 'win32con', 'win32api']
                original_modules = {}
                for mod in modules_to_clear:
                    if mod in sys.modules:
                        original_modules[mod] = sys.modules[mod]
                        del sys.modules[mod]

                try:
                    # Mock the __import__ builtin to fail for win32security modules
                    original_import = __builtins__.__import__

                    def mock_import(name, *args, **kwargs):
                        if name in ['win32security', 'win32con', 'win32api']:
                            raise ImportError(f"No module named '{name}'")
                        return original_import(name, *args, **kwargs)

                    with patch('builtins.__import__', side_effect=mock_import):
                        # The import attempt in __init__ should fail with ImportError
                        # which should be caught and re-raised as RuntimeError
                        with pytest.raises((ImportError, RuntimeError)) as exc_info:
                            Storage(path=str(test_path))

                        # Verify the error message mentions pywin32 or win32security
                        error_msg = str(exc_info.value).lower()
                        assert "pywin32" in error_msg or "win32" in error_msg

                finally:
                    # Restore modules
                    for mod, original in original_modules.items():
                        sys.modules[mod] = original

        finally:
            # Restore original os.name
            os.name = original_os_name

    def test_non_windows_does_not_check_pywin32(self):
        """Test that non-Windows platforms don't check for pywin32."""
        # Only run this test on non-Windows platforms
        if os.name == 'nt':
            pytest.skip("This test only runs on non-Windows platforms")

        # On Unix-like systems, Storage should work without pywin32
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "todos.json"
            # Should not raise any errors about pywin32
            storage = Storage(path=str(test_path))
            assert storage is not None
            storage.close()
