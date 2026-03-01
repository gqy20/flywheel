"""Regression tests for Issue #6605: CLI missing edit/rename command.

This test file ensures that CLI exposes an 'edit' command that allows users
to modify todo text via command line, using the existing Todo.rename() method.

Acceptance criteria:
- Running 'todo edit 1 new text' modifies the todo with id=1
- Empty text triggers 'Todo text cannot be empty' error
- updated_at is automatically updated after edit
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_modifies_todo_text(tmp_path, capsys) -> None:
    """edit command should modify existing todo text.

    Issue #6605: CLI lacks edit command, users cannot modify todo text via CLI.
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
    assert "Updated" in captured.out or "Edited" in captured.out
    assert "#1" in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty text.

    The Todo.rename() method validates that text cannot be empty.
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


def test_cli_edit_command_updates_timestamp(tmp_path, capsys) -> None:
    """edit command should update the updated_at timestamp.

    Issue #6605: After modification, updated_at should be automatically updated.
    """
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Read the initial timestamp
    initial_data = json.loads(db.read_text())
    initial_updated_at = initial_data[0]["updated_at"]

    # Wait a tiny bit to ensure timestamp differs
    time.sleep(0.01)

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"
    capsys.readouterr()  # Clear edit output

    # Verify timestamp was updated
    updated_data = json.loads(db.read_text())
    new_updated_at = updated_data[0]["updated_at"]
    assert new_updated_at != initial_updated_at, "updated_at should be changed after edit"


def test_cli_edit_command_sanitizes_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    Following the pattern from issue #2083 for terminal security.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated\nWithControls"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    # Output should NOT contain actual newline
    assert "\n" not in captured.out.strip()
