"""Regression tests for Issue #6001: Add rename command to CLI.

This test file ensures that the CLI supports the 'rename' subcommand
to rename todo items. The Todo.rename() method already exists in todo.py,
but there was no CLI entry point for it.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """CLI should support 'todo rename <id> <new_text>' command."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    added = app.add("original text")
    assert added.id == 1

    # Now test the rename command via CLI
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)

    assert result == 0, "rename command should return 0 on success"

    captured = capsys.readouterr()
    assert "Renamed #1: new text" in captured.out

    # Verify the text was actually changed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """CLI rename should return error for non-existent todo id."""
    db = str(tmp_path / "cli.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should return 1 for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """CLI rename should return error for empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1, "rename command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err.lower() or "cannot be empty" in captured.out.lower()


def test_cli_rename_command_whitespace_only(tmp_path, capsys) -> None:
    """CLI rename should return error for whitespace-only text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "   "])
    result = run_command(args)

    assert result == 1, "rename command should return 1 for whitespace-only text"

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.err.lower() or "cannot be empty" in captured.out.lower()


def test_cli_rename_command_strips_whitespace(tmp_path, capsys) -> None:
    """CLI rename should strip leading/trailing whitespace from text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    app.add("original text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "  padded text  "])
    result = run_command(args)

    assert result == 0

    captured = capsys.readouterr()
    # Output should show the stripped text
    assert "padded text" in captured.out

    # Verify the stored text is stripped
    todos = app.list()
    assert todos[0].text == "padded text"
