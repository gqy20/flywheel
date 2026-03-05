"""Regression tests for Issue #7330: Missing 'rename' command in CLI.

This test file ensures that the CLI exposes the Todo.rename() functionality
via a 'rename <id> <text>' command.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists(tmp_path, capsys) -> None:
    """The 'rename' subcommand should exist in the CLI parser."""
    parser = build_parser()

    # Should be able to parse the rename command
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """The 'rename' command should successfully rename a todo."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo first
    added = app.add("original text")
    todo_id = added.id

    # Use CLI to rename
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", str(todo_id), "new text"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    assert f"Renamed #{todo_id}" in captured.out
    assert "new text" in captured.out

    # Verify the rename persisted
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """The 'rename' command should return exit code 1 for non-existent ID."""
    db = str(tmp_path / "db.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "999", "new text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_sanitizes_output(tmp_path, capsys) -> None:
    """The 'rename' command should sanitize output with _sanitize_text()."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)

    # Add a todo with control characters
    added = app.add("original")
    todo_id = added.id

    # Rename with text containing control characters
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", str(todo_id), "new\rtext"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    # The output should not contain raw carriage return
    assert "\r" not in captured.out
