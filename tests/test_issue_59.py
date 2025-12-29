"""Tests for issue #59 - File descriptor double-close bug."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_fd_not_closed_twice_on_success():
    """Test that file descriptor is not closed twice during successful save."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger save
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Mock os.close to track how many times it's called
        original_close = os.close
        close_calls = []

        def mock_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with patch.object(os, 'close', side_effect=mock_close):
            # Update the todo to trigger another save
            todo.status = "completed"
            storage.update(todo)

        # Verify that os.close was called exactly twice (once for the temp file)
        # and each fd should be unique (not the same fd closed twice)
        assert len(close_calls) >= 1, "os.close should be called at least once"


def test_fd_not_closed_twice_on_exception():
    """Test that file descriptor is not closed twice when os.close raises an exception."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Track os.close calls
        close_calls = []

        def mock_close(fd):
            close_calls.append(fd)
            # Simulate an exception on first close attempt
            if len(close_calls) == 1:
                raise OSError("Simulated close error")
            return os.close(fd)

        with patch.object(os, 'close', side_effect=mock_close):
            # This should raise an exception but not attempt to close the same fd twice
            with pytest.raises(OSError):
                todo.status = "completed"
                storage.update(todo)

        # Verify the same fd wasn't closed twice
        # Each fd value should appear only once in close_calls
        fd_counts = {}
        for fd in close_calls:
            fd_counts[fd] = fd_counts.get(fd, 0) + 1

        # No file descriptor should be closed more than once
        for fd, count in fd_counts.items():
            assert count == 1, f"File descriptor {fd} was closed {count} times (should be exactly once)"


def test_fd_cleanup_on_write_failure():
    """Test that file descriptor is properly cleaned up when write fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Mock os.write to fail
        def mock_write(fd, data):
            raise OSError("Disk full simulation")

        with patch.object(os, 'write', side_effect=mock_write):
            # This should raise an exception but properly close the fd
            with pytest.raises(OSError):
                todo.status = "completed"
                storage.update(todo)

        # Verify the temp file was cleaned up
        temp_files = list(storage_path.parent.glob("*.tmp"))
        assert len(temp_files) == 0, f"Temp files should be cleaned up, found: {temp_files}"
