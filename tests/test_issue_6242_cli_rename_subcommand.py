"""Regression tests for Issue #6242: CLI missing 'rename' subcommand despite Todo.rename() method exists.

This test file ensures that the CLI provides a 'rename' subcommand that allows users
to rename existing todos using the Todo.rename() method that already exists in the codebase.

Acceptance criteria:
- 'todo rename <id> <text>' command successfully changes todo text
- 'todo rename <id> <text>' returns exit code 0 on success
- 'todo rename <id> <text>' returns exit code 1 when todo not found
- 'todo rename' with empty text raises error
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists(tmp_path) -> None:
    """The CLI should accept 'rename' as a valid subcommand."""
    parser = build_parser()
    # This should not raise an error - rename subcommand should exist
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_successfully_changes_todo_text(tmp_path, capsys) -> None:
    """'todo rename <id> <text>' should successfully change todo text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(add_args)
    assert result == 0
    capsys.readouterr()  # Clear add output

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "new text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should return 0 on success"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out


def test_cli_rename_command_returns_1_when_todo_not_found(tmp_path, capsys) -> None:
    """'todo rename <id> <text>' should return exit code 1 when todo not found."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "new text"])
    result = run_command(rename_args)
    assert result == 1, "rename command should return 1 when todo not found"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_with_empty_text_raises_error(tmp_path, capsys) -> None:
    """'todo rename' with empty text should raise validation error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)
    assert result == 1, "rename command should return 1 when text is empty"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_with_whitespace_only_text_raises_error(tmp_path, capsys) -> None:
    """'todo rename' with whitespace-only text should raise validation error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with whitespace-only text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(rename_args)
    assert result == 1, "rename command should return 1 when text is whitespace-only"


def test_cli_rename_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in success message."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "new\n\rtext"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Control characters should be escaped in output
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    # Actual control chars should NOT appear
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
