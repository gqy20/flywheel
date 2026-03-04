"""Tests for None timestamp handling in Todo.from_dict (Issue #7190).

These tests verify that:
1. Todo.from_dict with created_at=None generates a new timestamp
2. Todo.from_dict with created_at='' generates a new timestamp
3. Todo.from_dict with valid timestamp preserves the value
4. Todo.from_dict with literal string 'None' generates a new timestamp (robustness)
"""

from __future__ import annotations

from datetime import datetime

from flywheel.todo import Todo


def is_valid_iso_timestamp(value: str) -> bool:
    """Check if a string is a valid ISO format timestamp."""
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


class TestTodoFromDictNoneTimestamp:
    """Test suite for None timestamp handling."""

    def test_from_dict_with_none_created_at_generates_timestamp(self) -> None:
        """Todo.from_dict with created_at=None should generate a new timestamp."""
        todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None})

        assert todo.created_at != "None", "Should not store literal string 'None'"
        assert todo.created_at != "", "Should not store empty string"
        assert is_valid_iso_timestamp(todo.created_at), (
            f"Should be valid ISO timestamp, got: {todo.created_at!r}"
        )

    def test_from_dict_with_none_updated_at_uses_created_at(self) -> None:
        """Todo.from_dict with updated_at=None should use created_at."""
        todo = Todo.from_dict(
            {"id": 1, "text": "test", "created_at": "2020-01-01T00:00:00", "updated_at": None}
        )

        assert todo.updated_at == todo.created_at, "updated_at should equal created_at"

    def test_from_dict_with_empty_string_created_at_generates_timestamp(self) -> None:
        """Todo.from_dict with created_at='' should generate a new timestamp."""
        todo = Todo.from_dict({"id": 1, "text": "test", "created_at": ""})

        assert todo.created_at != "", "Should not store empty string"
        assert is_valid_iso_timestamp(todo.created_at), (
            f"Should be valid ISO timestamp, got: {todo.created_at!r}"
        )

    def test_from_dict_preserves_valid_timestamp(self) -> None:
        """Todo.from_dict with valid timestamp should preserve it."""
        expected = "2020-01-01T12:00:00+00:00"
        todo = Todo.from_dict({"id": 1, "text": "test", "created_at": expected})

        assert todo.created_at == expected, f"Should preserve timestamp, got: {todo.created_at!r}"

    def test_from_dict_with_literal_string_none_generates_timestamp(self) -> None:
        """Todo.from_dict with created_at='None' should generate a new timestamp.

        This handles corrupted data where str(None) was stored as 'None'.
        """
        todo = Todo.from_dict({"id": 1, "text": "test", "created_at": "None"})

        assert todo.created_at != "None", (
            "Should not preserve literal string 'None' from corrupted data"
        )
        assert is_valid_iso_timestamp(todo.created_at), (
            f"Should be valid ISO timestamp, got: {todo.created_at!r}"
        )

    def test_from_dict_with_both_timestamps_none(self) -> None:
        """Todo.from_dict with both timestamps as None should generate new ones."""
        todo = Todo.from_dict({"id": 1, "text": "test", "created_at": None, "updated_at": None})

        assert is_valid_iso_timestamp(todo.created_at), (
            f"created_at should be valid ISO timestamp, got: {todo.created_at!r}"
        )
        assert is_valid_iso_timestamp(todo.updated_at), (
            f"updated_at should be valid ISO timestamp, got: {todo.updated_at!r}"
        )
        assert todo.updated_at == todo.created_at, "updated_at should equal created_at"
