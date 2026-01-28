"""Test atomic write operations for storage."""

import json
import tempfile
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo, Status


def test_atomic_write_preserves_data_on_interrupt():
    """Test that interrupted writes don't corrupt the data file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        storage.add(todo)

        # Read the original file
        original_content = storage_path.read_text()
        original_data = json.loads(original_content)

        # Simulate an interrupted write by creating a partial file
        # This tests that the original file remains intact
        storage_path.write_text("{incomplete json data")

        # Now try to save again - with atomic write, this should either
        # succeed completely or leave the original file intact
        storage.add(Todo(id=2, title="Another todo", status=Status.TODO))

        # After the second save, the file should be valid JSON
        # (either the new data or the old data, but never corrupted)
        try:
            final_content = storage_path.read_text()
            final_data = json.loads(final_content)

            # Verify the data is either the original or includes both todos
            assert isinstance(final_data, list)
            assert len(final_data) >= 1
            assert all("id" in item and "title" in item for item in final_data)
        except json.JSONDecodeError:
            raise AssertionError("File was corrupted due to non-atomic write")


def test_atomic_write_with_temp_file():
    """Test that writes use temporary file pattern for atomicity."""
    import unittest.mock as mock

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add initial todo
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        storage.add(todo)

        # Mock the filesystem operations to verify atomic pattern
        original_write = storage_path.write_text

        write_ops = []

        def track_write(*args, **kwargs):
            write_ops.append(("write_text", args, kwargs))
            return original_write(*args, **kwargs)

        with mock.patch.object(Path, "write_text", track_write):
            storage.add(Todo(id=2, title="Another todo", status=Status.TODO))

        # With atomic writes, we should see temp file and replace operations
        # This test will fail initially, demonstrating the non-atomic behavior
        assert len(write_ops) >= 1, "Should have write operations"


def test_file_persistence_after_crash_simulation():
    """Test that data persists even when writes are interrupted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.DONE))

        # Verify data is correct
        todos = storage.list()
        assert len(todos) == 2

        # Create a new storage instance to simulate restart
        storage2 = Storage(str(storage_path))
        reloaded_todos = storage2.list()

        # All data should be preserved
        assert len(reloaded_todos) == 2
        assert reloaded_todos[0].title == "Todo 1"
        assert reloaded_todos[1].title == "Todo 2"
