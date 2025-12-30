"""Tests for Issue #79 - get method implementation."""

import pytest
from flywheel.storage import Storage
from flywheel.todo import Todo


def test_get_method_exists_and_has_correct_signature():
    """Test that get method exists and has the correct signature."""
    storage = Storage()
    # Check method exists
    assert hasattr(storage, 'get')
    # Check method is callable
    assert callable(storage.get)


def test_get_returns_todo_by_id():
    """Test that get can retrieve a todo by its ID."""
    storage = Storage()
    # Add a test todo
    todo = Todo(id=1, title="Test Todo", status="pending")
    storage.add(todo)

    # Get the todo back
    retrieved = storage.get(1)
    assert retrieved is not None
    assert retrieved.id == 1
    assert retrieved.title == "Test Todo"
    assert retrieved.status == "pending"


def test_get_returns_none_for_nonexistent_id():
    """Test that get returns None when todo doesn't exist."""
    storage = Storage()
    # Try to get a non-existent todo
    result = storage.get(999)
    assert result is None


def test_get_with_multiple_todos():
    """Test get method with multiple todos in storage."""
    storage = Storage()
    # Add multiple todos
    todo1 = Todo(id=1, title="First", status="pending")
    todo2 = Todo(id=2, title="Second", status="completed")
    todo3 = Todo(id=3, title="Third", status="pending")
    storage.add(todo1)
    storage.add(todo2)
    storage.add(todo3)

    # Get each todo by ID
    assert storage.get(1).title == "First"
    assert storage.get(2).title == "Second"
    assert storage.get(3).title == "Third"


def test_get_returns_correct_type():
    """Test that get returns Todo | None type."""
    storage = Storage()
    todo = Todo(id=1, title="Test", status="pending")
    storage.add(todo)

    # Should return Todo when found
    result = storage.get(1)
    assert isinstance(result, Todo)

    # Should return None when not found
    result = storage.get(999)
    assert result is None
