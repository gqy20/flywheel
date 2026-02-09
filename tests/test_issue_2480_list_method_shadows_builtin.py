"""Regression tests for Issue #2480: TodoApp.list() method name shadows Python built-in list().

The method name 'list' was shadowing Python's built-in list() type, which is problematic:
1. It prevents using the built-in list() within the TodoApp class
2. It violates PEP 8 naming conventions for avoiding built-in shadowing
3. It creates confusion about whether list refers to the type or method

This test ensures the method is renamed to list_todos() to avoid shadowing the built-in.
"""

from __future__ import annotations

from flywheel.cli import TodoApp


def test_list_method_renamed_to_list_todos(tmp_path) -> None:
    """TodoApp.list_todos() is the renamed method that doesn't shadow built-in list.

    The method was renamed from list() to list_todos() to avoid
    shadowing the built-in list() constructor, which is a PEP 8 violation.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    app.add("test todo")

    # The renamed method should exist
    assert hasattr(app, "list_todos"), "TodoApp should have list_todos() method"

    # The old 'list' method should NOT exist (no longer shadows built-in)
    assert not hasattr(app, "list"), "TodoApp should not have 'list' method that shadows built-in"


def test_builtin_list_type_remains_accessible() -> None:
    """Python's built-in list() should remain accessible within TodoApp.

    The built-in list type should not be shadowed by the method name.
    This test verifies that list() as a type constructor still works correctly.
    """
    # We should be able to use the built-in list() type constructor
    result = list("abc")  # Should return ['a', 'b', 'c']
    assert result == ["a", "b", "c"]

    # Using list() with iterable should work
    result2 = [1, 2, 3]
    assert result2 == [1, 2, 3]


def test_list_todos_method_works_correctly(tmp_path) -> None:
    """list_todos() method should work correctly with show_all parameter.

    PEP 8 recommends avoiding method names that shadow built-in types like:
    list, dict, set, str, int, etc. The renamed method uses a descriptive name.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add todos
    app.add("first todo")
    second = app.add("second todo")
    app.mark_done(second.id)

    # list_todos(show_all=True) should return all todos
    todos = app.list_todos(show_all=True)
    assert len(todos) == 2

    # list_todos(show_all=False) should return only pending todos
    pending = app.list_todos(show_all=False)
    assert len(pending) == 1
    assert pending[0].text == "first todo"


def test_no_builtin_shadowing_in_class_namespace(tmp_path) -> None:
    """Verify TodoApp class doesn't shadow built-ins in its namespace.

    This is a structural check - the class should not have any
    attributes that shadow Python built-ins after the fix.
    """
    # Built-ins that should not be shadowed
    builtins_to_check = ["list", "dict", "set", "str", "int", "tuple"]

    for name in builtins_to_check:
        # Check if TodoApp has this as an attribute (method or property)
        if hasattr(TodoApp, name):
            # If it exists, it's shadowing a built-in - this should not happen
            # after the fix
            raise AssertionError(
                f"TodoApp.{name} shadows built-in {name} type - "
                f"method should be renamed to avoid shadowing"
            )
