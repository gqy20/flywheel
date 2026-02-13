"""Regression tests for Issue #2992: Add rename command to CLI.

This test file ensures that the CLI exposes the Todo.rename() functionality
through a 'rename' subcommand, allowing users to rename todos from the command line.

Issue #2992 acceptance criteria:
- User can use 'todo rename <id> <new_text>' command to rename a todo
- updated_at is automatically updated after rename
- Empty text triggers an error
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """rename command should update the todo text.

    Issue #2992: User can use 'todo rename <id> <new_text>' command to rename a todo.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear add output

    # Now rename it
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed task"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should indicate successful rename
    assert "Renamed" in captured.out or "rename" in captured.out.lower()
    assert "Renamed task" in captured.out

    # Verify the rename persisted
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Renamed task" in captured.out
    assert "Original task" not in captured.out


def test_cli_rename_command_updates_updated_at(tmp_path) -> None:
    """rename command should update the updated_at timestamp.

    Issue #2992: updated_at is automatically updated after rename.
    """
    import json
    import time

    db = tmp_path / "db.json"
    parser = build_parser()

    # Add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Task to rename"])
    run_command(add_args)

    # Get the original updated_at
    data = json.loads(db.read_text())
    original_updated_at = data[0]["updated_at"]

    # Small delay to ensure timestamp difference
    time.sleep(0.01)

    # Rename the todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Renamed"])
    run_command(rename_args)

    # Verify updated_at changed
    data = json.loads(db.read_text())
    new_updated_at = data[0]["updated_at"]
    assert new_updated_at != original_updated_at, "updated_at should be updated after rename"


def test_cli_rename_command_empty_text_returns_error(tmp_path, capsys) -> None:
    """rename command should return error for empty text.

    Issue #2992: Empty text triggers an error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to rename with empty text
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(rename_args)

    # Should return error code 1
    assert result == 1, "rename with empty text should return error code 1"

    captured = capsys.readouterr()
    # Error message should mention empty or cannot be empty
    assert "empty" in captured.err.lower() or "error" in captured.err.lower()


def test_cli_rename_command_nonexistent_todo_returns_error(tmp_path, capsys) -> None:
    """rename command should return error for non-existent todo ID."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a non-existent todo
    rename_args = parser.parse_args(["--db", str(db), "rename", "999", "New text"])
    result = run_command(rename_args)

    # Should return error code 1
    assert result == 1, "rename with non-existent ID should return error code 1"

    captured = capsys.readouterr()
    # Error message should mention not found
    assert "not found" in captured.err.lower() or "error" in captured.err.lower()


def test_cli_rename_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """rename command should sanitize control characters in success message.

    Ensure consistency with other commands (add, done, undone) that sanitize output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Rename with control characters
    rename_args = parser.parse_args(["--db", str(db), "rename", "1", "Task\nWith\x1b[31mColor"])
    result = run_command(rename_args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
