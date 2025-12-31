"""Test Issue #9: Save failure should not corrupt internal state.

This test verifies that when a save operation fails (e.g., disk full),
the internal state (self._todos and self._next_id) remains consistent
and does not get partially updated.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_add_save_failure_preserves_state():
    """Test that add() preserves state when save fails.

    When add() fails to save (e.g., disk full), both self._todos
    and self._next_id should remain unchanged to prevent state
    inconsistency where memory has been modified but disk hasn't.
    """
    storage = Storage()
    initial_next_id = storage.get_next_id()
    initial_todos = storage.list()

    # Add a todo, but mock the write to fail (simulate disk full)
    with patch.object(storage, '_save_with_todos', side_effect=OSError("Disk full")):
        with pytest.raises(OSError, match="Disk full"):
            storage.add(Todo(title="New task"))

    # After failure, state should be unchanged
    assert storage.list() == initial_todos, "self._todos should not be modified on save failure"
    assert storage.get_next_id() == initial_next_id, "self._next_id should not be modified on save failure"


def test_update_save_failure_preserves_state():
    """Test that update() preserves state when save fails.

    When update() fails to save, the internal state should remain
    unchanged to prevent inconsistency.
    """
    storage = Storage()
    todo = storage.add(Todo(title="Original task"))
    initial_todos = storage.list()

    # Attempt to update, but mock the save to fail
    updated_todo = Todo(id=todo.id, title="Updated task")
    with patch.object(storage, '_save_with_todos', side_effect=OSError("Disk full")):
        with pytest.raises(OSError, match="Disk full"):
            storage.update(updated_todo)

    # After failure, state should be unchanged (still has original title)
    todos = storage.list()
    assert len(todos) == 1
    assert todos[0].title == "Original task", "Todo should not be modified on save failure"


def test_delete_save_failure_preserves_state():
    """Test that delete() preserves state when save fails.

    When delete() fails to save, the internal state should remain
    unchanged to prevent inconsistency.
    """
    storage = Storage()
    todo = storage.add(Todo(title="Task to delete"))

    # Attempt to delete, but mock the save to fail
    with patch.object(storage, '_save_with_todos', side_effect=OSError("Disk full")):
        with pytest.raises(OSError, match="Disk full"):
            storage.delete(todo.id)

    # After failure, state should be unchanged (todo still exists)
    todos = storage.list()
    assert len(todos) == 1, "Todo should not be deleted on save failure"
    assert todos[0].id == todo.id


def test_state_consistency_after_save_failure_and_reload():
    """Test that state is consistent after save failure and reload.

    This simulates the real-world scenario where:
    1. User tries to add a todo
    2. Save fails (e.g., disk full)
    3. User restarts the application (reload from disk)
    4. State should be consistent with what's on disk
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(path=str(storage_path))

        # Add initial todo
        storage.add(Todo(title="Task 1"))
        initial_next_id = storage.get_next_id()

        # Create a new storage instance to simulate reload
        storage_reloaded = Storage(path=str(storage_path))

        # Verify the reloaded state matches the saved state
        assert len(storage_reloaded.list()) == 1
        assert storage_reloaded.list()[0].title == "Task 1"
        assert storage_reloaded.get_next_id() == initial_next_id

        # Now test failure case: try to add, but save fails
        with patch.object(storage_reloaded, '_save_with_todos', side_effect=OSError("Disk full")):
            with pytest.raises(OSError, match="Disk full"):
                storage_reloaded.add(Todo(title="Task 2"))

        # Even though we tried to add Task 2, it shouldn't be in memory
        assert len(storage_reloaded.list()) == 1, "Task should not be added to memory on save failure"

        # Create another reload to verify disk state is unchanged
        storage_final = Storage(path=str(storage_path))

        # Disk state should still only have Task 1
        assert len(storage_final.list()) == 1
        assert storage_final.list()[0].title == "Task 1"
        assert storage_final.get_next_id() == initial_next_id
