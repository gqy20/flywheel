"""Tests for issue #4118: Add rename CLI command."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_exists_in_parser() -> None:
    """Verify 'rename' subparser is registered in build_parser()."""
    parser = build_parser()
    # Test that 'rename' command is parseable
    args = parser.parse_args(["rename", "1", "new text"])
    assert args.command == "rename"
    assert args.id == 1
    assert args.text == "new text"


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Verify rename command updates todo text and returns success."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename it via CLI
    args = parser.parse_args(["--db", db, "rename", "1", "updated text"])
    result = run_command(args)
    assert result == 0

    # Verify the text was updated
    out = capsys.readouterr()
    assert "Renamed #1" in out.out
    assert "updated text" in out.out

    # Verify via list command
    args = parser.parse_args(["--db", db, "list"])
    run_command(args)
    out = capsys.readouterr()
    assert "updated text" in out.out
    assert "original text" not in out.out


def test_cli_rename_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """Verify rename command returns error for non-existent todo ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """Verify rename command returns error for empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)
    assert result == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method(tmp_path) -> None:
    """Verify TodoApp.rename() method works correctly."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original")
    assert added.id == 1
    assert app.list()[0].text == "original"

    # Rename via app method
    renamed = app.rename(1, "renamed")
    assert renamed.id == 1
    assert renamed.text == "renamed"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed"


def test_app_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """Verify TodoApp.rename() raises error for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")


def test_app_rename_raises_for_empty_text(tmp_path) -> None:
    """Verify TodoApp.rename() raises error for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("original")

    with pytest.raises(ValueError, match="empty"):
        app.rename(1, "")

    # Verify original text unchanged
    assert app.list()[0].text == "original"
