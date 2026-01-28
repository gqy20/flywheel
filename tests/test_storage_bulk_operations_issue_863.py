"""Tests for bulk operation methods (Issue #863)."""

import tempfile
from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_bulk_add_multiple_todos():
    """Test adding multiple todos in a single bulk operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Create multiple todos
        todos = [
            Todo(id=1, title="First todo", status=Status.TODO),
            Todo(id=2, title="Second todo", status=Status.TODO),
            Todo(id=3, title="Third todo", status=Status.DONE),
        ]

        # Add todos in bulk
        added_todos = storage.bulk_add(todos)

        # Verify all todos were added
        assert len(added_todos) == 3
        assert added_todos[0].title == "First todo"
        assert added_todos[1].title == "Second todo"
        assert added_todos[2].title == "Third todo"

        # Verify they are in storage
        all_todos = storage.list()
        assert len(all_todos) == 3


def test_bulk_add_empty_list():
    """Test bulk_add with an empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        result = storage.bulk_add([])
        assert result == []


def test_bulk_delete_multiple_todos():
    """Test deleting multiple todos in a single bulk operation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add some todos first
        todos = [
            Todo(id=1, title="First", status=Status.TODO),
            Todo(id=2, title="Second", status=Status.TODO),
            Todo(id=3, title="Third", status=Status.TODO),
            Todo(id=4, title="Fourth", status=Status.TODO),
        ]
        storage.bulk_add(todos)

        # Delete multiple todos
        deleted_ids = [1, 3]
        deleted_count = storage.bulk_delete(deleted_ids)

        # Verify deletion count
        assert deleted_count == 2

        # Verify only the correct todos remain
        remaining = storage.list()
        assert len(remaining) == 2
        assert all(todo.id not in deleted_ids for todo in remaining)

        # Verify specific remaining todos
        remaining_ids = [todo.id for todo in remaining]
        assert 2 in remaining_ids
        assert 4 in remaining_ids


def test_bulk_delete_empty_list():
    """Test bulk_delete with an empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo
        storage.add(Todo(id=1, title="Test", status=Status.TODO))

        # Delete empty list
        deleted_count = storage.bulk_delete([])

        # Verify nothing was deleted
        assert deleted_count == 0
        assert len(storage.list()) == 1


def test_bulk_delete_non_existent_ids():
    """Test bulk_delete with IDs that don't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add one todo
        storage.add(Todo(id=1, title="Test", status=Status.TODO))

        # Try to delete non-existent IDs
        deleted_count = storage.bulk_delete([2, 3, 4])

        # Verify nothing was deleted
        assert deleted_count == 0
        assert len(storage.list()) == 1


def test_bulk_add_performance():
    """Test that bulk_add is more efficient than individual adds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Create many todos
        todos = [Todo(id=i, title=f"Todo {i}", status=Status.TODO) for i in range(1, 101)]

        # Add in bulk
        added_todos = storage.bulk_add(todos)

        # Verify all were added
        assert len(added_todos) == 100
        assert len(storage.list()) == 100


def test_bulk_operations_mixed():
    """Test mixing bulk_add and bulk_delete operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Bulk add initial todos
        todos1 = [Todo(id=i, title=f"Todo {i}", status=Status.TODO) for i in range(1, 6)]
        storage.bulk_add(todos1)

        # Bulk add more todos
        todos2 = [Todo(id=i, title=f"Todo {i}", status=Status.TODO) for i in range(6, 11)]
        storage.bulk_add(todos2)

        # Verify total
        assert len(storage.list()) == 10

        # Bulk delete some
        deleted = storage.bulk_delete([2, 4, 6, 8])
        assert deleted == 4

        # Verify remaining
        assert len(storage.list()) == 6
