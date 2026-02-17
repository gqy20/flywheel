"""Regression tests for Issue #3924: CLI missing edit command to call Todo.rename().

This test file ensures that the CLI exposes an edit command that allows users
to modify todo text content using the existing Todo.rename() method.

Issue #3924 specifically requests:
- User can use `todo edit <id> <new_text>` to modify todo text
- Empty or whitespace-only text returns clear error message
- Successful edit shows confirmation message (like "Updated #1: new text")
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_successfully_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update todo text and show confirmation message.

    Issue #3924: User should be able to edit todo text via CLI.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should show confirmation message
    assert "Updated #1" in captured.out
    assert "Updated text" in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id.

    Issue #3924: Editing non-existent id should return error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a todo that doesn't exist
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "not found" in captured.err


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty or whitespace-only text.

    Issue #3924: Empty or whitespace-only text should be rejected.
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
    assert result == 1, "edit command should fail for empty text"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_edit_command_rejects_whitespace_only_text(tmp_path, capsys) -> None:
    """edit command should reject whitespace-only text.

    Issue #3924: Whitespace-only text should be rejected.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with whitespace-only text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for whitespace-only text"

    captured = capsys.readouterr()
    assert "Error" in captured.err
    assert "empty" in captured.err.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in output.

    Following Issue #2083 pattern: Output should escape control characters.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with text containing control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\x1b[31mColor\x1b[0m"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
