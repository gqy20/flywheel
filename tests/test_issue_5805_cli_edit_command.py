"""Regression tests for Issue #5805: Add CLI 'edit' command to rename todos.

This test file ensures that the CLI has an 'edit' subcommand that allows users
to rename todo items without having to delete and re-add them.

Acceptance criteria:
- 'todo edit 1 new text' updates todo #1's text
- 'todo edit 99 x' returns error for non-existent todo
- Empty text is rejected with clear error message
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update the text of an existing todo.

    Issue #5805: Users should be able to fix typos or update todo text
    without delete/re-add cycle.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit it
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated task"])
    result = run_command(edit_args)

    assert result == 0, "edit command should succeed"
    captured = capsys.readouterr()
    assert "Updated" in captured.out or "Edited" in captured.out or "#1" in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_todo(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo.

    Issue #5805: 'todo edit 99 x' returns error for non-existent todo.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "99", "new text"])
    result = run_command(edit_args)

    assert result == 1, "edit command should fail for non-existent todo"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty text with clear error message.

    Issue #5805: Empty text is rejected with clear error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)

    assert result == 1, "edit command should fail for empty text"
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_text_in_success_message(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    Following the pattern from Issue #2083, edit command should also
    use _sanitize_text for output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\rControls"])
    result = run_command(edit_args)

    assert result == 0, "edit command should succeed"
    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out


def test_cli_edit_command_updates_todo_in_storage(tmp_path, capsys) -> None:
    """edit command should persist the updated text in storage."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit it
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated task"])
    run_command(edit_args)
    capsys.readouterr()  # Clear edit output

    # Verify the update persisted by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()

    assert "Updated task" in captured.out
    assert "Original task" not in captured.out
