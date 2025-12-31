"""Tests for storage.py - verifying _save and _save_with_todos methods.

This test suite verifies that the _save and _save_with_todos methods are
complete and functional (Issue #174).
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestSaveMethods:
    """Test suite for _save and _save_with_todos methods."""

    def test_save_method_creates_valid_file(self):
        """Test that _save creates a valid JSON file with todos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add some todos
            storage.add(Todo(title="Task 1"))
            storage.add(Todo(title="Task 2"))

            # Verify file was created and contains valid JSON
            assert storage_path.exists()

            with storage_path.open('r') as f:
                data = json.load(f)

            assert isinstance(data, dict)
            assert "todos" in data
            assert "next_id" in data
            assert len(data["todos"]) == 2
            assert data["next_id"] == 3

    def test_save_with_todos_method_updates_state(self):
        """Test that _save_with_todos updates internal state after write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add initial todos
            storage.add(Todo(title="Task 1"))
            assert storage.get_next_id() == 2

            # Use _save_with_todos with new list
            new_todos = [Todo(id=1, title="Updated Task 1"), Todo(id=10, title="Task with high ID")]
            storage._save_with_todos(new_todos)

            # Verify internal state was updated
            assert len(storage._todos) == 2
            assert storage._todos[0].title == "Updated Task 1"
            assert storage._todos[1].title == "Task with high ID"
            # next_id should be updated to 11 (max_id + 1)
            assert storage.get_next_id() == 11

    def test_save_atomic_operation(self):
        """Test that save operations are atomic (using temp file)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add a todo
            storage.add(Todo(title="Task 1"))

            # Verify no .tmp files remain (atomic write cleanup)
            tmp_files = list(storage_path.parent.glob("*.tmp"))
            assert len(tmp_files) == 0

            # Verify main file exists and is valid
            assert storage_path.exists()
            with storage_path.open('r') as f:
                data = json.load(f)
            assert len(data["todos"]) == 1

    def test_save_handles_write_errors(self):
        """Test that save handles write errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Make parent directory read-only to simulate write error
            # This should raise an error during save
            parent_dir = storage_path.parent
            original_mode = parent_dir.stat().st_mode

            try:
                # Make directory read-only
                parent_dir.chmod(0o444)

                # Try to add a todo (should fail during save)
                with pytest.raises(Exception):
                    storage.add(Todo(title="Should fail"))
            finally:
                # Restore permissions for cleanup
                parent_dir.chmod(original_mode)

    def test_save_with_empty_todos_list(self):
        """Test that _save_with_todos handles empty list correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add a todo first
            storage.add(Todo(title="Task 1"))

            # Save with empty list
            storage._save_with_todos([])

            # Verify both file and state are empty
            assert len(storage._todos) == 0
            assert storage.get_next_id() == 1

            with storage_path.open('r') as f:
                data = json.load(f)
            assert data["todos"] == []
            assert data["next_id"] == 1

    def test_save_preserves_metadata(self):
        """Test that save correctly preserves todos and next_id metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # Add todos with specific IDs
            storage.add(Todo(id=5, title="High ID task"))
            assert storage.get_next_id() == 6

            # Add another todo (should get ID 6)
            todo = storage.add(Todo(title="Next task"))
            assert todo.id == 6
            assert storage.get_next_id() == 7

            # Reload storage to verify persistence
            storage2 = Storage(str(storage_path))
            assert storage2.get_next_id() == 7

            todos = storage2.list()
            assert len(todos) == 2
            assert todos[0].id == 5
            assert todos[1].id == 6


class TestSaveMethodsCompleteness:
    """Verify the completeness of _save and _save_with_todos implementation (Issue #174)."""

    def test_save_method_has_complete_logic(self):
        """Verify _save method has complete implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # The method should:
            # 1. Capture data under lock
            # 2. Serialize to JSON
            # 3. Write to temp file
            # 4. fsync to disk
            # 5. Close fd
            # 6. Replace original file
            # 7. Handle errors with cleanup

            # Test the full flow
            storage.add(Todo(title="Test task"))
            assert storage_path.exists()

            # Verify JSON structure
            with storage_path.open('r') as f:
                data = json.load(f)
            assert "todos" in data
            assert "next_id" in data
            assert data["todos"][0]["title"] == "Test task"

    def test_save_with_todos_has_complete_logic(self):
        """Verify _save_with_todos method has complete implementation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            # The method should:
            # 1. Capture data under lock
            # 2. Calculate next_id
            # 3. Serialize to JSON
            # 4. Write to temp file
            # 5. fsync to disk
            # 6. Close fd
            # 7. Replace original file
            # 8. Update internal state AFTER successful write
            # 9. Handle errors with cleanup

            # Test the full flow
            new_todos = [
                Todo(id=1, title="Task 1"),
                Todo(id=2, title="Task 2"),
                Todo(id=10, title="Task 10")
            ]
            storage._save_with_todos(new_todos)

            # Verify internal state was updated AFTER write
            assert len(storage._todos) == 3
            assert storage._todos[0].title == "Task 1"
            assert storage._todos[2].title == "Task 10"

            # Verify next_id was recalculated correctly
            assert storage.get_next_id() == 11

            # Verify file was written correctly
            with storage_path.open('r') as f:
                data = json.load(f)
            assert len(data["todos"]) == 3
            assert data["next_id"] == 11

    def test_syntax_correctness(self):
        """Verify the code is syntactically correct (Issue #174)."""
        # This test passes if the module can be imported without SyntaxError
        # If the code was truncated as described in the issue, this would fail
        from flywheel.storage import Storage
        assert Storage is not None

        # Verify methods exist and are callable
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            assert hasattr(storage, '_save')
            assert callable(storage._save)
            assert hasattr(storage, '_save_with_todos')
            assert callable(storage._save_with_todos)

            # Verify methods can be called without error
            storage._save()
            storage._save_with_todos([Todo(title="Test")])
