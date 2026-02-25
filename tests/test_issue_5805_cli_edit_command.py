"""Regression tests for Issue #5805: Add CLI 'edit' command to rename todos.

This test file ensures that the CLI provides an 'edit' subcommand that allows
users to rename existing todos without having to delete and re-add them.

The Todo.rename() method already exists in todo.py but is not exposed via CLI.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update the text of an existing todo.

    Issue #5805: 'todo edit 1 new text' updates todo #1's text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"

    capsys.readouterr()  # Clear add output

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should show the updated text
    assert "Updated text" in captured.out
    assert "Edited #1" in captured.out


def test_cli_edit_command_returns_error_for_non_existent_todo(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo.

    Issue #5805: 'todo edit 99 x' returns error for non-existent todo.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a todo that doesn't exist
    edit_args = parser.parse_args(["--db", str(db), "edit", "99", "new text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should return 1 for non-existent todo"

    captured = capsys.readouterr()
    # Error message should indicate todo not found
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty text with clear error message.

    Issue #5805: Empty text is rejected with clear error message.
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
    assert result == 1, "edit command should return 1 for empty text"

    captured = capsys.readouterr()
    # Error message should indicate text cannot be empty
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in output.

    Following the pattern from Issue #2083, the edit command should use
    _sanitize_text for output to prevent terminal control character injection.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\n\rWith\x00Controls"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\x00" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
    assert "\x00" not in captured.out


def test_cli_edit_command_preserves_done_status(tmp_path, capsys) -> None:
    """edit command should preserve the done status of a todo.

    When editing a todo, the done status should not be changed.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Add and mark done a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    done_args = parser.parse_args(["--db", str(db), "done", "1"])
    run_command(done_args)
    capsys.readouterr()  # Clear output

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    # List todos to verify done status is preserved
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()

    # The todo should still be marked as done ([x] in output)
    assert "[x]" in captured.out
