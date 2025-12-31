"""Tests for Issue #224 - Verify fchmod error handling and permission setting.

This test ensures that:
1. os.fchmod is called immediately after mkstemp
2. fchmod failures are properly handled
3. File permissions are set correctly before writing data
"""

import os
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestFchmodHandling:
    """Test fchmod error handling and permission setting (Issue #224)."""

    def test_fchmod_called_before_write(self):
        """Verify os.fchmod is called before any data is written."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Patch os.fchmod to track when it's called
            with mock.patch('os.fchmod') as mock_fchmod:
                # Create storage and add a todo
                storage = Storage(str(storage_path))
                storage.add(Todo(title="Test todo", status="pending"))

                # Verify fchmod was called
                assert mock_fchmod.called, "os.fchmod should be called to set file permissions"

                # Verify it was called with 0o600 permissions
                mock_fchmod.assert_called_with(mock.ANY, 0o600)

    def test_fchmod_failure_raises_error(self):
        """Verify that fchmod failure raises an error and prevents data write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.fchmod to raise OSError
            with mock.patch('os.fchmod', side_effect=OSError("fchmod failed")):
                storage = Storage(str(storage_path))

                # This should raise an exception
                with pytest.raises(Exception):
                    storage.add(Todo(title="Test todo", status="pending"))

                # Verify the main file was not created (since chmod failed)
                assert not storage_path.exists(), "File should not be created if fchmod fails"

    def test_windows_fchmod_fallback(self):
        """Verify Windows fallback to chmod when fchmod is not available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Mock os.fchmod to raise AttributeError (not available)
            with mock.patch('os.fchmod', side_effect=AttributeError("fchmod not available")):
                # Mock os.chmod to track calls
                with mock.patch('os.chmod') as mock_chmod:
                    storage = Storage(str(storage_path))
                    storage.add(Todo(title="Test todo", status="pending"))

                    # Verify chmod was called as fallback
                    assert mock_chmod.called, "os.chmod should be called as fallback on Windows"

                    # Verify it was called with 0o600 permissions
                    mock_chmod.assert_called_with(mock.ANY, 0o600)

    def test_file_permissions_set_before_data_write(self):
        """Verify file permissions are set before any data is written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # Track the order of operations
            call_order = []

            original_fchmod = os.fchmod
            original_write = os.write

            def mock_fchmod(fd, mode):
                call_order.append('fchmod')
                return original_fchmod(fd, mode)

            def mock_write(fd, data):
                call_order.append('write')
                return original_write(fd, data)

            with mock.patch('os.fchmod', side_effect=mock_fchmod):
                with mock.patch('os.write', side_effect=mock_write):
                    storage = Storage(str(storage_path))
                    storage.add(Todo(title="Test todo", status="pending"))

                    # Verify fchmod was called before write
                    assert call_order == ['fchmod', 'write'], \
                        "fchmod should be called before write to ensure permissions are set before data"

    def test_temp_file_has_restrictive_permissions(self):
        """Verify temporary files have 0o600 permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = Storage(str(storage_path))
            storage.add(Todo(title="Test todo", status="pending"))

            # Check the permissions of the created file
            # Note: On Windows, permissions may not work the same way
            if os.name != 'nt':
                stat_info = os.stat(storage_path)
                permissions = stat_info.st_mode & 0o777
                assert permissions == 0o600, \
                    f"File should have 0o600 permissions, got {oct(permissions)}"
