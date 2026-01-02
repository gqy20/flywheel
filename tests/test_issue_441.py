"""Test for Issue #441 - Parent directories security on Windows.

This test verifies that _secure_all_parent_directories is called on all platforms,
including Windows, to ensure parent directories are secured even if they were
created by other processes.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from flywheel.storage import Storage


class TestParentDirectoriesSecurityWindows:
    """Test that parent directories are secured on Windows (Issue #441)."""

    def test_secure_all_parent_directories_called_on_windows(self):
        """Test that _secure_all_parent_directories is called on Windows.

        This test verifies that when os.name == 'nt' (Windows), the
        _secure_all_parent_directories method is still called to ensure
        parent directories created by other processes are secured.
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_storage" / "nested" / "todos.json"

            # Mock os.name to simulate Windows
            with patch('os.name', 'nt'):
                # Mock the Windows security modules to avoid import errors
                mock_win32security = MagicMock()
                mock_win32con = MagicMock()
                mock_win32api = MagicMock()
                mock_win32file = MagicMock()

                # Patch the imports in storage.py
                modules = {
                    'win32security': mock_win32security,
                    'win32con': mock_win32con,
                    'win32api': mock_win32api,
                    'win32file': mock_win32file,
                }

                # Track calls to _secure_all_parent_directories
                original_secure_all = None
                secure_all_called = []

                def mock_secure_all(self, directory):
                    """Mock that tracks calls to _secure_all_parent_directories."""
                    secure_all_called.append(directory)

                with patch.dict('sys.modules', modules):
                    # Create a storage instance
                    storage = Storage(str(test_path))

                    # Patch _secure_all_parent_directories to track calls
                    with patch.object(
                        Storage,
                        '_secure_all_parent_directories',
                        mock_secure_all
                    ):
                        # Re-initialize to trigger the call
                        storage = Storage(str(test_path))

                # Verify that _secure_all_parent_directories was called
                # even on Windows (os.name == 'nt')
                assert len(secure_all_called) > 0, (
                    "_secure_all_parent_directories should be called on Windows "
                    "to secure parent directories created by other processes"
                )

    def test_parent_directories_secured_on_unix(self):
        """Test that _secure_all_parent_directories is called on Unix systems.

        This is a regression test to ensure the existing Unix behavior is maintained.
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_storage" / "nested" / "todos.json"

            # Mock os.name to simulate Unix
            with patch('os.name', 'posix'):
                # Track calls to _secure_all_parent_directories
                secure_all_called = []

                def mock_secure_all(self, directory):
                    """Mock that tracks calls to _secure_all_parent_directories."""
                    secure_all_called.append(directory)

                # Patch _secure_all_parent_directories to track calls
                with patch.object(
                    Storage,
                    '_secure_all_parent_directories',
                    mock_secure_all
                ):
                    # Create a storage instance
                    storage = Storage(str(test_path))

                # Verify that _secure_all_parent_directories was called on Unix
                assert len(secure_all_called) > 0, (
                    "_secure_all_parent_directories should be called on Unix systems"
                )

    def test_windows_parent_directory_security_with_existing_dirs(self):
        """Test that existing parent directories are secured on Windows.

        This test simulates the scenario where parent directories already exist
        (created by another process) and verifies that they are secured.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create parent directories beforehand (simulating another process)
            parent_dir = Path(tmpdir) / "test_storage"
            parent_dir.mkdir(parents=True, exist_ok=True)
            test_path = parent_dir / "todos.json"

            # Mock os.name to simulate Windows
            with patch('os.name', 'nt'):
                # Mock the Windows security modules
                mock_win32security = MagicMock()
                mock_win32con = MagicMock()
                mock_win32api = MagicMock()
                mock_win32file = MagicMock()

                modules = {
                    'win32security': mock_win32security,
                    'win32con': mock_win32con,
                    'win32api': mock_win32api,
                    'win32file': mock_win32file,
                }

                # Track calls to _secure_directory
                secure_dir_calls = []

                original_secure = Storage._secure_directory

                def mock_secure(self, directory):
                    """Mock that tracks calls to _secure_directory."""
                    secure_dir_calls.append(directory)

                with patch.dict('sys.modules', modules):
                    with patch.object(Storage, '_secure_directory', mock_secure):
                        # Create storage - should secure parent directories
                        storage = Storage(str(test_path))

                # Verify that parent directories were secured
                # The parent_dir should be in the secure_dir_calls list
                assert any(
                    parent_dir in call_args or call_args == parent_dir
                    for call_args in secure_dir_calls
                ), (
                    "Parent directories should be secured on Windows even if "
                    "they already existed before Storage initialization"
                )
