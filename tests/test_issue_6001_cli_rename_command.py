"""Regression tests for Issue #6001: Add rename command to CLI.

This test file ensures that the CLI supports a 'rename' subcommand that allows
users to modify todo text via the command line interface.

Issue #6001: Todo.rename() method exists but CLI lacks corresponding 'rename' subcommand.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_normal_flow(tmp_path, capsys) -> None:
    """rename command should rename an existing todo and print success message."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    parser = build_parser()

    # First add a todo
    app.add("original text")

    # Rename it via CLI
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)

    assert result == 0, "rename command should succeed"
    captured = capsys.readouterr()
    assert "Renamed #1: new text" in captured.out

    # Verify the todo was actually renamed
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """rename command should return error for non-existent todo id."""
    db = str(tmp_path / "db.json")
    parser = build_parser()

    # Try to rename a todo that doesn't exist
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1, "rename command should fail for non-existent id"
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_empty_string_returns_error(tmp_path, capsys) -> None:
    """rename command should return error when new text is empty."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    parser = build_parser()

    # First add a todo
    app.add("original text")

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1, "rename command should fail for empty text"
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()

    # Verify the todo was not renamed
    todos = app.list()
    assert todos[0].text == "original text"


def test_cli_rename_whitespace_only_returns_error(tmp_path, capsys) -> None:
    """rename command should return error when new text is whitespace only."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    parser = build_parser()

    # First add a todo
    app.add("original text")

    # Try to rename with whitespace-only text
    args = parser.parse_args(["--db", db, "rename", "1", "   "])
    result = run_command(args)

    assert result == 1, "rename command should fail for whitespace-only text"
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()

    # Verify the todo was not renamed
    todos = app.list()
    assert todos[0].text == "original text"


def test_cli_rename_strips_whitespace(tmp_path, capsys) -> None:
    """rename command should strip whitespace from the new text."""
    db = str(tmp_path / "db.json")
    app = TodoApp(db)
    parser = build_parser()

    # First add a todo
    app.add("original text")

    # Rename with padded text
    args = parser.parse_args(["--db", db, "rename", "1", "  padded text  "])
    result = run_command(args)

    assert result == 0, "rename command should succeed"

    # Verify the whitespace was stripped
    todos = app.list()
    assert todos[0].text == "padded text"


def test_cli_rename_sanitizes_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in success message."""
    db = tmp_path / "db.json"
    app = TodoApp(str(db))
    parser = build_parser()

    # First add a todo
    app.add("original text")

    # Rename with control characters in the new text
    args = parser.parse_args(["--db", str(db), "rename", "1", "new\ntext"])
    result = run_command(args)

    assert result == 0, "rename command should succeed"
    captured = capsys.readouterr()

    # Output should contain escaped representation (visible as literal \n)
    assert "\\n" in captured.out
    # Output should NOT contain actual newline (single line output)
    assert "\n" not in captured.out.strip()
