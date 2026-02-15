"""Tests for issue #3545: CLI rename command.

The Todo.rename() method exists but the CLI does not expose a 'rename' command.
These tests verify the CLI rename command functionality.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_success(tmp_path, capsys) -> None:
    """Test successful rename via CLI."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename it
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "new text" in captured.out

    # Verify the change persisted
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "new text" in captured.out
    assert "original text" not in captured.out


def test_cli_rename_command_nonexistent_id(tmp_path, capsys) -> None:
    """Test rename with non-existent ID returns error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename a non-existent todo
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_command_empty_text(tmp_path, capsys) -> None:
    """Test rename with empty text returns error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1
    captured = capsys.readouterr()
    assert "cannot be empty" in captured.out or "cannot be empty" in captured.err


def test_app_rename_method_success(tmp_path) -> None:
    """Test TodoApp.rename() method works correctly."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original")
    assert added.id == 1

    # Rename it
    renamed = app.rename(1, "renamed")
    assert renamed.text == "renamed"
    assert renamed.id == 1

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed"


def test_app_rename_method_nonexistent_id(tmp_path) -> None:
    """Test TodoApp.rename() raises for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="not found"):
        app.rename(99, "new text")


def test_app_rename_method_empty_text(tmp_path) -> None:
    """Test TodoApp.rename() raises for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("original")

    with pytest.raises(ValueError, match="cannot be empty"):
        app.rename(1, "")
