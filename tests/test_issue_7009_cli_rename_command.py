"""Tests for CLI rename command (Issue #7009)."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """Verify 'rename' subcommand updates todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "old text"])
    assert run_command(args) == 0

    # Rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0

    # Verify output shows the rename
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out

    # Verify the change persisted via list
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "old text" not in captured.out


def test_cli_rename_command_rejects_empty_text(tmp_path, capsys) -> None:
    """Verify 'rename' subcommand rejects empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add a todo first
    args = parser.parse_args(["--db", db, "add", "original"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    # Verify error message
    captured = capsys.readouterr()
    assert "empty" in captured.err.lower()

    # Verify original text unchanged
    args = parser.parse_args(["--db", db, "list"])
    run_command(args)
    captured = capsys.readouterr()
    assert "original" in captured.out


def test_cli_rename_command_rejects_nonexistent_id(tmp_path, capsys) -> None:
    """Verify 'rename' subcommand returns error for non-existent ID."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a todo that doesn't exist
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_app_rename_method(tmp_path) -> None:
    """Verify TodoApp.rename() method works directly."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add and rename
    app.add("original")
    renamed = app.rename(1, "renamed")

    assert renamed.id == 1
    assert renamed.text == "renamed"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "renamed"


def test_app_rename_rejects_empty_text(tmp_path) -> None:
    """Verify TodoApp.rename() rejects empty text."""
    app = TodoApp(str(tmp_path / "db.json"))

    app.add("original")

    with pytest.raises(ValueError, match="empty"):
        app.rename(1, "")

    # Verify original unchanged
    assert app.list()[0].text == "original"


def test_app_rename_rejects_nonexistent_id(tmp_path) -> None:
    """Verify TodoApp.rename() raises for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")
