"""Regression tests for Issue #6562: CLI missing 'rename' command.

This test file ensures that the CLI exposes the Todo.rename() functionality
through a 'todo rename <id> <new_text>' command.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_rename_command_updates_todo_text(tmp_path, capsys) -> None:
    """CLI should accept 'todo rename <id> <new_text>' and update todo.text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0

    # Rename the todo
    args = parser.parse_args(["--db", db, "rename", "1", "renamed text"])
    assert run_command(args) == 0

    # Verify the rename output
    captured = capsys.readouterr()
    assert "Renamed #1" in captured.out
    assert "renamed text" in captured.out

    # Verify via list command
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "renamed text" in captured.out
    assert "original text" not in captured.out


def test_cli_rename_command_returns_error_for_missing_todo(tmp_path, capsys) -> None:
    """Running 'todo rename 999 x' should return exit code 1 with not found error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to rename non-existent todo
    args = parser.parse_args(["--db", db, "rename", "999", "x"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.out.lower() or "not found" in captured.err.lower()


def test_cli_rename_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """Running 'todo rename 1 ""' should return exit code 1 with empty error."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "test"])
    assert run_command(args) == 0

    # Try to rename with empty text
    args = parser.parse_args(["--db", db, "rename", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "empty" in captured.out.lower() or "empty" in captured.err.lower()


def test_app_rename_method(tmp_path) -> None:
    """TodoApp should have a rename method that calls Todo.rename()."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    assert added.id == 1
    assert added.text == "original"

    renamed = app.rename(1, "renamed")
    assert renamed.id == 1
    assert renamed.text == "renamed"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed"


def test_app_rename_raises_for_missing_todo(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.rename(999, "x")
        raise AssertionError("Expected ValueError for non-existent todo")
    except ValueError as e:
        assert "not found" in str(e).lower()


def test_app_rename_raises_for_empty_text(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("test")

    try:
        app.rename(1, "")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()
