"""Test for issue #506 - from_dict method tags field logic error."""

import pytest
from flywheel.todo import Todo


def test_from_dict_with_none_tags():
    """Test that from_dict handles None tags correctly."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": None,
    }

    # This should not raise TypeError
    todo = Todo.from_dict(data)

    # tags should default to empty list
    assert todo.tags == []


def test_from_dict_with_missing_tags():
    """Test that from_dict handles missing tags field correctly."""
    data = {
        "id": 1,
        "title": "Test Todo",
    }

    # This should not raise any error
    todo = Todo.from_dict(data)

    # tags should default to empty list
    assert todo.tags == []


def test_from_dict_with_valid_tags():
    """Test that from_dict handles valid tags correctly."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["work", "urgent"],
    }

    todo = Todo.from_dict(data)

    assert todo.tags == ["work", "urgent"]


def test_from_dict_with_invalid_tag_type():
    """Test that from_dict rejects non-string tag values."""
    data = {
        "id": 1,
        "title": "Test Todo",
        "tags": ["work", 123],  # 123 is not a string
    }

    with pytest.raises(ValueError, match="All items in 'tags' must be str"):
        Todo.from_dict(data)
