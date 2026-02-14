"""Tests for timestamp format validation in Todo.from_dict (Issue #3228).

These tests verify that:
1. Invalid ISO format for created_at raises ValueError with clear message
2. Invalid ISO format for updated_at raises ValueError with clear message
3. Valid ISO format timestamps are accepted
4. Empty timestamps are still allowed for backward compatibility
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_invalid_created_at_format() -> None:
    """Todo.from_dict should reject non-ISO format strings for 'created_at'."""
    with pytest.raises(ValueError, match=r"(?i)invalid.*'created_at'|'created_at'.*iso"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": "not-a-date"})


def test_todo_from_dict_rejects_invalid_updated_at_format() -> None:
    """Todo.from_dict should reject non-ISO format strings for 'updated_at'."""
    with pytest.raises(ValueError, match=r"(?i)invalid.*'updated_at'|'updated_at'.*iso"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": "not-a-date"})


def test_todo_from_dict_accepts_valid_iso_created_at() -> None:
    """Todo.from_dict should accept valid ISO format for 'created_at'."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-15T10:30:00+00:00"
    })
    assert todo.created_at == "2024-01-15T10:30:00+00:00"


def test_todo_from_dict_accepts_valid_iso_updated_at() -> None:
    """Todo.from_dict should accept valid ISO format for 'updated_at'."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "updated_at": "2024-01-15T10:30:00.123456+00:00"
    })
    assert todo.updated_at == "2024-01-15T10:30:00.123456+00:00"


def test_todo_from_dict_accepts_empty_timestamps() -> None:
    """Todo.from_dict should still accept empty timestamps for backward compatibility."""
    # When timestamps are empty, __post_init__ will generate them
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "", "updated_at": ""})
    # __post_init__ generates timestamps when they're empty
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_todo_from_dict_accepts_none_timestamps() -> None:
    """Todo.from_dict should handle None timestamps by treating as empty."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None, "updated_at": None})
    # __post_init__ generates timestamps when they're empty (converted from None)
    assert todo.created_at != ""
    assert todo.updated_at != ""
