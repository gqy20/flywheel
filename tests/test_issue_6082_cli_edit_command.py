"""Regression tests for Issue #6082: Expose rename method in CLI to allow editing todo text.

This test file ensures that the CLI has an 'edit' subcommand that allows users to
update todo text using the existing Todo.rename() method.

Issue #6082 acceptance criteria:
- CLI accepts 'todo edit <id> <new_text>' command
- Running edit updates the todo text and updated_at timestamp
- Error is shown if todo id not found or text is empty
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should update todo text.

    Issue #6082: CLI should expose Todo.rename() method via edit subcommand.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo with a typo
    add_args = parser.parse_args(["--db", str(db), "add", "Buy milm"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit the todo to fix the typo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Buy milk"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Edited #1" in captured.out
    assert "Buy milk" in captured.out

    # Verify the text was actually updated
    list_args = parser.parse_args(["--db", str(db), "list"])
    run_command(list_args)
    captured = capsys.readouterr()
    assert "Buy milk" in captured.out
    assert "Buy milm" not in captured.out


def test_cli_edit_command_shows_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should show error if todo id not found.

    Issue #6082: Error is shown if todo id not found.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should return 1 for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_shows_error_for_empty_text(tmp_path, capsys) -> None:
    """edit command should show error if text is empty.

    Issue #6082: Error is shown if text is empty.
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
    assert result == 1, "edit command should return 1 for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_control_characters(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    Following the pattern of Issue #2083, edit command should escape
    control characters in output to prevent terminal injection.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original task"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Task\nWith\x1b[31mRed\x1b[0m"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\x1b" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\x1b" not in captured.out
