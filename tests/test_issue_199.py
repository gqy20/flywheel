"""Test that _save_with_todos method is complete and functional (Issue #199).

This test verifies that the _save_with_todos method in Storage class is
properly implemented and can handle all operations including:
- File writing
- Permission setting
- Atomic replacement
- Internal state update (self._todos = todos)
"""

import json
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_method_exists():
    """Test that _save_with_todos method exists and is callable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Verify method exists
        assert hasattr(storage, "_save_with_todos"), "_save_with_todos method not found"
        assert callable(getattr(storage, "_save_with_todos")), "_save_with_todos is not callable"


def test_save_with_todos_writes_file():
    """Test that _save_with_todos writes todos to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create test todos
        todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="completed"),
        ]

        # Call _save_with_todos
        storage._save_with_todos(todos)

        # Verify file was written
        assert storage_path.exists(), "File was not created"

        # Verify file contents
        with storage_path.open('r') as f:
            data = json.load(f)

        assert "todos" in data, "File missing 'todos' key"
        assert "next_id" in data, "File missing 'next_id' key"
        assert len(data["todos"]) == 2, "Wrong number of todos in file"
        assert data["todos"][0]["title"] == "Task 1"
        assert data["todos"][1]["title"] == "Task 2"


def test_save_with_todos_updates_internal_state():
    """Test that _save_with_todos updates self._todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create test todos
        todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="completed"),
        ]

        # Call _save_with_todos
        storage._save_with_todos(todos)

        # Verify internal state was updated
        assert len(storage._todos) == 2, "Internal _todos not updated"
        assert storage._todos[0].title == "Task 1"
        assert storage._todos[1].title == "Task 2"


def test_save_with_todos_updates_next_id():
    """Test that _save_with_todos updates next_id correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create test todos with high IDs
        todos = [
            Todo(id=100, title="Task 100", status="pending"),
            Todo(id=200, title="Task 200", status="completed"),
        ]

        # Call _save_with_todos
        storage._save_with_todos(todos)

        # Verify next_id was updated
        assert storage._next_id == 201, f"next_id should be 201, got {storage._next_id}"

        # Verify file has correct next_id
        with storage_path.open('r') as f:
            data = json.load(f)
        assert data["next_id"] == 201, f"File next_id should be 201, got {data['next_id']}"


def test_save_with_todos_empty_list():
    """Test that _save_with_todos handles empty list correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo first to set next_id
        storage.add(Todo(id=1, title="Task 1", status="pending"))
        original_next_id = storage._next_id

        # Save empty list
        storage._save_with_todos([])

        # Verify internal state
        assert len(storage._todos) == 0, "Internal _todos should be empty"
        # next_id should be preserved when saving empty list (Issue #175)
        assert storage._next_id == original_next_id, "next_id should be preserved with empty list"


def test_save_with_todos_atomic_replace():
    """Test that _save_with_todos uses atomic file replacement."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create initial todos
        todos = [Todo(id=1, title="Task 1", status="pending")]

        # Call _save_with_todos
        storage._save_with_todos(todos)

        # Verify no temporary files left behind
        tmp_files = list(Path(tmpdir).glob("*.tmp"))
        assert len(tmp_files) == 0, f"Temporary files not cleaned up: {tmp_files}"


def test_save_with_todos_line_241_complete():
    """Test that line 241 in storage.py is complete and functional.

    Issue #199 claims line 241 is truncated. This test verifies the
    logic around that line (max_id calculation and next_id assignment).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create todos with various IDs
        todos = [
            Todo(id=5, title="Task 5", status="pending"),
            Todo(id=10, title="Task 10", status="pending"),
            Todo(id=15, title="Task 15", status="pending"),
        ]

        # This tests the logic at line 239-241:
        # max_id = max((t.id for t in todos if isinstance(t.id, int) and t.id > 0), default=0)
        # next_id_copy = max(max_id + 1, self._next_id)
        storage._save_with_todos(todos)

        # Verify max_id was calculated correctly (should be 15)
        # So next_id should be max(15 + 1, 1) = 16
        assert storage._next_id == 16, f"next_id should be 16, got {storage._next_id}"

        # Verify file has correct next_id
        with storage_path.open('r') as f:
            data = json.load(f)
        assert data["next_id"] == 16, f"File next_id should be 16, got {data['next_id']}"
