"""Tests for issue #1551 - Mutable default argument for 'description' field."""

import pytest
from flywheel.todo import Todo


def test_description_none_consistency():
    """Test that description handles None consistently with tags field.

    Issue #1551: The from_dict method should handle None consistently.
    - tags: distinguishes between None (use default_factory) and missing (use default_factory)
    - description: should do the same or enforce strict types
    """
    # Test 1: description=None should be allowed (consistency with tags)
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": None,
    }
    # This should not raise an error - None should be treated like missing
    todo = Todo.from_dict(data)
    assert todo.description == ""  # None should default to empty string


def test_description_missing():
    """Test that missing description field defaults to empty string."""
    data = {
        "id": 1,
        "title": "Test Todo",
    }
    todo = Todo.from_dict(data)
    assert todo.description == ""


def test_description_empty_string():
    """Test that empty string description is preserved."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "",
    }
    todo = Todo.from_dict(data)
    assert todo.description == ""


def test_description_valid_string():
    """Test that valid description string is preserved."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Valid description",
    }
    todo = Todo.from_dict(data)
    assert todo.description == "Valid description"


def test_tags_none_vs_missing_consistency():
    """Test that tags properly handles None vs missing for comparison."""
    # Test with None - should use default_factory
    data1 = {
        "id": 1,
        "title": "Test Todo",
        "tags": None,
    }
    todo1 = Todo.from_dict(data1)
    assert todo1.tags == []

    # Test missing - should use default_factory
    data2 = {
        "id": 2,
        "title": "Test Todo",
    }
    todo2 = Todo.from_dict(data2)
    assert todo2.tags == []

    # Both should result in empty list
    assert todo1.tags == todo2.tags


def test_direct_instantiation_description_none():
    """Test that Todo can be instantiated directly with description=None."""
    # This should be allowed for consistency
    todo = Todo(
        id=1,
        title="Test Todo",
        description=None,
    )
    # description should be None or "" based on type hint
    assert todo.description in (None, "")
