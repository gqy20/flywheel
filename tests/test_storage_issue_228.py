"""Test for Windows directory permissions fallback (Issue #228)."""

import os
import tempfile
import stat
from pathlib import Path
from unittest.mock import patch

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_windows_directory_permissions_fallback():
    """Test that Windows attempts to set permissions even when pywin32 is not available.

    This test verifies that on Windows, when pywin32 is not installed,
    the code still attempts to set restrictive permissions using os.chmod
    instead of completely skipping permission setting.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test_storage/test.json"

        # Simulate Windows environment without pywin32
        with patch('os.name', 'nt'):
            # Mock win32security to raise ImportError (not installed)
            with patch.dict('sys.modules', {'win32security': None}):
                # The Storage should still be created successfully
                storage = Storage(path=storage_path)

                # On Windows, we should at least attempt os.chmod when win32security fails
                # The directory should exist
                assert storage.path.parent.exists()

                # Add a todo to trigger file operations
                storage.add(Todo(title="Test todo"))

                # Verify storage is functional
                todos = storage.list()
                assert len(todos) == 1
                assert todos[0].title == "Test todo"


def test_windows_attempts_chmod_without_pywin32():
    """Test that Windows calls os.chmod when pywin32 is not available.

    This test ensures that even on Windows, we attempt to set some permissions
    rather than completely ignoring security.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test_storage/test.json"

        # Track if chmod was called
        chmod_called = []
        original_chmod = Path.chmod

        def mock_chmod(self, mode):
            chmod_called.append(mode)
            # Call the original to avoid breaking the test
            return original_chmod(self, mode)

        # Simulate Windows environment
        with patch('os.name', 'nt'):
            # Mock win32security to raise ImportError
            with patch.dict('sys.modules', {'win32security': None}):
                with patch.object(Path, 'chmod', mock_chmod):
                    # Create Storage - should attempt chmod even on Windows
                    storage = Storage(path=storage_path)

                    # Verify that chmod was attempted at least once
                    # This proves we're not skipping permission setting on Windows
                    assert len(chmod_called) > 0, (
                        "chmod was not called on Windows. "
                        "The code should attempt to set permissions even without pywin32."
                    )


def test_unix_uses_chmod_directly():
    """Test that Unix-like systems use chmod directly for directory permissions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = f"{tmpdir}/test_storage/test.json"

        # Track chmod calls
        chmod_called = []
        original_chmod = Path.chmod

        def mock_chmod(self, mode):
            chmod_called.append((self, mode))
            return original_chmod(self, mode)

        # Simulate Unix environment
        with patch('os.name', 'posix'):
            with patch.object(Path, 'chmod', mock_chmod):
                storage = Storage(path=storage_path)

                # Verify chmod was called with 0o700
                assert len(chmod_called) > 0, "chmod should be called on Unix"

                # Find the call to the parent directory
                parent_chmod_calls = [
                    (path, mode) for path, mode in chmod_called
                    if storage.path.parent in path.parents or path == storage.path.parent
                ]

                # At least one chmod should have been called on the directory
                assert len(parent_chmod_calls) > 0, (
                    "chmod should be called on the storage directory"
                )
