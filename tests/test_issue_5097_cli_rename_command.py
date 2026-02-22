"""Regression tests for Issue #5097: Todo.rename() not exposed via CLI.

This test file ensures that the 'rename' subcommand is available in the CLI
and properly calls the Todo.rename() method.
"""

from __future__ import annotations

from flywheel.cli import build_parser, run_command


def test_cli_rename_command_exists() -> None:
    """The 'rename' subcommand should be recognized by the parser."""
    parser = build_parser()
    # Should not raise an error when parsing 'rename' command
    args = parser.parse_args(["--db", ".test.json", "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Calling 'todo rename <id> <text>' should update the todo's text."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "old text"])
    result = run_command(args)
    assert result == 0, "add command should succeed"

    # Now rename it
    args = parser.parse_args(["--db", str(db), "rename", "1", "new text"])
    result = run_command(args)
    assert result == 0, "rename command should succeed"

    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out

    # Verify the change persisted
    args = parser.parse_args(["--db", str(db), "list"])
    result = run_command(args)
    assert result == 0

    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "old text" not in captured.out


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """Renaming a non-existent todo should return error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # Try to rename a todo that doesn't exist
    args = parser.parse_args(["--db", str(db), "rename", "999", "new text"])
    result = run_command(args)
    assert result == 1, "rename command should fail for non-existent id"

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """Renaming with empty text should return error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "some text"])
    result = run_command(args)
    assert result == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", str(db), "rename", "1", ""])
    result = run_command(args)
    assert result == 1, "rename command should fail for empty text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_rename_command_whitespace_only(tmp_path, capsys) -> None:
    """Renaming with whitespace-only text should return error."""
    db = tmp_path / "db.json"
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", str(db), "add", "some text"])
    result = run_command(args)
    assert result == 0

    # Try to rename with whitespace-only text
    args = parser.parse_args(["--db", str(db), "rename", "1", "   "])
    result = run_command(args)
    assert result == 1, "rename command should fail for whitespace-only text"

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()
