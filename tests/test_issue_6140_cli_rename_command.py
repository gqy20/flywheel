"""Regression tests for Issue #6140: CLI does not expose 'rename' command.

This test file ensures that the CLI exposes a 'rename' command that allows
users to rename todo items via the command line interface.

The Todo.rename() method exists in todo.py, but it was not exposed through
the CLI's build_parser() and run_command() functions.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_parses_successfully() -> None:
    """The 'rename' subcommand should be parseable."""
    parser = build_parser()
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """'todo rename <id> <text>' should update the todo text and print confirmation."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)
    assert result == 0

    # Verify output contains confirmation
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out or "renamed" in captured.out.lower()

    # Verify the text was actually changed
    app = TodoApp(db)
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_command_returns_error_for_non_existent_id(tmp_path, capsys) -> None:
    """'todo rename 999 "text"' should return exit code 1 for non-existent ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_handles_whitespace_text(tmp_path, capsys) -> None:
    """'todo rename' should strip whitespace from text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename with padded text
    args = parser.parse_args(["--db", db, "rename", "1", "  padded text  "])
    result = run_command(args)
    assert result == 0

    # Verify whitespace was stripped
    app = TodoApp(db)
    todos = app.list()
    assert todos[0].text == "padded text"


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """'todo rename' should reject empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()
