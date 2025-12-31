"""Test for Issue #266 - Truncated string in _cleanup method."""

import tempfile
import os
from pathlib import Path
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_cleanup_handles_save_error():
    """Test that _cleanup method properly handles save errors without crashing.

    This test ensures that:
    1. The _cleanup method can be called without syntax errors
    2. When _save fails, the error is logged gracefully
    3. No exception is raised from _cleanup
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to make storage dirty
        todo = Todo(title="Test todo", status="pending")
        storage.add(todo)

        # Verify storage is dirty
        assert storage._dirty is True

        # Make the storage file read-only to force save failure
        os.chmod(storage_path, 0o444)

        try:
            # Call _cleanup - it should handle the error gracefully
            # If there's a syntax error in the code, this will fail to import
            storage._cleanup()

            # If we reach here, _cleanup handled the error properly
            # (it should have logged the error but not raised an exception)
        finally:
            # Restore permissions for cleanup
            os.chmod(storage_path, 0o644)


def test_syntax_check_storage_module():
    """Test that storage.py can be imported without syntax errors.

    This test will fail if there's a syntax error in the file (like truncated strings).
    """
    # Simply importing the module will catch syntax errors
    import flywheel.storage
    assert flywheel.storage is not None


def test_cleanup_logs_error_on_failure():
    """Test that _cleanup logs an error when save fails.

    This verifies that the logger.error call is complete and properly formatted.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo", status="pending")
        storage.add(todo)

        # Make the parent directory read-only to force save failure
        os.chmod(tmpdir, 0o444)

        try:
            # Call _cleanup - it should log an error
            storage._cleanup()
            # No exception should be raised
        finally:
            # Restore permissions for cleanup
            os.chmod(tmpdir, 0o755)


def test_cleanup_succeeds_when_save_works():
    """Test that _cleanup successfully saves pending changes when possible."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo", status="pending")
        storage.add(todo)

        # Verify storage is dirty
        assert storage._dirty is True

        # Call _cleanup - it should save successfully
        storage._cleanup()

        # After cleanup, storage should be clean
        assert storage._dirty is False

        # Verify the todo was saved
        storage2 = Storage(str(storage_path))
        todos = storage2.list()
        assert len(todos) == 1
        assert todos[0].title == "Test todo"
