"""Regression tests for Issue #3924: CLI missing edit command.

This test file ensures that the CLI exposes an `edit` command to call
the existing Todo.rename() method, allowing users to modify todo text
through the CLI instead of having to delete and re-add.

Issue #3924 acceptance criteria:
- User can edit todo text via `todo edit <id> <new_text>` command
- Empty or whitespace-only text returns a clear error message
- Success shows confirmation message like "Updated #1: new text"
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_successfully_updates_todo_text(tmp_path, capsys) -> None:
    """edit command should successfully update todo text.

    Issue #3924: User can edit todo text via `todo edit <id> <new_text>` command.
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
    assert "Updated #1:" in captured.out
    assert "Updated text" in captured.out


def test_cli_edit_command_rejects_empty_text(tmp_path, capsys) -> None:
    """edit command should reject empty or whitespace-only text.

    Issue #3924: Empty or whitespace-only text returns a clear error message.
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
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_edit_command_rejects_whitespace_only_text(tmp_path, capsys) -> None:
    """edit command should reject whitespace-only text.

    Issue #3924: Whitespace-only text returns a clear error message.
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

    assert result == 1, "edit command should fail for whitespace-only text"
    captured = capsys.readouterr()
    assert "error" in captured.err.lower() or "error" in captured.out.lower()


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id.

    Issue #3924 minimum test plan: test editing non-existent id returns error.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)

    assert result == 1, "edit command should fail for non-existent id"
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_sanitizes_control_characters(tmp_path, capsys) -> None:
    """edit command should sanitize control characters in success message.

    Ensures consistency with add/done/undone commands that sanitize output.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(
        ["--db", str(db), "edit", "1", "Updated\x1b[31mRed\x1b[0m"]
    )
    result = run_command(edit_args)

    assert result == 0, "edit command should succeed"
    captured = capsys.readouterr()
    # Output should contain escaped representation, not actual ESC character
    assert "\\x1b" in captured.out
    assert "\x1b" not in captured.out
