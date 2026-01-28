"""Tests for storage len() and iteration support (Issue #873)."""

import tempfile
from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_len_empty_storage():
    """Test that len() returns 0 for empty storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Should raise TypeError if __len__ is not implemented
        count = len(storage)

        assert count == 0


def test_len_with_todos():
    """Test that len() returns the correct count of todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add some todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.TODO))
        storage.add(Todo(id=3, title="Todo 3", status=Status.DONE))

        count = len(storage)

        assert count == 3


def test_len_updates_after_add():
    """Test that len() updates after adding todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        assert len(storage) == 0

        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))

        assert len(storage) == 1


def test_len_updates_after_delete():
    """Test that len() updates after deleting todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.DONE))

        assert len(storage) == 2

        storage.delete(1)

        assert len(storage) == 1


def test_iteration_empty_storage():
    """Test that iteration works on empty storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        todos = list(storage)

        assert todos == []


def test_iteration_with_todos():
    """Test that iteration yields all todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add some todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.TODO))
        storage.add(Todo(id=3, title="Todo 3", status=Status.DONE))

        todos = list(storage)

        assert len(todos) == 3
        assert all(isinstance(todo, Todo) for todo in todos)


def test_iteration_in_for_loop():
    """Test that storage can be used in a for loop."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        # Add some todos
        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.DONE))

        titles = []
        for todo in storage:
            titles.append(todo.title)

        assert set(titles) == {"Todo 1", "Todo 2"}


def test_combined_len_and_iteration():
    """Test that len() and iteration work together correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        storage.add(Todo(id=1, title="Todo 1", status=Status.TODO))
        storage.add(Todo(id=2, title="Todo 2", status=Status.TODO))
        storage.add(Todo(id=3, title="Todo 3", status=Status.DONE))

        # len() should match the count from iteration
        count_by_len = len(storage)
        count_by_iter = len(list(storage))

        assert count_by_len == count_by_iter == 3
