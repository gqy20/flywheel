"""Tests for storage statistics/metrics (Issue #868)."""

import tempfile
from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_stats_returns_all_required_fields():
    """Test that stats() returns all required fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Get stats
        stats = storage.stats()

        # Verify all required fields are present
        assert "total" in stats
        assert "pending" in stats
        assert "completed" in stats
        assert "last_modified" in stats


def test_stats_empty_storage():
    """Test stats() with empty storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        stats = storage.stats()

        # Empty storage should have zero counts
        assert stats["total"] == 0
        assert stats["pending"] == 0
        assert stats["completed"] == 0
        # last_modified should be None or a timestamp
        assert stats["last_modified"] is None or isinstance(stats["last_modified"], (int, float, str))


def test_stats_with_todos():
    """Test stats() with various todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add some todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.TODO))
        storage.add(Todo(id=3, title="Todo 3", status=Status.IN_PROGRESS))
        storage.add(Todo(id=4, title="Todo 4", status=Status.DONE))

        stats = storage.stats()

        # Verify counts
        assert stats["total"] == 4
        assert stats["pending"] == 3  # TODO and IN_PROGRESS count as pending
        assert stats["completed"] == 1  # Only DONE counts as completed


def test_stats_all_completed():
    """Test stats() when all todos are completed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add completed todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.DONE))
        storage.add(Todo(id=2, title="Todo 2", status=Status.DONE))

        stats = storage.stats()

        assert stats["total"] == 2
        assert stats["pending"] == 0
        assert stats["completed"] == 2


def test_stats_updates_after_add():
    """Test that stats() updates after adding todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Initial stats
        stats = storage.stats()
        assert stats["total"] == 0

        # Add a todo
        storage.add(Todo(id=1, title="New todo", status=Status.TODO))

        # Updated stats
        stats = storage.stats()
        assert stats["total"] == 1
        assert stats["pending"] == 1


def test_stats_updates_after_delete():
    """Test that stats() updates after deleting todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.DONE))

        # Initial stats
        stats = storage.stats()
        assert stats["total"] == 2

        # Delete a todo
        storage.delete(1)

        # Updated stats
        stats = storage.stats()
        assert stats["total"] == 1
        assert stats["pending"] == 0


def test_stats_updates_after_update():
    """Test that stats() updates after updating todo status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a pending todo
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))

        # Initial stats
        stats = storage.stats()
        assert stats["pending"] == 1
        assert stats["completed"] == 0

        # Update to completed
        todo = storage.get(1)
        todo.status = Status.DONE
        storage.update(todo)

        # Updated stats
        stats = storage.stats()
        assert stats["pending"] == 0
        assert stats["completed"] == 1


def test_stats_last_modified_timestamp():
    """Test that last_modified timestamp is included in stats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))

        stats = storage.stats()

        # last_modified should be present and be a timestamp (number or string)
        assert stats["last_modified"] is not None
        assert isinstance(stats["last_modified"], (int, float, str))
