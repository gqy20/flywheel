"""Tests for timestamp validation in from_dict (Issue #6393).

These tests verify that:
1. from_dict with valid ISO 8601 timestamp succeeds
2. from_dict with invalid timestamp string raises ValueError
3. from_dict with empty string timestamp succeeds (existing behavior)
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_from_dict_with_valid_iso_timestamp_succeeds() -> None:
    """Todo.from_dict should accept valid ISO 8601 timestamp strings."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T12:30:45+00:00",
        }
    )
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-02T12:30:45+00:00"


def test_from_dict_with_invalid_created_at_raises_value_error() -> None:
    """Todo.from_dict should reject invalid timestamp strings for created_at."""
    with pytest.raises(ValueError, match=r"Invalid value for 'created_at'.*ISO 8601"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": "invalid"})


def test_from_dict_with_invalid_updated_at_raises_value_error() -> None:
    """Todo.from_dict should reject invalid timestamp strings for updated_at."""
    with pytest.raises(ValueError, match=r"Invalid value for 'updated_at'.*ISO 8601"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": "not-a-timestamp"})


def test_from_dict_with_empty_string_created_at_succeeds() -> None:
    """Todo.from_dict should accept empty string for created_at (allows __post_init__ to fill)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "created_at": ""})
    # __post_init__ should fill in the current timestamp
    assert todo.created_at != ""
    assert "T" in todo.created_at  # Basic ISO format check


def test_from_dict_with_empty_string_updated_at_succeeds() -> None:
    """Todo.from_dict should accept empty string for updated_at (allows __post_init__ to fill)."""
    todo = Todo.from_dict({"id": 1, "text": "task", "updated_at": ""})
    # __post_init__ should fill in the current timestamp
    assert todo.updated_at != ""


def test_from_dict_with_missing_timestamps_succeeds() -> None:
    """Todo.from_dict should work when timestamps are not provided."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # __post_init__ should fill in the timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_from_dict_with_z_suffix_timestamp_succeeds() -> None:
    """Todo.from_dict should accept ISO 8601 timestamps with Z suffix."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00Z",
        }
    )
    assert todo.created_at == "2024-01-01T00:00:00Z"


def test_from_dict_with_microseconds_timestamp_succeeds() -> None:
    """Todo.from_dict should accept ISO 8601 timestamps with microseconds."""
    todo = Todo.from_dict(
        {
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00.123456+00:00",
        }
    )
    assert todo.created_at == "2024-01-01T00:00:00.123456+00:00"
