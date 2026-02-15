"""Tests for Todo tags/category field support (Issue #3492).

These tests verify that:
1. Todo dataclass contains tags field
2. from_dict() can parse tags list (default empty list)
3. to_dict() output includes tags
4. Non-string tag values raise clear error
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_has_tags_field_with_default_empty_tuple() -> None:
    """Todo should have a tags field that defaults to an empty tuple."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "tags")
    assert todo.tags == ()


def test_todo_tags_accepts_list_of_strings() -> None:
    """Todo tags field should accept a list of strings and store as tuple."""
    todo = Todo(id=1, text="x", tags=["work"])
    assert todo.tags == ("work",)


def test_todo_from_dict_parses_tags_list() -> None:
    """Todo.from_dict should parse tags list from dictionary."""
    todo = Todo.from_dict({"id": 1, "text": "x", "tags": ["a", "b"]})
    assert todo.tags == ("a", "b")


def test_todo_from_dict_defaults_to_empty_tuple_when_no_tags() -> None:
    """Todo.from_dict should default to empty tuple when tags not present."""
    todo = Todo.from_dict({"id": 1, "text": "x"})
    assert todo.tags == ()


def test_todo_to_dict_includes_tags() -> None:
    """Todo.to_dict should include tags in the output dictionary."""
    todo = Todo(id=1, text="x", tags=["work", "personal"])
    result = todo.to_dict()
    assert "tags" in result
    assert result["tags"] == ("work", "personal")


def test_todo_from_dict_rejects_non_string_tag_values() -> None:
    """Todo.from_dict should reject non-string values in tags list."""
    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*string|'tags'.*must be string"):
        Todo.from_dict({"id": 1, "text": "x", "tags": ["valid", 123]})


def test_todo_from_dict_rejects_non_list_tags() -> None:
    """Todo.from_dict should reject tags that is not a list/tuple."""
    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list|'tags'.*tuple"):
        Todo.from_dict({"id": 1, "text": "x", "tags": "not-a-list"})


def test_todo_tags_are_stored_as_tuple_for_immutability() -> None:
    """Todo tags should be stored as tuple for immutability."""
    todo = Todo(id=1, text="x", tags=["a", "b", "c"])
    # Should be a tuple
    assert isinstance(todo.tags, tuple)
    assert todo.tags == ("a", "b", "c")
