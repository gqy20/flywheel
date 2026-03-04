"""Tests for Todo.from_dict timestamp None handling (Issue #7190).

These tests verify that:
1. None timestamps generate new timestamps instead of string 'None'
2. Empty string timestamps generate new timestamps
3. Valid timestamps are preserved
"""

from __future__ import annotations

from datetime import datetime

from flywheel.todo import Todo


def test_from_dict_none_created_at_generates_timestamp() -> None:
    """Todo.from_dict with created_at=None should generate a new timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # Should not be the literal string 'None'
    assert todo.created_at != "None"
    # Should be a valid ISO timestamp (not empty after __post_init__)
    assert todo.created_at != ""
    # Should be parseable as an ISO timestamp
    datetime.fromisoformat(todo.created_at)


def test_from_dict_none_updated_at_generates_timestamp() -> None:
    """Todo.from_dict with updated_at=None should generate a new timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": None})
    assert todo.updated_at != "None"
    assert todo.updated_at != ""
    datetime.fromisoformat(todo.updated_at)


def test_from_dict_empty_string_created_at_generates_timestamp() -> None:
    """Todo.from_dict with created_at='' should generate a new timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    assert todo.created_at != ""
    datetime.fromisoformat(todo.created_at)


def test_from_dict_empty_string_updated_at_generates_timestamp() -> None:
    """Todo.from_dict with updated_at='' should generate a new timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": ""})
    assert todo.updated_at != ""
    datetime.fromisoformat(todo.updated_at)


def test_from_dict_valid_timestamp_preserved() -> None:
    """Todo.from_dict with valid timestamp should preserve it."""
    expected = "2020-01-01T00:00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": expected})
    assert todo.created_at == expected


def test_from_dict_missing_timestamp_generates_one() -> None:
    """Todo.from_dict without timestamp fields should generate them."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.created_at != ""
    assert todo.updated_at != ""
    datetime.fromisoformat(todo.created_at)
    datetime.fromisoformat(todo.updated_at)
