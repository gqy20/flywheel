"""Tests for issue #4118: Add rename CLI command.

Bug: Todo.rename() method exists in Todo class but has no corresponding CLI command.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists_in_parser() -> None:
    """Regression test for #4118: 'rename' subcommand should be available."""
    parser = build_parser()
    # This should not raise an error if 'rename' subcommand exists
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Regression test for #4118: rename command should update todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed task"])
    assert run_command(args) == 0

    # Verify the rename was successful
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the text was actually changed
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "renamed task" in captured.out
    assert "original task" not in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """Regression test for #4118: rename should return error for non-existent ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """Regression test for #4118: rename should return error for empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "cannot be empty" in captured.out or "cannot be empty" in captured.err


def test_app_rename_method_exists(tmp_path) -> None:
    """Regression test for #4118: TodoApp should have a rename method."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original task")

    # Rename should exist and work
    renamed = app.rename(1, "renamed task")
    assert renamed.text == "renamed task"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "renamed task"
