"""Tests for Issue #2483: CLI integration for due date functionality."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.formatter import TodoFormatter
from flywheel.todo import Todo


class TestCLIDueDateIntegration:
    """Test CLI integration for due date functionality."""

    def test_cli_add_with_due_flag(self, tmp_path, capsys) -> None:
        """CLI `add --due <date>` should create todo with due_date set."""
        db = str(tmp_path / "test.json")
        parser = build_parser()

        # Add todo with due date
        args = parser.parse_args(["--db", db, "add", "--due", "2026-02-15", "task with deadline"])
        assert run_command(args) == 0

        # Verify todo was created with due date
        app = TodoApp(db)
        todos = app.list()
        assert len(todos) == 1
        assert todos[0].due_date == "2026-02-15"

    def test_cli_add_without_due_flag(self, tmp_path, capsys) -> None:
        """CLI `add` without --due flag should create todo without due_date."""
        db = str(tmp_path / "test.json")
        parser = build_parser()

        # Add todo without due date
        args = parser.parse_args(["--db", db, "add", "normal task"])
        assert run_command(args) == 0

        # Verify todo was created without due date
        app = TodoApp(db)
        todos = app.list()
        assert len(todos) == 1
        assert todos[0].due_date is None

    def test_cli_due_command_sets_due_date(self, tmp_path, capsys) -> None:
        """CLI `due <id> <date>` command should set due_date on existing todo."""
        db = str(tmp_path / "test.json")
        parser = build_parser()

        # First add a todo
        args = parser.parse_args(["--db", db, "add", "task"])
        assert run_command(args) == 0

        # Set due date using due command
        args = parser.parse_args(["--db", db, "due", "1", "2026-02-15"])
        assert run_command(args) == 0

        # Verify due date was set
        app = TodoApp(db)
        todos = app.list()
        assert todos[0].due_date == "2026-02-15"

    def test_cli_due_command_validates_date_format(self, tmp_path, capsys) -> None:
        """CLI `due` command should validate date format."""
        db = str(tmp_path / "test.json")
        parser = build_parser()

        # Add a todo
        args = parser.parse_args(["--db", db, "add", "task"])
        assert run_command(args) == 0

        # Try to set invalid date format
        args = parser.parse_args(["--db", db, "due", "1", "2026/02/15"])
        result = run_command(args)

        # Should return error
        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid date format" in captured.out or "Invalid date format" in captured.err

    def test_cli_list_shows_overdue_indicator(self, tmp_path, capsys) -> None:
        """CLI list should show [OVERDUE] indicator for overdue tasks."""
        db = str(tmp_path / "test.json")
        parser = build_parser()

        # Create an overdue todo
        past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        args = parser.parse_args(["--db", db, "add", "--due", past_date, "overdue task"])
        assert run_command(args) == 0

        # List todos
        args = parser.parse_args(["--db", db, "list"])
        assert run_command(args) == 0

        captured = capsys.readouterr()
        # Should show OVERDUE indicator
        assert "OVERDUE" in captured.out

    def test_cli_list_shows_due_date(self, tmp_path, capsys) -> None:
        """CLI list should show due date for tasks with due_date."""
        db = str(tmp_path / "test.json")
        parser = build_parser()

        # Create todo with future due date
        args = parser.parse_args(["--db", db, "add", "--due", "2026-12-25", "holiday task"])
        assert run_command(args) == 0

        # List todos
        args = parser.parse_args(["--db", db, "list"])
        assert run_command(args) == 0

        captured = capsys.readouterr()
        # Should show the due date
        assert "2026-12-25" in captured.out

    def test_todo_formatter_format_todo_includes_due_date(self) -> None:
        """TodoFormatter.format_todo should include due date in output."""
        todo = Todo(id=1, text="task", due_date="2026-02-15")
        formatted = TodoFormatter.format_todo(todo)

        assert "2026-02-15" in formatted

    def test_todo_formatter_format_todo_shows_overdue_indicator(self) -> None:
        """TodoFormatter.format_todo should show [OVERDUE] for overdue tasks."""
        # Create an overdue todo
        past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="overdue task", due_date=past_date, done=False)

        formatted = TodoFormatter.format_todo(todo)

        assert "[OVERDUE]" in formatted

    def test_todo_formatter_format_todo_no_overdue_for_completed(self) -> None:
        """TodoFormatter.format_todo should not show OVERDUE for completed tasks."""
        # Create a completed todo with past due date
        past_date = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        todo = Todo(id=1, text="completed task", due_date=past_date, done=True)

        formatted = TodoFormatter.format_todo(todo)

        # Should show x status but not OVERDUE
        assert "[x]" in formatted
        assert "[OVERDUE]" not in formatted
