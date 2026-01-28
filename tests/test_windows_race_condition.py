"""Test for Windows race condition fix (Issue #200)."""
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestWindowsRaceCondition:
    """Test that Windows chmod fallback doesn't have race conditions."""

    def test_windows_chmod_before_close(self):
        """Test that chmod is called BEFORE file close on Windows.

        This test verifies that when os.fchmod is not available (Windows),
        the file permissions are set BEFORE closing the file descriptor,
        preventing the race condition where the file could be accessed
        with default permissions between close and chmod.

        See Issue #200.
        """
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Track the order of operations
            operations = []

            # Mock os.close to track when it's called
            original_close = os.close
            def mock_close(fd):
                operations.append(('close', fd))
                return original_close(fd)

            # Mock os.chmod to track when it's called
            original_chmod = os.chmod
            def mock_chmod(path, mode):
                operations.append(('chmod', path, mode))
                return original_chmod(path, mode)

            # Mock os.fchmod to simulate it not being available (Windows scenario)
            def mock_fchmod(fd, mode):
                raise AttributeError("os.fchmod not available")

            with patch('os.close', side_effect=mock_close), \
                 patch('os.chmod', side_effect=mock_chmod), \
                 patch('os.fchmod', side_effect=mock_fchmod):

                # Create storage and add a todo (this triggers _save)
                storage = Storage(str(storage_path))
                storage.add(Todo(title="Test todo"))

                # Verify that chmod was called BEFORE close
                # Find the indices of chmod and close operations
                chmod_idx = None
                close_idx = None

                for i, op in enumerate(operations):
                    if op[0] == 'chmod':
                        chmod_idx = i
                    elif op[0] == 'close':
                        close_idx = i

                # The fix should ensure chmod happens before close
                # (or there's no close at all if using fchmod)
                assert chmod_idx is not None, "chmod should have been called on Windows"
                assert close_idx is not None, "close should have been called"

                # Verify chmod was called before close
                # This prevents the race condition
                assert chmod_idx < close_idx, \
                    f"chmod (index {chmod_idx}) should be called BEFORE close (index {close_idx}) to prevent race condition"

    def test_windows_temp_file_has_strict_permissions(self):
        """Test that temporary files created on Windows have strict permissions.

        Even on Windows where os.fchmod is not available, the temporary file
        should have 0o600 permissions before it replaces the original file.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.fchmod to simulate Windows
            original_fchmod = getattr(os, 'fchmod', None)
            if original_fchmod:
                def mock_fchmod(fd, mode):
                    raise AttributeError("os.fchmod not available")

                with patch('os.fchmod', side_effect=mock_fchmod):
                    # Create storage and add a todo
                    storage = Storage(str(storage_path))
                    storage.add(Todo(title="Test todo"))

            # Verify the final file has strict permissions
            # Skip on Windows where chmod doesn't work the same way
            if os.name != 'nt':
                stat_info = os.stat(storage_path)
                file_mode = stat_info.st_mode & 0o777
                assert file_mode == 0o600, \
                    f"File should have 0o600 permissions, got {oct(file_mode)}"

    def test_windows_race_condition_prevention_via_directory_permissions(self):
        """Test that even with the race condition, directory permissions protect files.

        The code sets directory permissions to 0o700, which mitigates the race
        condition on Windows where os.fchmod is not available.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "subdir" / "todos.json"

            # Create storage
            storage = Storage(str(storage_path))

            # Verify parent directory has restrictive permissions
            # Skip on Windows where chmod doesn't work the same way
            if os.name != 'nt':
                parent_stat = os.stat(storage_path.parent)
                parent_mode = parent_stat.st_mode & 0o777
                assert parent_mode == 0o700, \
                    f"Parent directory should have 0o700 permissions, got {oct(parent_mode)}"

            # Add a todo
            storage.add(Todo(title="Test todo"))

            # Verify file was created successfully
            assert storage_path.exists(), "File should have been created"
            assert storage.list() == [Todo(id=1, title="Test todo", status="pending")]
