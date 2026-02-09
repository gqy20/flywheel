"""Tests for Issue #2483: Due date/deadline field in Todo model."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Test Todo model due_date field functionality."""

    def test_todo_accepts_due_date_field(self) -> None:
        """Todo dataclass should accept due_date field with ISO date string."""
        todo = Todo(id=1, text="task with deadline", due_date="2026-02-15")
        assert todo.due_date == "2026-02-15"

    def test_todo_due_date_defaults_to_none(self) -> None:
        """Todo dataclass should default due_date to None when not provided."""
        todo = Todo(id=1, text="task without deadline")
        assert todo.due_date is None

    def test_set_due_date_accepts_valid_iso_date(self) -> None:
        """Todo.set_due_date() should accept valid ISO date format (YYYY-MM-DD)."""
        todo = Todo(id=1, text="task")
        todo.set_due_date("2026-02-15")
        assert todo.due_date == "2026-02-15"

    def test_set_due_date_raises_value_error_for_invalid_format(self) -> None:
        """Todo.set_due_date() should raise ValueError for invalid date formats."""
        todo = Todo(id=1, text="task")

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("2026/02/15")  # Wrong separator

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("02-15-2026")  # Wrong order

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("2026-02-15T12:00:00")  # Full datetime, not date

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("invalid")  # Complete garbage

    def test_set_due_date_raises_value_error_for_invalid_date(self) -> None:
        """Todo.set_due_date() should raise ValueError for invalid dates."""
        todo = Todo(id=1, text="task")

        with pytest.raises(ValueError, match="Invalid date"):
            todo.set_due_date("2026-02-30")  # February 30th doesn't exist

        with pytest.raises(ValueError, match="Invalid date"):
            todo.set_due_date("2026-13-01")  # Month 13 doesn't exist

        with pytest.raises(ValueError, match="Invalid date"):
            todo.set_due_date("2026-00-01")  # Month 00 doesn't exist

    def test_is_overdue_returns_true_for_past_due_incomplete_task(self) -> None:
        """Todo.is_overdue should return True for past-due incomplete tasks."""
        # Create a todo with a due date in the past
        past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="overdue task", due_date=past_date, done=False)

        assert todo.is_overdue is True

    def test_is_overdue_returns_false_for_completed_task(self) -> None:
        """Todo.is_overdue should return False for completed tasks regardless of due_date."""
        # Create a completed todo with a due date in the past
        past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="completed task", due_date=past_date, done=True)

        assert todo.is_overdue is False

    def test_is_overdue_returns_false_for_future_due_date(self) -> None:
        """Todo.is_overdue should return False for tasks with future due dates."""
        # Create a todo with a due date in the future
        future_date = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="future task", due_date=future_date, done=False)

        assert todo.is_overdue is False

    def test_is_overdue_returns_false_when_due_date_is_none(self) -> None:
        """Todo.is_overdue should return False when due_date is None."""
        todo = Todo(id=1, text="task without deadline", due_date=None)

        assert todo.is_overdue is False

    def test_is_overdue_returns_false_for_today(self) -> None:
        """Todo.is_overdue should return False for tasks due today."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="task due today", due_date=today, done=False)

        assert todo.is_overdue is False

    def test_set_due_date_updates_timestamp(self) -> None:
        """Todo.set_due_date() should update the updated_at timestamp."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        todo.set_due_date("2026-02-15")

        assert todo.updated_at > original_updated_at

    def test_from_dict_handles_due_date_field(self) -> None:
        """Todo.from_dict() should deserialize due_date field correctly."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
            "due_date": "2026-02-15",
            "created_at": "2026-02-09T12:00:00+00:00",
            "updated_at": "2026-02-09T12:00:00+00:00",
        }

        todo = Todo.from_dict(data)
        assert todo.due_date == "2026-02-15"

    def test_from_dict_validates_due_date_format(self) -> None:
        """Todo.from_dict() should validate due_date format when provided."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
            "due_date": "2026/02/15",  # Invalid format
        }

        with pytest.raises(ValueError, match="Invalid date format"):
            Todo.from_dict(data)

    def test_from_dict_accepts_none_due_date(self) -> None:
        """Todo.from_dict() should accept None for due_date."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
            "due_date": None,
        }

        todo = Todo.from_dict(data)
        assert todo.due_date is None

    def test_from_dict_accepts_missing_due_date(self) -> None:
        """Todo.from_dict() should handle missing due_date field (backward compat)."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
        }

        todo = Todo.from_dict(data)
        assert todo.due_date is None

    def test_to_dict_includes_due_date_field(self) -> None:
        """Todo.to_dict() should serialize due_date field."""
        todo = Todo(id=1, text="task", due_date="2026-02-15")
        data = todo.to_dict()

        assert "due_date" in data
        assert data["due_date"] == "2026-02-15"

    def test_to_dict_includes_none_due_date(self) -> None:
        """Todo.to_dict() should include due_date even when None."""
        todo = Todo(id=1, text="task", due_date=None)
        data = todo.to_dict()

        assert "due_date" in data
        assert data["due_date"] is None
