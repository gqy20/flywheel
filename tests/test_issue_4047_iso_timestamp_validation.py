"""Tests for ISO 8601 timestamp validation (Issue #4047).

These tests verify that:
1. Todo.from_dict accepts valid ISO 8601 formatted timestamps
2. Todo.from_dict rejects invalid timestamp formats with clear error messages
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


def test_todo_from_dict_accepts_valid_iso_timestamp() -> None:
    """Todo.from_dict should accept valid ISO 8601 formatted timestamps."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-02T12:30:45+00:00",
    })
    assert todo.created_at == "2024-01-01T00:00:00+00:00"
    assert todo.updated_at == "2024-01-02T12:30:45+00:00"


def test_todo_from_dict_accepts_iso_timestamp_with_z_suffix() -> None:
    """Todo.from_dict should accept ISO 8601 timestamps with Z suffix."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T12:30:45Z",
    })
    assert todo.created_at == "2024-01-01T00:00:00Z"
    assert todo.updated_at == "2024-01-02T12:30:45Z"


def test_todo_from_dict_accepts_iso_timestamp_without_timezone() -> None:
    """Todo.from_dict should accept ISO 8601 timestamps without timezone."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-02T12:30:45",
    })
    assert todo.created_at == "2024-01-01T00:00:00"
    assert todo.updated_at == "2024-01-02T12:30:45"


def test_todo_from_dict_rejects_invalid_created_at_format() -> None:
    """Todo.from_dict should reject invalid timestamp format for 'created_at'."""
    with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*ISO|'created_at'.*format"):
        Todo.from_dict({"id": 1, "text": "task", "created_at": "not-a-date"})


def test_todo_from_dict_rejects_invalid_updated_at_format() -> None:
    """Todo.from_dict should reject invalid timestamp format for 'updated_at'."""
    with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*ISO|'updated_at'.*format"):
        Todo.from_dict({"id": 1, "text": "task", "updated_at": "random-text"})


def test_todo_from_dict_accepts_empty_timestamps() -> None:
    """Todo.from_dict should accept empty string timestamps (will be filled by __post_init__)."""
    todo = Todo.from_dict({
        "id": 1,
        "text": "task",
        "created_at": "",
        "updated_at": "",
    })
    # Empty strings trigger __post_init__ to generate timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""


def test_todo_from_dict_accepts_missing_timestamps() -> None:
    """Todo.from_dict should accept missing timestamp fields (will be filled by __post_init__)."""
    todo = Todo.from_dict({"id": 1, "text": "task"})
    # Missing timestamps trigger __post_init__ to generate timestamps
    assert todo.created_at != ""
    assert todo.updated_at != ""
