"""Tests for issue #3531: CLI 'edit' command to expose Todo.rename() functionality."""

from __future__ import annotations

from flywheel.cli import TodoApp, build_parser, run_command


def test_cli_edit_command_renames_todo(tmp_path, capsys) -> None:
    """Issue #3531: 'todo edit <id> <text>' should rename a todo."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # First add a todo
    args = parser.parse_args(["--db", db, "add", "original text"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    # Now edit the todo
    args = parser.parse_args(["--db", db, "edit", "1", "new text"])
    assert run_command(args) == 0
    capsys.readouterr()  # Clear output

    # Verify the edit worked by listing
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0
    out = capsys.readouterr().out
    assert "new text" in out
    assert "original text" not in out


def test_cli_edit_command_returns_error_for_nonexistent_id(tmp_path, capsys) -> None:
    """Issue #3531: 'todo edit 999 text' on non-existent id should return error code 1."""
    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Try to edit a non-existent todo
    args = parser.parse_args(["--db", db, "edit", "999", "some text"])
    result = run_command(args)

    assert result == 1
    captured = capsys.readouterr()
    assert "Todo #999 not found" in captured.err


def test_app_edit_method(tmp_path) -> None:
    """Issue #3531: TodoApp.edit() should rename a todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original")
    assert added.id == 1
    assert app.list()[0].text == "original"

    # Edit the todo
    edited = app.edit(1, "renamed")
    assert edited.id == 1
    assert edited.text == "renamed"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "renamed"


def test_app_edit_raises_for_nonexistent_id(tmp_path) -> None:
    """Issue #3531: TodoApp.edit() should raise ValueError for non-existent id."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Try to edit non-existent todo
    try:
        app.edit(999, "some text")
        raise AssertionError("Expected ValueError for non-existent todo")
    except ValueError as e:
        assert "Todo #999 not found" in str(e)
