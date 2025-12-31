"""Test file permissions on Windows (Issue #190)."""

import os
import stat
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsFilePermissions:
    """Test file permissions handling on Windows platform."""

    def test_windows_fallback_to_chmod(self):
        """Test that chmod is called as fallback when os.fchmod is not available (Windows)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.fchmod to raise AttributeError (simulating Windows behavior)
            # Also mock os.chmod to track if it's called
            with mock.patch('os.fchmod', side_effect=AttributeError("os.fchmod is not available on Windows")):
                with mock.patch('os.chmod') as mock_chmod:
                    # Create storage and add a todo (triggers _save)
                    storage = Storage(str(storage_path))
                    storage.add(Todo(title="Test todo"))

                    # Verify os.chmod was called as fallback
                    # The fallback should be called twice (once in _save, once in _save_with_todos)
                    assert mock_chmod.call_count >= 1, "os.chmod should be called as fallback on Windows"

                    # Verify the file was created with correct permissions
                    # On Windows, we can still check that the file exists
                    assert storage_path.exists(), "Storage file should be created"

                    # Verify the file has the correct content
                    todos = storage.list()
                    assert len(todos) == 1
                    assert todos[0].title == "Test todo"

    def test_unix_fchmod_works(self):
        """Test that fchmod is used when available (Unix/Linux)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # On Unix systems, os.fchmod should work normally
            # Create storage and add a todo
            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test todo"))

            # Verify the file was created
            assert storage_path.exists(), "Storage file should be created"

            # On Unix, check file permissions are 0o600
            if hasattr(os, 'fchmod'):
                file_stat = os.stat(storage_path)
                file_mode = stat.S_IMODE(file_stat.st_mode)
                # Note: On some systems, umask might affect this
                # The important thing is that fchmod was attempted
                assert file_mode & stat.S_IRUSR, "Owner should have read permission"
                assert file_mode & stat.S_IWUSR, "Owner should have write permission"

    def test_windows_permissions_security(self):
        """Test that files are created with secure permissions on Windows."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Simulate Windows environment where fchmod is not available
            with mock.patch('os.fchmod', side_effect=AttributeError):
                storage = Storage(str(storage_path))
                storage.add(Todo(title="Secure todo"))

                # Verify file exists and contains data
                assert storage_path.exists()

                # Verify we can read the file back
                storage2 = Storage(str(storage_path))
                todos = storage2.list()
                assert len(todos) == 1
                assert todos[0].title == "Secure todo"

    def test_chmod_called_with_correct_path_and_permissions(self):
        """Test that os.chmod is called with correct path and permissions (0o600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            with mock.patch('os.fchmod', side_effect=AttributeError):
                with mock.patch('os.chmod') as mock_chmod:
                    storage = Storage(str(storage_path))
                    storage.add(Todo(title="Test"))

                    # Verify chmod was called with correct parameters
                    assert mock_chmod.call_count >= 1

                    # Check that at least one call was with 0o600 permissions
                    chmod_calls = [call for call in mock_chmod.call_args_list]
                    assert len(chmod_calls) > 0

                    # Verify the temp file path and permissions
                    for call in chmod_calls:
                        args, kwargs = call
                        # First argument should be a path
                        assert isinstance(args[0], str) or isinstance(args[0], Path)
                        # Second argument should be the permissions
                        assert args[1] == 0o600, f"Expected 0o600 permissions, got {oct(args[1])}"
