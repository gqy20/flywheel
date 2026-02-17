"""Regression tests for Issue #3924: CLI lacks `edit` command to invoke Todo.rename().

This test file ensures that the CLI provides an `edit` command that allows users
to modify todo text content without needing to delete and re-add the todo.

Issue #3924 specifically requests:
- `todo edit <id> <new_text>` command to modify todo text
- Empty/whitespace-only text should return a clear error
- Success message showing "Updated #id: new text"
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_exists(tmp_path, capsys) -> None:
    """edit command should be available in CLI.

    The parser should accept 'edit' as a valid subcommand.
    """
    parser = build_parser()
    # Should not raise an error when parsing 'edit'
    args = parser.parse_args(["--db", str(tmp_path / "db.json"), "edit", "1", "new text"])
    assert args.command == "edit"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_edit_command_successfully_updates_text(tmp_path, capsys) -> None:
    """edit command should successfully update todo text.

    Issue #3924 acceptance criteria: User can modify todo text via `todo edit <id> <new_text>`.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit it
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)

    assert result == 0, "edit command should succeed"
    captured = capsys.readouterr()
    assert "Updated #1: Updated text" in captured.out


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty or whitespace-only text.

    Issue #3924 acceptance criteria: Empty/whitespace text should return clear error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)

    assert result == 1, "edit command with empty text should fail"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_rejects_whitespace_only_text(tmp_path, capsys) -> None:
    """edit command should reject whitespace-only text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with whitespace-only text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(edit_args)

    assert result == 1, "edit command with whitespace-only text should fail"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id.

    Issue #3924 acceptance criteria: Editing non-existent id returns error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "new text"])
    result = run_command(edit_args)

    assert result == 1, "edit command for non-existent id should fail"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_sanitizes_control_characters(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    Consistent with Issue #2083 fix, success message should escape control chars.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\n\r\tWith\x00Controls"])
    result = run_command(edit_args)

    assert result == 0, "edit command should succeed"
    captured = capsys.readouterr()
    # Control characters should be escaped
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\t" in captured.out
    assert "\\x00" in captured.out
    # Raw control characters should NOT be present
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
    assert "\x00" not in captured.out
