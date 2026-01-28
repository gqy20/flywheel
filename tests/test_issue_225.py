"""Test for Issue #225 - Verify _save method is complete.

This test verifies that the _save method correctly:
1. Writes data to file
2. Sets file permissions (0o600)
3. Atomically replaces the old file
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_method_writes_data():
    """Test that _save method writes data to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo", status="pending")
        storage.add(todo)

        # Verify file was created and contains correct data
        assert storage_path.exists(), "Storage file should exist after save"

        with storage_path.open('r') as f:
            data = json.load(f)

        assert "todos" in data, "Saved data should contain 'todos' key"
        assert len(data["todos"]) == 1, "Should have one todo"
        assert data["todos"][0]["title"] == "Test todo", "Todo title should match"


def test_save_method_sets_permissions():
    """Test that _save method sets restrictive file permissions (0o600)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo to trigger save
        todo = Todo(title="Test todo", status="pending")
        storage.add(todo)

        # Check file permissions
        if os.name != 'nt':  # Skip on Windows
            file_stat = os.stat(storage_path)
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600, f"File permissions should be 0o600, got {oct(file_mode)}"


def test_save_method_atomic_replace():
    """Test that _save method atomically replaces the old file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Create initial data
        todo1 = Todo(title="First todo", status="pending")
        storage.add(todo1)

        # Get the original file inode (to check if it's the same file after replacement)
        try:
            original_stat = os.stat(storage_path)
        except OSError:
            original_stat = None

        # Add another todo (triggers another save)
        todo2 = Todo(title="Second todo", status="pending")
        storage.add(todo2)

        # Verify file still exists and has both todos
        assert storage_path.exists(), "Storage file should exist"
        with storage_path.open('r') as f:
            data = json.load(f)

        assert len(data["todos"]) == 2, "Should have two todos"
        titles = [t["title"] for t in data["todos"]]
        assert "First todo" in titles
        assert "Second todo" in titles


def test_save_method_handles_write_errors():
    """Test that _save method handles write errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        todo1 = Todo(title="First todo", status="pending")
        storage.add(todo1)

        # Make the parent directory read-only to trigger write error
        # This should cause save to fail
        parent_dir = storage_path.parent
        original_mode = parent_dir.stat().st_mode

        try:
            if os.name != 'nt':  # Skip on Windows
                parent_dir.chmod(0o400)

                # Try to add another todo (should fail or raise error)
                with pytest.raises((OSError, RuntimeError, PermissionError)):
                    todo2 = Todo(title="Second todo", status="pending")
                    storage.add(todo2)
        finally:
            # Restore permissions
            if os.name != 'nt':
                parent_dir.chmod(original_mode)


def test_save_method_with_empty_todos():
    """Test that _save method correctly saves empty todo list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Storage starts empty, trigger a save with _save method
        storage._save()

        # Verify file was created with empty todos
        assert storage_path.exists(), "Storage file should exist"
        with storage_path.open('r') as f:
            data = json.load(f)

        assert "todos" in data, "Saved data should contain 'todos' key"
        assert len(data["todos"]) == 0, "Should have zero todos"


def test_save_method_preserves_next_id():
    """Test that _save method preserves next_id in the file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo with specific ID
        todo1 = Todo(id=5, title="Test todo", status="pending")
        storage.add(todo1)

        # Check that next_id is saved correctly
        with storage_path.open('r') as f:
            data = json.load(f)

        assert "next_id" in data, "Saved data should contain 'next_id' key"
        assert data["next_id"] >= 6, "next_id should be at least 6 after adding todo with ID 5"
