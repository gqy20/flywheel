"""Tests for Issue #161 - State update consistency (VERIFICATION TEST).

This test verifies that issue #161 is a FALSE POSITIVE.
The _save_with_todos method DOES properly update the internal state
after successfully writing to disk (lines 256-268 in storage.py).

The code ensures:
1. Internal state (_todos) is only updated AFTER successful file write
2. If file write fails, internal state remains unchanged
3. Memory state always matches disk state
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestStateConsistency:
    """Test state consistency between memory and disk.

    These tests VERIFY that Issue #161 is a false positive.
    The code at lines 256-268 already updates self._todos after successful write.
    """

    def test_state_updated_only_after_successful_write(self):
        """Test that internal state is updated only after successful file write.

        This test VERIFIES that Issue #161 is a false positive.
        The code at line 254 (Path(temp_path).replace(self.path)) is followed by
        lines 258-262 which update self._todos within a lock, ensuring consistency.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add a todo
            todo1 = storage.add(Todo(title="Task 1"))
            assert storage.get(todo1.id) is not None

            # Verify file exists and contains the todo
            with storage_path.open('r') as f:
                data = json.load(f)
            assert len(data["todos"]) == 1
            assert data["todos"][0]["title"] == "Task 1"

    def test_state_unchanged_when_file_write_fails(self):
        """Test that internal state remains unchanged when file write fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add initial todo
            todo1 = storage.add(Todo(title="Task 1"))
            original_todos = storage.list()
            assert len(original_todos) == 1

            # Mock replace to fail (simulate disk full, permission error, etc.)
            with patch.object(Path, 'replace') as mock_replace:
                mock_replace.side_effect = OSError("No space left on device")

                # Attempt to add another todo - should fail
                with pytest.raises(OSError):
                    storage.add(Todo(title="Task 2"))

                # Verify internal state is UNCHANGED
                current_todos = storage.list()
                assert len(current_todos) == 1
                assert current_todos[0].title == "Task 1"

                # Verify file still has only the original todo
                with storage_path.open('r') as f:
                    data = json.load(f)
                assert len(data["todos"]) == 1
                assert data["todos"][0]["title"] == "Task 1"

    def test_state_consistency_after_update(self):
        """Test that memory state matches disk state after update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add a todo
            todo1 = storage.add(Todo(title="Task 1"))

            # Update the todo
            updated_todo = Todo(id=todo1.id, title="Updated Task 1", status="done")
            storage.update(updated_todo)

            # Verify memory state
            from_memory = storage.get(todo1.id)
            assert from_memory.title == "Updated Task 1"
            assert from_memory.status == "done"

            # Verify disk state matches memory
            with storage_path.open('r') as f:
                data = json.load(f)
            assert len(data["todos"]) == 1
            assert data["todos"][0]["title"] == "Updated Task 1"
            assert data["todos"][0]["status"] == "done"

    def test_state_consistency_after_delete(self):
        """Test that memory state matches disk state after delete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add two todos
            todo1 = storage.add(Todo(title="Task 1"))
            todo2 = storage.add(Todo(title="Task 2"))

            # Delete one todo
            storage.delete(todo1.id)

            # Verify memory state
            from_memory = storage.list()
            assert len(from_memory) == 1
            assert from_memory[0].id == todo2.id

            # Verify disk state matches memory
            with storage_path.open('r') as f:
                data = json.load(f)
            assert len(data["todos"]) == 1
            assert data["todos"][0]["title"] == "Task 2"

    def test_next_id_updated_after_successful_write(self):
        """Test that _next_id is updated correctly after successful operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add todos with specific IDs
            storage.add(Todo(id=5, title="Task 5"))
            assert storage.get_next_id() == 6  # Should be updated to max_id + 1

            storage.add(Todo(id=10, title="Task 10"))
            assert storage.get_next_id() == 11

            # Verify disk state has correct next_id
            with storage_path.open('r') as f:
                data = json.load(f)
            assert data["next_id"] == 11

    def test_write_failure_does_not_corrupt_next_id(self):
        """Test that _next_id is not corrupted when write fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add initial todo
            storage.add(Todo(title="Task 1"))
            original_next_id = storage.get_next_id()

            # Mock replace to fail
            with patch.object(Path, 'replace') as mock_replace:
                mock_replace.side_effect = OSError("Disk full")

                # Attempt to add another todo
                with pytest.raises(OSError):
                    storage.add(Todo(title="Task 2"))

                # Verify _next_id is UNCHANGED
                assert storage.get_next_id() == original_next_id
