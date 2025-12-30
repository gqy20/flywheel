"""Tests for issue #129: Verify _save_with_todos Phase 3 completeness.

This test verifies that the _save_with_todos method has complete Phase 3 logic,
which updates self._todos after successful file write to ensure memory state
matches disk state.

The issue reports that code was cut off at "Phase 3: Update inter", but the
actual implementation is complete. This test verifies the correct behavior.
"""

import os
import tempfile

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_updates_internal_state_after_write():
    """Test that _save_with_todos updates self._todos after successful write.

    This is the Phase 3 logic that ensures consistency between memory and disk.
    After calling _save_with_todos, the internal state should reflect the new
    todos list.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))
        todo2 = storage.add(Todo(title="Task 2"))

        # Create a new todos list with an updated todo
        updated_todos = [
            Todo(id=todo1.id, title="Task 1 updated", status="done"),
            Todo(id=todo2.id, title="Task 2", status="todo"),
        ]

        # Call _save_with_todos directly
        storage._save_with_todos(updated_todos)

        # Verify internal state was updated (Phase 3 logic)
        assert storage._todos == updated_todos, (
            "self._todos should be updated after successful write"
        )

        # Verify the changes persisted to disk
        storage2 = Storage(storage_path)
        loaded_todos = storage2.list()
        assert len(loaded_todos) == 2
        assert loaded_todos[0].title == "Task 1 updated"
        assert loaded_todos[0].status == "done"
        assert loaded_todos[1].title == "Task 2"


def test_save_with_todos_phase3_lock_protection():
    """Test that Phase 3 update is protected by lock.

    The Phase 3 update should occur within a lock to prevent race conditions.
    This test verifies the behavior by checking thread safety.
    """
    import threading

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        storage.add(Todo(title="Task 1"))

        errors = []

        def modify_todos():
            try:
                for i in range(10):
                    new_todos = [Todo(id=1, title=f"Task {i}", status="todo")]
                    storage._save_with_todos(new_todos)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = [threading.Thread(target=modify_todos) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not have any errors
        assert not errors, f"Thread safety errors: {errors}"

        # Verify final state is consistent
        final_todos = storage.list()
        assert len(final_todos) == 1
        # The title should be one of the set values
        assert final_todos[0].title.startswith("Task ")


def test_save_with_todos_phase3_only_updates_on_success():
    """Test that Phase 3 update only happens after successful write.

    If the write fails, self._todos should NOT be updated.
    """
    from unittest.mock import patch
    import pathlib

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")
        storage = Storage(storage_path)

        # Add initial todos
        todo1 = storage.add(Todo(title="Task 1"))

        original_todos = storage._todos.copy()

        # Create new todos list
        new_todos = [Todo(id=todo1.id, title="Should not save", status="done")]

        # Mock Path.replace to fail
        def mock_replace(self, target):
            raise OSError("Simulated write failure")

        # Attempt to save with mocked failure
        with patch.object(pathlib.Path, 'replace', mock_replace):
            try:
                storage._save_with_todos(new_todos)
                assert False, "Should have raised OSError"
            except OSError:
                pass

        # Verify internal state was NOT updated (Phase 3 should not execute)
        assert storage._todos == original_todos, (
            "self._todos should not be updated if write fails"
        )
