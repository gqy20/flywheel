"""Tests for Todo.edit() alias method (Issue #3680).

These tests verify that:
1. Todo.edit() method exists as an alias for rename()
2. edit() and rename() produce identical behavior
3. CLI edit command works correctly
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.todo import Todo


class TestTodoEditAlias:
    """Tests for Todo.edit() method as alias for rename()."""

    def test_todo_edit_method_exists(self) -> None:
        """Todo.edit() method should exist."""
        todo = Todo(id=1, text="original")
        assert hasattr(todo, "edit")

    def test_todo_edit_calls_rename(self) -> None:
        """Todo.edit() should have same behavior as rename()."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        todo.edit("new text")

        assert todo.text == "new text"
        assert todo.updated_at >= original_updated_at

    def test_todo_edit_strips_whitespace(self) -> None:
        """Todo.edit() should strip whitespace like rename()."""
        todo = Todo(id=1, text="original")

        todo.edit("  padded text  ")

        assert todo.text == "padded text"

    def test_todo_edit_rejects_empty_string(self) -> None:
        """Todo.edit() should reject empty strings after strip."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.edit("")

        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_todo_edit_rejects_whitespace_only(self) -> None:
        """Todo.edit() should reject whitespace-only strings."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.edit("   ")

        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_edit_and_rename_produce_identical_results(self) -> None:
        """edit() and rename() should produce identical behavior."""
        todo1 = Todo(id=1, text="original")
        todo2 = Todo(id=2, text="original")

        todo1.edit("modified")
        todo2.rename("modified")

        assert todo1.text == todo2.text
        # Both should update updated_at
        assert todo1.updated_at >= todo1.created_at
        assert todo2.updated_at >= todo2.created_at


class TestTodoAppEdit:
    """Tests for TodoApp.edit() method."""

    def test_app_edit_method_exists(self) -> None:
        """TodoApp should have an edit method."""
        # This test should pass after implementation
        assert hasattr(TodoApp, "edit")

    def test_app_edit_updates_todo_text(self, tmp_path) -> None:
        """TodoApp.edit() should update todo text."""
        app = TodoApp(str(tmp_path / "db.json"))

        added = app.add("original text")
        assert added.text == "original text"

        edited = app.edit(1, "new text")
        assert edited.text == "new text"

        # Verify persistence
        todos = app.list()
        assert todos[0].text == "new text"

    def test_app_edit_raises_for_nonexistent_todo(self, tmp_path) -> None:
        """TodoApp.edit() should raise ValueError for nonexistent todo."""
        app = TodoApp(str(tmp_path / "db.json"))

        with pytest.raises(ValueError, match="Todo #99 not found"):
            app.edit(99, "new text")


class TestCliEditCommand:
    """Tests for CLI edit command."""

    def test_cli_edit_command_exists(self) -> None:
        """CLI should have edit subcommand."""
        parser = build_parser()
        # Parse with edit command - should not raise
        args = parser.parse_args(["--db", "test.json", "edit", "1", "new text"])
        assert args.command == "edit"
        assert args.id == 1
        assert args.text == "new text"

    def test_cli_edit_command_updates_todo(self, tmp_path, capsys) -> None:
        """CLI edit command should update todo text."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # Add a todo first
        args = parser.parse_args(["--db", db, "add", "original text"])
        assert run_command(args) == 0

        # Edit the todo
        args = parser.parse_args(["--db", db, "edit", "1", "new text"])
        assert run_command(args) == 0

        # Verify output
        captured = capsys.readouterr()
        assert "Edited #1" in captured.out or "Edit" in captured.out

        # Verify persistence via list
        args = parser.parse_args(["--db", db, "list"])
        assert run_command(args) == 0
        out = capsys.readouterr().out
        assert "new text" in out

    def test_cli_edit_command_shows_error_for_nonexistent(self, tmp_path, capsys) -> None:
        """CLI edit command should show error for nonexistent todo."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        args = parser.parse_args(["--db", db, "edit", "99", "new text"])
        assert run_command(args) == 1

        captured = capsys.readouterr()
        assert "not found" in captured.err or "not found" in captured.out
