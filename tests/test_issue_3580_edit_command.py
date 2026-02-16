"""Regression tests for Issue #3580: Add Todo edit command to CLI.

This test file ensures that the CLI exposes an 'edit' subcommand that allows
users to modify the text of an existing todo. The Todo.rename() method already
exists but was not exposed via CLI.

Acceptance criteria:
- CLI supports: todo edit <id> <new_text>
- updated_at is automatically updated after edit
- Empty text throws clear error
"""

from __future__ import annotations

import time

from flywheel.cli import build_parser, run_command
from flywheel.storage import TodoStorage


def test_cli_edit_command_exists(tmp_path, capsys) -> None:
    """CLI should support 'edit' subcommand to rename a todo.

    Issue #3580: The edit command was missing from CLI despite Todo.rename()
    method already being implemented.
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
    assert "Updated text" in captured.out
    assert "Edited #1" in captured.out


def test_cli_edit_command_updates_timestamp(tmp_path, capsys) -> None:
    """Edit command should update the updated_at timestamp.

    Issue #3580 acceptance criteria: updated_at is automatically updated after edit.
    """
    db = tmp_path / "db.json"
    parser = build_parser()
    storage = TodoStorage(str(db))

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Test todo"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Get the original updated_at
    todos = storage.load()
    original_updated_at = todos[0].updated_at

    # Wait a tiny bit to ensure timestamp differs
    time.sleep(0.01)

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Modified todo"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    # Verify updated_at changed
    todos = storage.load()
    assert todos[0].text == "Modified todo"
    assert todos[0].updated_at != original_updated_at


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """Edit command should reject empty text with clear error.

    Issue #3580 acceptance criteria: Empty text throws clear error.
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
    assert "empty" in captured.err.lower()


def test_cli_edit_command_nonexistent_todo(tmp_path, capsys) -> None:
    """Edit command should error when todo doesn't exist."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a todo that doesn't exist
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for non-existent todo"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """Edit command should sanitize control characters in output.

    Consistency with other CLI commands - text should be sanitized before output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Normal todo"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\n\r\tWith\x00Controls"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    assert "\\t" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
    assert "\x00" not in captured.out
