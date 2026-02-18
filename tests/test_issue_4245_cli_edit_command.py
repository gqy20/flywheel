"""Regression tests for Issue #4245: CLI edit command for Todo.rename.

This test file ensures that the CLI exposes an edit command that allows
users to rename todo items using the Todo.rename method.
"""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_edit_command_modifies_todo_text(tmp_path, capsys) -> None:
    """CLI edit command should successfully modify todo text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original task"])
    assert run_command(args) == 0

    # Edit the todo
    args = parser.parse_args(["--db", db, "edit", "1", "updated task"])
    assert run_command(args) == 0

    # Verify output shows the edit
    captured = capsys.readouterr()
    assert "Edited #1" in captured.out
    assert "updated task" in captured.out

    # Verify the change persisted
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    captured = capsys.readouterr()
    assert "updated task" in captured.out
    assert "original task" not in captured.out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """CLI edit command should return error for non-existent todo id."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to edit a todo that doesn't exist
    args = parser.parse_args(["--db", db, "edit", "99", "new text"])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "not found" in captured.err.lower() or "not found" in captured.out.lower()


def test_cli_edit_command_returns_error_for_empty_text(tmp_path, capsys) -> None:
    """CLI edit command should return error for empty text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "test task"])
    assert run_command(args) == 0

    # Try to edit with empty text
    args = parser.parse_args(["--db", db, "edit", "1", ""])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_cli_edit_command_returns_error_for_whitespace_only_text(
    tmp_path, capsys
) -> None:
    """CLI edit command should return error for whitespace-only text."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "test task"])
    assert run_command(args) == 0

    # Try to edit with whitespace-only text
    args = parser.parse_args(["--db", db, "edit", "1", "   "])
    assert run_command(args) == 1

    captured = capsys.readouterr()
    assert "empty" in captured.err.lower() or "empty" in captured.out.lower()


def test_app_edit_modifies_todo_and_persists(tmp_path) -> None:
    """TodoApp.edit should modify todo text and save to storage."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original")
    assert added.text == "original"

    # Edit the todo
    edited = app.edit(1, "modified")
    assert edited.text == "modified"
    assert edited.id == 1

    # Verify persistence by listing
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "modified"


def test_app_edit_raises_error_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.edit should raise ValueError for non-existent id."""
    app = TodoApp(str(tmp_path / "db.json"))

    try:
        app.edit(99, "new text")
        raise AssertionError("Expected ValueError for non-existent id")
    except ValueError as e:
        assert "not found" in str(e).lower()


def test_app_edit_raises_error_for_empty_text(tmp_path) -> None:
    """TodoApp.edit should raise ValueError for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("test")

    try:
        app.edit(1, "")
        raise AssertionError("Expected ValueError for empty text")
    except ValueError as e:
        assert "empty" in str(e).lower()
