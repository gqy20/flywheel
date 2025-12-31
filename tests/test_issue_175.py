"""Test for Issue #175 - next_id should not be reset to 1 when saving empty todos list."""

import pytest
import tempfile
import os
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_next_id_not_reset_when_saving_empty_todos():
    """Test that _save_with_todos preserves next_id when todos list is empty (Issue #175)."""
    # Create a temporary file for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"

        # Initialize storage
        storage = Storage(str(storage_path))

        # Add some todos to build up next_id
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))
        todo3 = storage.add(Todo(title="Task 3"))

        # Verify next_id is correctly incremented
        assert storage.get_next_id() == 4

        # Now delete all todos (which calls _save_with_todos with empty list)
        storage.delete(todo1.id)
        storage.delete(todo2.id)
        storage.delete(todo3.id)

        # After deleting all todos, list should be empty
        assert len(storage.list()) == 0

        # BUG: The next_id should still be 4, not reset to 1
        # This is the failing assertion that demonstrates the bug
        assert storage.get_next_id() == 4, "next_id should not be reset to 1 when saving empty todos list"

        # Add a new todo - it should get ID 4, not 1
        new_todo = storage.add(Todo(title="New task after clearing all"))

        # The new todo should have ID 4 (continuing from where we left off)
        assert new_todo.id == 4, f"Expected new todo to have ID 4, but got {new_todo.id}"

        # Verify next_id is now 5
        assert storage.get_next_id() == 5


def test_next_id_preserved_after_clearing_via_save_with_todos():
    """Test that directly calling _save_with_todos with empty list preserves next_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Add todos to build up next_id
        for i in range(5):
            storage.add(Todo(title=f"Task {i}"))

        assert storage.get_next_id() == 6

        # Directly call _save_with_todos with empty list
        # This simulates clearing all todos
        storage._save_with_todos([])

        # BUG: next_id should still be 6, not reset to 1
        assert storage.get_next_id() == 6, "next_id should be preserved when _save_with_todos is called with empty list"

        # Add a new todo - should get ID 6
        new_todo = storage.add(Todo(title="New task"))
        assert new_todo.id == 6
