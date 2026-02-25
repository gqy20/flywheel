"""Regression tests for Issue #5805: Add CLI 'edit' command to rename todos.

This test file ensures that the 'todo edit' subcommand works correctly
for updating todo text without requiring a delete/re-add cycle.

Acceptance criteria:
- 'todo edit 1 new text' updates todo #1's text
- 'todo edit 99 x' returns error for non-existent todo
- Empty text is rejected with clear error message
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update todo text.

    Issue #5805: 'todo edit 1 new text' updates todo #1's text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear add output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Edited #1:" in captured.out
    assert "Updated text" in captured.out

    # Verify the edit persisted by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Updated text" in captured.out
    assert "Original text" not in captured.out


def test_cli_edit_nonexistent_todo_returns_error(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo.

    Issue #5805: 'todo edit 99 x' returns error for non-existent todo.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "99", "some text"])
    result = run_command(edit_args)

    assert result == 1, "edit command should return 1 on error"
    captured = capsys.readouterr()
    # Error message should mention the todo was not found
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_empty_text_rejected(tmp_path, capsys) -> None:
    """edit command should reject empty text with clear error message.

    Issue #5805: Empty text is rejected with clear error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with empty text (only whitespace)
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(edit_args)

    assert result == 1, "edit command should return 1 for empty text"
    captured = capsys.readouterr()
    # Error message should mention empty text
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in output.

    Similar to add/done/undone commands, edit should use _sanitize_text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with text containing control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\x1b[31mColor"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representations
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
