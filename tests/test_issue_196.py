"""Tests for Issue #196 - File descriptor leak when os.fchmod fails.

This test verifies that file descriptors are properly closed even when
os.fchmod() fails with an exception.
"""

import os
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_file_descriptor_closed_when_fchmod_fails_in_save():
    """Test that file descriptor is closed when os.fchmod fails in _save method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with one todo
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Test todo"))
        initial_fd_count = len(os.listdir("/proc/self/fd")) if Path("/proc/self/fd").exists() else 0

        # Mock os.fchmod to raise an exception
        with unittest.mock.patch('os.fchmod', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                # This should trigger the bug where fd is not closed
                storage.add(Todo(title="Another todo"))

        # Check that file descriptor was closed
        # (On systems with /proc, we can check; otherwise we just verify no exception in cleanup)
        if Path("/proc/self/fd").exists():
            final_fd_count = len(os.listdir("/proc/self/fd"))
            # File descriptor count should be the same as initial
            assert final_fd_count == initial_fd_count, "File descriptor was leaked"


def test_file_descriptor_closed_when_fchmod_fails_in_save_with_todos():
    """Test that file descriptor is closed when os.fchmod fails in _save_with_todos method."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with one todo
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Test todo"))
        initial_fd_count = len(os.listdir("/proc/self/fd")) if Path("/proc/self/fd").exists() else 0

        # Mock os.fchmod to raise an exception
        with unittest.mock.patch('os.fchmod', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                # Update will call _save_with_todos, triggering the bug
                todo = storage.get(1)
                todo.status = "completed"
                storage.update(todo)

        # Check that file descriptor was closed
        if Path("/proc/self/fd").exists():
            final_fd_count = len(os.listdir("/proc/self/fd"))
            # File descriptor count should be the same as initial
            assert final_fd_count == initial_fd_count, "File descriptor was leaked"


def test_temp_file_cleaned_up_when_fchmod_fails():
    """Test that temporary file is cleaned up when os.fchmod fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Test todo"))

        # Count initial .tmp files
        initial_tmp_count = len(list(Path(tmpdir).glob("*.tmp")))

        # Mock os.fchmod to raise an exception
        with unittest.mock.patch('os.fchmod', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                storage.add(Todo(title="Another todo"))

        # Verify no temporary files leaked
        final_tmp_count = len(list(Path(tmpdir).glob("*.tmp")))
        assert final_tmp_count == initial_tmp_count, "Temporary file was not cleaned up"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
