"""Tests for issue #6053: Add rename CLI command.

This module tests the rename functionality that was missing from the CLI
despite Todo.rename() being implemented in todo.py.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


class TestRenameCLI:
    """Tests for the rename CLI command."""

    def test_cli_rename_command_exists_in_parser(self) -> None:
        """The 'rename' subcommand should be available in the CLI parser."""
        parser = build_parser()
        # Should not raise - rename command should be valid
        args = parser.parse_args(["rename", "1", "new text"])
        assert args.command == "rename"
        assert args.id == 1
        assert args.text == "new text"

    def test_cli_rename_updates_todo_text(self, tmp_path, capsys) -> None:
        """Rename command should update todo text via CLI."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # Add a todo first
        args = parser.parse_args(["--db", db, "add", "original task"])
        assert run_command(args) == 0

        # Rename it
        args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
        assert run_command(args) == 0

        # Verify the rename happened
        captured = capsys.readouterr()
        assert "Renamed #1" in captured.out

        # Verify via list
        args = parser.parse_args(["--db", db, "list"])
        run_command(args)
        captured = capsys.readouterr()
        assert "renamed task" in captured.out
        assert "original task" not in captured.out

    def test_cli_rename_validates_non_empty_text(self, tmp_path, capsys) -> None:
        """Rename command should reject empty text."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # Add a todo first
        args = parser.parse_args(["--db", db, "add", "original task"])
        run_command(args)

        # Try to rename with empty text
        args = parser.parse_args(["--db", db, "rename", "1", ""])
        assert run_command(args) == 1  # Should fail

        captured = capsys.readouterr()
        assert "cannot be empty" in captured.err or "cannot be empty" in captured.out

    def test_cli_rename_rejects_whitespace_only(self, tmp_path, capsys) -> None:
        """Rename command should reject whitespace-only text."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        # Add a todo first
        args = parser.parse_args(["--db", db, "add", "original task"])
        run_command(args)

        # Try to rename with whitespace-only text
        args = parser.parse_args(["--db", db, "rename", "1", "   "])
        assert run_command(args) == 1  # Should fail

        captured = capsys.readouterr()
        assert "cannot be empty" in captured.err or "cannot be empty" in captured.out

    def test_cli_rename_returns_error_for_nonexistent_todo(
        self, tmp_path, capsys
    ) -> None:
        """Rename command should return error for non-existent todo."""
        db = str(tmp_path / "cli.json")
        parser = build_parser()

        args = parser.parse_args(["--db", db, "rename", "99", "new text"])
        assert run_command(args) == 1

        captured = capsys.readouterr()
        assert "not found" in captured.err or "not found" in captured.out


class TestTodoAppRename:
    """Tests for the TodoApp.rename method."""

    def test_app_rename_method_exists(self, tmp_path) -> None:
        """TodoApp should have a rename method."""
        app = TodoApp(str(tmp_path / "db.json"))
        assert hasattr(app, "rename")
        assert callable(app.rename)

    def test_app_rename_updates_todo(self, tmp_path) -> None:
        """TodoApp.rename should update todo text and return the todo."""
        app = TodoApp(str(tmp_path / "db.json"))

        added = app.add("original text")
        assert added.id == 1

        renamed = app.rename(1, "new text")
        assert renamed.text == "new text"
        assert renamed.id == 1

        # Verify persistence
        todos = app.list()
        assert len(todos) == 1
        assert todos[0].text == "new text"

    def test_app_rename_updates_updated_at(self, tmp_path) -> None:
        """TodoApp.rename should update the updated_at timestamp."""
        app = TodoApp(str(tmp_path / "db.json"))

        added = app.add("original")
        original_updated = added.updated_at

        renamed = app.rename(1, "new")
        assert renamed.updated_at >= original_updated

    def test_app_rename_validates_non_empty_text(self, tmp_path) -> None:
        """TodoApp.rename should reject empty text."""
        app = TodoApp(str(tmp_path / "db.json"))
        app.add("original")

        with pytest.raises(ValueError, match="cannot be empty"):
            app.rename(1, "")

    def test_app_rename_raises_for_nonexistent_id(self, tmp_path) -> None:
        """TodoApp.rename should raise ValueError for non-existent id."""
        app = TodoApp(str(tmp_path / "db.json"))

        with pytest.raises(ValueError, match="not found"):
            app.rename(99, "new text")
