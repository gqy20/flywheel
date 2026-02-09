"""Tests for due date feature (issue #2483)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Test due_date field exists and is properly serialized."""

    def test_todo_has_due_date_field(self) -> None:
        todo = Todo(id=1, text="Test todo")
        assert hasattr(todo, "due_date")
        assert todo.due_date is None

    def test_todo_due_date_can_be_set(self) -> None:
        todo = Todo(id=1, text="Test todo", due_date="2025-12-25")
        assert todo.due_date == "2025-12-25"

    def test_todo_to_dict_includes_due_date(self) -> None:
        todo = Todo(id=1, text="Test todo", due_date="2025-12-25")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] == "2025-12-25"

    def test_todo_from_dict_restores_due_date(self) -> None:
        data = {
            "id": 1,
            "text": "Test todo",
            "done": False,
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
            "due_date": "2025-12-25",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == "2025-12-25"

    def test_todo_from_dict_handles_missing_due_date(self) -> None:
        data = {
            "id": 1,
            "text": "Test todo",
            "done": False,
        }
        todo = Todo.from_dict(data)
        assert todo.due_date is None


class TestSetDueDateMethod:
    """Test set_due_date method with ISO date validation."""

    def test_set_due_date_with_valid_iso_date(self) -> None:
        todo = Todo(id=1, text="Test todo")
        todo.set_due_date("2025-12-25")
        assert todo.due_date == "2025-12-25"

    def test_set_due_date_with_invalid_format_raises_value_error(self) -> None:
        todo = Todo(id=1, text="Test todo")
        with pytest.raises(ValueError, match="Invalid due date format"):
            todo.set_due_date("25-12-2025")

    def test_set_due_date_with_non_date_string_raises_value_error(self) -> None:
        todo = Todo(id=1, text="Test todo")
        with pytest.raises(ValueError, match="Invalid due date format"):
            todo.set_due_date("not a date")

    def test_set_due_date_updates_timestamp(self) -> None:
        todo = Todo(id=1, text="Test todo")
        original_updated = todo.updated_at
        todo.set_due_date("2025-12-25")
        assert todo.updated_at != original_updated

    def test_set_due_date_to_clears_existing(self) -> None:
        todo = Todo(id=1, text="Test todo", due_date="2025-12-25")
        todo.set_due_date(None)
        assert todo.due_date is None


class TestIsOverdueProperty:
    """Test is_overdue property logic."""

    def test_pending_todo_past_due_date_is_overdue(self) -> None:
        """A pending todo with a due date in the past is overdue."""
        past_date = (date.today() - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Test todo", due_date=past_date, done=False)
        assert todo.is_overdue is True

    def test_pending_todo_today_is_not_overdue(self) -> None:
        """A pending todo due today is not considered overdue."""
        today = date.today().isoformat()
        todo = Todo(id=1, text="Test todo", due_date=today, done=False)
        assert todo.is_overdue is False

    def test_pending_todo_future_date_is_not_overdue(self) -> None:
        """A pending todo with a future due date is not overdue."""
        future_date = (date.today() + timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Test todo", due_date=future_date, done=False)
        assert todo.is_overdue is False

    def test_completed_todo_is_never_overdue(self) -> None:
        """A completed todo is never considered overdue."""
        past_date = (date.today() - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Test todo", due_date=past_date, done=True)
        assert todo.is_overdue is False

    def test_todo_without_due_date_is_not_overdue(self) -> None:
        """A todo without a due date is not overdue."""
        todo = Todo(id=1, text="Test todo", done=False)
        assert todo.is_overdue is False


class TestCLIDueOption:
    """Test CLI --due option."""

    def test_add_command_accepts_due_argument(self) -> None:
        """Verify the add command parser accepts --due argument."""
        from flywheel.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["add", "Buy milk", "--due", "2025-12-25"])
        assert args.command == "add"
        assert args.text == "Buy milk"
        assert args.due == "2025-12-25"

    def test_due_command_exists(self) -> None:
        """Verify the 'due' subcommand exists."""
        from flywheel.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["due", "1", "2025-12-25"])
        assert args.command == "due"
        assert args.id == 1
        assert args.date == "2025-12-25"


class TestFormatterDueDateDisplay:
    """Test formatter displays due dates and overdue indicators."""

    def test_formatter_shows_overdue_indicator(self) -> None:
        """Overdue todos should show [OVERDUE] in their output."""
        from flywheel.formatter import TodoFormatter

        past_date = (date.today() - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Buy milk", due_date=past_date, done=False)
        output = TodoFormatter.format_todo(todo)
        assert "[OVERDUE]" in output

    def test_formatter_shows_due_date_for_pending_todos(self) -> None:
        """Pending todos with due dates should show the date."""
        from flywheel.formatter import TodoFormatter

        # Use a future date to avoid it being marked as overdue
        future_date = (date.today() + timedelta(days=7)).isoformat()
        todo = Todo(id=1, text="Buy milk", due_date=future_date, done=False)
        output = TodoFormatter.format_todo(todo)
        assert future_date in output

    def test_formatter_does_not_show_due_date_for_completed_todos(self) -> None:
        """Completed todos don't need to show the due date."""
        from flywheel.formatter import TodoFormatter

        todo = Todo(id=1, text="Buy milk", due_date="2025-12-25", done=True)
        output = TodoFormatter.format_todo(todo)
        # Completed todos don't show due date since they're done
        # The date is still in the data but not shown in list view
        assert "2025-12-25" not in output
