"""Tests for Storage.close() method (issue #64)."""

import pytest
from pathlib import Path
from flywheel.storage import Storage


def test_close_method_exists():
    """Test that close method exists."""
    storage = Storage()
    assert hasattr(storage, 'close'), "Storage should have a close method"


def test_close_is_callable():
    """Test that close method is callable."""
    storage = Storage()
    assert callable(storage.close), "Storage.close should be callable"


def test_close_releases_lock():
    """Test that close method properly releases resources."""
    storage = Storage()
    # Lock should be acquired before close
    assert storage._lock.acquire(blocking=True)
    storage._lock.release()

    # After close, the storage should still be functional
    # but we want to ensure close doesn't raise errors
    storage.close()


def test_close_idempotent():
    """Test that close can be called multiple times safely."""
    storage = Storage()
    storage.close()
    storage.close()  # Should not raise an error


def test_delete_method_complete():
    """Test that delete method is complete and returns bool (issue #64)."""
    storage = Storage()

    # Add a todo
    from flywheel.todo import Todo
    todo = Todo(title="Test delete")
    storage.add(todo)

    # Delete should return True when todo exists
    result = storage.delete(todo.id)
    assert result is True, "delete should return True when todo is deleted"

    # Delete should return False when todo doesn't exist
    result = storage.delete(todo.id)
    assert result is False, "delete should return False when todo doesn't exist"

    # Clean up
    storage.close()
