"""Regression tests for Issue #3058: Add 'todo edit' CLI command.

This test file ensures that the CLI exposes the Todo.rename() method
through an 'edit' subcommand, allowing users to modify todo text after creation.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """The 'edit' command should update the text of an existing todo.

    Acceptance criteria:
    - 'todo edit <id> <text>' successfully updates todo text
    """
    db = tmp_path / "db.json"

    parser = build_parser()

    # First, add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"
    capsys.readouterr()  # Clear captured output

    # Now edit the todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "new text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    # Verify edit command output
    captured = capsys.readouterr()
    assert "Edited #1" in captured.out
    assert "new text" in captured.out

    # Verify the text was actually updated in storage
    list_args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(list_args)
    assert result == 0

    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_edit_command_nonexistent_id_returns_error(tmp_path, capsys) -> None:
    """The 'edit' command should return error for non-existent id.

    Acceptance criteria:
    - 'todo edit 999 x' returns error for non-existent id
    """
    db = tmp_path / "db.json"

    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "some text"])
    result = run_command(edit_args)

    # Should return 1 (error exit code)
    assert result == 1, "edit command should return 1 for non-existent id"

    captured = capsys.readouterr()
    # Error should be in stderr or stdout
    combined = (captured.err + captured.out).lower()
    assert "not found" in combined or "error" in combined


def test_cli_edit_command_empty_text_raises_error(tmp_path, capsys) -> None:
    """The 'edit' command should reject empty text.

    Acceptance criteria:
    - Empty text triggers ValueError per rename() validation
    """
    db = tmp_path / "db.json"

    parser = build_parser()

    # First, add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "some todo"])
    result = run_command(add_args)
    assert result == 0, "add command should succeed"

    # Try to edit with empty text
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(edit_args)

    # Should return 1 (error exit code)
    assert result == 1, "edit command should return 1 for empty text"

    captured = capsys.readouterr()
    # Error should be in stderr or stdout
    combined = (captured.err + captured.out).lower()
    assert "empty" in combined or "error" in combined
