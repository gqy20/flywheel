"""Test Windows dependency checking (Issue #414)."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from flywheel.storage import Storage


class TestWindowsDependencyCheck:
    """Test that Windows dependencies are checked at import/init time.

    Issue #414: Windows dependencies (pywin32) are lazily loaded, which can
    cause runtime crashes when _secure_directory or _create_and_secure_directories
    are called on Windows without pywin32 installed.

    The fix should check dependencies early in __init__ and provide a clear
    error message instead of crashing later.
    """

    def test_windows_requires_pywin32_at_init(self):
        """Test that Windows raises clear error if pywin32 is missing at init.

        On Windows, if pywin32 is not installed, Storage.__init__ should raise
        a clear ImportError or RuntimeError immediately, not wait until
        _secure_directory is called.
        """
        # Only test on Windows
        if os.name != 'nt':
            pytest.skip("This test only runs on Windows")

        # Mock the pywin32 imports to simulate missing dependency
        with patch.dict(sys.modules, {
            'win32security': None,
            'win32con': None,
            'win32api': None,
            'win32file': None
        }):
            with tempfile.TemporaryDirectory() as tmpdir:
                storage_path = Path(tmpdir) / "todos.json"

                # Attempting to create Storage should fail with clear error
                # NOT when calling _secure_directory later, but during __init__
                with pytest.raises((ImportError, RuntimeError)) as exc_info:
                    Storage(str(storage_path))

                # Error message should mention pywin32
                error_msg = str(exc_info.value).lower()
                assert "pywin32" in error_msg, (
                    f"Error message should mention pywin32, got: {exc_info.value}"
                )

    def test_non_windows_does_not_require_pywin32(self):
        """Test that non-Windows platforms don't require pywin32.

        On Unix-like systems, Storage should work fine without pywin32.
        """
        # Only test on non-Windows
        if os.name == 'nt':
            pytest.skip("This test only runs on non-Windows platforms")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Should work fine on Unix without pywin32
            storage = Storage(str(storage_path))
            assert storage is not None
            storage.close()

    def test_windows_with_pywin32_works(self):
        """Test that Windows with pywin32 installed works correctly.

        If pywin32 is available, Storage should initialize successfully.
        """
        # Only test on Windows
        if os.name != 'nt':
            pytest.skip("This test only runs on Windows")

        # Try to import pywin32 - skip test if not available
        try:
            import win32security  # noqa: F401
        except ImportError:
            pytest.skip("pywin32 not installed, skipping test")

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Should work fine with pywin32 installed
            storage = Storage(str(storage_path))
            assert storage is not None
            storage.close()

    def test_windows_check_happens_before_directory_operations(self):
        """Test that dependency check happens before any directory operations.

        This ensures the error is raised early, not after directories are created.
        """
        # Only test on Windows
        if os.name != 'nt':
            pytest.skip("This test only runs on Windows")

        # Mock pywin32 as unavailable
        with patch.dict(sys.modules, {
            'win32security': None,
            'win32con': None,
            'win32api': None,
            'win32file': None
        }):
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use a path that doesn't exist yet
                storage_path = Path(tmpdir) / "new_dir" / "todos.json"

                # Should fail during __init__ before creating directories
                # (or fail immediately when trying to create directories with clear error)
                with pytest.raises((ImportError, RuntimeError)) as exc_info:
                    Storage(str(storage_path))

                # Error should be clear about pywin32 requirement
                error_msg = str(exc_info.value).lower()
                assert "pywin32" in error_msg
