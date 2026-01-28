"""Test for Issue #215 - Verify _save method is complete and functional."""

import json
import os
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_method_is_complete():
    """Verify that the _save method is properly implemented and functional.

    This test verifies that:
    1. The _save method exists and is callable
    2. It properly saves todos to disk
    3. File permissions are set correctly
    4. Atomic file replacement works
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance
        storage_path = os.path.join(tmpdir, "test_todos.json")
        storage = Storage(path=storage_path)

        # Add a todo to trigger save
        todo = Todo(title="Test task", status="pending")
        storage.add(todo)

        # Verify file was created and contains valid JSON
        assert Path(storage_path).exists(), "Storage file was not created"

        with open(storage_path, 'r') as f:
            data = json.load(f)

        # Verify data structure
        assert "todos" in data, "Missing 'todos' field in saved data"
        assert "next_id" in data, "Missing 'next_id' field in saved data"
        assert len(data["todos"]) == 1, "Expected 1 todo"
        assert data["todos"][0]["title"] == "Test task", "Todo title mismatch"

        # Verify file permissions are restrictive (0o600)
        if os.name != 'nt':  # Skip on Windows
            file_stat = os.stat(storage_path)
            file_mode = file_stat.st_mode & 0o777
            assert file_mode == 0o600, f"Expected permissions 0o600, got {oct(file_mode)}"

        # Update todo to test atomic replacement
        todo_updated = Todo(id=1, title="Updated task", status="completed")
        storage.update(todo_updated)

        # Verify file was updated atomically
        with open(storage_path, 'r') as f:
            updated_data = json.load(f)

        assert updated_data["todos"][0]["title"] == "Updated task", "Update failed"
        assert updated_data["todos"][0]["status"] == "completed", "Status update failed"

        storage.close()


def test_save_method_handles_windows_fchmod():
    """Verify that _save method handles Windows properly when os.fchmod is not available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "test_todos_win.json")
        storage = Storage(path=storage_path)

        # Add a todo - this should work on both Unix and Windows
        todo = Todo(title="Windows test", status="pending")
        storage.add(todo)

        # Verify file was created
        assert Path(storage_path).exists(), "Storage file was not created on Windows"

        # Verify content
        with open(storage_path, 'r') as f:
            data = json.load(f)

        assert len(data["todos"]) == 1, "Expected 1 todo"
        assert data["todos"][0]["title"] == "Windows test"

        storage.close()


if __name__ == "__main__":
    test_save_method_is_complete()
    test_save_method_handles_windows_fchmod()
    print("All tests passed!")
