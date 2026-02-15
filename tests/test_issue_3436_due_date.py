"""Tests for Todo due_date field (Issue #3436).

These tests verify that:
1. Todo dataclass includes optional due_date field (empty string by default)
2. Todo.set_due_date(date_str) validates ISO format and updates
3. Todo.is_overdue property returns bool (None if no due_date)
4. from_dict/to_dict handle due_date
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Tests for the due_date field in Todo dataclass."""

    def test_todo_has_due_date_field_with_default_empty_string(self) -> None:
        """Todo should have a due_date field that defaults to empty string."""
        todo = Todo(id=1, text="task without due date")
        assert hasattr(todo, "due_date")
        assert todo.due_date == ""

    def test_todo_can_be_created_with_due_date(self) -> None:
        """Todo should accept a due_date value during creation."""
        todo = Todo(id=1, text="task with due date", due_date="2026-03-15T12:00:00+00:00")
        assert todo.due_date == "2026-03-15T12:00:00+00:00"


class TestSetDueDate:
    """Tests for the set_due_date() method."""

    def test_set_due_date_with_valid_iso_string(self) -> None:
        """set_due_date() should accept valid ISO 8601 date strings."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        todo.set_due_date("2026-03-15T12:00:00+00:00")
        assert todo.due_date == "2026-03-15T12:00:00+00:00"
        assert todo.updated_at != original_updated_at

    def test_set_due_date_with_valid_iso_string_utc_suffix(self) -> None:
        """set_due_date() should accept ISO strings with Z suffix."""
        todo = Todo(id=1, text="task")

        todo.set_due_date("2026-03-15T12:00:00Z")
        assert todo.due_date == "2026-03-15T12:00:00Z"

    def test_set_due_date_updates_updated_at(self) -> None:
        """set_due_date() should update the updated_at timestamp."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        todo.set_due_date("2026-03-15T12:00:00+00:00")
        assert todo.updated_at >= original_updated_at

    def test_set_due_date_rejects_invalid_format(self) -> None:
        """set_due_date() should raise ValueError for invalid date formats."""
        todo = Todo(id=1, text="task")

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("not-a-date")

    def test_set_due_date_rejects_non_string(self) -> None:
        """set_due_date() should raise TypeError for non-string input."""
        todo = Todo(id=1, text="task")

        with pytest.raises(TypeError):
            todo.set_due_date(12345)

    def test_set_due_date_can_clear_with_empty_string(self) -> None:
        """set_due_date() should accept empty string to clear due date."""
        todo = Todo(id=1, text="task", due_date="2026-03-15T12:00:00+00:00")

        todo.set_due_date("")
        assert todo.due_date == ""


class TestIsOverdue:
    """Tests for the is_overdue property."""

    def test_is_overdue_returns_none_when_no_due_date(self) -> None:
        """is_overdue should return None when no due_date is set."""
        todo = Todo(id=1, text="task without due date")
        assert todo.is_overdue is None

    def test_is_overdue_returns_false_for_future_date(self) -> None:
        """is_overdue should return False for dates in the future."""
        future_date = datetime.now(UTC) + timedelta(days=7)
        todo = Todo(id=1, text="future task", due_date=future_date.isoformat())
        assert todo.is_overdue is False

    def test_is_overdue_returns_true_for_past_date(self) -> None:
        """is_overdue should return True for dates in the past."""
        past_date = datetime.now(UTC) - timedelta(days=1)
        todo = Todo(id=1, text="overdue task", due_date=past_date.isoformat())
        assert todo.is_overdue is True

    def test_is_overdue_returns_false_for_soon(self) -> None:
        """is_overdue should return False for dates slightly in the future."""
        future_date = datetime.now(UTC) + timedelta(hours=1)
        todo = Todo(id=1, text="task due in an hour", due_date=future_date.isoformat())
        assert todo.is_overdue is False


class TestDueDateSerialization:
    """Tests for from_dict/to_dict handling of due_date."""

    def test_to_dict_includes_due_date(self) -> None:
        """to_dict() should include the due_date field."""
        todo = Todo(id=1, text="task", due_date="2026-03-15T12:00:00+00:00")
        data = todo.to_dict()

        assert "due_date" in data
        assert data["due_date"] == "2026-03-15T12:00:00+00:00"

    def test_to_dict_includes_empty_due_date(self) -> None:
        """to_dict() should include due_date even when empty."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()

        assert "due_date" in data
        assert data["due_date"] == ""

    def test_from_dict_with_due_date(self) -> None:
        """from_dict() should parse due_date from data."""
        data = {"id": 1, "text": "task", "due_date": "2026-03-15T12:00:00+00:00"}
        todo = Todo.from_dict(data)

        assert todo.due_date == "2026-03-15T12:00:00+00:00"

    def test_from_dict_without_due_date(self) -> None:
        """from_dict() should handle missing due_date gracefully."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)

        assert todo.due_date == ""

    def test_roundtrip_preserves_due_date(self) -> None:
        """to_dict() -> from_dict() should preserve due_date."""
        original = Todo(id=1, text="task", due_date="2026-03-15T12:00:00+00:00")
        data = original.to_dict()
        restored = Todo.from_dict(data)

        assert restored.due_date == original.due_date
