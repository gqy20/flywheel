"""Tests for timestamp validation in from_dict (Issue #4103).

These tests verify that:
1. from_dict rejects non-string types for created_at/updated_at
2. Valid ISO string timestamps still work
3. None/missing values are handled properly (coerced to empty string)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_int_created_at() -> None:
    """Todo.from_dict should reject integers for 'created_at' field."""
    with pytest.raises(
        ValueError, match=r"invalid.*'created_at'|'created_at'.*string|timestamp"
    ):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123})


def test_todo_from_dict_rejects_dict_created_at() -> None:
    """Todo.from_dict should reject dicts for 'created_at' field."""
    with pytest.raises(
        ValueError, match=r"invalid.*'created_at'|'created_at'.*string|timestamp"
    ):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {"a": 1}})


def test_todo_from_dict_rejects_int_updated_at() -> None:
    """Todo.from_dict should reject integers for 'updated_at' field."""
    with pytest.raises(
        ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string|timestamp"
    ):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": 456})


def test_todo_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dicts for 'updated_at' field."""
    with pytest.raises(
        ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string|timestamp"
    ):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {"b": 2}})


def test_todo_from_dict_rejects_float_created_at() -> None:
    """Todo.from_dict should reject floats for 'created_at' field."""
    with pytest.raises(
        ValueError, match=r"invalid.*'created_at'|'created_at'.*string|timestamp"
    ):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123.456})


def test_todo_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject lists for 'created_at' field."""
    with pytest.raises(
        ValueError, match=r"invalid.*'created_at'|'created_at'.*string|timestamp"
    ):
        Todo.from_dict({"id": 1, "text": "task", "created_at": [1, 2, 3]})


def test_todo_from_dict_accepts_iso_string_timestamps() -> None:
    """Todo.from_dict should accept valid ISO string timestamps."""
    iso_timestamp = "2024-01-15T10:30:00+00:00"
    todo = Todo.from_dict(
        {"id": 1, "text": "task", "created_at": iso_timestamp, "updated_at": iso_timestamp}
    )
    assert todo.created_at == iso_timestamp
    assert todo.updated_at == iso_timestamp


def test_todo_from_dict_handles_none_timestamp_as_empty() -> None:
    """Todo.from_dict with None timestamp should coerce to empty string (triggers __post_init__)."""
    # None becomes empty string, which triggers __post_init__ to set current time
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # Should have a timestamp set by __post_init__, not "None"
    assert todo.created_at != "None"
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format contains T


def test_todo_from_dict_handles_missing_timestamp_as_empty() -> None:
    """Todo.from_dict with missing timestamp should coerce to empty string (triggers __post_init__)."""
    # Missing field becomes empty string, which triggers __post_init__
    todo = Todo.from_dict({"id": 1, "text": "task"})
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format contains T


def test_todo_from_dict_accepts_empty_string_timestamp() -> None:
    """Todo.from_dict should accept empty string for timestamps (triggers __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    # Empty string triggers __post_init__ to set current time
    assert todo.created_at != ""
    assert "T" in todo.created_at
