"""Regression tests for Issue #4245: CLI lacks edit command.

This test file ensures that the CLI exposes the Todo.rename method
via an `edit` subcommand.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_edit_command_successfully_modifies_text(tmp_path, capsys) -> None:
    """CLI should support `todo edit <id> <new_text>` command.

    The edit command should call Todo.rename method and save changes.
    """
    db = tmp_path / "db.json"

    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(args)
    assert result == 0

    # Now edit the todo
    args = parser.parse_args(["--db", str(db), "edit", "1", "new text"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "Edited" in captured.out or "edit" in captured.out.lower()
    assert "new text" in captured.out

    # Verify the change persisted
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """edit command should return clear error for non-existent id."""
    db = tmp_path / "db.json"

    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "edit", "999", "new text"])

    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """edit command should return clear error for empty text."""
    db = tmp_path / "db.json"

    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(args)
    assert result == 0

    # Try to edit with empty text
    args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_strips_whitespace(tmp_path, capsys) -> None:
    """edit command should strip whitespace from text (like add command)."""
    db = tmp_path / "db.json"

    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "original text"])
    result = run_command(args)
    assert result == 0

    # Edit with whitespace around text
    args = parser.parse_args(["--db", str(db), "edit", "1", "  trimmed text  "])
    result = run_command(args)
    assert result == 0

    # Verify the whitespace was stripped
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "trimmed text" in captured.out
