"""Tests for Todo tags field (Issue #6858).

These tests verify that:
1. Todo dataclass includes tags field with default empty list
2. from_dict correctly parses tags as list of strings
3. from_dict rejects non-list types for tags
4. to_dict serializes tags field
5. tags elements are deduplicated and stripped of whitespace
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_default_tags_is_empty_list() -> None:
    """Todo should have tags field defaulting to empty list."""
    todo = Todo(id=1, text="task")
    assert todo.tags == []


def test_todo_can_be_created_with_tags() -> None:
    """Todo should accept tags at creation."""
    todo = Todo(id=1, text="task", tags=["work", "personal"])
    assert todo.tags == ["work", "personal"]


def test_todo_from_dict_parses_valid_tags() -> None:
    """from_dict should correctly parse tags as list of strings."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "urgent"]})
    assert todo.tags == ["work", "urgent"]


def test_todo_from_dict_handles_missing_tags() -> None:
    """from_dict should default tags to empty list when not provided."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.tags == []


def test_todo_from_dict_rejects_non_list_tags() -> None:
    """from_dict should reject non-list types for tags field."""
    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*list|'tags'.*array"):
        Todo.from_dict({"id": 1, "text": "task", "tags": "work"})


def test_todo_from_dict_rejects_non_string_elements_in_tags() -> None:
    """from_dict should reject non-string elements in tags list."""
    with pytest.raises(ValueError, match=r"invalid.*'tags'|'tags'.*string|'tags'.*element"):
        Todo.from_dict({"id": 1, "text": "task", "tags": ["work", 123]})


def test_todo_to_dict_includes_tags() -> None:
    """to_dict should serialize tags field."""
    todo = Todo(id=1, text="task", tags=["work", "personal"])
    data = todo.to_dict()
    assert "tags" in data
    assert data["tags"] == ["work", "personal"]


def test_todo_from_dict_strips_whitespace_from_tags() -> None:
    """from_dict should strip whitespace from tag elements."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": [" work ", "  personal  "]})
    assert todo.tags == ["work", "personal"]


def test_todo_from_dict_deduplicates_tags() -> None:
    """from_dict should remove duplicate tags."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "personal", "work"]})
    # Duplicates should be removed, order preserved (first occurrence kept)
    assert len(todo.tags) == 2
    assert "work" in todo.tags
    assert "personal" in todo.tags


def test_todo_from_dict_filters_empty_tags() -> None:
    """from_dict should filter out empty strings after stripping."""
    todo = Todo.from_dict({"id": 1, "text": "task", "tags": ["work", "  ", "", "personal"]})
    assert todo.tags == ["work", "personal"]
