"""Tests for Todo tags/category field support (Issue #6802).

These tests verify that:
1. Todo dataclass contains optional tags field (list[str], defaults to empty list)
2. Todo.from_dict correctly parses dicts containing tags
3. Todo.to_dict returns dict containing tags field
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_has_tags_field_with_default_empty_list() -> None:
    """Todo should have a tags field that defaults to empty list."""
    todo = Todo(id=1, text="test task")
    assert hasattr(todo, "tags")
    assert todo.tags == []


def test_todo_accepts_tags_on_construction() -> None:
    """Todo should accept tags parameter on construction."""
    todo = Todo(id=1, text="test task", tags=["work", "urgent"])
    assert todo.tags == ["work", "urgent"]


def test_todo_from_dict_parses_tags() -> None:
    """Todo.from_dict should correctly parse tags from dict."""
    todo = Todo.from_dict({"id": 1, "text": "test", "tags": ["a", "b"]})
    assert todo.tags == ["a", "b"]


def test_todo_from_dict_defaults_tags_to_empty_list() -> None:
    """Todo.from_dict should default tags to empty list if not provided."""
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert todo.tags == []


def test_todo_to_dict_includes_tags() -> None:
    """Todo.to_dict should include tags field in output."""
    todo = Todo(id=1, text="test", tags=["work", "personal"])
    result = todo.to_dict()
    assert "tags" in result
    assert result["tags"] == ["work", "personal"]


def test_todo_to_dict_includes_empty_tags() -> None:
    """Todo.to_dict should include tags field even when empty."""
    todo = Todo(id=1, text="test")
    result = todo.to_dict()
    assert "tags" in result
    assert result["tags"] == []


def test_todo_tags_are_mutable() -> None:
    """Tags list should be mutable and changes should be reflected in to_dict."""
    todo = Todo(id=1, text="test", tags=["initial"])
    todo.tags.append("added")
    assert "added" in todo.tags
    result = todo.to_dict()
    assert "added" in result["tags"]


def test_todo_from_dict_handles_empty_tags_list() -> None:
    """Todo.from_dict should handle explicit empty tags list."""
    todo = Todo.from_dict({"id": 1, "text": "test", "tags": []})
    assert todo.tags == []


def test_todo_preserves_tags_order() -> None:
    """Todo should preserve the order of tags."""
    todo = Todo(id=1, text="test", tags=["alpha", "beta", "gamma"])
    assert todo.tags == ["alpha", "beta", "gamma"]

    result = todo.to_dict()
    assert result["tags"] == ["alpha", "beta", "gamma"]
