"""Tests for timestamp validation in from_dict (Issue #4242).

These tests verify that:
1. Todo.from_dict raises ValueError when created_at/updated_at is a non-string type
2. Todo.from_dict raises ValueError when timestamp string is not valid ISO format
3. Valid ISO format strings pass through unchanged
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


# Tests for Issue #4242 - validate timestamp fields are proper strings
def test_todo_from_dict_rejects_int_created_at() -> None:
    """Todo.from_dict should reject integer for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 1234567890})


def test_todo_from_dict_rejects_int_updated_at() -> None:
    """Todo.from_dict should reject integer for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": 1234567890})


def test_todo_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject list for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": []})


def test_todo_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dict for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {}})


def test_todo_from_dict_rejects_float_created_at() -> None:
    """Todo.from_dict should reject float for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 1708364400.123})


def test_todo_from_dict_rejects_bool_created_at() -> None:
    """Todo.from_dict should reject bool for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": True})


def test_todo_from_dict_accepts_valid_iso_timestamp() -> None:
    """Todo.from_dict should accept valid ISO format strings for timestamps."""
    valid_iso = "2024-02-19T12:00:00+00:00"
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": valid_iso,
            "updated_at": valid_iso,
        }
    )
    assert todo.created_at == valid_iso
    assert todo.updated_at == valid_iso


def test_todo_from_dict_accepts_none_created_at() -> None:
    """Todo.from_dict should accept None for 'created_at' (will generate in __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # __post_init__ will generate a new timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format has 'T'


def test_todo_from_dict_accepts_empty_string_created_at() -> None:
    """Todo.from_dict should accept empty string for 'created_at' (will generate in __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    # __post_init__ will generate a new timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format has 'T'


def test_todo_from_dict_accepts_omitted_created_at() -> None:
    """Todo.from_dict should work when created_at is omitted (defaults to empty, then generated)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # __post_init__ will generate a new timestamp since created_at defaults to ""
    assert todo.created_at != ""
    assert "T" in todo.created_at  # ISO format has 'T'
