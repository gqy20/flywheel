"""Test for Todo description field type consistency (issue #1581)."""

import pytest
from flywheel.todo import Todo


def test_description_none_should_remain_none():
    """Test that None description remains None after from_dict conversion."""
    # Create a todo with None description
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": None,
    }

    todo = Todo.from_dict(data)

    # Description should be None, not empty string
    assert todo.description is None, (
        f"Expected description to be None, but got '{todo.description}' "
        f"(type: {type(todo.description).__name__})"
    )


def test_description_empty_string_should_become_none():
    """Test that empty string description is converted to None."""
    # Create a todo with empty string description
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "",
    }

    todo = Todo.from_dict(data)

    # Empty description should be converted to None
    assert todo.description is None, (
        f"Expected description to be None for empty string, but got '{todo.description}' "
        f"(type: {type(todo.description).__name__})"
    )


def test_description_whitespace_only_should_become_none():
    """Test that whitespace-only description is converted to None."""
    # Create a todo with whitespace-only description
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "   \t\n   ",
    }

    todo = Todo.from_dict(data)

    # Whitespace-only description should be converted to None after sanitization
    assert todo.description is None, (
        f"Expected description to be None for whitespace-only string, but got '{todo.description}' "
        f"(type: {type(todo.description).__name__})"
    )


def test_description_valid_text_should_remain():
    """Test that valid description text is preserved."""
    # Create a todo with valid description
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "This is a valid description",
    }

    todo = Todo.from_dict(data)

    # Valid description should be preserved
    assert todo.description == "This is a valid description", (
        f"Expected 'This is a valid description', but got '{todo.description}'"
    )
    assert isinstance(todo.description, str), (
        f"Expected description to be str, but got {type(todo.description).__name__}"
    )
