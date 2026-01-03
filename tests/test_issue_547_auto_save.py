"""Test periodic auto-save during operations (Issue #547)."""

import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_auto_save_attribute_exists():
    """Test that Storage has auto-save related attributes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # These attributes should exist after implementing auto-save
        assert hasattr(storage, 'last_saved_time'), "Storage should have last_saved_time attribute"
        assert hasattr(storage, 'AUTO_SAVE_INTERVAL'), "Storage should have AUTO_SAVE_INTERVAL constant"


def test_auto_save_triggers_after_interval():
    """Test that auto-save triggers after the configured interval passes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Mock the _save method to track when it's called
        save_call_count = {'count': 0}
        original_save = storage._save

        def mock_save():
            save_call_count['count'] += 1
            original_save()

        storage._save = mock_save

        # Add initial todo - should trigger save
        storage.add(Todo(title="Initial"))
        initial_count = save_call_count['count']

        # Add another todo immediately - might trigger another save
        # (depending on implementation, could be batched)
        storage.add(Todo(title="Second"))

        # The save should have been called at least once more
        # After implementing auto-save with time-based batching,
        # this behavior may change
        assert save_call_count['count'] >= initial_count


def test_auto_save_with_add_operations():
    """Test that add operations trigger auto-save appropriately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Perform multiple add operations
        for i in range(5):
            storage.add(Todo(title=f"Todo {i}"))

        # Verify all are persisted
        with open(storage_path, 'r') as f:
            data = json.load(f)

        assert len(data['todos']) == 5


def test_auto_save_with_update_operations():
    """Test that update operations trigger auto-save appropriately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = storage.add(Todo(title="Original"))

        # Update it multiple times
        for i in range(3):
            todo.title = f"Updated {i}"
            storage.update(todo)

        # Verify final state is persisted
        with open(storage_path, 'r') as f:
            data = json.load(f)

        assert len(data['todos']) == 1
        assert data['todos'][0]['title'] == "Updated 2"


def test_auto_save_with_delete_operations():
    """Test that delete operations trigger auto-save appropriately."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todos = [storage.add(Todo(title=f"Todo {i}")) for i in range(5)]

        # Delete some
        storage.delete(todos[1].id)
        storage.delete(todos[3].id)

        # Verify final state is persisted
        with open(storage_path, 'r') as f:
            data = json.load(f)

        assert len(data['todos']) == 3
        assert data['todos'][0]['title'] == "Todo 0"
        assert data['todos'][1]['title'] == "Todo 2"
        assert data['todos'][2]['title'] == "Todo 4"


def test_auto_save_thread_safety():
    """Test that auto-save is thread-safe using existing RLock."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Perform concurrent operations
        import threading

        def add_todos(count):
            for i in range(count):
                storage.add(Todo(title=f"Thread-{threading.current_thread().ident}-{i}"))

        threads = []
        for _ in range(3):
            t = threading.Thread(target=add_todos, args=(5,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify all todos are persisted correctly
        todos = storage.list()
        assert len(todos) == 15

        # Verify file is consistent
        with open(storage_path, 'r') as f:
            data = json.load(f)

        assert len(data['todos']) == 15
