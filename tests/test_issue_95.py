"""Test for Issue #95: _save_with_todos doesn't update self._todos."""

import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_updates_internal_state():
    """Test that _save_with_todos updates self._todos to maintain consistency.

    This test verifies the bug described in Issue #95:
    The _save_with_todos method saves the external todos list to file but
    doesn't update self._todos, causing inconsistency between memory and file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage and add initial todos
        storage = Storage(str(storage_path))
        storage.add(Todo(title="Task 1"))
        storage.add(Todo(title="Task 2"))

        # Get current internal state
        original_todos = storage.list()
        assert len(original_todos) == 2

        # Create a new todos list with different content
        new_todos = [
            Todo(id=1, title="Modified Task 1", status="completed"),
            Todo(id=2, title="Modified Task 2", status="pending"),
            Todo(id=3, title="New Task 3", status="pending"),
        ]

        # Call _save_with_todos directly with the new list
        storage._save_with_todos(new_todos)

        # BUG: self._todos should be updated to match the file content
        # After calling _save_with_todos, the internal state should reflect the new list
        assert storage._todos == new_todos, (
            "self._todos should be updated to match the saved file content. "
            f"Expected {len(new_todos)} todos, but got {len(storage._todos)}"
        )

        # Verify the file was actually updated
        storage2 = Storage(str(storage_path))
        file_todos = storage2.list()
        assert len(file_todos) == 3, "File should contain 3 todos"
        assert file_todos[0].title == "Modified Task 1"
        assert file_todos[0].status == "completed"

        # Verify consistency: memory should match file
        assert len(storage._todos) == len(file_todos), (
            f"Memory has {len(storage._todos)} todos but file has {len(file_todos)}"
        )
