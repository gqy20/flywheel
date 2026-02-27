"""Regression tests for Issue #6001: Add rename command to CLI.

This test file ensures that the CLI supports the 'rename' subcommand
to modify todo text, since Todo.rename() method already exists but
there was no CLI entry point for it.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists(tmp_path, capsys) -> None:
    """CLI should support 'rename' subcommand."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Now rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0

    # Verify rename worked
    captured = capsys.readouterr()
    assert "Renamed" in captured.out
    assert "new text" in captured.out


def test_cli_rename_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """Rename command should return error for non-existent todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_rejects_empty_string(tmp_path, capsys) -> None:
    """Rename command should reject empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method(tmp_path) -> None:
    """TodoApp should have rename method."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    assert added.id == 1
    assert app.list()[0].text == "original"

    renamed = app.rename(1, "new text")
    assert renamed.id == 1
    assert renamed.text == "new text"
    assert app.list()[0].text == "new text"


def test_app_rename_returns_error_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename should raise error for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(99, "new text")
        raise AssertionError("Expected ValueError for missing todo")
    except ValueError as e:
        assert "not found" in str(e).lower()
