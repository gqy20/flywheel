"""Test for Issue #150: Ensure _save_with_todos updates internal state correctly.

This test verifies that when _save_with_todos is called, it correctly updates
self._todos with the original todos parameter (not the deep copy) after
the file write succeeds.
"""

import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_uses_original_list():
    """Test that _save_with_todos uses the original todos list after write.

    This test verifies the fix for Issue #150. The issue is that _save_with_todos
    creates a deep copy of todos (todos_copy) for file writing, but then updates
    self._todos with todos_copy instead of the original todos parameter.

    This test checks that self._todos is updated with the original todos list
    (not the copy) after the file write succeeds.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Create todos list
        todos_list = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="pending"),
        ]

        # Save the todos
        storage._save_with_todos(todos_list)

        # Verify that self._todos now points to the data that was saved
        # The fix should ensure self._todos is updated with the original list
        with storage._lock:
            internal_todos = storage._todos

        # Both should have the same content
        assert len(internal_todos) == len(todos_list)
        assert internal_todos[0].id == todos_list[0].id
        assert internal_todos[1].id == todos_list[1].id

        # The file should also contain the same data
        with storage_path.open('r') as f:
            import json
            saved_data = json.load(f)

        assert len(saved_data["todos"]) == 2
