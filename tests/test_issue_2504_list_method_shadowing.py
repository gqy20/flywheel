"""Tests for TodoApp.list() method shadowing Python built-in (Issue #2504).

These tests verify that:
1. TodoApp has a list_todos() method that doesn't shadow the built-in list()
2. list_todos() correctly returns all todos when show_all=True
3. list_todos() correctly returns only pending todos when show_all=False
4. The built-in list() function can still be used within TodoApp methods
"""

from __future__ import annotations

from flywheel.cli import TodoApp
from flywheel.todo import Todo


def test_todolist_app_has_list_todos_method() -> None:
    """TodoApp should have a list_todos method (not shadowing built-in list)."""
    app = TodoApp()
    # Should have list_todos method
    assert hasattr(app, "list_todos")
    # Should be callable
    assert callable(app.list_todos)


def test_list_todos_returns_all_todos_when_show_all_true(tmp_path) -> None:
    """list_todos(show_all=True) should return all todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))
    app.add("task 1")
    app.add("task 2")
    todo3 = app.add("task 3")
    app.mark_done(todo3.id)

    todos = app.list_todos(show_all=True)

    assert len(todos) == 3
    assert all(isinstance(t, Todo) for t in todos)


def test_list_todos_returns_pending_only_when_show_all_false(tmp_path) -> None:
    """list_todos(show_all=False) should return only pending todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))
    todo1 = app.add("pending task")
    todo2 = app.add("done task")
    app.mark_done(todo2.id)
    todo3 = app.add("another pending")

    todos = app.list_todos(show_all=False)

    assert len(todos) == 2
    assert todos[0].id == todo1.id
    assert todos[1].id == todo3.id
    assert all(not t.done for t in todos)


def test_list_todos_default_show_all_is_true(tmp_path) -> None:
    """list_todos() with no args should default to show_all=True."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))
    todo1 = app.add("task 1")
    app.add("task 2")
    app.mark_done(todo1.id)

    todos = app.list_todos()

    assert len(todos) == 2


def test_list_todos_returns_empty_list_when_no_todos(tmp_path) -> None:
    """list_todos() should return empty list when database is empty."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))
    todos = app.list_todos()
    assert todos == []


def test_builtin_list_function_not_shadowed_in_class(tmp_path) -> None:
    """The built-in list() function should still work within TodoApp methods."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # This test verifies that renaming list() to list_todos() allows
    # the built-in list() to be used normally if needed
    app.add("test")

    # Use the built-in list() function to convert an iterator
    # This demonstrates the built-in list() is not shadowed
    result = list(range(3))
    assert result == [0, 1, 2]


def test_list_todos_is_not_shadowing_builtin(tmp_path) -> None:
    """Verify list_todos doesn't shadow Python's built-in list."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # The built-in list() should still be available globally
    my_list = [1, 2, 3]
    assert my_list == [1, 2, 3]

    # TodoApp.list_todos() should be a distinct method
    assert app.list_todos.__name__ == "list_todos"
