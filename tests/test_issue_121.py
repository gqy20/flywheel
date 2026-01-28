"""Tests for issue #121: Race condition in _save_with_todos.

This test verifies that the storage state remains consistent when file writes fail.
The issue is that _save_with_todos updates internal state before confirming the write.
"""

import os
import pathlib
import tempfile
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_rollback_on_write_failure():
    """Test that internal state is not updated if file write fails.

    This test simulates a scenario where the file write operation fails
    after the internal state has been updated. The internal state should
    remain unchanged if the write fails.
    """
    # Create a temporary storage with initial todos
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))

        # Get the current state
        todos_before = storage.list()
        assert len(todos_before) == 2

        # Try to add a new todo, but mock os.write to fail
        todo3 = Todo(title="Task 3")

        # Mock os.write to simulate a write failure (e.g., disk full)
        original_write = os.write

        def mock_write(fd, data):
            # First call succeeds (writing the temp file header)
            # Second call fails to simulate disk full or other error
            if hasattr(mock_write, 'call_count'):
                mock_write.call_count += 1
            else:
                mock_write.call_count = 1

            if mock_write.call_count > 1:
                raise OSError(28, "No space left on device")  # ENOSPC
            return original_write(fd, data)

        with patch('os.write', side_effect=mock_write):
            # This should raise an exception due to write failure
            with pytest.raises(OSError):
                storage.add(todo3)

        # Verify that internal state was NOT updated
        # The storage should still have only the original 2 todos
        todos_after = storage.list()
        assert len(todos_after) == 2, (
            f"Expected 2 todos after failed write, but got {len(todos_after)}. "
            "Internal state was updated despite write failure!"
        )

        # Verify the todos are the original ones
        titles_after = [t.title for t in todos_after]
        assert titles_after == ["Task 1", "Task 2"], (
            f"Expected original todos, but got {titles_after}"
        )


def test_save_with_todos_rollback_on_fsync_failure():
    """Test that internal state is not updated if fsync fails.

    Similar to test_save_with_todos_rollback_on_write_failure, but
    simulates a failure during fsync instead of write.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))

        todos_before = storage.list()
        assert len(todos_before) == 1

        # Try to update a todo, but mock os.fsync to fail
        todo1_updated = Todo(id=todo1.id, title="Task 1 updated", status="done")

        with patch('os.fsync', side_effect=OSError("Input/output error")):
            # This should raise an exception due to fsync failure
            with pytest.raises(OSError):
                storage.update(todo1_updated)

        # Verify that internal state was NOT updated
        todos_after = storage.list()
        assert len(todos_after) == 1
        assert todos_after[0].title == "Task 1", (
            "Todo title should remain unchanged after failed write"
        )
        assert todos_after[0].status == "todo", (
            "Todo status should remain unchanged after failed write"
        )


def test_save_with_todos_rollback_on_replace_failure():
    """Test that internal state is not updated if file replace fails.

    This simulates a failure during the atomic replace operation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))

        # Try to delete a todo, but mock Path.replace to fail
        original_replace = pathlib.Path.replace

        def mock_replace(self, target):
            raise OSError("Permission denied")

        with patch.object(pathlib.Path, 'replace', mock_replace):
            # This should raise an exception due to replace failure
            with pytest.raises(OSError):
                storage.delete(todo1.id)

        # Verify that internal state was NOT updated
        todos_after = storage.list()
        assert len(todos_after) == 2, (
            f"Expected 2 todos after failed delete, but got {len(todos_after)}"
        )
