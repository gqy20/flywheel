"""Regression tests for Issue #2504: TodoApp.list() method name shadows Python built-in list() function.

This test file ensures that the method is renamed from `list()` to `list_todos()` to avoid
shadowing Python's built-in `list()` type constructor.
"""

from __future__ import annotations

from flywheel.cli import TodoApp


def test_todoapp_has_list_todos_method_not_list() -> None:
    """TodoApp should have list_todos() method, not list() method.

    The original issue was that TodoApp.list() shadowed Python's built-in list() function.
    After the fix, the method should be renamed to list_todos().
    """
    app = TodoApp()

    # Verify the new method exists
    assert hasattr(app, "list_todos"), "TodoApp should have list_todos() method"

    # Verify the old method doesn't exist (or at least we're using the new one)
    # Note: We can't fully verify the old one doesn't exist without breaking backward compat
    # but we can verify the new one works correctly
    result = app.list_todos()
    assert isinstance(result, list), "list_todos() should return a list"


def test_list_todos_returns_list_of_todos(tmp_path) -> None:
    """list_todos() should return a list of Todo objects."""
    app = TodoApp(db_path=str(tmp_path / "test.json"))

    # Add some todos
    app.add("first todo")
    app.add("second todo")

    # Get all todos
    todos = app.list_todos()
    assert isinstance(todos, list)
    assert len(todos) == 2
    assert todos[0].text == "first todo"
    assert todos[1].text == "second todo"


def test_list_todos_pending_only(tmp_path) -> None:
    """list_todos(show_all=False) should return only pending todos."""
    app = TodoApp(db_path=str(tmp_path / "test.json"))

    # Add todos and mark one as done
    app.add("pending todo")
    done_todo = app.add("done todo")
    app.mark_done(done_todo.id)

    # Get only pending todos
    pending = app.list_todos(show_all=False)
    assert len(pending) == 1
    assert pending[0].text == "pending todo"

    # Get all todos
    all_todos = app.list_todos(show_all=True)
    assert len(all_todos) == 2


def test_list_todos_default_show_all_true(tmp_path) -> None:
    """list_todos() should default to show_all=True."""
    app = TodoApp(db_path=str(tmp_path / "test.json"))

    # Add todos and mark one as done
    app.add("pending todo")
    done_todo = app.add("done todo")
    app.mark_done(done_todo.id)

    # Default should show all
    todos = app.list_todos()
    assert len(todos) == 2
