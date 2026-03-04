"""Tests for issue #7276: Export core public API to package entry point."""

from __future__ import annotations


def test_can_import_todo_from_package_entry() -> None:
    """Todo should be importable directly from flywheel package."""
    from flywheel import Todo

    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"


def test_can_import_todo_app_from_package_entry() -> None:
    """TodoApp should be importable directly from flywheel package."""
    from flywheel import TodoApp

    assert TodoApp is not None


def test_can_import_todo_storage_from_package_entry() -> None:
    """TodoStorage should be importable directly from flywheel package."""
    from flywheel import TodoStorage

    assert TodoStorage is not None


def test_can_import_todo_formatter_from_package_entry() -> None:
    """TodoFormatter should be importable directly from flywheel package."""
    from flywheel import TodoFormatter

    assert TodoFormatter is not None


def test_dunder_all_contains_all_public_api() -> None:
    """__all__ should contain all public API names."""
    import flywheel

    expected_exports = {"__version__", "Todo", "TodoApp", "TodoStorage", "TodoFormatter"}
    assert expected_exports.issubset(set(flywheel.__all__))


def test_deep_imports_still_work() -> None:
    """Existing deep imports (from flywheel.todo import Todo) should still work."""
    # Verify they are the same classes
    from flywheel import Todo, TodoApp, TodoFormatter, TodoStorage
    from flywheel.cli import TodoApp as DeepTodoApp
    from flywheel.formatter import TodoFormatter as DeepTodoFormatter
    from flywheel.storage import TodoStorage as DeepTodoStorage
    from flywheel.todo import Todo as DeepTodo

    assert Todo is DeepTodo
    assert TodoApp is DeepTodoApp
    assert TodoStorage is DeepTodoStorage
    assert TodoFormatter is DeepTodoFormatter
