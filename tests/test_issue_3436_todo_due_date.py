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
    """Tests for due_date field existence and default value."""

    def test_todo_has_due_date_field_with_default_empty(self) -> None:
        """Todo should include due_date field with empty string default."""
        todo = Todo(id=1, text="task")
        assert hasattr(todo, "due_date")
        assert todo.due_date == ""

    def test_todo_can_be_created_with_due_date(self) -> None:
        """Todo should accept due_date during creation."""
        todo = Todo(id=1, text="task", due_date="2026-03-15T10:00:00+00:00")
        assert todo.due_date == "2026-03-15T10:00:00+00:00"


class TestTodoSetDueDate:
    """Tests for set_due_date method."""

    def test_set_due_date_with_valid_iso_string(self) -> None:
        """set_due_date should accept valid ISO 8601 date strings."""
        todo = Todo(id=1, text="task")
        todo.set_due_date("2026-03-15T10:00:00+00:00")
        assert todo.due_date == "2026-03-15T10:00:00+00:00"

    def test_set_due_date_updates_updated_at(self) -> None:
        """set_due_date should update updated_at timestamp."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at
        todo.set_due_date("2026-03-15T10:00:00+00:00")
        assert todo.updated_at >= original_updated_at

    def test_set_due_date_rejects_invalid_format(self) -> None:
        """set_due_date should raise ValueError for invalid date format."""
        todo = Todo(id=1, text="task")
        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("not-a-date")

    def test_set_due_date_rejects_non_iso_format(self) -> None:
        """set_due_date should raise ValueError for non-ISO format."""
        todo = Todo(id=1, text="task")
        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("03/15/2026")


class TestTodoIsOverdue:
    """Tests for is_overdue property."""

    def test_is_overdue_returns_none_when_no_due_date(self) -> None:
        """is_overdue should return None when no due_date is set."""
        todo = Todo(id=1, text="task")
        assert todo.is_overdue is None

    def test_is_overdue_returns_false_for_future_date(self) -> None:
        """is_overdue should return False for due_date in the future."""
        future_date = datetime.now(UTC) + timedelta(days=7)
        todo = Todo(id=1, text="task", due_date=future_date.isoformat())
        assert todo.is_overdue is False

    def test_is_overdue_returns_true_for_past_date(self) -> None:
        """is_overdue should return True for due_date in the past."""
        past_date = datetime.now(UTC) - timedelta(days=1)
        todo = Todo(id=1, text="task", due_date=past_date.isoformat())
        assert todo.is_overdue is True

    def test_is_overdue_returns_false_for_today(self) -> None:
        """is_overdue should return False for due_date set to today."""
        today = datetime.now(UTC) + timedelta(hours=12)
        todo = Todo(id=1, text="task", due_date=today.isoformat())
        assert todo.is_overdue is False


class TestTodoDueDateSerialization:
    """Tests for due_date in serialization (from_dict/to_dict)."""

    def test_to_dict_includes_due_date(self) -> None:
        """to_dict should include due_date field."""
        todo = Todo(id=1, text="task", due_date="2026-03-15T10:00:00+00:00")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] == "2026-03-15T10:00:00+00:00"

    def test_to_dict_includes_empty_due_date(self) -> None:
        """to_dict should include due_date field even when empty."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] == ""

    def test_from_dict_handles_due_date(self) -> None:
        """from_dict should populate due_date from data."""
        data = {"id": 1, "text": "task", "due_date": "2026-03-15T10:00:00+00:00"}
        todo = Todo.from_dict(data)
        assert todo.due_date == "2026-03-15T10:00:00+00:00"

    def test_from_dict_handles_missing_due_date(self) -> None:
        """from_dict should default due_date to empty string when missing."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)
        assert todo.due_date == ""

    def test_roundtrip_preserves_due_date(self) -> None:
        """Serialization roundtrip should preserve due_date."""
        original = Todo(id=1, text="task", due_date="2026-03-15T10:00:00+00:00")
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.due_date == original.due_date
