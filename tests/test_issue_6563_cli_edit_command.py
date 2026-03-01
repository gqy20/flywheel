"""Regression tests for Issue #6563: CLI missing rename command.

This test file ensures that the CLI exposes the 'edit' command to allow
users to rename todo items via command line. The Todo.rename() method
already exists in todo.py but was not exposed through the CLI.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_modifies_existing_todo(tmp_path, capsys) -> None:
    """The 'edit' command should modify the text of an existing todo."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args_add = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(args_add)
    assert result == 0

    # Now edit the todo
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", "new text"])
    result = run_command(args_edit)
    assert result == 0, "edit command should return 0 on success"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out, "Should output 'Renamed #1' message"
    assert "new text" in captured.out, "Should show the new text in output"


def test_cli_edit_command_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """The 'edit' command with non-existent id should return error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    args = parser.parse_args(["--db", str(db), "edit", "999", "new text"])
    result = run_command(args)
    assert result == 1, "edit command should return 1 for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_empty_text_returns_error(tmp_path, capsys) -> None:
    """The 'edit' command with empty text should return error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args_add = parser.parse_args(["--db", str(db), "add", "original text"])
    run_command(args_add)

    # Try to edit with empty text
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(args_edit)
    assert result == 1, "edit command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_output(tmp_path, capsys) -> None:
    """The 'edit' command output should be sanitized for control characters."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args_add = parser.parse_args(["--db", str(db), "add", "original text"])
    run_command(args_add)

    # Edit with text containing control characters
    args_edit = parser.parse_args(["--db", str(db), "edit", "1", "text\x1b[31mred"])
    result = run_command(args_edit)
    assert result == 0

    captured = capsys.readouterr()
    # Control characters should be sanitized (escaped or removed)
    assert "\x1b" not in captured.out, "Output should not contain raw escape sequences"
