"""Test for issue #170 - next_id calculation clarity in _save_with_todos.

Issue #170 is about code clarity: the formula max(max_id, self._next_id - 1) + 1
is mathematically correct but confusing. It should be changed to max(max_id + 1, self._next_id)
to make the intent clear: next_id should be the max of (max existing ID + 1) and (current next_id).

This test ensures the behavior is correct after the formula is clarified.
"""

import json
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_next_id_formula_behavior():
    """Test that the next_id calculation in _save_with_todos preserves high _next_id values.

    The formula should ensure that next_id is the max of (max_id + 1) and (self._next_id).
    This means:
    - If we have todos with IDs up to 10, but _next_id is 100, next_id should be 100
    - If we have todos with IDs up to 100, but _next_id is 5, next_id should be 101

    This test verifies the behavior that next_id = max(max_id + 1, self._next_id).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add some todos with low IDs
        todo1 = storage.add(Todo(title="Todo 1"))
        todo2 = storage.add(Todo(title="Todo 2"))
        todo3 = storage.add(Todo(title="Todo 3"))

        # Add a todo with a high ID
        high_todo = storage.add(Todo(id=100, title="High ID Todo"))

        # _next_id should now be 101 (100 + 1)
        assert storage.get_next_id() == 101

        # Delete a low-ID todo
        storage.delete(todo2.id)

        # Read the file to verify saved next_id
        with storage_path.open('r') as f:
            data = json.load(f)

        # max_id in file is 100, so max_id + 1 = 101
        # self._next_id is also 101
        # The saved next_id should be max(101, 101) = 101
        assert data["next_id"] == 101, (
            f"Expected next_id=101 (max of max_id+1=101 and _next_id=101), "
            f"but got {data['next_id']}"
        )

        # Add another todo - should get ID 101
        new_todo = storage.add(Todo(title="New Todo"))
        assert new_todo.id == 101


def test_next_id_preserves_high_value_when_deleting_high_ids():
    """Test that _next_id is preserved even when deleting high-ID todos.

    If we have _next_id = 100 and delete all todos, the saved next_id should
    still be 100 (or higher), not reset to 1.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo with high ID
        high_todo = storage.add(Todo(id=100, title="High ID Todo"))

        # _next_id should be 101
        assert storage.get_next_id() == 101

        # Delete the high-ID todo
        storage.delete(high_todo.id)

        # Read the file to verify saved next_id
        with storage_path.open('r') as f:
            data = json.load(f)

        # max_id in file is 0 (no todos), so max_id + 1 = 1
        # But self._next_id is still 101
        # The saved next_id should be max(1, 101) = 101
        assert data["next_id"] == 101, (
            f"Expected next_id=101 (preserved _next_id), "
            f"but got {data['next_id']}"
        )

        # Add a new todo - should get ID 101
        new_todo = storage.add(Todo(title="New Todo"))
        assert new_todo.id == 101
