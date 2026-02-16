"""Tests for Todo due_date field (Issue #3765).

These tests verify that:
1. Todo instances support due_date field (optional, default empty string)
2. is_overdue() method correctly determines if current time exceeds due_date
3. from_dict/to_dict correctly handle due_date field
"""

from __future__ import annotations

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Tests for the due_date field on Todo."""

    def test_todo_has_due_date_field(self) -> None:
        """Todo should have a due_date field."""
        todo = Todo(id=1, text="test task", due_date="2025-01-01T00:00:00")
        assert todo.due_date == "2025-01-01T00:00:00"

    def test_due_date_defaults_to_empty_string(self) -> None:
        """due_date should default to empty string."""
        todo = Todo(id=1, text="test task")
        assert todo.due_date == ""

    def test_due_date_can_be_set_to_future_date(self) -> None:
        """due_date can be set to a future date."""
        todo = Todo(id=1, text="test task", due_date="2099-12-31T23:59:59")
        assert todo.due_date == "2099-12-31T23:59:59"


class TestTodoIsOverdue:
    """Tests for the is_overdue() method on Todo."""

    def test_is_overdue_returns_true_for_past_date(self) -> None:
        """is_overdue() should return True for a past due_date."""
        todo = Todo(id=1, text="test task", due_date="2025-01-01T00:00:00")
        assert todo.is_overdue() is True

    def test_is_overdue_returns_false_for_future_date(self) -> None:
        """is_overdue() should return False for a future due_date."""
        todo = Todo(id=1, text="test task", due_date="2099-12-31T23:59:59")
        assert todo.is_overdue() is False

    def test_is_overdue_returns_false_for_no_due_date(self) -> None:
        """is_overdue() should return False when no due_date is set."""
        todo = Todo(id=1, text="test task")
        assert todo.is_overdue() is False


class TestTodoDueDateSerialization:
    """Tests for due_date field serialization/deserialization."""

    def test_to_dict_includes_due_date(self) -> None:
        """to_dict() should include due_date field."""
        todo = Todo(id=1, text="test task", due_date="2025-06-01T12:00:00")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] == "2025-06-01T12:00:00"

    def test_from_dict_handles_due_date(self) -> None:
        """from_dict() should correctly handle due_date field."""
        data = {
            "id": 1,
            "text": "test task",
            "done": False,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "due_date": "2025-06-01T12:00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == "2025-06-01T12:00:00"

    def test_from_dict_handles_missing_due_date(self) -> None:
        """from_dict() should handle missing due_date (default to empty string)."""
        data = {
            "id": 1,
            "text": "test task",
            "done": False,
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == ""
