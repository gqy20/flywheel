"""Tests for Todo.from_dict() timestamp type validation (Issue #2126).

These tests verify that:
1. from_dict() rejects invalid timestamp types (int, list, dict)
2. from_dict() accepts valid ISO string timestamps
3. from_dict() handles null/missing timestamps with defaults
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_rejects_int_created_at() -> None:
    """Bug #2126: from_dict() should reject int for created_at."""
    with pytest.raises(ValueError, match=r"created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": 123456})


def test_from_dict_rejects_list_created_at() -> None:
    """Bug #2126: from_dict() should reject list for created_at."""
    with pytest.raises(ValueError, match=r"created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": ["2024", "01", "01"]})


def test_from_dict_rejects_dict_created_at() -> None:
    """Bug #2126: from_dict() should reject dict for created_at."""
    with pytest.raises(ValueError, match=r"created_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "created_at": {"iso": "2024-01-01"}})


def test_from_dict_rejects_int_updated_at() -> None:
    """Bug #2126: from_dict() should reject int for updated_at."""
    with pytest.raises(ValueError, match=r"updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": 123456})


def test_from_dict_rejects_list_updated_at() -> None:
    """Bug #2126: from_dict() should reject list for updated_at."""
    with pytest.raises(ValueError, match=r"updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": ["2024", "01", "01"]})


def test_from_dict_rejects_dict_updated_at() -> None:
    """Bug #2126: from_dict() should reject dict for updated_at."""
    with pytest.raises(ValueError, match=r"updated_at.*must be a string"):
        Todo.from_dict({"id": 1, "text": "test", "updated_at": {"iso": "2024-01-01"}})


def test_from_dict_accepts_valid_iso_timestamp() -> None:
    """Bug #2126: from_dict() should accept valid ISO string timestamps."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-15T11:00:00+00:00"
    })
    assert todo.created_at == "2024-01-15T10:30:00+00:00"
    assert todo.updated_at == "2024-01-15T11:00:00+00:00"


def test_from_dict_handles_null_timestamps() -> None:
    """Bug #2126: from_dict() should handle null/missing timestamps with defaults."""
    # Missing timestamps - should default to current time via __post_init__
    todo = Todo.from_dict({"id": 1, "text": "test"})
    assert isinstance(todo.created_at, str)
    assert isinstance(todo.updated_at, str)
    assert len(todo.created_at) > 0
    assert len(todo.updated_at) > 0

    # Explicit None should also work
    todo2 = Todo.from_dict({"id": 2, "text": "test2", "created_at": None, "updated_at": None})
    assert isinstance(todo2.created_at, str)
    assert isinstance(todo2.updated_at, str)
    assert len(todo2.created_at) > 0
    assert len(todo2.updated_at) > 0


def test_from_dict_accepts_empty_string_timestamps() -> None:
    """Bug #2126: from_dict() should accept empty strings for timestamps (triggers default)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "test",
        "created_at": "",
        "updated_at": ""
    })
    # Empty string triggers __post_init__ to set current time
    assert len(todo.created_at) > 0
    assert len(todo.updated_at) > 0
