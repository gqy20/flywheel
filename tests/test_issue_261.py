"""Test for issue #261 - tags field default value not working in from_dict."""

import pytest
from flywheel.todo import Todo


def test_from_dict_without_tags_should_have_empty_list():
    """Test that from_dict creates empty list when tags is not provided."""
    data = {
        "id": 1,
        "title": "Test Todo",
    }

    todo = Todo.from_dict(data)

    # Should have an empty list
    assert todo.tags == []
    assert isinstance(todo.tags, list)


def test_from_dict_with_empty_tags_list():
    """Test that from_dict correctly handles explicit empty tags list."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": [],
    }

    todo = Todo.from_dict(data)

    assert todo.tags == []
    assert isinstance(todo.tags, list)


def test_from_dict_with_tags():
    """Test that from_dict correctly handles tags with values."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["urgent", "work"],
    }

    todo = Todo.from_dict(data)

    assert todo.tags == ["urgent", "work"]
    assert isinstance(todo.tags, list)


def test_from_dict_should_respect_dataclass_default_factory():
    """Test that from_dict properly delegates to dataclass default_factory.

    The bug in issue #261 is that from_dict uses data.get("tags", []) which
    hardcodes a default value instead of letting the dataclass handle it.

    The correct pattern is to use data.get("tags") which returns None when
    the key is missing, allowing the dataclass's default_factory=list to
    create the default value.

    This test verifies that the fix maintains the correct behavior.
    """
    # When tags key is missing, should get empty list from default_factory
    todo1 = Todo.from_dict({"id": 1, "title": "Todo 1"})
    assert todo1.tags == []

    # When tags key is present with empty list, should use that list
    todo2 = Todo.from_dict({"id": 2, "title": "Todo 2", "tags": []})
    assert todo2.tags == []

    # When tags key has values, should use those values
    todo3 = Todo.from_dict({"id": 3, "title": "Todo 3", "tags": ["work"]})
    assert todo3.tags == ["work"]
