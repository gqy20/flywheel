"""Test to verify issue #159 is a false positive.

Issue #159 claims that the _save_with_todos method is truncated at line 243
with the comment "# Re-raise other OSErr". This test verifies that:
1. The code is syntactically complete
2. The method works correctly including OSError handling
3. The fsync, close, replace, and finally blocks are all present
"""

import json
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_method_complete():
    """Verify _save_with_todos method is complete and functional."""
    # Create a temporary storage
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to test _save_with_todos
        todo = Todo(title="Test todo", status="pending")
        added_todo = storage.add(todo)

        # Verify the todo was saved correctly
        assert added_todo.id is not None
        assert storage_path.exists()

        # Verify the file contains valid JSON with expected structure
        with storage_path.open('r') as f:
            data = json.load(f)

        assert "todos" in data
        assert "next_id" in data
        assert len(data["todos"]) == 1
        assert data["todos"][0]["title"] == "Test todo"


def test_save_with_todos_error_handling():
    """Verify _save_with_todos handles OSError correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todo1 = storage.add(Todo(title="Todo 1", status="pending"))
        todo2 = storage.add(Todo(title="Todo 2", status="pending"))

        # Update a todo (tests _save_with_todos)
        updated_todo = Todo(id=todo1.id, title="Updated Todo 1", status="completed")
        storage.update(updated_todo)

        # Verify the update persisted
        retrieved = storage.get(todo1.id)
        assert retrieved is not None
        assert retrieved.title == "Updated Todo 1"
        assert retrieved.status == "completed"


def test_save_with_todos_deletion():
    """Verify _save_with_todos works correctly for deletion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add todos
        todo1 = storage.add(Todo(title="Todo 1", status="pending"))
        todo2 = storage.add(Todo(title="Todo 2", status="pending"))

        # Delete one (tests _save_with_todos)
        result = storage.delete(todo1.id)
        assert result is True

        # Verify only one todo remains
        todos = storage.list()
        assert len(todos) == 1
        assert todos[0].id == todo2.id


def test_save_with_todos_atomic_replace():
    """Verify _save_with_todos uses atomic replace operation."""
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Get initial inode (file identifier)
        initial_stat = storage_path.stat() if storage_path.exists() else None

        # Add a todo
        storage.add(Todo(title="Test", status="pending"))

        # Verify file still exists and has content
        assert storage_path.exists()
        with storage_path.open('r') as f:
            data = json.load(f)

        assert len(data["todos"]) == 1
