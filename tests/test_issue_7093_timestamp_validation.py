"""Tests for timestamp validation in from_dict (Issue #7093).

These tests verify that:
1. Todo.from_dict with valid ISO timestamp succeeds
2. Todo.from_dict with invalid timestamp string raises ValueError
3. Todo.from_dict with empty/missing timestamp uses auto-generated value
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_accepts_valid_iso_timestamp() -> None:
    """Todo.from_dict should accept valid ISO format timestamps."""
    valid_iso = "2024-01-15T10:30:00+00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": valid_iso,
        "updated_at": valid_iso,
    })
    assert todo.created_at == valid_iso
    assert todo.updated_at == valid_iso


def test_todo_from_dict_accepts_valid_iso_timestamp_with_z() -> None:
    """Todo.from_dict should accept ISO format timestamps with Z suffix."""
    valid_iso_z = "2024-01-15T10:30:00Z"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": valid_iso_z,
        "updated_at": valid_iso_z,
    })
    assert todo.created_at == valid_iso_z
    assert todo.updated_at == valid_iso_z


def test_todo_from_dict_accepts_valid_iso_timestamp_with_microseconds() -> None:
    """Todo.from_dict should accept ISO format timestamps with microseconds."""
    valid_iso_us = "2024-01-15T10:30:00.123456+00:00"
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": valid_iso_us,
        "updated_at": valid_iso_us,
    })
    assert todo.created_at == valid_iso_us
    assert todo.updated_at == valid_iso_us


def test_todo_from_dict_rejects_invalid_created_at_timestamp() -> None:
    """Todo.from_dict should reject invalid timestamp string for 'created_at'."""
    with pytest.raises(ValueError, match=r"invalid.*timestamp|'created_at'.*format"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "invalid-date",
        })


def test_todo_from_dict_rejects_invalid_updated_at_timestamp() -> None:
    """Todo.from_dict should reject invalid timestamp string for 'updated_at'."""
    with pytest.raises(ValueError, match=r"invalid.*timestamp|'updated_at'.*format"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "updated_at": "not-a-timestamp",
        })


def test_todo_from_dict_rejects_malformed_date_string() -> None:
    """Todo.from_dict should reject malformed date strings."""
    with pytest.raises(ValueError, match=r"invalid.*timestamp|'created_at'.*format"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2024/01/15 10:30:00",  # Wrong format
        })


def test_todo_from_dict_rejects_plain_text_timestamp() -> None:
    """Todo.from_dict should reject plain text that isn't a timestamp."""
    with pytest.raises(ValueError, match=r"invalid.*timestamp|'created_at'.*format"):
        Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "yesterday at noon",
        })


def test_todo_from_dict_without_timestamps_uses_auto_generated() -> None:
    """Todo.from_dict without timestamps should auto-generate valid ISO timestamps."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # Auto-generated timestamps should be non-empty ISO format strings
    assert todo.created_at != ""
    assert todo.updated_at != ""
    # Verify they are valid ISO format by parsing them
    from datetime import datetime
    # Should not raise ValueError if parsing succeeds
    datetime.fromisoformat(todo.created_at.replace("Z", "+00:00"))
    datetime.fromisoformat(todo.updated_at.replace("Z", "+00:00"))


def test_todo_from_dict_with_empty_timestamps_uses_auto_generated() -> None:
    """Todo.from_dict with empty string timestamps should auto-generate values."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "",
        "updated_at": "",
    })
    # Auto-generated timestamps should be non-empty
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_todo_from_dict_with_none_timestamps_uses_auto_generated() -> None:
    """Todo.from_dict with None timestamps should auto-generate values."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": None,
        "updated_at": None,
    })
    # Auto-generated timestamps should be non-empty
    assert todo.created_at != ""
    assert todo.updated_at != ""
