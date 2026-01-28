"""Test for Issue #165 - Verify self._todos is updated after save."""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_updates_internal_state():
    """Test that _save_with_todos updates self._todos after successful write.

    This test verifies that after calling _save_with_todos, the internal
    self._todos state is updated to match the saved data.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo1 = Todo(id=1, title="Task 1", status="pending")
        storage.add(todo1)

        # Verify the todo is in memory
        assert len(storage._todos) == 1
        assert storage._todos[0].title == "Task 1"

        # Create a new todos list
        new_todos = [
            Todo(id=1, title="Task 1 - updated", status="pending"),
            Todo(id=2, title="Task 2", status="pending"),
        ]

        # Call _save_with_todos directly
        storage._save_with_todos(new_todos)

        # Verify internal state is updated
        assert len(storage._todos) == 2, f"Expected 2 todos in memory, got {len(storage._todos)}"
        assert storage._todos[0].title == "Task 1 - updated", f"Expected 'Task 1 - updated', got '{storage._todos[0].title}'"
        assert storage._todos[1].title == "Task 2", f"Expected 'Task 2', got '{storage._todos[1].title}'"

        # Also verify the file was written correctly
        with storage_path.open('r') as f:
            data = json.load(f)
        assert len(data["todos"]) == 2
        assert data["todos"][0]["title"] == "Task 1 - updated"
        assert data["todos"][1]["title"] == "Task 2"


def test_save_with_todos_updates_next_id():
    """Test that _save_with_todos updates self._next_id after successful write.

    This test verifies that after calling _save_with_todos, the internal
    self._next_id state is updated correctly based on the saved todos.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Start with empty todos
        assert storage._next_id == 1

        # Create todos with higher IDs
        new_todos = [
            Todo(id=5, title="Task 5", status="pending"),
            Todo(id=10, title="Task 10", status="pending"),
        ]

        # Call _save_with_todos directly
        storage._save_with_todos(new_todos)

        # Verify _next_id is updated to max_id + 1
        assert storage._next_id == 11, f"Expected _next_id to be 11, got {storage._next_id}"

        # Verify internal state is updated
        assert len(storage._todos) == 2

        # Add a new todo - it should use the updated _next_id
        new_todo = Todo(title="New task", status="pending")
        added = storage.add(new_todo)
        assert added.id == 11, f"Expected new todo to have ID 11, got {added.id}"
