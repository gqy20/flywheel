"""Tests for ISO 8601 timestamp validation in Todo.from_dict (Issue #4047).

These tests verify that:
1. Valid ISO 8601 timestamps are accepted
2. Invalid timestamp formats raise ValueError with clear message
"""

from __future__ import annotations

import pytest

from flywheel.todo import Todo


class TestTodoFromDictTimestampValidation:
    """Tests for timestamp validation in Todo.from_dict."""

    def test_todo_from_dict_accepts_valid_iso_timestamp_with_timezone(self) -> None:
        """Todo.from_dict should accept valid ISO 8601 timestamps with timezone."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T12:30:45+05:30",
        })
        assert todo.created_at == "2024-01-01T00:00:00+00:00"
        assert todo.updated_at == "2024-01-02T12:30:45+05:30"

    def test_todo_from_dict_accepts_valid_iso_timestamp_with_z(self) -> None:
        """Todo.from_dict should accept valid ISO 8601 timestamps with Z suffix."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-06-15T23:59:59Z",
        })
        assert todo.created_at == "2024-01-01T00:00:00Z"
        assert todo.updated_at == "2024-06-15T23:59:59Z"

    def test_todo_from_dict_accepts_valid_iso_timestamp_without_timezone(self) -> None:
        """Todo.from_dict should accept valid ISO 8601 timestamps without timezone."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-12-31T23:59:59.999999",
        })
        assert todo.created_at == "2024-01-01T00:00:00"
        assert todo.updated_at == "2024-12-31T23:59:59.999999"

    def test_todo_from_dict_accepts_empty_string_timestamp(self) -> None:
        """Todo.from_dict should accept empty string (will be auto-filled)."""
        todo = Todo.from_dict({
            "id": 1,
            "text": "task",
            "created_at": "",
            "updated_at": "",
        })
        # Empty strings get auto-filled by __post_init__
        assert todo.created_at != ""
        assert todo.updated_at != ""

    def test_todo_from_dict_accepts_missing_timestamp(self) -> None:
        """Todo.from_dict should accept missing timestamps (will be auto-filled)."""
        todo = Todo.from_dict({"id": 1, "text": "task"})
        # Missing timestamps get auto-filled by __post_init__
        assert todo.created_at != ""
        assert todo.updated_at != ""

    def test_todo_from_dict_rejects_invalid_created_at_format(self) -> None:
        """Todo.from_dict should reject non-ISO format for created_at."""
        with pytest.raises(ValueError, match=r"invalid.*'created_at'|'created_at'.*ISO|'created_at'.*format"):
            Todo.from_dict({
                "id": 1,
                "text": "task",
                "created_at": "not-a-date",
            })

    def test_todo_from_dict_rejects_invalid_updated_at_format(self) -> None:
        """Todo.from_dict should reject non-ISO format for updated_at."""
        with pytest.raises(ValueError, match=r"invalid.*'updated_at'|'updated_at'.*ISO|'updated_at'.*format"):
            Todo.from_dict({
                "id": 1,
                "text": "task",
                "updated_at": "01/01/2024",
            })

    def test_todo_from_dict_rejects_simple_date_without_time(self) -> None:
        """Todo.from_dict should reject date-only format (must include time)."""
        with pytest.raises(ValueError, match=r"Invalid.*'created_at'|'created_at'.*ISO"):
            Todo.from_dict({
                "id": 1,
                "text": "task",
                "created_at": "2024-01-01",
            })

    def test_todo_from_dict_rejects_loose_date_string(self) -> None:
        """Todo.from_dict should reject loosely formatted date strings."""
        with pytest.raises(ValueError, match=r"Invalid.*'created_at'|'created_at'.*ISO"):
            Todo.from_dict({
                "id": 1,
                "text": "task",
                "created_at": "Jan 1, 2024",
            })
