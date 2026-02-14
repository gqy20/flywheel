"""Regression tests for Issue #3338: Todo due_at field support.

This test file ensures that:
- Todo can accept due_at parameter (ISO format string or None)
- is_overdue() method correctly determines if current time is past due_at
- CLI supports todo set-due <id> <due_date> command
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flywheel.cli import TodoApp, build_parser, main
from flywheel.todo import Todo


class TestTodoDueAtField:
    """Tests for the due_at field on Todo."""

    def test_todo_due_at_optional(self) -> None:
        """Todo should have due_at field that defaults to None."""
        todo = Todo(id=1, text="Buy groceries")
        assert todo.due_at is None

    def test_todo_due_at_can_be_set(self) -> None:
        """Todo due_at can be set with an ISO format string."""
        due_date = "2026-03-15T10:00:00+00:00"
        todo = Todo(id=1, text="Submit report", due_at=due_date)
        assert todo.due_at == due_date

    def test_todo_from_dict_includes_due_at(self) -> None:
        """Todo.from_dict should handle due_at field."""
        data = {
            "id": 1,
            "text": "Task with due date",
            "done": False,
            "due_at": "2026-03-15T10:00:00+00:00",
        }
        todo = Todo.from_dict(data)
        assert todo.due_at == "2026-03-15T10:00:00+00:00"

    def test_todo_from_dict_handles_missing_due_at(self) -> None:
        """Todo.from_dict should handle missing due_at as None."""
        data = {
            "id": 1,
            "text": "Task without due date",
            "done": False,
        }
        todo = Todo.from_dict(data)
        assert todo.due_at is None

    def test_todo_to_dict_includes_due_at(self) -> None:
        """Todo.to_dict should include due_at field."""
        todo = Todo(id=1, text="Task", due_at="2026-03-15T10:00:00+00:00")
        result = todo.to_dict()
        assert result["due_at"] == "2026-03-15T10:00:00+00:00"


class TestTodoIsOverdue:
    """Tests for the is_overdue() method."""

    def test_todo_is_overdue_true(self) -> None:
        """Todo with past due_at should be overdue."""
        # Create a due date in the past
        past_due = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Overdue task", due_at=past_due)
        assert todo.is_overdue() is True

    def test_todo_is_overdue_false_future(self) -> None:
        """Todo with future due_at should not be overdue."""
        # Create a due date in the future
        future_due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Future task", due_at=future_due)
        assert todo.is_overdue() is False

    def test_todo_is_overdue_false_no_due(self) -> None:
        """Todo without due_at should not be overdue."""
        todo = Todo(id=1, text="Task without due date")
        assert todo.is_overdue() is False

    def test_todo_is_overdue_false_done(self) -> None:
        """Completed todo should not be overdue even if past due."""
        past_due = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        todo = Todo(id=1, text="Done task", done=True, due_at=past_due)
        assert todo.is_overdue() is False


class TestTodoSetDueMethod:
    """Tests for the set_due() method."""

    def test_todo_set_due(self) -> None:
        """Todo.set_due should update due_at and updated_at."""
        todo = Todo(id=1, text="Task")
        original_updated_at = todo.updated_at

        new_due = "2026-03-15T10:00:00+00:00"
        todo.set_due(new_due)

        assert todo.due_at == new_due
        assert todo.updated_at != original_updated_at

    def test_todo_set_due_can_clear(self) -> None:
        """Todo.set_due should allow clearing due_at with None."""
        todo = Todo(id=1, text="Task", due_at="2026-03-15T10:00:00+00:00")
        todo.set_due(None)
        assert todo.due_at is None


class TestTodoAppSetDue:
    """Tests for TodoApp.set_due method."""

    def test_app_set_due(self, tmp_path) -> None:
        """TodoApp.set_due should update due_at for existing todo."""
        app = TodoApp(db_path=str(tmp_path / "test.json"))
        todo = app.add("Test task")

        updated = app.set_due(todo.id, "2026-03-15T10:00:00+00:00")

        assert updated.due_at == "2026-03-15T10:00:00+00:00"

    def test_app_set_due_not_found(self, tmp_path) -> None:
        """TodoApp.set_due should raise for non-existent todo."""
        app = TodoApp(db_path=str(tmp_path / "test.json"))

        try:
            app.set_due(999, "2026-03-15T10:00:00+00:00")
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "not found" in str(e)


class TestSetDueCommand:
    """Tests for CLI set-due command."""

    def test_parser_has_set_due_command(self) -> None:
        """Parser should have set-due subcommand."""
        parser = build_parser()
        # Parse set-due command
        args = parser.parse_args(["set-due", "1", "2026-03-15T10:00:00+00:00"])
        assert args.command == "set-due"
        assert args.id == 1
        assert args.due_date == "2026-03-15T10:00:00+00:00"

    def test_cli_set_due_success(self, tmp_path, capsys, monkeypatch) -> None:
        """CLI set-due command should update todo due_at."""
        db_path = str(tmp_path / "test.json")

        # First add a todo
        exit_code = main(["--db", db_path, "add", "Test task"])
        assert exit_code == 0

        # Now set due date
        exit_code = main(
            ["--db", db_path, "set-due", "1", "2026-03-15T10:00:00+00:00"]
        )
        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Set due date" in captured.out
        assert "#1" in captured.out

    def test_cli_set_due_not_found(self, tmp_path, capsys) -> None:
        """CLI set-due should fail for non-existent todo."""
        db_path = str(tmp_path / "test.json")

        exit_code = main(
            ["--db", db_path, "set-due", "999", "2026-03-15T10:00:00+00:00"]
        )
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err
        assert "not found" in captured.err
