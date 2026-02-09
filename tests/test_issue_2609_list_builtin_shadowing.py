"""Regression tests for Issue #2609: Method name 'list' shadows Python built-in function.

This test file demonstrates that the 'list' method name shadows Python's built-in
list() function, which is a code smell and can cause confusion or errors.
"""

from __future__ import annotations

from flywheel.cli import TodoApp


def test_list_method_does_not_shadow_builtin_list_constructor(tmp_path) -> None:
    """TodoApp should not shadow Python's built-in list() function.

    The method named 'list' in TodoApp shadows Python's built-in list() function,
    which is problematic because:
    1. It makes the code less readable (unclear if it's the built-in or method)
    2. It prevents using the built-in list() naturally within methods
    3. It's a common anti-pattern flagged by linters

    After the fix, the method should be renamed to list_todos().
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    app.add("test todo")

    # Before fix: app.list() shadows built-in list()
    # After fix: app.list_todos() does NOT shadow built-in list()

    # Verify that we can use the built-in list() function naturally
    # within the same context as the app method
    some_data = [1, 2, 3]
    list(some_data)  # This should always work (built-in)

    # The renamed method should work
    assert hasattr(app, "list_todos"), "TodoApp should have list_todos() method, not list()"

    # The old 'list' method should not exist
    assert not hasattr(app, "list"), "TodoApp should not have a method named 'list' that shadows the built-in"


def test_list_todos_returns_correct_todos(tmp_path) -> None:
    """list_todos() should return the correct list of Todo objects."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")

    # Test list_todos returns all todos
    all_todos = app.list_todos(show_all=True)
    assert len(all_todos) == 2
    assert all_todos[0].id == todo1.id
    assert all_todos[1].id == todo2.id


def test_list_todos_filters_pending_when_show_all_false(tmp_path) -> None:
    """list_todos(show_all=False) should return only pending todos."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add todos and mark one as done
    todo1 = app.add("pending todo")
    todo2 = app.add("completed todo")
    app.mark_done(todo2.id)

    # Test list_todos filters by completion status
    pending_todos = app.list_todos(show_all=False)
    assert len(pending_todos) == 1
    assert pending_todos[0].id == todo1.id
    assert not pending_todos[0].done

    all_todos = app.list_todos(show_all=True)
    assert len(all_todos) == 2
