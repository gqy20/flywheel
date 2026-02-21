"""Tests for ISO 8601 timestamp validation (Issue #4931).

These tests verify that:
1. Todo.from_dict rejects invalid ISO 8601 timestamps in created_at
2. Todo.from_dict rejects invalid ISO 8601 timestamps in updated_at
3. Todo.from_dict accepts valid ISO 8601 timestamps (backward compatible)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_invalid_created_at() -> None:
    """Todo.from_dict should reject non-ISO 8601 format for created_at."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'.*ISO 8601"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": "not-a-date"})


def test_todo_from_dict_rejects_malformed_iso_created_at() -> None:
    """Todo.from_dict should reject malformed ISO 8601 for created_at."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'.*ISO 8601"):
        # Missing time separator T - fails format validation
        Todo.from_dict({"id": 1, "text": "task", "created_at": "2024-01-15 10:30:00"})


def test_todo_from_dict_rejects_invalid_updated_at() -> None:
    """Todo.from_dict should reject non-ISO 8601 format for updated_at."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'.*ISO 8601"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": "invalid-timestamp"})


def test_todo_from_dict_rejects_malformed_iso_updated_at() -> None:
    """Todo.from_dict should reject malformed ISO 8601 for updated_at."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'.*ISO 8601"):
        # Invalid format - missing T separator
        Todo.from_dict({"id": 1, "text": "task", "updated_at": "2024-01-15 10:30:00"})


def test_todo_from_dict_accepts_valid_iso_created_at() -> None:
    """Todo.from_dict should accept valid ISO 8601 timestamp for created_at."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-15T10:30:00+00:00"
    })
    assert todo.created_at == "2024-01-15T10:30:00+00:00"


def test_todo_from_dict_accepts_valid_iso_updated_at() -> None:
    """Todo.from_dict should accept valid ISO 8601 timestamp for updated_at."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "updated_at": "2024-01-15T10:30:00.123456+00:00"
    })
    assert todo.updated_at == "2024-01-15T10:30:00.123456+00:00"


def test_todo_from_dict_accepts_valid_iso_with_z_suffix() -> None:
    """Todo.from_dict should accept ISO 8601 timestamp with Z suffix."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
    })
    assert todo.created_at == "2024-01-15T10:30:00Z"
    assert todo.updated_at == "2024-01-15T10:30:00Z"


def test_todo_from_dict_accepts_empty_timestamps() -> None:
    """Todo.from_dict should accept empty timestamps (defaults to current time)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "",
        "updated_at": ""
    })
    # __post_init__ will set timestamps to current time
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_todo_from_dict_accepts_missing_timestamps() -> None:
    """Todo.from_dict should accept missing timestamps (defaults to current time)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # __post_init__ will set timestamps to current time
    assert todo.created_at != ""
    assert todo.updated_at != ""
