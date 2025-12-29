"""Test for issue #28 - duplicate file descriptor close."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_does_not_double_close_fd():
    """Test that _save doesn't attempt to close an already-closed file descriptor."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(id=1, title="Test todo", status="pending")
        storage._todos = [todo]

        # Track os.close calls to detect double close
        original_close = os.close
        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with patch('os.close', side_effect=tracking_close):
            # This should succeed without any errors
            storage._save()

        # Verify that os.close was called exactly once per save operation
        # (once for the successful close in the try block)
        assert len(close_calls) == 1, f"Expected 1 close call, got {len(close_calls)}"


def test_save_with_todos_does_not_double_close_fd():
    """Test that _save_with_todos doesn't attempt to close an already-closed file descriptor."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        todos = [Todo(id=1, title="Test todo", status="pending")]

        # Track os.close calls to detect double close
        original_close = os.close
        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        with patch('os.close', side_effect=tracking_close):
            # This should succeed without any errors
            storage._save_with_todos(todos)

        # Verify that os.close was called exactly once
        assert len(close_calls) == 1, f"Expected 1 close call, got {len(close_calls)}"


def test_save_handles_write_error_without_double_close():
    """Test that _save handles write errors without attempting to close an already-closed fd."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        todo = Todo(id=1, title="Test todo", status="pending")
        storage._todos = [todo]

        # Track os.close calls
        original_close = os.close
        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        # Make os.write fail after os.fsync
        with patch('os.write', side_effect=OSError("Write error")):
            with patch('os.close', side_effect=tracking_close):
                # This should raise an error but not attempt double close
                with pytest.raises(OSError, match="Write error"):
                    storage._save()

        # Even on error, close should only be called once
        assert len(close_calls) == 1, f"Expected 1 close call even on error, got {len(close_calls)}"


def test_save_with_todos_handles_write_error_without_double_close():
    """Test that _save_with_todos handles write errors without attempting double close."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        todos = [Todo(id=1, title="Test todo", status="pending")]

        # Track os.close calls
        original_close = os.close
        close_calls = []

        def tracking_close(fd):
            close_calls.append(fd)
            return original_close(fd)

        # Make os.write fail
        with patch('os.write', side_effect=OSError("Write error")):
            with patch('os.close', side_effect=tracking_close):
                # This should raise an error but not attempt double close
                with pytest.raises(OSError, match="Write error"):
                    storage._save_with_todos(todos)

        # Even on error, close should only be called once
        assert len(close_calls) == 1, f"Expected 1 close call even on error, got {len(close_calls)}"
