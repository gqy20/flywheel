"""Tests for timestamp validation in from_dict (Issue #6393).

These tests verify that:
1. Valid ISO 8601 timestamp strings are accepted
2. Invalid timestamp strings raise ValueError
3. Empty string timestamps are allowed (for __post_init__ to fill)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_accepts_valid_iso8601_created_at() -> None:
    """Todo.from_dict should accept valid ISO 8601 timestamp for created_at."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-01T00:00:00+00:00"
    })
    assert todo.created_at == "2024-01-01T00:00:00+00:00"


def test_from_dict_accepts_valid_iso8601_updated_at() -> None:
    """Todo.from_dict should accept valid ISO 8601 timestamp for updated_at."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "updated_at": "2024-06-15T12:30:45+00:00"
    })
    assert todo.updated_at == "2024-06-15T12:30:45+00:00"


def test_from_dict_accepts_empty_string_timestamps() -> None:
    """Todo.from_dict should allow empty string timestamps (filled by __post_init__)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "",
        "updated_at": ""
    })
    # __post_init__ will fill with current time
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_accepts_none_timestamps() -> None:
    """Todo.from_dict should treat None as empty (filled by __post_init__)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": None,
        "updated_at": None
    })
    # __post_init__ will fill with current time
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_rejects_invalid_created_at() -> None:
    """Todo.from_dict should reject invalid timestamp string for created_at."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'|ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "invalid"
        })


def test_from_dict_rejects_invalid_updated_at() -> None:
    """Todo.from_dict should reject invalid timestamp string for updated_at."""
    with pytest.raises(ValueError, match=r"Invalid.*'updated_at'|ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "updated_at": "not-a-date"
        })


def test_from_dict_rejects_non_iso_format_timestamp() -> None:
    """Todo.from_dict should reject timestamp not in ISO 8601 format."""
    with pytest.raises(ValueError, match=r"Invalid.*'created_at'|ISO 8601"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2024/01/01 12:00:00"  # Wrong format
        })
