"""Tests for Issue #841 - created_at None handling in from_dict."""

import re
from flywheel.todo import Todo


def test_from_dict_with_none_created_at_should_use_default_factory():
    """Test that from_dict uses default factory when created_at is None."""
    # Arrange
    data = {
        "id": 1,
        "title": "Test Todo",
        "created_at": None,
    }

    # Act
    todo = Todo.from_dict(data)

    # Assert
    # created_at should not be None, it should use the default_factory
    assert todo.created_at is not None, "created_at should not be None when default_factory is defined"
    # Should be a valid ISO format timestamp
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", todo.created_at), \
        f"created_at should be ISO format timestamp, got: {todo.created_at}"


def test_from_dict_without_created_at_should_use_default_factory():
    """Test that from_dict uses default factory when created_at is missing."""
    # Arrange
    data = {
        "id": 2,
        "title": "Test Todo 2",
    }

    # Act
    todo = Todo.from_dict(data)

    # Assert
    assert todo.created_at is not None, "created_at should not be None when using default_factory"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+", todo.created_at), \
        f"created_at should be ISO format timestamp, got: {todo.created_at}"


def test_from_dict_with_valid_created_at_should_preserve_value():
    """Test that from_dict preserves valid created_at value."""
    # Arrange
    data = {
        "id": 3,
        "title": "Test Todo 3",
        "created_at": "2024-01-01T12:00:00.000000",
    }

    # Act
    todo = Todo.from_dict(data)

    # Assert
    assert todo.created_at == "2024-01-01T12:00:00.000000"
