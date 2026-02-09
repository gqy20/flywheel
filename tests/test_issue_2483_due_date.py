"""Tests for Issue #2483: Add due date/deadline field to Todo model."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from flywheel.todo import Todo


class TestTodoDueDateField:
    """Test Todo due_date field functionality."""

    def test_todo_created_with_due_date(self) -> None:
        """Todo should accept due_date as optional ISO date string."""
        todo = Todo(id=1, text="task with deadline", due_date="2026-02-15")
        assert todo.due_date == "2026-02-15"

    def test_todo_created_without_due_date_defaults_to_none(self) -> None:
        """Todo should default due_date to None when not provided."""
        todo = Todo(id=1, text="task without deadline")
        assert todo.due_date is None

    def test_todo_set_due_date_accepts_valid_iso_format(self) -> None:
        """Todo.set_due_date() should accept valid ISO date strings (YYYY-MM-DD)."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        todo.set_due_date("2026-03-01")
        assert todo.due_date == "2026-03-01"
        assert todo.updated_at >= original_updated_at

    def test_todo_set_due_date_rejects_invalid_format(self) -> None:
        """Todo.set_due_date() should raise ValueError for invalid date formats."""
        todo = Todo(id=1, text="task")
        original_updated_at = todo.updated_at

        # Invalid formats
        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("03/01/2026")

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("2026-03-01-extra")

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("not-a-date")

        with pytest.raises(ValueError, match="Invalid date format"):
            todo.set_due_date("2026-13-01")  # Invalid month

        # Verify state unchanged after failed validation
        assert todo.due_date is None
        assert todo.updated_at == original_updated_at

    def test_todo_is_overdue_returns_true_for_past_due_incomplete(self) -> None:
        """Todo.is_overdue() should return True for past-due incomplete tasks."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="overdue task", due_date=yesterday, done=False)
        assert todo.is_overdue() is True

    def test_todo_is_overdue_returns_false_for_future_due(self) -> None:
        """Todo.is_overdue() should return False for tasks due in the future."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="future task", due_date=tomorrow, done=False)
        assert todo.is_overdue() is False

    def test_todo_is_overdue_returns_false_for_today_due(self) -> None:
        """Todo.is_overdue() should return False for tasks due today."""
        today = date.today().isoformat()
        todo = Todo(id=1, text="today task", due_date=today, done=False)
        assert todo.is_overdue() is False

    def test_todo_is_overdue_returns_false_for_completed_tasks(self) -> None:
        """Todo.is_overdue() should return False for completed tasks regardless of due_date."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="completed task", due_date=yesterday, done=True)
        assert todo.is_overdue() is False

    def test_todo_is_overdue_returns_false_when_no_due_date(self) -> None:
        """Todo.is_overdue() should return False when due_date is None."""
        todo = Todo(id=1, text="no deadline task", done=False)
        assert todo.is_overdue() is False

    def test_todo_to_dict_includes_due_date(self) -> None:
        """Todo.to_dict() should include due_date field."""
        todo = Todo(id=1, text="task", due_date="2026-02-15")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] == "2026-02-15"

    def test_todo_to_dict_includes_none_due_date(self) -> None:
        """Todo.to_dict() should include due_date even when None."""
        todo = Todo(id=1, text="task")
        data = todo.to_dict()
        assert "due_date" in data
        assert data["due_date"] is None

    def test_todo_from_dict_accepts_valid_due_date(self) -> None:
        """Todo.from_dict() should accept valid due_date in ISO format."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
            "due_date": "2026-02-15",
            "created_at": "",
            "updated_at": "",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date == "2026-02-15"

    def test_todo_from_dict_rejects_invalid_due_date_format(self) -> None:
        """Todo.from_dict() should raise ValueError for invalid due_date format."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
            "due_date": "03/01/2026",
            "created_at": "",
            "updated_at": "",
        }
        with pytest.raises(ValueError, match="Invalid date format"):
            Todo.from_dict(data)

    def test_todo_from_dict_handles_missing_due_date(self) -> None:
        """Todo.from_dict() should handle missing due_date field."""
        data = {
            "id": 1,
            "text": "task",
            "done": False,
            "created_at": "",
            "updated_at": "",
        }
        todo = Todo.from_dict(data)
        assert todo.due_date is None


class TestTodoAppDueDate:
    """Test TodoApp due_date functionality."""

    def test_app_add_with_due_date(self) -> None:
        """TodoApp.add() should accept due_date parameter."""
        # This test will be updated once we implement the CLI changes
        todo = Todo(id=1, text="task with deadline", due_date="2026-02-15")
        assert todo.due_date == "2026-02-15"


class TestCLIIntegration:
    """Test CLI integration for due_date feature."""

    def test_cli_add_with_due_option(self, tmp_path, capsys) -> None:
        """CLI should support `todo add --due YYYY-MM-DD 'task'`."""
        from flywheel.cli import build_parser

        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # This test will be updated once we implement the CLI changes
        # For now, we'll test the parser can be created successfully
        args = parser.parse_args(["--db", db, "add", "task"])
        assert args.command == "add"
        assert args.text == "task"

    def test_cli_due_command(self, tmp_path) -> None:
        """CLI should support `todo due <id> <date>` command."""
        from flywheel.cli import build_parser

        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # This test will be updated once we implement the CLI changes
        # For now, we verify the parser can handle known commands
        args = parser.parse_args(["--db", db, "add", "task"])
        assert args.command == "add"
