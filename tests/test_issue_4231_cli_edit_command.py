"""Regression tests for Issue #4231: Add `edit`/`rename` command to CLI for updating todo text.

This test file ensures that CLI provides an `edit` subcommand that allows users to
update todo text without losing the created_at timestamp.

Acceptance criteria:
- `todo edit 1 "new text"` successfully updates todo #1's text
- updated_at timestamp is refreshed after edit
- empty text raises clear error message
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should successfully update todo text.

    Issue #4231: Acceptance criteria - `todo edit 1 "new text"` should update
    todo #1's text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit it
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "New text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Edited #1: New text" in captured.out

    # Verify the change persisted
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "New text" in captured.out
    assert "Original text" not in captured.out


def test_cli_edit_command_refreshes_updated_at_timestamp(tmp_path, capsys) -> None:
    """edit command should refresh updated_at timestamp.

    Issue #4231: Acceptance criteria - updated_at timestamp is refreshed after edit.
    """
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Get original timestamps
    original_data = json.loads(db.read_text())
    original_updated_at = original_data[0]["updated_at"]

    # Wait a bit to ensure timestamp difference
    time.sleep(0.01)

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated"])
    run_command(edit_args)
    capsys.readouterr()  # Clear edit output

    # Verify updated_at changed
    new_data = json.loads(db.read_text())
    assert new_data[0]["updated_at"] != original_updated_at, "updated_at should be refreshed"
    assert new_data[0]["created_at"] == original_data[0]["created_at"], "created_at should be preserved"


def test_cli_edit_command_empty_text_shows_error(tmp_path, capsys) -> None:
    """edit command with empty text should show clear error message.

    Issue #4231: Acceptance criteria - empty text raises clear error message.
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
    assert result == 1, "edit command should fail with empty text"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "cannot be empty" in captured.err.lower()


def test_cli_edit_command_whitespace_only_shows_error(tmp_path, capsys) -> None:
    """edit command with whitespace-only text should show clear error message.

    Issue #4231: Related to empty text acceptance criteria.
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
    assert result == 1, "edit command should fail with whitespace-only text"

    captured = capsys.readouterr()
    assert "Error:" in captured.err


def test_cli_edit_command_nonexistent_id_shows_error(tmp_path, capsys) -> None:
    """edit command with non-existent ID should show clear error message.

    Following the pattern of existing done/undone/rm commands.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail with non-existent ID"

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "not found" in captured.err.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in output.

    Following the security pattern from Issue #2083.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a clean todo
    add_args = parser.parse_args(["--db", str(db), "add", "Clean task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\x1b[31mColor\x1b[0m"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representations
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
