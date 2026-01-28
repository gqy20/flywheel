"""Test that Todo sanitizes text in all initialization methods."""

import pytest
from flywheel.todo import Todo


def test_direct_init_sanitizes_title():
    """Test that title is sanitized when creating Todo directly."""
    # Title with control characters
    dirty_title = "Buy\x00milk\x01and\x02bread"
    todo = Todo(id=1, title=dirty_title)

    # Should be sanitized
    assert todo.title == "Buy milk and bread"


def test_direct_init_sanitizes_description():
    """Test that description is sanitized when creating Todo directly."""
    # Description with zero-width spaces
    dirty_description = "Task\u200Bwith\u200Czero\u200Dwidth\u200Espaces"
    todo = Todo(id=1, title="Test", description=dirty_description)

    # Should be sanitized
    assert todo.description == "Task with zero width spaces"


def test_direct_init_normalizes_whitespace():
    """Test that whitespace is normalized when creating Todo directly."""
    # Title with tabs and newlines
    dirty_title = "Multi\tline\n\rtitle"
    todo = Todo(id=1, title=dirty_title)

    # Should be normalized
    assert todo.title == "Multi line title"


def test_from_dict_still_sanitizes():
    """Test that from_dict still sanitizes correctly (regression test)."""
    data = {
        "id": 1,
        "title": "Test\x00Title",
        "description": "Desc\u200Bwith\u200Cinvisible"
    }
    todo = Todo.from_dict(data)

    assert todo.title == "Test Title"
    assert todo.description == "Desc with invisible"


def test_direct_init_with_invisible_chars():
    """Test various invisible characters are removed in direct init."""
    # Contains various invisible characters
    dirty_title = "Test\u200B\u200C\u200D\u200E\u200F\u2060\uFEFFTitle"
    todo = Todo(id=1, title=dirty_title)

    # All invisible characters should be removed
    assert todo.title == "Test Title"
