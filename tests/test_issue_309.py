"""Test for issue #309: Windows security should raise error when pywin32 is missing.

This test verifies that the Storage class raises a RuntimeError when:
1. Running on Windows
2. pywin32 is not installed or fails to import

This ensures the application doesn't run with insecure directory permissions.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from flywheel.storage import Storage


class TestWindowsSecurityIssue309:
    """Test Windows security handling for missing pywin32."""

    def test_windows_raises_error_when_pywin32_not_installed(self):
        """Test that Storage raises RuntimeError on Windows when pywin32 is missing.

        This test ensures that if pywin32 is not available on Windows,
        the Storage class raises a RuntimeError instead of continuing
        with insecure permissions.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.name to simulate Windows
            # Mock win32security import to fail (simulate not installed)
            with patch('flywheel.storage.os.name', 'nt'):
                # We need to mock the import at the module level
                # The _secure_directory method tries to import win32security
                # We'll make it fail with ImportError
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    """Mock import that fails for win32security modules."""
                    if name in ['win32security', 'win32con', 'win32api']:
                        raise ImportError(f"No module named '{name}'")
                    return original_import(name, *args, **kwargs)

                with patch('builtins.__import__', side_effect=mock_import):
                    # Attempting to create Storage should raise RuntimeError
                    with pytest.raises(RuntimeError) as exc_info:
                        Storage(path=str(storage_path))

                    # Verify the error message mentions pywin32
                    error_msg = str(exc_info.value)
                    assert "pywin32" in error_msg.lower()
                    assert "required" in error_msg.lower() or "cannot be secured" in error_msg.lower()

    def test_unix_does_not_require_pywin32(self):
        """Test that Unix systems don't require pywin32.

        This is a sanity check to ensure the fix doesn't break Unix systems.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.name to simulate Unix
            with patch('flywheel.storage.os.name', 'posix'):
                # Storage should work fine on Unix without pywin32
                storage = Storage(path=str(storage_path))
                # If we get here without exception, the test passes
                assert storage is not None
                storage.close()

    def test_windows_with_pywin32_succeeds(self):
        """Test that Windows with pywin32 works correctly.

        This test verifies that when pywin32 is available, the security
        setup succeeds (or fails with a different error if ACL setup fails,
        but not due to missing pywin32).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.name to simulate Windows
            with patch('flywheel.storage.os.name', 'nt'):
                # On non-Windows systems, we can't fully test Windows ACL setup
                # but we can verify the code path doesn't immediately fail
                # due to the import check

                # If we're actually on Windows and pywin32 is installed, it should work
                # If we're on Unix, this test is skipped
                if os.name != 'nt':
                    pytest.skip("This test requires actual Windows environment")
                else:
                    # Try to create storage - it should work if pywin32 is installed
                    try:
                        import win32security  # noqa: F401
                        storage = Storage(path=str(storage_path))
                        assert storage is not None
                        storage.close()
                    except ImportError:
                        # If pywin32 is not installed, skip this test
                        pytest.skip("pywin32 not installed on Windows")
