"""Regression tests for Issue #6082: Expose rename method in CLI to allow editing todo text.

This test file ensures that the CLI exposes a 'edit' subcommand that calls
Todo.rename() to allow users to fix typos or update task descriptions.

Issue #6082 acceptance criteria:
- CLI accepts 'todo edit <id> <new_text>' command
- Running edit updates the todo text and updated_at timestamp
- Error is shown if todo id not found or text is empty
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update the todo text.

    Issue #6082: Add 'edit' subcommand in cli.py that calls Todo.rename().
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated task"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Should show success message with updated text
    assert "Updated task" in captured.out or "#1" in captured.out

    # Verify the text was actually updated by listing
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Updated task" in captured.out
    assert "Original task" not in captured.out


def test_cli_edit_command_updates_timestamp(tmp_path) -> None:
    """edit command should update the updated_at timestamp."""
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Task to edit"])
    run_command(add_args)

    # Read the original timestamp
    data = json.loads(db.read_text())
    original_updated_at = data[0]["updated_at"]

    # Wait a tiny bit to ensure timestamp differs
    time.sleep(0.01)

    # Edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Edited task"])
    result = run_command(edit_args)
    assert result == 0

    # Read the new timestamp
    data = json.loads(db.read_text())
    new_updated_at = data[0]["updated_at"]

    # Timestamp should have changed
    assert new_updated_at != original_updated_at


def test_cli_edit_command_shows_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should show error if todo id not found."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)

    assert result == 1, "edit command should return 1 for non-existent id"

    captured = capsys.readouterr()
    # Error should be shown in stderr
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_shows_error_for_empty_text(tmp_path, capsys) -> None:
    """edit command should show error if text is empty."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)

    assert result == 1, "edit command should return 1 for empty text"

    captured = capsys.readouterr()
    # Error should be shown
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_output(tmp_path, capsys) -> None:
    """edit command should sanitize todo text in success message."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(
        ["--db", str(db), "edit", "1", "Updated\nWith\rControls"]
    )
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    # Should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
