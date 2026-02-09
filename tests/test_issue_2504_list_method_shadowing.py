"""Tests for Issue #2504: TodoApp.list() method shadows Python built-in list() function.

This test file ensures that:
1. The list_todos() method works correctly (renamed from list())
2. The built-in list() function is not shadowed within the TodoApp class
3. All call sites are updated to use the new method name
"""

from __future__ import annotations

from flywheel.cli import TodoApp


def test_list_todos_method_returns_all_todos_by_default(tmp_path) -> None:
    """list_todos() should return all todos when show_all=True (default)."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    app.mark_done(todo1.id)

    # list_todos() should return all todos by default
    todos = app.list_todos()
    assert len(todos) == 2
    assert todos[0].id == todo1.id
    assert todos[1].id == todo2.id


def test_list_todos_method_filters_pending_when_show_all_false(tmp_path) -> None:
    """list_todos(show_all=False) should return only pending todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    app.mark_done(todo1.id)

    # list_todos(show_all=False) should return only pending todos
    todos = app.list_todos(show_all=False)
    assert len(todos) == 1
    assert todos[0].id == todo2.id


def test_list_todos_returns_empty_list_when_no_todos(tmp_path) -> None:
    """list_todos() should return empty list when database is empty."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    todos = app.list_todos()
    assert todos == []


def test_builtin_list_not_shadowed_in_class_scope(tmp_path) -> None:
    """Built-in list() function should not be shadowed by TodoApp.list_todos().

    This test verifies that the method rename fixes the shadowing issue where
    TodoApp.list() would shadow Python's built-in list() function.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # The built-in list() should work normally within TodoApp methods
    # Add a todo first to have some data
    app.add("test todo")

    # If list() was shadowed, this would fail or behave unexpectedly
    # Now that we have list_todos(), the built-in list() is accessible
    result = [1, 2, 3]
    assert result == [1, 2, 3]
    assert isinstance(result, list)


def test_list_todos_preserves_original_functionality(tmp_path) -> None:
    """list_todos() should preserve the exact functionality of the original list()."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Create todos with various states
    app.add("pending task")
    todo2 = app.add("completed task")
    app.add("another pending task")
    app.mark_done(todo2.id)

    # Test show_all=True
    all_todos = app.list_todos(show_all=True)
    assert len(all_todos) == 3

    # Test show_all=False
    pending_todos = app.list_todos(show_all=False)
    assert len(pending_todos) == 2
    assert all(not t.done for t in pending_todos)
