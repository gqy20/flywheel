"""Test for Issue #101 - next_id not updated in _save_with_todos.

This test verifies that when _save_with_todos is called with todos that have
higher IDs than the current _next_id, the _next_id is properly updated to
maintain consistency.
"""

import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_next_id_updated_after_save_with_todos():
    """Test that _next_id is updated when saving todos with higher IDs.

    This tests the scenario where _save_with_todos receives a todos list
    containing IDs higher than the current _next_id. The method should
    update _next_id to maintain consistency and prevent ID conflicts.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Initially, _next_id should be 1 (no todos yet)
        assert storage.get_next_id() == 1

        # Add a todo with ID 1
        todo1 = Todo(id=1, title="Todo 1")
        storage.add(todo1)
        # After adding ID 1, _next_id should be 2
        assert storage.get_next_id() == 2

        # Now simulate a scenario where we directly manipulate todos
        # with a higher ID (e.g., from an external source)
        # Create a new storage instance to simulate loading from file
        storage2 = Storage(str(storage_path))

        # Directly call _save_with_todos with a todo that has a higher ID
        # This simulates what happens when we add a todo with ID=10
        high_id_todo = Todo(id=10, title="High ID todo")
        storage2._save_with_todos([todo1, high_id_todo])

        # BUG: After _save_with_todos, _next_id should be updated to 11
        # but it's still 2, which will cause ID conflict on next add
        assert storage2.get_next_id() == 11, (
            f"Expected _next_id to be 11 after saving todo with ID=10, "
            f"but got {storage2.get_next_id()}. "
            f"This is the bug in issue #101."
        )

        # Verify that adding a new todo gets ID=11 (not ID=2 which would conflict)
        new_todo = Todo(title="New todo")
        added = storage2.add(new_todo)
        assert added.id == 11, (
            f"Expected new todo to get ID=11, but got ID={added.id}. "
            f"This indicates _next_id was not properly updated."
        )


def test_next_id_consistency_after_update():
    """Test that _next_id remains consistent after updating todos.

    When a todo is updated through _save_with_todos, _next_id should
    not be affected if the IDs haven't changed.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo1 = Todo(id=1, title="Todo 1")
        storage.add(todo1)
        assert storage.get_next_id() == 2

        # Update the todo (same ID)
        updated_todo = Todo(id=1, title="Updated Todo 1")
        storage.update(updated_todo)

        # _next_id should still be 2
        assert storage.get_next_id() == 2


def test_next_id_with_multiple_high_id_todos():
    """Test _next_id update with multiple high-ID todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Start with empty storage
        assert storage.get_next_id() == 1

        # Create todos with high IDs (simulating external import)
        todos = [
            Todo(id=5, title="Todo 5"),
            Todo(id=10, title="Todo 10"),
            Todo(id=15, title="Todo 15"),
        ]

        # Use _save_with_todos to save these todos
        storage._save_with_todos(todos)

        # BUG: _next_id should be 16 (max ID + 1)
        assert storage.get_next_id() == 16, (
            f"Expected _next_id to be 16 after saving todos with max ID=15, "
            f"but got {storage.get_next_id()}. "
            f"This is the bug in issue #101."
        )

        # Verify new todo gets correct ID
        new_todo = Todo(title="New todo")
        added = storage.add(new_todo)
        assert added.id == 16
