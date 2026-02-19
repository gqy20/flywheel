"""Tests for CLI rename command - Issue #4412.

This test file verifies that the CLI exposes Todo.rename() functionality.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_existing_todo_text(tmp_path, capsys) -> None:
    """CLI rename command should update existing todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "updated task"])
    assert run_command(args) == 0

    # Verify the rename output
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "updated task" in captured.out

    # Verify the todo was actually renamed
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "updated task" in captured.out
    assert "original task" not in captured.out


def test_cli_rename_returns_error_for_nonexistent_todo_id(tmp_path, capsys) -> None:
    """CLI rename should return error for non-existent todo id."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_rejects_empty_text(tmp_path, capsys) -> None:
    """CLI rename should reject empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method(tmp_path) -> None:
    """TodoApp should have a rename method that calls Todo.rename()."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original")
    assert added.id == 1
    assert app.list()[0].text == "original"

    # Rename the todo
    renamed = app.rename(1, "updated")
    assert renamed.text == "updated"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "updated"


def test_app_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent id."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")
