"""Test for Issue #115 - Verify file descriptor closure in _save_with_todos.

This test verifies that the `finally` clause in `_save_with_todos` properly
closes the file descriptor even when an exception occurs during write.
"""

import os
import tempfile
from unittest.mock import patch
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_closes_fd_on_write_error():
    """Test that _save_with_todos closes file descriptor on write error.

    This test simulates a write failure in os.write to ensure that the
    file descriptor is properly closed even when an exception occurs.

    This verifies the fix for Issue #115.
    """
    # Track open file descriptors before the test
    initial_fds = set(os.listdir('/proc/self/fd'))

    # Create a storage instance with a temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to initialize the storage
        todo = Todo(title="Test Todo", status="pending")
        storage.add(todo)

        # Mock os.write to raise an error on the second call (during _save_with_todos)
        original_write = os.write
        call_count = [0]

        def mock_write(fd, data):
            call_count[0] += 1
            # Let the first write succeed (initial save)
            if call_count[0] == 1:
                return original_write(fd, data)
            # Second write fails (simulating disk full or other error)
            raise OSError("Simulated write error")

        with patch('os.write', side_effect=mock_write):
            # Try to update, which will call _save_with_todos and fail
            updated_todo = Todo(id=todo.id, title="Updated", status="completed")
            with pytest.raises(OSError, match="Simulated write error"):
                storage.update(updated_todo)

        # Collect all open file descriptors
        final_fds = set(os.listdir('/proc/self/fd'))

        # The number of open file descriptors should be the same
        # (no file descriptor leak)
        leaked_fds = final_fds - initial_fds
        assert len(leaked_fds) == 0, f"File descriptors leaked: {leaked_fds}"


def test_save_with_todos_closes_fd_on_replace_error():
    """Test that _save_with_todos closes file descriptor on Path.replace error.

    This test simulates a failure during the atomic replace operation to ensure
    that the file descriptor is properly closed.
    """
    # Track open file descriptors before the test
    initial_fds = set(os.listdir('/proc/self/fd'))

    # Create a storage instance with a temporary file
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to initialize the storage
        todo = Todo(title="Test Todo", status="pending")
        storage.add(todo)

        # Mock Path.replace to raise an error
        original_replace = Path.replace
        call_count = [0]

        def mock_replace(self, target):
            call_count[0] += 1
            # Let the first replace succeed
            if call_count[0] == 1:
                return original_replace(self, target)
            # Second replace fails
            raise OSError("Simulated replace error")

        with patch.object(Path, 'replace', side_effect=mock_replace):
            # Try to update, which will call _save_with_todos and fail
            updated_todo = Todo(id=todo.id, title="Updated", status="completed")
            with pytest.raises(OSError, match="Simulated replace error"):
                storage.update(updated_todo)

        # Collect all open file descriptors
        final_fds = set(os.listdir('/proc/self/fd'))

        # The number of open file descriptors should be the same
        # (no file descriptor leak)
        leaked_fds = final_fds - initial_fds
        assert len(leaked_fds) == 0, f"File descriptors leaked: {leaked_fds}"
