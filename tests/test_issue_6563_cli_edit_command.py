"""Regression tests for Issue #6563: CLI lacks rename command.

This test file ensures that CLI supports an 'edit' command that allows
users to rename todo text via the command line. The Todo.rename() method
already exists but was not exposed via CLI.

Issue #6563 acceptance criteria:
- CLI supports 'todo edit <id> <new_text>' command
- Successful execution outputs similar to 'Renamed #1: new text'
- Non-existent id returns clear error message
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_renames_existing_todo(tmp_path, capsys) -> None:
    """edit command should rename existing todo text.

    Issue #6563: CLI should support 'edit' command to rename todo text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Now edit it
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "New text"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "New text" in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return error for non-existent todo id.

    Issue #6563: Non-existent id should return clear error message.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to edit a non-existent todo
    edit_args = parser.parse_args(["--db", str(db), "edit", "999", "New text"])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """edit command should return error for empty text.

    Issue #6563: Empty text should return error (Todo.rename() raises ValueError).
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Try to edit with empty text (only whitespace)
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(edit_args)
    assert result == 1, "edit command should fail for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_sanitizes_text_in_output(tmp_path, capsys) -> None:
    """edit command should sanitize text in success message.

    Issue #6563 + Issue #2083: Success message should use _sanitize_text.
    """
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    add_args = parser.parse_args(["--db", str(db), "add", "Original text"])
    run_command(add_args)
    capsys.readouterr()  # Clear add output

    # Edit with control characters
    edit_args = parser.parse_args(["--db", str(db), "edit", "1", "New\nText"])
    result = run_command(edit_args)
    assert result == 0, "edit command should succeed"

    captured = capsys.readouterr()
    # Should contain escaped representation
    assert "\\n" in captured.out
    # Should NOT contain actual newline
    assert "\n" not in captured.out.strip()
