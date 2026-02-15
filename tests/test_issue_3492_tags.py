"""Tests for Todo tags/category field support (Issue #3492).

These tests verify that:
1. Todo dataclass contains tags field with type tuple[str, ...]
2. tags field defaults to empty tuple ()
3. from_dict() parses tags list (defaulting to empty tuple if missing)
4. to_dict() output includes tags field
5. Non-string tag values raise clear ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_has_tags_field() -> None:
    """Todo dataclass should have a tags attribute."""
    todo = Todo(id=1, text="Test task")
    assert hasattr(todo, "tags")


def test_todo_tags_defaults_to_empty_tuple() -> None:
    """tags field should default to an empty tuple when not provided."""
    todo = Todo(id=1, text="Test task")
    assert todo.tags == ()
    assert isinstance(todo.tags, tuple)


def test_todo_tags_can_be_set_at_creation() -> None:
    """tags can be provided at Todo creation time."""
    todo = Todo(id=1, text="Test task", tags=("work", "urgent"))
    assert todo.tags == ("work", "urgent")


def test_todo_tags_from_dict_with_tags() -> None:
    """from_dict should parse tags list and convert to tuple."""
    todo = Todo.from_dict({"id": 1, "text": "Test task", "tags": ["a", "b"]})
    assert todo.tags == ("a", "b")
    assert isinstance(todo.tags, tuple)


def test_todo_tags_from_dict_without_tags() -> None:
    """from_dict should default tags to empty tuple when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "Test task"})
    assert todo.tags == ()


def test_todo_tags_to_dict_includes_tags() -> None:
    """to_dict should include tags field in output."""
    todo = Todo(id=1, text="Test task", tags=("work", "personal"))
    result = todo.to_dict()
    assert "tags" in result
    assert result["tags"] == ("work", "personal")


def test_todo_tags_rejects_non_string_in_list() -> None:
    """from_dict should raise ValueError for non-string tag values."""
    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*string|'tags'.*type"):
        Todo.from_dict({"id": 1, "text": "Test task", "tags": ["work", 123]})


def test_todo_tags_rejects_non_list() -> None:
    """from_dict should raise ValueError when tags is not a list."""
    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list|'tags'.*type"):
        Todo.from_dict({"id": 1, "text": "Test task", "tags": "not-a-list"})


def test_todo_tags_accepts_empty_list() -> None:
    """from_dict should accept an empty tags list."""
    todo = Todo.from_dict({"id": 1, "text": "Test task", "tags": []})
    assert todo.tags == ()
