"""Test issue #19: 原子写入失败时可能导致数据丢失."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_atomic_write_failure_consistency():
    """Test that memory state remains consistent when atomic write fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        todo1 = Todo(id=1, title="Initial todo", status="pending")
        storage.add(todo1)

        # Verify initial state
        assert len(storage.list()) == 1
        assert storage.get(1).title == "Initial todo"

        # Mock Path.replace to simulate write failure (e.g., permission denied)
        with patch.object(Path, 'replace', side_effect=PermissionError("Simulated permission denied")):
            # Attempt to add a second todo - this should fail
            todo2 = Todo(id=2, title="This should fail", status="pending")

            with pytest.raises(PermissionError):
                storage.add(todo2)

        # After the failure, the in-memory state should be consistent
        # Either:
        # 1. The new todo was not added (preferred behavior)
        # 2. Or the storage is marked as corrupted and operations are blocked
        assert len(storage.list()) == 1, f"Expected 1 todo, but got {len(storage.list())}"
        assert storage.get(1).title == "Initial todo"
        assert storage.get(2) is None, "New todo should not be in memory after failed write"


def test_atomic_write_failure_does_not_modify_disk():
    """Test that disk file remains unchanged when atomic write fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo and save
        todo1 = Todo(id=1, title="Initial todo", status="pending")
        storage.add(todo1)

        # Read the file content
        original_content = storage_path.read_text()
        original_data = json.loads(original_content)
        assert len(original_data) == 1

        # Mock Path.replace to simulate write failure
        with patch.object(Path, 'replace', side_effect=PermissionError("Simulated permission denied")):
            # Attempt to add a second todo
            todo2 = Todo(id=2, title="This should fail", status="pending")

            with pytest.raises(PermissionError):
                storage.add(todo2)

        # File on disk should be unchanged
        current_content = storage_path.read_text()
        current_data = json.loads(current_content)

        assert current_data == original_data, "File on disk should not be modified"
        assert len(current_data) == 1, "File should still contain only 1 todo"


def test_atomic_write_failure_with_subsequent_operations():
    """Test that subsequent operations work correctly after a failed write."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        todo1 = Todo(id=1, title="Initial todo", status="pending")
        storage.add(todo1)

        # Mock Path.replace to simulate write failure
        with patch.object(Path, 'replace', side_effect=PermissionError("Simulated permission denied")):
            # Attempt to add a second todo
            todo2 = Todo(id=2, title="This should fail", status="pending")

            with pytest.raises(PermissionError):
                storage.add(todo2)

        # Now try a successful operation
        todo3 = Todo(id=3, title="Third todo", status="pending")
        storage.add(todo3)

        # Should have 2 todos: the first one and the third one
        todos = storage.list()
        assert len(todos) == 2
        assert any(t.title == "Initial todo" for t in todos)
        assert any(t.title == "Third todo" for t in todos)
        assert not any(t.title == "This should fail" for t in todos)
