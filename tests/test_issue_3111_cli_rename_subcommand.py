"""Regression tests for Issue #3111: CLI缺少rename子命令.

This test file ensures that the CLI exposes the rename functionality
that already exists in the Todo data model and TodoApp.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_subcommand_exists() -> None:
    """The rename subcommand should be available in the CLI parser."""
    parser = build_parser()
    # This should not raise an error if 'rename' is a valid subcommand
    args = parser.parse_args(["--db", ".test.json", "rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_run_command_rename_success(tmp_path, capsys) -> None:
    """run_command should handle rename command and return 0 on success."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "old text"])
    assert run_command(args) == 0

    # Then rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)
    assert result == 0

    # Verify the text was changed
    captured = capsys.readouterr()
    assert "Renamed" in captured.out or "rename" in captured.out.lower()
    assert "new text" in captured.out


def test_cli_run_command_rename_updates_storage(tmp_path) -> None:
    """rename command should persist the change to storage."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo
    app.add("original text")

    # Use CLI to rename
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "updated text"])
    result = run_command(args)
    assert result == 0

    # Verify storage has the updated text
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "updated text"


def test_cli_run_command_rename_nonexistent_returns_error(tmp_path, capsys) -> None:
    """rename command should return 1 and output error for non-existent ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_run_command_rename_empty_text_returns_error(tmp_path, capsys) -> None:
    """rename command should return 1 and output error for empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)
    app.add("some text")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()
