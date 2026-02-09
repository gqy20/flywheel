"""Regression tests for Issue #2480: TodoApp.list() method name shadows Python built-in list().

This test file verifies that:
1. The TodoApp class uses list_todos() method instead of list()
2. The method works correctly for both show_all=True and show_all=False
3. The old list() method name is no longer available (AttributeError)
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_list_todos_returns_all_todos_when_show_all_true(tmp_path) -> None:
    """list_todos(show_all=True) should return all todos including completed ones."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    app.add("first todo")
    app.add("second todo")
    todo3 = app.add("third todo")
    app.mark_done(todo3.id)

    # Get all todos
    todos = app.list_todos(show_all=True)
    assert len(todos) == 3
    assert todos[0].text == "first todo"
    assert todos[1].text == "second todo"
    assert todos[2].text == "third todo"
    assert todos[2].done is True


def test_list_todos_returns_pending_only_when_show_all_false(tmp_path) -> None:
    """list_todos(show_all=False) should return only pending (not done) todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    app.add("pending todo 1")
    todo2 = app.add("completed todo")
    app.add("pending todo 2")
    app.mark_done(todo2.id)

    # Get only pending todos
    todos = app.list_todos(show_all=False)
    assert len(todos) == 2
    assert todos[0].text == "pending todo 1"
    assert todos[1].text == "pending todo 2"
    assert all(not t.done for t in todos)


def test_list_todos_default_show_all_is_true(tmp_path) -> None:
    """list_todos() should default to show_all=True."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add todos including a completed one
    app.add("pending todo")
    todo2 = app.add("completed todo")
    app.mark_done(todo2.id)

    # Default behavior should return all todos
    todos = app.list_todos()
    assert len(todos) == 2


def test_list_todos_returns_empty_list_when_no_todos(tmp_path) -> None:
    """list_todos() should return empty list when database is empty."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    todos = app.list_todos()
    assert todos == []


def test_todoapp_no_longer_shadows_builtin_list(tmp_path) -> None:
    """TodoApp should not have a list() method that shadows the built-in list().

    This test ensures the old list() method has been renamed to list_todos()
    to avoid shadowing Python's built-in list type constructor.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # The old list() method should not exist
    with pytest.raises(AttributeError):
        app.list()  # type: ignore


def test_list_todos_works_with_cli_run_command(tmp_path, capsys) -> None:
    """list_todos() should work correctly when called from CLI run_command."""
    from flywheel.cli import build_parser, run_command

    db = str(tmp_path / "cli.json")
    parser = build_parser()

    # Add todos via CLI
    args = parser.parse_args(["--db", db, "add", "task 1"])
    run_command(args)

    args = parser.parse_args(["--db", db, "add", "task 2"])
    run_command(args)

    # List todos via CLI
    args = parser.parse_args(["--db", db, "list"])
    assert run_command(args) == 0

    captured = capsys.readouterr()
    assert "task 1" in captured.out
    assert "task 2" in captured.out
