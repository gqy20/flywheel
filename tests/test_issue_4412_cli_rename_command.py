"""Regression tests for issue #4412: CLI rename command."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_existing_todo_text(tmp_path, capsys) -> None:
    """CLI rename command should update existing todo text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    # Add a todo first
    added = app.add("original text")
    assert added.id == 1

    # Use CLI to rename
    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "new text"])
    result = run_command(args)

    assert result == 0
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out

    # Verify the text was updated
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_cli_rename_returns_error_for_non_existent_todo_id(tmp_path, capsys) -> None:
    """CLI rename should return error for non-existent todo id."""
    db = str(tmp_path / "cli.json")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "99", "new text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "not found" in captured.out or "not found" in captured.err


def test_cli_rename_strips_whitespace_from_text(tmp_path, capsys) -> None:
    """CLI rename should strip whitespace from text like add does."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    app.add("original")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", "  padded text  "])
    result = run_command(args)

    assert result == 0
    todos = app.list()
    assert todos[0].text == "padded text"


def test_cli_rename_rejects_empty_text(tmp_path, capsys) -> None:
    """CLI rename should reject empty text."""
    db = str(tmp_path / "cli.json")
    app = TodoApp(db)

    app.add("original")

    parser = build_parser()
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()
