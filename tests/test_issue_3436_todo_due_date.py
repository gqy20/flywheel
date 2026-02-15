"""Tests for issue #3436: Add due_date field to Todo data model."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Tests for the due_date field on Todo."""

    def test_todo_created_with_no_due_date_defaults_to_empty_string(self) -> None:
        """A new Todo should have an empty string for due_date by default."""
        todo = Todo(id=1, text="task without deadline")
        assert todo.due_date == ""

    def test_todo_can_be_created_with_due_date(self) -> None:
        """A Todo can be initialized with a due_date."""
        due = "2026-03-15T12:00:00+00:00"
        todo = Todo(id=1, text="task with deadline", due_date=due)
        assert todo.due_date == due


class TestSetDueDateMethod:
    """Tests for the set_due_date() method."""

    def test_set_due_date_with_valid_iso_string(self) -> None:
        """set_due_date() should accept valid ISO 8601 date strings."""
        todo = Todo(id=1, text="task")
        due = "2026-03-15T12:00:00+00:00"
        todo.set_due_date(due)
        assert todo.due_date == due

    def test_set_due_date_updates_updated_at(self) -> None:
        """set_due_date() should update the updated_at timestamp."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at
        todo.set_due_date("2026-03-15T12:00:00+00:00")
        assert todo.updated_at != original_updated_at

    def test_set_due_date_with_invalid_format_raises_value_error(self) -> None:
        """set_due_date() should raise ValueError for invalid date format."""
        todo = Todo(id=1, text="task")
        with pytest.raises(ValueError, match=r"Invalid.*date.*format"):
            todo.set_due_date("not-a-date")

    def test_set_due_date_with_empty_string_clears_due_date(self) -> None:
        """set_due_date('') should clear the due_date."""
        todo = Todo(id=1, text="task", due_date="2026-03-15T12:00:00+00:00")
        todo.set_due_date("")
        assert todo.due_date == ""

    def test_set_due_date_accepts_date_only_format(self) -> None:
        """set_due_date() should accept date-only ISO format (YYYY-MM-DD)."""
        todo = Todo(id=1, text="task")
        todo.set_due_date("2026-03-15")
        assert todo.due_date == "2026-03-15"


class TestIsOverdueProperty:
    """Tests for the is_overdue property."""

    def test_is_overdue_returns_none_when_no_due_date(self) -> None:
        """is_overdue should return None when due_date is not set."""
        todo = Todo(id=1, text="task")
        assert todo.is_overdue is None

    def test_is_overdue_returns_false_for_future_date(self) -> None:
        """is_overdue should return False when due_date is in the future."""
        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        todo = Todo(id=1, text="task", due_date=future)
        assert todo.is_overdue is False

    def test_is_overdue_returns_true_for_past_date(self) -> None:
        """is_overdue should return True when due_date is in the past."""
        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="task", due_date=past)
        assert todo.is_overdue is True

    def test_is_overdue_returns_false_for_today(self) -> None:
        """is_overdue should return False when due_date is today."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="task", due_date=today)
        assert todo.is_overdue is False


class TestDueDateSerialization:
    """Tests for due_date in serialization (from_dict/to_dict)."""

    def test_to_dict_includes_due_date(self) -> None:
        """to_dict() should include the due_date field."""
        todo = Todo(id=1, text="task", due_date="2026-03-15T12:00:00+00:00")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] == "2026-03-15T12:00:00+00:00"

    def test_from_dict_handles_due_date(self) -> None:
        """from_dict() should properly load the due_date field."""
        data = {"id": 1, "text": "task", "due_date": "2026-03-15T12:00:00+00:00"}
        todo = Todo.from_dict(data)
        assert todo.due_date == "2026-03-15T12:00:00+00:00"

    def test_from_dict_handles_missing_due_date(self) -> None:
        """from_dict() should default to empty string if due_date is missing."""
        data = {"id": 1, "text": "task"}
        todo = Todo.from_dict(data)
        assert todo.due_date == ""

    def test_roundtrip_preserves_due_date(self) -> None:
        """A full roundtrip through to_dict/from_dict should preserve due_date."""
        original = Todo(id=1, text="task", due_date="2026-03-15T12:00:00+00:00")
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.due_date == original.due_date
