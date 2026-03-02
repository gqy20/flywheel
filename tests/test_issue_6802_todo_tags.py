"""Tests for Todo tags/category field support (Issue #6802).

These tests verify that:
1. Todo dataclass includes optional tags field (type list[str], defaults to empty list)
2. Todo.from_dict can correctly parse a dict containing tags
3. Todo.to_dict returns a dict that includes the tags field
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_tags_field_with_default_empty_list() -> None:
    """Todo should have a tags field that defaults to an empty list."""
    todo = Todo(id=1, text="Test task")
    assert hasattr(todo, "tags")
    assert todo.tags == []


def test_todo_accepts_tags_on_construction() -> None:
    """Todo should accept tags parameter with list of strings."""
    todo = Todo(id=1, text="Test task", tags=["work", "urgent"])
    assert todo.tags == ["work", "urgent"]


def test_todo_from_dict_parses_tags() -> None:
    """Todo.from_dict should correctly parse tags from dict."""
    todo = Todo.from_dict({"id": 1, "text": "x", "tags": ["a", "b"]})
    assert todo.tags == ["a", "b"]


def test_todo_from_dict_defaults_tags_to_empty_list() -> None:
    """Todo.from_dict should default tags to empty list when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "x"})
    assert todo.tags == []


def test_todo_to_dict_includes_tags() -> None:
    """Todo.to_dict should include tags field in output."""
    todo = Todo(id=1, text="Test task", tags=["work", "personal"])
    result = todo.to_dict()
    assert "tags" in result
    assert result["tags"] == ["work", "personal"]


def test_todo_to_dict_includes_empty_tags() -> None:
    """Todo.to_dict should include tags field even when empty."""
    todo = Todo(id=1, text="Test task")
    result = todo.to_dict()
    assert "tags" in result
    assert result["tags"] == []
