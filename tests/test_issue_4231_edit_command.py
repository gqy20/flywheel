"""Regression tests for Issue #4231: Add edit/rename command to CLI for updating todo text.

This test file ensures that the CLI has an 'edit' subcommand that allows users
to rename todos without deleting and re-adding them, preserving the created_at timestamp.

Issue #4231 acceptance criteria:
- `todo edit 1 "new text"` successfully updates todo #1's text
- updated_at timestamp is refreshed after edit
- empty text raises clear error message
"""

from __future__ import annotations

import time

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update the text of an existing todo.

    Issue #4231: `todo edit 1 "new text"` should update todo #1's text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear output

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "New text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Edited #1" in captured.out
    assert "New text" in captured.out

    # Verify the text was actually changed
    storage = TodoStorage(str(db))
    todos = storage.load()
    assert len(todos) == 1
    assert todos[0].text == "New text"


def test_cli_edit_command_refreshes_updated_at_timestamp(tmp_path, capsys) -> None:
    """edit command should refresh the updated_at timestamp.

    Issue #4231: updated_at timestamp should be refreshed after edit.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()

    # Get original updated_at
    storage = TodoStorage(str(db))
    original_todo = storage.load()[0]
    original_updated_at = original_todo.updated_at

    # Wait a tiny bit to ensure timestamp differs
    time.sleep(0.01)

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Modified text"])
    result = run_command(edit_args)
    assert result == 0

    # Verify updated_at changed
    todos = storage.load()
    assert todos[0].updated_at != original_updated_at
    # created_at should remain the same
    assert todos[0].created_at == original_todo.created_at


def test_cli_edit_command_empty_text_raises_error(tmp_path, capsys) -> None:
    """edit command with empty text should raise a clear error message.

    Issue #4231: empty text raises clear error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)
    assert result == 1, "edit command with empty text should fail"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_nonexistent_todo_raises_error(tmp_path, capsys) -> None:
    """edit command on non-existent todo should raise error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command on non-existent todo should fail"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_sanitizes_text_in_success_message(tmp_path, capsys) -> None:
    """edit command should sanitize text in success message.

    Following the pattern from Issue #2083, the success message should
    escape control characters.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\x1b[31mColor"])
    result = run_command(edit_args)
    assert result == 0

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
