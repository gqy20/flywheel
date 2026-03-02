"""Tests for Todo tags field support (Issue #6802).

These tests verify that:
1. Todo dataclass includes optional tags field (list[str], default empty list)
2. Todo.from_dict correctly parses tags from dictionary
3. Todo.to_dict returns dictionary containing tags field
"""

from __future__ import annotations

from flywheel.todo import Todo


def test_todo_tags_field_default_empty_list() -> None:
    """Todo should have tags field with default empty list."""
    todo = Todo(id=1, text="test task")

    assert hasattr(todo, "tags")
    assert todo.tags == []


def test_todo_tags_field_with_values() -> None:
    """Todo(tags=['work', 'urgent']) should correctly save tags."""
    todo = Todo(id=1, text="important task", tags=["work", "urgent"])

    assert todo.tags == ["work", "urgent"]


def test_todo_from_dict_parses_tags() -> None:
    """Todo.from_dict({'id': 1, 'text': 'x', 'tags': ['a']}) should correctly parse tags."""
    data = {"id": 1, "text": "task with tags", "tags": ["a", "b", "c"]}
    todo = Todo.from_dict(data)

    assert todo.tags == ["a", "b", "c"]


def test_todo_from_dict_missing_tags_defaults_to_empty_list() -> None:
    """Todo.from_dict without tags should default to empty list."""
    data = {"id": 1, "text": "task without tags"}
    todo = Todo.from_dict(data)

    assert todo.tags == []


def test_todo_to_dict_includes_tags() -> None:
    """Todo.to_dict() should return dictionary containing tags field."""
    todo = Todo(id=1, text="task", tags=["work", "personal"])
    result = todo.to_dict()

    assert "tags" in result
    assert result["tags"] == ["work", "personal"]


def test_todo_to_dict_includes_empty_tags() -> None:
    """Todo.to_dict() should include tags field even when empty."""
    todo = Todo(id=1, text="task")
    result = todo.to_dict()

    assert "tags" in result
    assert result["tags"] == []


def test_todo_roundtrip_preserves_tags() -> None:
    """Tags should be preserved through to_dict -> from_dict roundtrip."""
    original = Todo(id=1, text="task", tags=["urgent", "work"])
    data = original.to_dict()
    restored = Todo.from_dict(data)

    assert restored.tags == ["urgent", "work"]


def test_todo_tags_with_special_characters() -> None:
    """Todo tags should handle unicode and special characters."""
    todo = Todo(id=1, text="task", tags=["工作", "personal", "test-case"])

    assert todo.tags == ["工作", "personal", "test-case"]


def test_todo_from_dict_with_empty_tags_list() -> None:
    """Todo.from_dict with explicit empty tags list should work."""
    data = {"id": 1, "text": "task", "tags": []}
    todo = Todo.from_dict(data)

    assert todo.tags == []
