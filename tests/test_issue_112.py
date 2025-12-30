"""Tests for Issue #112 - Implement add method logic.

Tests verify:
1. ID conflict detection
2. Auto ID generation with _next_id
3. Counter increment
4. Adding todo to list
5. Persistence via _save_with_todos
"""

import tempfile
import pytest

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_add_generates_id_when_none():
    """Test add assigns auto-generated ID when todo.id is None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add todo without ID
        todo = Todo(title="Auto ID todo")
        result = storage.add(todo)

        # Should assign ID 1
        assert result.id == 1
        assert result.title == "Auto ID todo"
        assert storage.get(1) is not None


def test_add_increments_next_id():
    """Test add increments _next_id counter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # First todo should get ID 1
        todo1 = Todo(title="First")
        result1 = storage.add(todo1)
        assert result1.id == 1
        assert storage.get_next_id() == 2

        # Second todo should get ID 2
        todo2 = Todo(title="Second")
        result2 = storage.add(todo2)
        assert result2.id == 2
        assert storage.get_next_id() == 3


def test_add_rejects_duplicate_id():
    """Test add raises ValueError when ID already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add first todo with ID 1
        storage.add(Todo(id=1, title="First"))

        # Try to add another todo with ID 1
        with pytest.raises(ValueError, match="Todo with ID 1 already exists"):
            storage.add(Todo(id=1, title="Duplicate"))


def test_add_updates_next_id_for_explicit_id():
    """Test add updates _next_id when explicit ID is >= current _next_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add todo with explicit ID 100
        result = storage.add(Todo(id=100, title="High ID"))
        assert result.id == 100
        # _next_id should update to 101
        assert storage.get_next_id() == 101

        # Next auto-generated ID should be 101
        todo2 = Todo(title="Next")
        result2 = storage.add(todo2)
        assert result2.id == 101


def test_add_persists_to_file():
    """Test add persists todo to file via _save_with_todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = f"{tmpdir}/test.json"

        # Add todo
        storage1 = Storage(path=path)
        storage1.add(Todo(title="Persistent todo"))

        # Reload storage and verify todo exists
        storage2 = Storage(path=path)
        retrieved = storage2.get(1)
        assert retrieved is not None
        assert retrieved.title == "Persistent todo"


def test_add_returns_new_todo_with_generated_id():
    """Test add returns new Todo instance when ID is generated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        original = Todo(title="Original")
        result = storage.add(original)

        # Result should have generated ID
        assert result.id == 1

        # Original todo should remain unchanged
        assert original.id is None


def test_add_preserves_explicit_id():
    """Test add preserves explicitly set ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        todo = Todo(id=42, title="Explicit ID")
        result = storage.add(todo)

        # Should preserve the explicit ID
        assert result.id == 42
        assert storage.get(42) is not None
