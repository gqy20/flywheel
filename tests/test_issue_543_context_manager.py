"""Test context manager support for storage locks (Issue #543)."""

import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_storage_context_manager_basic():
    """Test that Storage supports context manager protocol."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Test that Storage can be used as a context manager
        with Storage(str(storage_path)) as storage:
            assert storage is not None
            # Verify we can perform operations inside the context
            todo = Todo(title="Test Task", status="pending")
            storage.add(todo)

        # Verify data was saved correctly after exiting context
        storage2 = Storage(str(storage_path))
        todos = storage2.list()
        assert len(todos) == 1
        assert todos[0].title == "Test Task"


def test_storage_context_manager_returns_self():
    """Test that __enter__ returns self."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        storage_obj = Storage(str(storage_path))
        with storage_obj as storage:
            # __enter__ should return self
            assert storage is storage_obj


def test_storage_context_manager_with_exception():
    """Test that context manager handles exceptions properly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # Create initial data
        storage1 = Storage(str(storage_path))
        todo1 = Todo(title="Original Task", status="pending")
        storage1.add(todo1)

        # Test exception handling in context manager
        with pytest.raises(ValueError):
            with Storage(str(storage_path)) as storage:
                # Add a task
                todo2 = Todo(title="Temporary Task", status="pending")
                storage.add(todo2)
                # Raise an exception
                raise ValueError("Test exception")

        # Verify storage is still functional after exception
        storage3 = Storage(str(storage_path))
        todos = storage3.list()
        # The context manager should handle cleanup properly
        # After exception, resources should be released
        assert len(todos) >= 1


def test_storage_has_context_manager_methods():
    """Test that Storage class has __enter__ and __exit__ methods."""
    assert hasattr(Storage, '__enter__')
    assert hasattr(Storage, '__exit__')
    assert callable(Storage.__enter__)
    assert callable(Storage.__exit__)
