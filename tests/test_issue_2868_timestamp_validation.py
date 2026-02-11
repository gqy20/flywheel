"""Tests for timestamp field type validation (Issue #2868).

These tests verify that:
1. created_at and updated_at must be strings (not int, bool, list, dict, etc.)
2. Empty strings are allowed for backward compatibility
3. Valid ISO format strings are accepted
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_int_created_at() -> None:
    """Todo.from_dict should reject integer values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123})


def test_from_dict_rejects_int_updated_at() -> None:
    """Todo.from_dict should reject integer values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": 456})


def test_from_dict_rejects_list_created_at() -> None:
    """Todo.from_dict should reject list values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": ["not", "a", "string"]})


def test_from_dict_rejects_list_updated_at() -> None:
    """Todo.from_dict should reject list values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": ["not", "a", "string"]})


def test_from_dict_rejects_bool_created_at() -> None:
    """Todo.from_dict should reject boolean values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": True})


def test_from_dict_rejects_bool_updated_at() -> None:
    """Todo.from_dict should reject boolean values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": False})


def test_from_dict_rejects_dict_created_at() -> None:
    """Todo.from_dict should reject dict values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {}})


def test_from_dict_rejects_dict_updated_at() -> None:
    """Todo.from_dict should reject dict values for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {"foo": "bar"}})


def test_from_dict_rejects_float_created_at() -> None:
    """Todo.from_dict should reject float values for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": 123.456})


def test_from_dict_rejects_none_created_at_explicit() -> None:
    """Todo.from_dict should reject explicit None for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": None})


def test_from_dict_accepts_empty_string_timestamps() -> None:
    """Todo.from_dict should accept empty strings for timestamp fields (backward compatibility).

    Note: Empty strings are replaced with current timestamp by __post_init__,
    but the key point is that empty strings are accepted as valid input.
    """
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "", "updated_at": ""})
    # Empty strings get replaced with current timestamp by __post_init__
    assert todo.created_at != ""
    assert todo.updated_at != ""
    # Verify they are valid ISO format timestamps
    assert "T" in todo.created_at
    assert "T" in todo.updated_at


def test_from_dict_accepts_valid_iso_timestamp() -> None:
    """Todo.from_dict should accept valid ISO format timestamp strings."""
    iso_timestamp = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": iso_timestamp, "updated_at": iso_timestamp})
    assert todo.created_at == iso_timestamp
    assert todo.updated_at == iso_timestamp


def test_from_dict_accepts_missing_timestamps() -> None:
    """Todo.from_dict should accept data without timestamp fields (defaults to empty string)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # Empty strings are replaced with current timestamp by __post_init__
    assert todo.created_at != ""
    assert todo.updated_at != ""
