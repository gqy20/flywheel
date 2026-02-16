"""Regression tests for issue #3765: Add due_date field to Todo dataclass."""

from datetime import UTC, datetime, timedelta

import pytest

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Tests for the due_date field on Todo."""

    def test_todo_has_due_date_field(self) -> None:
        """Todo instances should have a due_date attribute."""
        todo = Todo(id=1, text="Test todo")
        assert hasattr(todo, "due_date")

    def test_todo_due_date_default_empty(self) -> None:
        """The due_date field should default to an empty string."""
        todo = Todo(id=1, text="Test todo")
        assert todo.due_date == ""

    def test_todo_due_date_can_be_set(self) -> None:
        """The due_date field should accept a valid ISO date string."""
        due_date = "2024-12-31T23:59:59+00:00"
        todo = Todo(id=1, text="Test todo", due_date=due_date)
        assert todo.due_date == due_date


class TestTodoIsOverdue:
    """Tests for the is_overdue() method on Todo."""

    def test_todo_is_overdue_expired(self) -> None:
        """is_overdue() should return True when due_date is in the past."""
        # Set due_date to 1 hour in the past
        past_time = datetime.now(UTC) - timedelta(hours=1)
        todo = Todo(id=1, text="Overdue todo", due_date=past_time.isoformat())
        assert todo.is_overdue() is True

    def test_todo_is_overdue_not_expired(self) -> None:
        """is_overdue() should return False when due_date is in the future."""
        # Set due_date to 1 hour in the future
        future_time = datetime.now(UTC) + timedelta(hours=1)
        todo = Todo(id=1, text="Future todo", due_date=future_time.isoformat())
        assert todo.is_overdue() is False

    def test_todo_is_overdue_no_due_date(self) -> None:
        """is_overdue() should return False when due_date is empty."""
        todo = Todo(id=1, text="No due date", due_date="")
        assert todo.is_overdue() is False

    def test_todo_is_overdue_invalid_date_string(self) -> None:
        """is_overdue() should return False for invalid date strings."""
        todo = Todo(id=1, text="Invalid date", due_date="not-a-date")
        assert todo.is_overdue() is False


class TestTodoSerialization:
    """Tests for serialization and deserialization of due_date."""

    def test_todo_to_dict_includes_due_date(self) -> None:
        """to_dict() should include the due_date field."""
        due_date = "2024-12-31T23:59:59+00:00"
        todo = Todo(id=1, text="Test todo", due_date=due_date)
        result = todo.to_dict()
        assert "due_date" in result
        assert result["due_date"] == due_date

    def test_todo_from_dict_parses_due_date(self) -> None:
        """from_dict() should correctly parse the due_date field."""
        data = {
            "id": 1,
            "text": "Test todo",
            "due_date": "2024-12-31T23:59:59+00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == "2024-12-31T23:59:59+00:00"

    def test_todo_from_dict_missing_due_date_defaults_empty(self) -> None:
        """from_dict() should default due_date to empty string when missing."""
        data = {
            "id": 1,
            "text": "Test todo",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == ""

    def test_todo_roundtrip_preserves_due_date(self) -> None:
        """Roundtrip through to_dict/from_dict should preserve due_date."""
        original = Todo(id=1, text="Test todo", due_date="2024-12-31T23:59:59+00:00")
        data = original.to_dict()
        restored = Todo.from_dict(data)
        assert restored.due_date == original.due_date
