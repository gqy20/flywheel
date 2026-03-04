"""Tests for timestamp format validation in from_dict (Issue #7163).

These tests verify that:
1. from_dict with valid ISO timestamp succeeds
2. from_dict with empty string for timestamps succeeds (default behavior)
3. from_dict with invalid timestamp raises ValueError
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_with_valid_iso_timestamp_succeeds() -> None:
    """from_dict should accept valid ISO format timestamps."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T11:30:00+00:00",
        }
    )
    assert todo.created_at == "2024-01-15T10:30:00+00:00"
    assert todo.updated_at == "2024-01-15T11:30:00+00:00"


def test_from_dict_with_empty_timestamp_succeeds() -> None:
    """from_dict should accept empty string for timestamps (default behavior).

    Empty string triggers __post_init__ to set default timestamps.
    """
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "",
            "updated_at": "",
        }
    )
    # Empty strings are accepted, __post_init__ will set defaults
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_with_invalid_created_at_raises_value_error() -> None:
    """from_dict should reject malformed created_at timestamps."""
    with pytest.raises(
        ValueError, match=r"invalid.*'created_at'|'created_at'.*timestamp|'created_at'.*ISO"
    ):
        Todo.from_dict(
            {
                "id": 1,
                "text": "task",
                "created_at": "not-a-date",
            }
        )


def test_from_dict_with_invalid_updated_at_raises_value_error() -> None:
    """from_dict should reject malformed updated_at timestamps."""
    with pytest.raises(
        ValueError, match=r"invalid.*'updated_at'|'updated_at'.*timestamp|'updated_at'.*ISO"
    ):
        Todo.from_dict(
            {
                "id": 1,
                "text": "task",
                "updated_at": "invalid-timestamp",
            }
        )


def test_from_dict_without_timestamps_succeeds() -> None:
    """from_dict should succeed when timestamps are not provided (default behavior)."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
        }
    )
    # __post_init__ will set default timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_with_none_timestamp_succeeds() -> None:
    """from_dict should treat None as empty string for timestamps."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": None,
            "updated_at": None,
        }
    )
    # None is treated as empty string, __post_init__ will set defaults
    assert todo.created_at != ""
    assert todo.updated_at != ""
