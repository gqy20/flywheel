"""Tests for issue #3680: Add edit() as alias for rename()."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command
from flywheel.todo import Todo


class TestTodoEditAlias:
    """Test that edit() works as an alias for rename()."""

    def test_todo_edit_method_exists(self) -> None:
        """edit() method should exist on Todo class."""
        todo = Todo(id=1, text="original")
        assert hasattr(todo, "edit")

    def test_todo_edit_updates_text(self) -> None:
        """edit() should update the todo text."""
        todo = Todo(id=1, text="original")
        todo.edit("new text")
        assert todo.text == "new text"

    def test_todo_edit_updates_timestamp(self) -> None:
        """edit() should update the updated_at timestamp."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at
        todo.edit("new text")
        assert todo.updated_at >= original_updated_at

    def test_todo_edit_strips_whitespace(self) -> None:
        """edit() should strip whitespace from text."""
        todo = Todo(id=1, text="original")
        todo.edit("  padded  ")
        assert todo.text == "padded"

    def test_todo_edit_rejects_empty_string(self) -> None:
        """edit() should reject empty strings."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.edit("")

        # Verify state unchanged
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_todo_edit_rejects_whitespace_only(self) -> None:
        """edit() should reject whitespace-only strings."""
        todo = Todo(id=1, text="original")
        original_updated_at = todo.updated_at

        with pytest.raises(ValueError, match="Todo text cannot be empty"):
            todo.edit("   ")

        # Verify state unchanged
        assert todo.text == "original"
        assert todo.updated_at == original_updated_at

    def test_todo_edit_same_behavior_as_rename(self) -> None:
        """edit() and rename() should have identical behavior."""
        todo1 = Todo(id=1, text="original1")
        todo2 = Todo(id=2, text="original2")

        todo1.rename("new text")
        todo2.edit("new text")

        assert todo1.text == todo2.text
        # Both should update the timestamp


class TestCliEditCommand:
    """Test CLI edit command."""

    def test_cli_edit_command_exists(self) -> None:
        """CLI should have edit subcommand."""
        parser = build_parser()
        # This will raise if edit command doesn't exist
        args = parser.parse_args(["edit", "1", "new text"])
        assert args.command == "edit"

    def test_cli_edit_command_updates_todo(self, tmp_path) -> None:
        """CLI edit command should update todo text."""
        db = str(tmp_path / "cli.json")
        app = TodoApp(db)

        # Add a todo first
        app.add("original text")

        parser = build_parser()
        args = parser.parse_args(["--db", db, "edit", "1", "new text"])
        result = run_command(args)

        assert result == 0
        todos = app.list()
        assert len(todos) == 1
        assert todos[0].text == "new text"

    def test_cli_edit_command_shows_success_message(self, tmp_path, capsys) -> None:
        """CLI edit command should show success message."""
        db = str(tmp_path / "cli.json")
        app = TodoApp(db)

        # Add a todo first
        app.add("original text")

        parser = build_parser()
        args = parser.parse_args(["--db", db, "edit", "1", "new text"])
        result = run_command(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Edited" in captured.out
        assert "#1" in captured.out

    def test_cli_edit_command_fails_for_nonexistent_todo(self, tmp_path, capsys) -> None:
        """CLI edit command should fail for non-existent todo."""
        db = str(tmp_path / "cli.json")

        parser = build_parser()
        args = parser.parse_args(["--db", db, "edit", "99", "new text"])
        result = run_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out or "not found" in captured.err

    def test_cli_edit_command_with_multi_word_text(self, tmp_path) -> None:
        """CLI edit command should handle multi-word text."""
        db = str(tmp_path / "cli.json")
        app = TodoApp(db)

        # Add a todo first
        app.add("original text")

        parser = build_parser()
        args = parser.parse_args(["--db", db, "edit", "1", "new", "multi", "word", "text"])
        result = run_command(args)

        assert result == 0
        todos = app.list()
        assert todos[0].text == "new multi word text"
