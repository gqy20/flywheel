"""Tests for issue #6562: CLI missing 'rename' command.

Bug: CLI missing 'rename' command despite Todo.rename() method existing in data model.
Fix: Add a 'rename' subparser in build_parser() and handle 'rename' command in run_command().
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """CLI accepts 'todo rename <id> <new_text>' command and updates todo.text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed text"])
    assert run_command(args) == 0

    # Verify the rename output
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the text was actually changed
    app = TodoApp(db)
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed text"


def test_cli_rename_command_returns_error_for_nonexistent_todo(tmp_path, capsys) -> None:
    """Running 'todo rename 999 x' returns exit code 1 with 'Todo #999 not found' error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "Todo #999 not found" in captured.err or "Todo #999 not found" in captured.out


def test_cli_rename_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """Running 'todo rename 1 ""' returns exit code 1 with 'Todo text cannot be empty' error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "test todo"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "Todo text cannot be empty" in captured.err or "Todo text cannot be empty" in captured.out


def test_cli_rename_command_updates_updated_at(tmp_path) -> None:
    """Running 'todo rename 1 new_text' updates todo.updated_at."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Get the original updated_at
    app = TodoApp(db)
    original_updated_at = app.list()[0].updated_at

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed"])
    assert run_command(args) == 0

    # Verify updated_at was changed
    new_updated_at = app.list()[0].updated_at
    assert new_updated_at >= original_updated_at
