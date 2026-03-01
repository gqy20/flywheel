"""Regression tests for Issue #6605: CLI missing rename/edit command.

This test file ensures that the CLI exposes an 'edit' command that allows
users to modify todo text via the command line, leveraging the existing
Todo.rename() method.

Issue #6605 highlights that Todo.rename() exists (lines 50-55 in todo.py)
but CLI only has add/list/done/undone/rm commands, missing edit/rename.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_successfully_modifies_todo_text(tmp_path, capsys) -> None:
    """edit command should modify todo text successfully.

    Issue #6605: Running 'todo edit 1 new text' should modify id=1 todo.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "New text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Edited #1" in captured.out
    assert "New text" in captured.out

    # Verify the change persisted
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "New text" in captured.out
    assert "Original text" not in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo ID.

    Issue #6605: Editing non-existent ID should return error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for non-existent ID"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty text.

    Issue #6605: Empty text should trigger 'Todo text cannot be empty' error.
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
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in output.

    Following the pattern from Issue #2083, success messages should
    sanitize control characters to prevent terminal injection.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\x1b[31mColor"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out or "\n" not in captured.out.strip()
    assert "\\x1b" in captured.out or "\x1b" not in captured.out


def test_cli_edit_command_updates_timestamp(tmp_path, capsys) -> None:
    """edit command should update the updated_at timestamp.

    Issue #6605: updated_at should automatically update after edit.
    """
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Get original timestamp
    original_data = json.loads(db.read_text())
    original_updated_at = original_data[0]["updated_at"]

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "New text"])
    run_command(edit_args)
    capsys.readouterr()  # Clear edit output

    # Check timestamp was updated
    new_data = json.loads(db.read_text())
    new_updated_at = new_data[0]["updated_at"]
    assert new_updated_at != original_updated_at, "updated_at should be updated after edit"
