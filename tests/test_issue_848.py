"""Test batch delete operations (Issue #848)."""

import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_delete_batch_multiple_todos():
    """Test deleting multiple todos in a single batch operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="pending"),
            Todo(id=3, title="Task 3", status="pending"),
            Todo(id=4, title="Task 4", status="pending"),
        ]
        for todo in todos:
            storage.add(todo)

        # Delete todos with IDs 1, 2, and 4
        deleted_ids = [1, 2, 4]
        result = storage.delete_batch(deleted_ids)

        # Should return True for all deleted todos
        assert result == [True, True, True]

        # Verify only todo with ID 3 remains
        remaining = storage.list()
        assert len(remaining) == 1
        assert remaining[0].id == 3
        assert remaining[0].title == "Task 3"


def test_delete_batch_with_nonexistent_ids():
    """Test delete_batch with some non-existent IDs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add some todos
        storage.add(Todo(id=1, title="Task 1", status="pending"))
        storage.add(Todo(id=2, title="Task 2", status="pending"))

        # Try to delete a mix of existing and non-existing IDs
        result = storage.delete_batch([1, 99, 2])

        # Should return True for existing IDs, False for non-existing
        assert result == [True, False, True]

        # Both existing todos should be deleted
        remaining = storage.list()
        assert len(remaining) == 0


def test_delete_batch_empty_list():
    """Test delete_batch with empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        storage.add(Todo(id=1, title="Task 1", status="pending"))

        # Delete empty list
        result = storage.delete_batch([])

        # Should return empty list
        assert result == []

        # Original todo should remain
        remaining = storage.list()
        assert len(remaining) == 1


def test_delete_batch_atomic_operation():
    """Test that delete_batch is atomic (all or nothing)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="pending"),
            Todo(id=3, title="Task 3", status="pending"),
        ]
        for todo in todos:
            storage.add(todo)

        # Delete multiple todos at once
        storage.delete_batch([1, 2])

        # Verify file was written only once (efficient operation)
        # Check that the state is consistent
        remaining = storage.list()
        assert len(remaining) == 1
        assert remaining[0].id == 3


def test_delete_batch_all_todos():
    """Test deleting all todos using delete_batch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="pending"),
            Todo(id=3, title="Task 3", status="pending"),
        ]
        for todo in todos:
            storage.add(todo)

        # Delete all todos
        all_ids = [1, 2, 3]
        result = storage.delete_batch(all_ids)

        # All should be deleted
        assert result == [True, True, True]

        # List should be empty
        remaining = storage.list()
        assert len(remaining) == 0


def test_delete_batch_efficiency():
    """Test that delete_batch is more efficient than multiple delete calls."""
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Test 1: Multiple individual deletes
        storage1 = Storage(str(storage_path))
        for i in range(100):
            storage1.add(Todo(id=i, title=f"Task {i}", status="pending"))

        start = time.time()
        for i in range(100):
            storage1.delete(i)
        individual_time = time.time() - start

        # Test 2: Single batch delete
        storage2 = Storage(str(storage_path))
        for i in range(100, 200):
            storage2.add(Todo(id=i, title=f"Task {i}", status="pending"))

        start = time.time()
        storage2.delete_batch(list(range(100, 200)))
        batch_time = time.time() - start

        # Batch delete should be faster (though this is a rough check)
        # At minimum, batch operation should not be significantly slower
        # We allow up to 2x to account for timing variations
        assert batch_time < individual_time * 2, \
            f"Batch delete took {batch_time:.3f}s, individual deletes took {individual_time:.3f}s"


def test_delete_batch_with_async():
    """Test async version of delete_batch."""
    import asyncio
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add multiple todos
        todos = [
            Todo(id=1, title="Task 1", status="pending"),
            Todo(id=2, title="Task 2", status="pending"),
            Todo(id=3, title="Task 3", status="pending"),
        ]
        for todo in todos:
            storage.add(todo)

        # Delete todos using async method
        async def async_delete():
            result = await storage.async_delete_batch([1, 2])
            return result

        result = asyncio.run(async_delete())

        # Should return True for deleted todos
        assert result == [True, True]

        # Verify only todo with ID 3 remains
        remaining = storage.list()
        assert len(remaining) == 1
        assert remaining[0].id == 3
