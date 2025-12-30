"""Tests for Issue #156 - State update consistency (VERIFICATION TEST).

This test verifies that issue #156 is a FALSE POSITIVE.
The _save_with_todos method DOES properly update the internal state
after successfully writing to disk (lines 256-262 in storage.py).
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_updates_internal_state():
    """Test that _save_with_todos updates self._todos after successful write.

    This test VERIFIES that Issue #156 is a false positive.
    The code at lines 256-262 already updates self._todos after successful write:

        with self._lock:
            self._todos = copy.deepcopy(todos)

    The AI scanner that generated Issue #156 failed to detect this existing fix.
    """
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    storage_path = Path(temp_dir) / "todos.json"

    try:
        # Initialize storage and add a todo
        storage = Storage(str(storage_path))
        todo1 = storage.add(Todo(title="Task 1"))

        # Verify internal state matches file
        assert storage.get(todo1.id) is not None
        assert len(storage.list()) == 1

        # Call _save_with_todos directly with a new list of todos
        new_todos = [
            Todo(id=1, title="Task 1 Modified", status="completed"),
            Todo(id=2, title="Task 2", status="pending")
        ]

        # This should update both the file and the internal state
        storage._save_with_todos(new_todos)

        # Verify internal state was updated (this is the key test for issue #156)
        assert len(storage.list()) == 2, "Internal state should have 2 todos"
        assert storage.get(1).title == "Task 1 Modified", "Todo 1 should be modified"
        assert storage.get(1).status == "completed", "Todo 1 should be completed"
        assert storage.get(2).title == "Task 2", "Todo 2 should exist"
        assert storage.get(2).status == "pending", "Todo 2 should be pending"

        # Verify file also contains the new data
        storage2 = Storage(str(storage_path))
        assert len(storage2.list()) == 2, "File should have 2 todos"
        assert storage2.get(1).title == "Task 1 Modified", "File todo 1 should be modified"
        assert storage2.get(2).title == "Task 2", "File todo 2 should exist"

    finally:
        # Clean up
        shutil.rmtree(temp_dir)


def test_save_with_todos_preserves_state_on_write_failure():
    """Test that _save_with_todos preserves internal state if write fails.

    This verifies that the implementation correctly maintains consistency
    by NOT updating internal state when the file write fails.
    """
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    storage_path = Path(temp_dir) / "todos.json"

    try:
        # Initialize storage and add todos
        storage = Storage(str(storage_path))
        todo1 = storage.add(Todo(title="Original Task 1"))
        todo2 = storage.add(Todo(title="Original Task 2"))

        # Make the directory read-only to simulate write failure
        os.chmod(temp_dir, 0o444)

        # Try to save with new todos (should fail)
        new_todos = [
            Todo(id=1, title="Modified Task 1", status="completed")
        ]

        # This should fail because directory is read-only
        with pytest.raises(Exception):
            storage._save_with_todos(new_todos)

        # Verify internal state was NOT changed
        assert len(storage.list()) == 2, "Internal state should still have 2 todos"
        assert storage.get(1).title == "Original Task 1", "Todo 1 should remain unchanged"
        assert storage.get(2).title == "Original Task 2", "Todo 2 should still exist"

    finally:
        # Clean up (restore permissions first)
        os.chmod(temp_dir, 0o755)
        shutil.rmtree(temp_dir)


import os  # Import os for chmod in the test above
