"""Regression tests for Issue #6563: CLI lacks rename command but Todo class has rename method.

This test file ensures that CLI exposes the rename functionality through an 'edit' command
that allows users to modify todo text without having to delete and recreate the todo.

Issue #6563 specifically highlights that Todo.rename() method exists (todo.py:50-55) but
CLI does not expose this functionality.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_modifies_existing_todo_text(tmp_path, capsys) -> None:
    """edit command should modify the text of an existing todo.

    Issue #6563: CLI should support 'todo edit <id> <new_text>' command.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should confirm the rename
    assert "Renamed" in captured.out or "Updated" in captured.out or "#1" in captured.out
    assert "Updated text" in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id.

    Issue #6563: edit command should return clear error for non-existent id.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "Error" in captured.err or "not found" in captured.err.lower()


def test_cli_edit_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """edit command should return error for empty text.

    Issue #6563: edit command should return clear error for empty text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Some text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for empty text"

    captured = capsys.readouterr()
    assert "Error" in captured.err or "empty" in captured.err.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    This ensures consistency with other CLI commands (add, done, undone) that
    sanitize user-supplied text before output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "Updated\nWith\rControls"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Output should contain escaped representation
    assert "\\n" in captured.out
    assert "\\r" in captured.out
    # Output should NOT contain actual control characters
    assert "\n" not in captured.out.strip()
    assert "\r" not in captured.out
