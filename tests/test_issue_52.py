"""Test for issue #52 - update method return values."""

import tempfile
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo, Status


def test_update_returns_todo_on_success():
    """Test that update() returns the updated Todo when successful."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add a todo
        todo = Todo(id=1, title="Original", status=Status.TODO)
        storage.add(todo)

        # Update the todo
        updated_todo = Todo(id=1, title="Updated", status=Status.DONE)
        result = storage.update(updated_todo)

        # Assert that update returns the updated todo
        assert result is not None, "update() should return the updated Todo, not None"
        assert result.id == 1
        assert result.title == "Updated"
        assert result.status == Status.DONE


def test_update_returns_none_when_not_found():
    """Test that update() returns None when todo ID is not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Try to update a non-existent todo
        non_existent = Todo(id=999, title="Ghost", status=Status.TODO)
        result = storage.update(non_existent)

        # Assert that update returns None
        assert result is None, "update() should return None when todo is not found"


def test_update_returns_actual_todo_not_none():
    """Test that update() doesn't implicitly return None (issue #52)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add multiple todos
        todo1 = Todo(id=1, title="Task 1", status=Status.TODO)
        todo2 = Todo(id=2, title="Task 2", status=Status.TODO)
        storage.add(todo1)
        storage.add(todo2)

        # Update todo2
        todo2.title = "Updated Task 2"
        result = storage.update(todo2)

        # Verify return value is not None
        assert result is not None, (
            "update() should return the updated Todo object, not None. "
            "Issue #52: Implicit None return causing data loss."
        )
        assert result.id == 2
        assert result.title == "Updated Task 2"
