"""Tests for per-operation dry_run mode (Issue #1503)."""

import tempfile
from pathlib import Path

from flywheel.storage import FileStorage
from flywheel.todo import Status, Todo


def test_add_method_dry_run_parameter():
    """Test that add method accepts dry_run parameter (Issue #1503)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # Add with dry_run=True
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        result = storage.add(todo, dry_run=True)

        # The result should be returned (simulating success)
        assert result is not None
        assert result.id == 1

        # But the file should not be modified
        todos = storage.list()
        assert len(todos) == 0, "Todo should not be added in dry_run mode"


def test_update_method_dry_run_parameter():
    """Test that update method accepts dry_run parameter (Issue #1503)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # First add a real todo
        original = Todo(id=1, title="Original", status=Status.TODO)
        storage.add(original)

        # Update with dry_run=True
        updated = Todo(id=1, title="Updated", status=Status.DONE)
        result = storage.update(updated, dry_run=True)

        # The result should be returned (simulating success)
        assert result is not None

        # But the todo should not be modified
        todo = storage.get(1)
        assert todo.title == "Original", "Todo should not be updated in dry_run mode"
        assert todo.status == Status.TODO


def test_delete_method_dry_run_parameter():
    """Test that delete method accepts dry_run parameter (Issue #1503)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # First add a real todo
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        storage.add(todo)

        # Delete with dry_run=True
        result = storage.delete(1, dry_run=True)

        # The result should be True (simulating success)
        assert result is True

        # But the todo should still exist
        assert storage.get(1) is not None, "Todo should not be deleted in dry_run mode"
        assert len(storage.list()) == 1


def test_dry_run_false_performs_actual_operation():
    """Test that dry_run=False performs the actual operation (Issue #1503)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(f"{tmpdir}/test.json")
        storage = FileStorage(path=str(test_file))

        # Add with dry_run=False (explicit)
        todo = Todo(id=1, title="Test todo", status=Status.TODO)
        result = storage.add(todo, dry_run=False)

        assert result is not None
        assert result.id == 1

        # The todo should actually be added
        todos = storage.list()
        assert len(todos) == 1
        assert todos[0].title == "Test todo"
