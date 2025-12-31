"""Tests for Issue #184 - Verify code completeness.

Issue #184 claimed that:
1. The `_save_with_todos` method was incomplete/truncated
2. The `__init__` method was missing `self._load()` call

This test verifies that both issues are resolved.
"""

import json
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_method_exists():
    """Test that _save_with_todos method is complete and functional."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create some todos
        todo1 = Todo(id=1, title="Task 1", status="pending")
        todo2 = Todo(id=2, title="Task 2", status="completed")

        # Call _save_with_todos directly to ensure it's implemented
        storage._save_with_todos([todo1, todo2])

        # Verify file was written correctly
        assert storage_path.exists()
        with open(storage_path) as f:
            data = json.load(f)

        assert "todos" in data
        assert len(data["todos"]) == 2
        assert data["todos"][0]["title"] == "Task 1"
        assert data["todos"][1]["title"] == "Task 2"
        assert "next_id" in data


def test_init_calls_load():
    """Test that __init__ calls _load() to initialize state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Pre-create a todo file with data
        test_data = {
            "todos": [
                {"id": 1, "title": "Preloaded Task", "status": "pending"}
            ],
            "next_id": 2
        }
        with open(storage_path, 'w') as f:
            json.dump(test_data, f)

        # Create storage - this should call _load() automatically
        storage = Storage(str(storage_path))

        # Verify that data was loaded
        assert len(storage._todos) == 1
        assert storage._todos[0].title == "Preloaded Task"
        assert storage._next_id == 2


def test_save_with_todos_with_empty_list():
    """Test that _save_with_todos handles empty list correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo first to set _next_id
        todo1 = Todo(id=1, title="Task 1", status="pending")
        storage._save_with_todos([todo1])
        assert storage._next_id == 2

        # Save with empty list - should preserve _next_id
        storage._save_with_todos([])
        assert storage._next_id == 2  # Should not reset to 1

        # Verify file was written correctly
        with open(storage_path) as f:
            data = json.load(f)
        assert data["todos"] == []
        assert data["next_id"] == 2


def test_save_with_todos_atomic_update():
    """Test that _save_with_todos updates internal state only after successful write."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create new todos list
        new_todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="completed")
        ]

        # Save
        storage._save_with_todos(new_todos)

        # Verify internal state was updated
        assert len(storage._todos) == 2
        assert storage._todos[0].title == "Task 1"
        assert storage._todos[1].title == "Task 2"

        # Verify file matches internal state
        with open(storage_path) as f:
            data = json.load(f)
        assert len(data["todos"]) == 2
