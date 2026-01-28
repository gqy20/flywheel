"""Test for issue #24: File descriptor synchronization error handling."""

import os
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_fsync_failure_does_not_cause_double_close():
    """
    Test that if os.fsync fails after os.write succeeds,
    the file descriptor is not closed twice.
    """
    # Create a temporary storage path
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger _save
        todo = Todo(id=1, title="Test todo", status="pending")

        # Mock os.write to succeed, os.fsync to fail, and os.close to track calls
        original_write = os.write
        original_fsync = os.fsync
        original_close = os.close
        close_calls = []

        def mock_write(fd, data):
            # Call original write
            return original_write(fd, data)

        def mock_fsync(fd):
            # Simulate fsync failure
            raise OSError("Simulated fsync failure")

        def mock_close(fd):
            # Track close calls
            close_calls.append(fd)
            return original_close(fd)

        with mock.patch('os.write', side_effect=mock_write):
            with mock.patch('os.fsync', side_effect=mock_fsync):
                with mock.patch('os.close', side_effect=mock_close):
                    # This should raise an exception due to fsync failure
                    with pytest.raises(OSError, match="Simulated fsync failure"):
                        storage._save_with_todos([todo])

        # Verify that os.close was called exactly once
        # The bug would cause it to be called twice (once after fsync fails, once in finally)
        assert len(close_calls) == 1, f"Expected os.close to be called once, but was called {len(close_calls)} times"


def test_fsync_failure_cleans_up_temp_file():
    """
    Test that if os.fsync fails, the temporary file is cleaned up
    and the original file is not modified.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create an initial todo
        todo1 = Todo(id=1, title="Original todo", status="pending")
        storage._save_with_todos([todo1])

        # Try to save with fsync failing
        todo2 = Todo(id=2, title="New todo", status="pending")

        with mock.patch('os.fsync', side_effect=OSError("Simulated fsync failure")):
            with pytest.raises(OSError, match="Simulated fsync failure"):
                storage._save_with_todos([todo1, todo2])

        # Verify original file is unchanged
        storage2 = Storage(str(storage_path))
        todos = storage2.list()
        assert len(todos) == 1
        assert todos[0].title == "Original todo"


def test_save_success_closes_fd_exactly_once():
    """
    Test that on successful save, the file descriptor is closed exactly once.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        todo = Todo(id=1, title="Test todo", status="pending")

        # Track close calls
        original_close = os.close
        close_calls = []

        def mock_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with mock.patch('os.close', side_effect=mock_close):
            storage._save_with_todos([todo])

        # Verify that os.close was called exactly once in the finally block
        assert len(close_calls) == 1, f"Expected os.close to be called once, but was called {len(close_calls)} times"
