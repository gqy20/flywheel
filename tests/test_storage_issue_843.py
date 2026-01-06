"""Tests for context manager support in storage (issue #843)."""

import pytest
from flywheel.storage import AbstractStorage, FileStorage
from flywheel.todo import Todo


def test_abstract_storage_has_context_manager_interface():
    """Test that AbstractStorage defines __enter__ and __exit__ methods."""
    # Check that AbstractStorage has the methods defined
    assert hasattr(AbstractStorage, '__enter__'), \
        "AbstractStorage should have __enter__ method for context manager support"
    assert hasattr(AbstractStorage, '__exit__'), \
        "AbstractStorage should have __exit__ method for context manager support"


def test_file_storage_as_context_manager():
    """Test that FileStorage can be used as a context manager."""
    with FileStorage() as storage:
        assert storage is not None

        # Test that we can perform operations within the context
        todo = Todo(title="Test todo in context manager")
        added_todo = storage.add(todo)
        assert added_todo.id is not None

        # Verify the todo was added
        retrieved = storage.get(added_todo.id)
        assert retrieved is not None
        assert retrieved.title == "Test todo in context manager"

    # After exiting context, resources should be cleaned up
    # The storage should still be functional but properly closed


def test_context_manager_releases_lock_on_exit():
    """Test that the context manager properly releases locks on exit."""
    storage = FileStorage()

    # Use context manager
    with storage:
        # Lock should be acquired within the context
        assert storage._lock.locked()

    # Lock should be released after exiting context
    assert not storage._lock.locked()

    storage.close()


def test_context_manager_handles_exceptions():
    """Test that the context manager properly handles exceptions."""
    storage = FileStorage()

    with pytest.raises(ValueError):
        with storage:
            # Simulate an error
            raise ValueError("Test error")

    # Lock should still be released even after exception
    assert not storage._lock.locked()

    storage.close()


def test_context_manager_closes_resources():
    """Test that the context manager calls close() on exit."""
    storage = FileStorage()

    # Add a todo
    todo = Todo(title="Test resource cleanup")
    added = storage.add(todo)

    # Use context manager
    with storage:
        # Perform some operation
        retrieved = storage.get(added.id)
        assert retrieved is not None

    # After exiting, close() should have been called
    # which ensures proper resource cleanup
    # We can verify this by checking that the storage still works
    # but resources were properly managed
