"""Regression tests for Issue #3058: CLI lacks 'edit' command to expose Todo.rename().

This test file ensures that the CLI provides an 'edit' command that allows users
to modify todo text after creation, using the existing Todo.rename() method.
"""

from __future__ import annotations

from flywheel.cli import build_parser, main, run_command


def test_cli_edit_command_exists() -> None:
    """The CLI should have an 'edit' subcommand."""
    parser = build_parser()
    # Parse with edit command - should not raise an error
    args = parser.parse_args(["edit", "1", "new text"])
    assert args.command == "edit"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_edit_command_updates_todo_text(tmp_path, capsys) -> None:
    """'todo edit 1 new text' should successfully update todo text."""
    db = tmp_path / "test.json"

    # First add a todo
    result = main(["--db", str(db), "add", "old text"])
    assert result == 0

    # Edit the todo
    result = main(["--db", str(db), "edit", "1", "new text"])
    assert result == 0

    # Verify the text was updated
    captured = capsys.readouterr()
    assert "Edited #1" in captured.out or "new text" in captured.out

    # List todos to verify the change persisted
    result = main(["--db", str(db), "list"])
    assert result == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "old text" not in captured.out


def test_cli_edit_command_non_existent_id_returns_error(tmp_path, capsys) -> None:
    """'todo edit 999 x' should return error for non-existent id."""
    db = tmp_path / "test.json"

    # Try to edit a non-existent todo
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "edit", "999", "x"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_empty_text_raises_error(tmp_path, capsys) -> None:
    """Empty text should trigger ValueError per rename() validation."""
    db = tmp_path / "test.json"

    # First add a todo
    result = main(["--db", str(db), "add", "test todo"])
    assert result == 0

    # Try to edit with empty text
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "edit", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_whitespace_only_text_raises_error(tmp_path, capsys) -> None:
    """Whitespace-only text should trigger ValueError after stripping."""
    db = tmp_path / "test.json"

    # First add a todo
    result = main(["--db", str(db), "add", "test todo"])
    assert result == 0

    # Try to edit with whitespace-only text
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "edit", "1", "   "])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()
