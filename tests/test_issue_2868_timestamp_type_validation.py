"""Tests for timestamp field type validation (Issue #2868).

These tests verify that:
1. created_at and updated_at must be strings or None/missing
2. Non-string timestamp values (int, bool, list, dict) are rejected with clear errors
3. Empty strings are allowed (backward compatibility)
4. Valid ISO format strings are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_rejects_int_created_at() -> None:
    """Todo.from_dict should reject integer values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123})


def test_todo_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject list values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": ["not", "a", "string"]})


def test_todo_from_dict_rejects_dict_created_at() -> None:
    """Todo.from_dict should reject dict values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {"not": "a string"}})


def test_todo_from_dict_rejects_bool_created_at() -> None:
    """Todo.from_dict should reject boolean values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": True})


def test_todo_from_dict_rejects_int_updated_at() -> None:
    """Todo.from_dict should reject integer values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": 123})


def test_todo_from_dict_rejects_list_updated_at() -> None:
    """Todo.from_dict should reject list values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": ["not", "a", "string"]})


def test_todo_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dict values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {"not": "a string"}})


def test_todo_from_dict_rejects_bool_updated_at() -> None:
    """Todo.from_dict should reject boolean values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": False})


def test_todo_from_dict_accepts_empty_string_created_at() -> None:
    """Todo.from_dict should accept empty string for 'created_at' field (backward compatibility)."""
    # Empty string is allowed as input, but __post_init__ will replace it with current time
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    # __post_init__ converts empty string to ISO timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # Basic ISO format check


def test_todo_from_dict_accepts_empty_string_updated_at() -> None:
    """Todo.from_dict should accept empty string for 'updated_at' field (backward compatibility)."""
    # Empty string is allowed as input, but __post_init__ will replace it
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": ""})
    # __post_init__ converts empty string to same value as created_at
    assert todo.updated_at != ""
    assert "T" in todo.updated_at  # Basic ISO format check


def test_todo_from_dict_accepts_valid_iso_string_created_at() -> None:
    """Todo.from_dict should accept valid ISO format strings for 'created_at' field."""
    iso_time = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": iso_time})
    assert todo.created_at == iso_time


def test_todo_from_dict_accepts_valid_iso_string_updated_at() -> None:
    """Todo.from_dict should accept valid ISO format strings for 'updated_at' field."""
    iso_time = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": iso_time})
    assert todo.updated_at == iso_time


def test_todo_from_dict_accepts_missing_timestamps() -> None:
    """Todo.from_dict should work when timestamps are not provided (will use defaults)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # __post_init__ should fill in timestamps with ISO format
    assert todo.created_at != ""
    assert todo.updated_at != ""
    assert "T" in todo.created_at  # Basic ISO format check
    assert "T" in todo.updated_at


def test_todo_from_dict_rejects_both_invalid_timestamps() -> None:
    """Todo.from_dict should reject when both timestamp fields are invalid types."""
    with pytest.raises(ValueError, match=r"Invalid.*(created_at|updated_at)"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123, "updated_at": [1, 2, 3]})
