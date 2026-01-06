"""Test for issue #875 - from_dict missing created_at field handling."""

import pytest
from flywheel.todo import Todo


def test_from_dict_without_created_at_field():
    """Test that from_dict works when 'created_at' field is missing from input data.

    This test verifies the fix for issue #875 where from_dict would fail
    when the input dictionary doesn't contain a 'created_at' field.

    The expected behavior is that the default_factory should generate
    a timestamp automatically.
    """
    # Data without 'created_at' field
    data = {
        "id": 1,
        "title": "Test todo without created_at",
        "description": "This should use default_factory",
        "status": "todo",
        "priority": "medium",
    }

    # This should not raise an error and should use default_factory
    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test todo without created_at"
    assert todo.created_at is not None
    assert isinstance(todo.created_at, str)


def test_from_dict_with_explicit_none_created_at():
    """Test that from_dict works when 'created_at' is explicitly None.

    When 'created_at' is explicitly set to None in the input data,
    the default_factory should still be used.
    """
    data = {
        "id": 2,
        "title": "Test todo with None created_at",
        "created_at": None,
    }

    todo = Todo.from_dict(data)

    assert todo.id == 2
    assert todo.created_at is not None
    assert isinstance(todo.created_at, str)


def test_from_dict_with_valid_created_at():
    """Test that from_dict preserves provided 'created_at' value."""
    data = {
        "id": 3,
        "title": "Test todo with created_at",
        "created_at": "2025-01-06T10:00:00",
    }

    todo = Todo.from_dict(data)

    assert todo.id == 3
    assert todo.created_at == "2025-01-06T10:00:00"
