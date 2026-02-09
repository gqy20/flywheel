"""Tests for timestamp field validation in Todo.from_dict (Issue #2456).

These tests verify that created_at and updated_at fields properly validate
their types and reject non-string/non-None values.
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_int_created_at() -> None:
    """Todo.from_dict should reject integer values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123})


def test_todo_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject list values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": ["invalid"]})


def test_todo_from_dict_rejects_dict_created_at() -> None:
    """Todo.from_dict should reject dict values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {"key": "value"}})


def test_todo_from_dict_accepts_none_created_at() -> None:
    """Todo.from_dict should accept None for 'created_at' (defaults to timestamp in __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # None becomes empty string via data.get() or "", then __post_init__ sets timestamp
    assert todo.created_at != ""  # Should be populated by __post_init__


def test_todo_from_dict_accepts_string_created_at() -> None:
    """Todo.from_dict should accept valid ISO string for 'created_at'."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "2024-01-01T00:00:00+00:00"})
    assert todo.created_at == "2024-01-01T00:00:00+00:00"


def test_todo_from_dict_rejects_int_updated_at() -> None:
    """Todo.from_dict should reject integer values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": 123})


def test_todo_from_dict_rejects_list_updated_at() -> None:
    """Todo.from_dict should reject list values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": ["invalid"]})


def test_todo_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dict values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {"key": "value"}})


def test_todo_from_dict_accepts_none_updated_at() -> None:
    """Todo.from_dict should accept None for 'updated_at' (defaults to timestamp in __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": None})
    # None becomes empty string via data.get() or "", then __post_init__ sets timestamp
    assert todo.updated_at != ""  # Should be populated by __post_init__


def test_todo_from_dict_accepts_string_updated_at() -> None:
    """Todo.from_dict should accept valid ISO string for 'updated_at'."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": "2024-01-01T00:00:00+00:00"})
    assert todo.updated_at == "2024-01-01T00:00:00+00:00"


def test_todo_from_dict_rejects_both_timestamps_as_int() -> None:
    """Todo.from_dict should reject integer values for both timestamp fields."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123, "updated_at": 456})
