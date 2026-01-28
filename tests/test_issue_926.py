"""Test for issue #926 - tags None should use default_factory."""

import pytest
from flywheel.todo import Todo


def test_from_dict_with_tags_none_should_use_default_factory():
    """Test that from_dict handles 'tags': None by using default_factory."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": None,
    }

    todo = Todo.from_dict(data)

    # Should be an empty list, not None
    assert todo.tags is not None
    assert isinstance(todo.tags, list)
    assert todo.tags == []
    # Verify it's a mutable list (default_factory creates new instances)
    todo.tags.append("work")
    assert todo.tags == ["work"]


def test_from_dict_with_tags_not_present_should_use_default_factory():
    """Test that from_dict handles missing 'tags' key by using default_factory."""
    data = {
        "id": 1,
        "title": "Test Todo",
    }

    todo = Todo.from_dict(data)

    # Should be an empty list from default_factory
    assert todo.tags is not None
    assert isinstance(todo.tags, list)
    assert todo.tags == []
    # Verify it's a mutable list (default_factory creates new instances)
    todo.tags.append("work")
    assert todo.tags == ["work"]


def test_from_dict_with_tags_list():
    """Test that from_dict correctly sets tags when provided as a list."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["work", "urgent"],
    }

    todo = Todo.from_dict(data)

    assert todo.tags == ["work", "urgent"]


def test_default_factory_creates_independent_lists():
    """Test that default_factory creates independent lists for each instance."""
    todo1 = Todo(id=1, title="Todo 1")
    todo2 = Todo(id=2, title="Todo 2")

    # Modify tags of todo1
    todo1.tags.append("shared")

    # todo2.tags should remain unaffected
    assert todo2.tags == []
    assert "shared" not in todo2.tags
