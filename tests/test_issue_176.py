"""Test for issue #176: Invalid ID 0 should be filtered out when calculating max_id."""

import tempfile
import os
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_filters_invalid_zero_id():
    """Test that _save_with_todos correctly filters out ID 0 when calculating max_id.

    Issue #176: If a list contains a Todo with id=0 (invalid), the max() call
    returns 0, causing next_id to be calculated as 1, which may cause primary
    key conflicts.

    The fix should filter out non-positive integers (id <= 0) when calculating max_id.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage and add a valid todo with id=5
        storage = Storage(str(storage_path))
        todo1 = Todo(id=5, title="Valid Todo 1", status="pending")
        storage.add(todo1)

        # Verify _next_id is updated correctly
        assert storage.get_next_id() == 6

        # Manually create an invalid todo with id=0
        todo_invalid = Todo(id=0, title="Invalid Todo", status="pending")

        # Manually create a valid todo with id=10
        todo2 = Todo(id=10, title="Valid Todo 2", status="pending")

        # Create a list with mixed valid and invalid IDs (0 and negative)
        todos_with_invalid = [
            todo_invalid,  # id=0 (invalid)
            Todo(id=-1, title="Negative ID", status="pending"),  # id=-1 (invalid)
            todo1,  # id=5 (valid)
            todo2,  # id=10 (valid)
        ]

        # Call _save_with_todos directly
        storage._save_with_todos(todos_with_invalid)

        # The max valid ID should be 10, so next_id should be 11
        assert storage.get_next_id() == 11, (
            f"Expected next_id to be 11 (max valid ID + 1), but got {storage.get_next_id()}. "
            f"This suggests the code is not properly filtering out invalid IDs (0, negative)."
        )

        # Verify the storage was updated correctly
        todos = storage.list()
        assert len(todos) == 3  # We added todo1, then saved 3 valid todos (0, -1, 5, 10) but filtered
        # Actually, let's verify what was actually saved

        # Reload storage to verify persistence
        storage2 = Storage(str(storage_path))
        assert storage2.get_next_id() == 11, "next_id should persist correctly after reload"

        # Add a new todo - it should get id=11
        todo3 = Todo(title="New Todo", status="pending")
        added_todo = storage2.add(todo3)
        assert added_todo.id == 11, f"Expected new todo to have id=11, but got {added_todo.id}"

        storage.close()
        storage2.close()


def test_save_with_todos_filters_negative_ids():
    """Test that _save_with_todos correctly filters out negative IDs when calculating max_id.

    Issue #176: Negative IDs should also be filtered out when calculating max_id.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = Storage(str(storage_path))

        # Create todos with negative IDs only
        todos_with_negative = [
            Todo(id=-5, title="Negative 1", status="pending"),
            Todo(id=-1, title="Negative 2", status="pending"),
            Todo(id=0, title="Zero", status="pending"),
        ]

        # Call _save_with_todos with only invalid IDs
        storage._save_with_todos(todos_with_negative)

        # With no valid IDs, max_id should be 0 (default), so next_id should be 1
        assert storage.get_next_id() == 1, (
            f"Expected next_id to be 1 when all IDs are invalid (negative or 0), "
            f"but got {storage.get_next_id()}"
        )

        storage.close()
