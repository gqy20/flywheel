"""Tests for created_at/updated_at type validation in Todo.from_dict (Issue #2828).

These tests verify that:
1. from_dict rejects dict/list types for created_at/updated_at fields
2. from_dict handles None for created_at/updated_at by using empty string
3. from_dict accepts valid ISO timestamp strings for created_at/updated_at
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_dict_for_created_at() -> None:
    """Todo.from_dict should reject dict type for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*type|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": {"key": "value"}})


def test_from_dict_rejects_list_for_created_at() -> None:
    """Todo.from_dict should reject list type for 'created_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*type|'created_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": ["2024-01-01"]})


def test_from_dict_rejects_dict_for_updated_at() -> None:
    """Todo.from_dict should reject dict type for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*type|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": {"key": "value"}})


def test_from_dict_rejects_list_for_updated_at() -> None:
    """Todo.from_dict should reject list type for 'updated_at' field."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*type|'updated_at'.*string"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": ["2024-01-01"]})


def test_from_dict_handles_none_for_created_at() -> None:
    """Todo.from_dict should use empty string when 'created_at' is None.
    Note: __post_init__ will convert empty string to ISO timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None})
    # Should get a valid ISO timestamp (not 'None' string)
    assert todo.created_at != ""
    assert "None" not in todo.created_at
    assert todo.created_at.count("-") >= 2  # ISO format has dates


def test_from_dict_handles_none_for_updated_at() -> None:
    """Todo.from_dict should use empty string when 'updated_at' is None.
    Note: __post_init__ will convert empty string to ISO timestamp."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": None})
    # Should get a valid ISO timestamp (not 'None' string)
    assert todo.updated_at != ""
    assert "None" not in todo.updated_at
    assert todo.updated_at.count("-") >= 2  # ISO format has dates


def test_from_dict_handles_none_for_both_timestamps() -> None:
    """Todo.from_dict should use empty string when both timestamps are None.
    Note: __post_init__ will convert empty strings to ISO timestamps."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": None, "updated_at": None})
    # Should get valid ISO timestamps (not 'None' string)
    assert "None" not in todo.created_at
    assert "None" not in todo.updated_at
    assert todo.created_at.count("-") >= 2
    assert todo.updated_at.count("-") >= 2


def test_from_dict_accepts_valid_iso_timestamp() -> None:
    """Todo.from_dict should accept valid ISO timestamp strings."""
    iso_time = "2024-01-01T00:00:00+00:00"
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": iso_time, "updated_at": iso_time})
    assert todo.created_at == iso_time
    assert todo.updated_at == iso_time


def test_from_dict_accepts_string_timestamp() -> None:
    """Todo.from_dict should accept string timestamps."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "2024-01-01", "updated_at": "2024-01-02"})
    assert todo.created_at == "2024-01-01"
    assert todo.updated_at == "2024-01-02"


def test_from_dict_defaults_to_empty_when_timestamps_missing() -> None:
    """Todo.from_dict should use empty string when timestamps are missing."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # After __post_init__, empty strings become ISO timestamps
    # So we just verify no error is raised and timestamps are valid strings
    assert isinstance(todo.created_at, str)
    assert isinstance(todo.updated_at, str)


def test_from_dict_serializes_with_valid_timestamps() -> None:
    """Todo.from_dict should produce objects that can serialize correctly."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": "2024-01-01T00:00:00+00:00"})
    # Should be able to convert back to dict without error
    result = todo.to_dict()
    assert result["created_at"] == "2024-01-01T00:00:00+00:00"
