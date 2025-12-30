"""Test for issue #166: next_id in saved file should reflect actual todos.

Issue #166 points out that in _save_with_todos, the next_id value written to
the file is captured BEFORE any recalculation. If the incoming todos list
contains items with IDs higher than self._next_id, the file will contain an
incorrect (too low) next_id value.

The key issue is at line 214: next_id_copy = self._next_id
This captures the OLD next_id value, which is then written to the file at line 220.
Even though self._next_id is correctly updated in memory at lines 265-268,
the file already contains the stale value.
"""

import tempfile
import os
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_saved_file_next_id_matches_actual_todos():
    """Test that the next_id saved to file reflects the actual max ID in todos.

    This is the core bug in issue #166: when _save_with_todos is called with
    todos containing IDs higher than the current _next_id, the file should
    contain the correct next_id (max_id + 1), not the stale _next_id value.
    """
    # Create a temporary storage file
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage with an initial todo
        storage = Storage(str(storage_path))
        todo1 = storage.add(Todo(title="Todo 1"))
        assert todo1.id == 1
        assert storage.get_next_id() == 2

        # Now simulate a scenario where we directly save todos with higher IDs
        # (e.g., from external sync or import)
        external_todos = [
            Todo(id=10, title="External Todo 1", status="pending"),
            Todo(id=20, title="External Todo 2", status="pending"),
        ]

        # Call _save_with_todos directly with todos containing higher IDs
        storage._save_with_todos(external_todos)

        # Verify the saved file contains the correct next_id
        # BUG: The file should contain next_id=21 (max ID 20 + 1)
        # but it currently contains next_id=2 (the stale value)
        import json
        with open(storage_path, 'r') as f:
            saved_data = json.load(f)
            assert saved_data["next_id"] == 21, (
                f"BUG: Expected saved next_id to be 21 (max ID 20 + 1), "
                f"but got {saved_data['next_id']}. "
                f"This is issue #166 - the file contains stale next_id."
            )

        # Also verify in-memory next_id is correct (this already works due to issue #101 fix)
        assert storage.get_next_id() == 21

        # Adding a new todo should use the correct next_id
        new_todo = storage.add(Todo(title="New Todo"))
        assert new_todo.id == 21


def test_reload_storage_has_correct_next_id():
    """Test that reloading storage from file produces correct next_id.

    If the file contains a stale next_id, reloading the storage will
    start with an incorrect next_id value, leading to ID conflicts.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create storage and add initial todo
        storage1 = Storage(str(storage_path))
        storage1.add(Todo(title="Todo 1"))
        assert storage1.get_next_id() == 2

        # Save todos with higher IDs directly
        high_id_todos = [
            Todo(id=10, title="High ID Todo"),
            Todo(id=50, title="Even Higher ID Todo"),
        ]
        storage1._save_with_todos(high_id_todos)

        # Create a NEW storage instance (simulates app restart)
        # This will load from the file
        storage2 = Storage(str(storage_path))

        # BUG: If the file contains stale next_id=2, the reloaded storage
        # will have next_id=2 instead of next_id=51
        assert storage2.get_next_id() == 51, (
            f"BUG: Expected reloaded storage to have next_id=51, "
            f"but got {storage2.get_next_id()}. "
            f"This happens because the file contains stale next_id (issue #166)."
        )

        # Try adding a todo - it should get ID=51, not ID=2
        new_todo = storage2.add(Todo(title="New Todo"))
        assert new_todo.id == 51, (
            f"BUG: Expected new todo to get ID=51, but got {new_todo.id}"
        )


def test_saved_next_id_when_lower_ids():
    """Test that saved next_id is correct when todos have lower IDs than current _next_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage = Storage(str(storage_path))

        # Add some todos to raise _next_id
        storage.add(Todo(title="Todo 1"))
        storage.add(Todo(title="Todo 2"))
        storage.add(Todo(title="Todo 3"))
        assert storage.get_next_id() == 4

        # Save only the first todo (lower IDs)
        # The saved next_id should still be 2 (max ID 1 + 1)
        # NOT 4 (the stale _next_id)
        single_todo = [storage.get(1)]
        storage._save_with_todos(single_todo)

        import json
        with open(storage_path, 'r') as f:
            saved_data = json.load(f)
            assert saved_data["next_id"] == 2, (
                f"Expected saved next_id to be 2 (max ID 1 + 1), "
                f"but got {saved_data['next_id']}"
            )
