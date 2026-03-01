"""Regression tests for Issue #6479: TodoApp lacks rename CLI command entry.

This test file ensures that the CLI supports the 'rename' subcommand to rename
existing todos, matching the Todo.rename() method that already exists.

Issue #6479 specifically highlights that cli.py only defines add/list/done/undone/rm
subcommands, but is missing the rename subcommand.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_succeeds_for_existing_todo(tmp_path, capsys) -> None:
    """rename command should successfully rename an existing todo.

    Issue #6479: CLI should support 'todo rename <id> <text>' command.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed task"])
    result = run_command(rename_args)

    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1:" in captured.out
    assert "Renamed task" in captured.out


def test_cli_rename_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """rename command should return error code 1 for non-existent ID.

    Issue #6479: rename command should fail with error when ID doesn't exist.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    assert result == 1, "rename command should return 1 for non-existent ID"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """rename command should return error code 1 for empty text.

    Issue #6479: rename command should fail when text is empty or whitespace.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)

    assert result == 1, "rename command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_sanitizes_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in success message.

    Like add/done/undone commands, rename should escape control characters.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Task\nWith\x1b[31mColor"])
    result = run_command(rename_args)

    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
