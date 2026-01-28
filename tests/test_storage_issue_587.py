"""Tests for context manager support (issue #587)."""

import pytest
from pathlib import Path
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_context_manager_methods_exist():
    """Test that FileStorage has __enter__ and __exit__ methods."""
    storage = Storage()
    assert hasattr(storage, '__enter__'), "Storage should have __enter__ method"
    assert hasattr(storage, '__exit__'), "Storage should have __exit__ method"


def test_context_manager_basic_usage():
    """Test that Storage can be used as a context manager."""
    with Storage() as storage:
        assert storage is not None
        # Storage should be functional within context
        todo = Todo(title="Test todo")
        storage.add(todo)
        assert len(storage.all()) == 1


def test_context_manager_returns_self():
    """Test that __enter__ returns self."""
    storage = Storage()
    with storage as ctx:
        assert ctx is storage, "__enter__ should return self"


def test_context_manager_cleanup_on_normal_exit():
    """Test that cleanup is called when exiting context normally."""
    storage = Storage()

    # Add a todo to make data dirty
    todo = Todo(title="Test todo")
    storage.add(todo)

    # Track if cleanup was called
    original_cleanup = storage._cleanup
    cleanup_called = []

    def tracked_cleanup():
        cleanup_called.append(True)
        original_cleanup()

    storage._cleanup = tracked_cleanup

    # Exit context
    with storage:
        pass

    assert len(cleanup_called) > 0, "_cleanup should be called on context exit"


def test_context_manager_cleanup_on_exception():
    """Test that cleanup is called even when exception occurs."""
    storage = Storage()

    # Add a todo to make data dirty
    todo = Todo(title="Test todo")
    storage.add(todo)

    # Track if cleanup was called
    original_cleanup = storage._cleanup
    cleanup_called = []

    def tracked_cleanup():
        cleanup_called.append(True)
        original_cleanup()

    storage._cleanup = tracked_cleanup

    # Exit context with exception
    with pytest.raises(ValueError):
        with storage:
            raise ValueError("Test exception")

    assert len(cleanup_called) > 0, "_cleanup should be called even on exception"


def test_context_manager_exception_propagation():
    """Test that exceptions are properly propagated."""
    with pytest.raises(ValueError, match="Test exception"):
        with Storage():
            raise ValueError("Test exception")


def test_context_manager_with_suppressed_exception():
    """Test that __exit__ can suppress exception if needed."""
    storage = Storage()

    # This test verifies that the exception handling works correctly
    # By default, __exit__ should not suppress exceptions
    exception_raised = False
    try:
        with storage:
            raise ValueError("Test")
    except ValueError:
        exception_raised = True

    assert exception_raised, "Exception should be propagated by default"
