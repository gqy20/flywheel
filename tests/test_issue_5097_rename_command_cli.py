"""Regression tests for Issue #5097: Todo.rename() not exposed via CLI.

This test file ensures that the 'rename' subcommand is available in the CLI
to expose the Todo.rename() functionality to users.

Issue #5097 specifically highlights that rename() method exists in todo.py
but is never called from CLI, making it dead code.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists_in_parser() -> None:
    """The 'rename' subcommand should be defined in build_parser()."""
    parser = build_parser()
    # Parse the help to check available commands
    # The parser should accept 'rename' as a valid command
    args = parser.parse_args(["--db", ".todo.json", "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """rename command should update the todo's text and updated_at.

    Issue #5097 acceptance criteria: Calling 'todo rename 1 new text'
    updates the todo's text and updated_at.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "old text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear add output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "new text"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1:" in captured.out
    assert "new text" in captured.out


def test_cli_rename_command_shows_updated_text(tmp_path, capsys) -> None:
    """rename command should show the updated text in list output."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(add_args)
    capsys.readouterr()

    # Rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "renamed"])
    run_command(rename_args)
    capsys.readouterr()

    # List todos to verify the text was updated
    list_args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(list_args)
    assert result == 0

    captured = capsys.readouterr()
    assert "renamed" in captured.out
    assert "original" not in captured.out


def test_cli_rename_command_handles_nonexistent_id(tmp_path, capsys) -> None:
    """rename command should return error for non-existent todo id.

    Issue #5097 acceptance criteria: Verify non-existent id raises
    'Todo #X not found'.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "new text"])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_handles_empty_text(tmp_path, capsys) -> None:
    """rename command should reject empty text.

    Issue #5097 acceptance criteria: Verify empty text raises ValueError.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "valid task"])
    run_command(add_args)
    capsys.readouterr()

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)
    assert result == 1, "rename command should fail for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize text in success message.

    Following the pattern from Issue #2083, success messages should
    sanitize control characters.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original"])
    run_command(add_args)
    capsys.readouterr()

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "new\n\rtext"])
    result = run_command(rename_args)
    assert result == 0

    captured = capsys.readouterr()
    # Control characters should be escaped in output
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    # Actual control chars should not be present
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
