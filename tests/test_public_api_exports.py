"""Tests for public API exports from package entry point.

Issue #7276: Verify that core public API is accessible via top-level imports.
"""

from __future__ import annotations


def test_todo_exported_at_package_level() -> None:
    """Verify Todo class is accessible via `from flywheel import Todo`."""
    from flywheel import Todo

    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"
    assert todo.done is False


def test_todo_app_exported_at_package_level() -> None:
    """Verify TodoApp class is accessible via `from flywheel import TodoApp`."""
    from flywheel import TodoApp

    # Verify the class is properly exported
    assert hasattr(TodoApp, "__init__")
    assert hasattr(TodoApp, "add")
    assert hasattr(TodoApp, "list")
    assert hasattr(TodoApp, "mark_done")
    assert hasattr(TodoApp, "remove")


def test_todo_storage_exported_at_package_level() -> None:
    """Verify TodoStorage class is accessible via `from flywheel import TodoStorage`."""
    from flywheel import TodoStorage

    # Verify the class is properly exported
    assert hasattr(TodoStorage, "__init__")
    assert hasattr(TodoStorage, "load")
    assert hasattr(TodoStorage, "save")
    assert hasattr(TodoStorage, "next_id")


def test_todo_formatter_exported_at_package_level() -> None:
    """Verify TodoFormatter class is accessible via `from flywheel import TodoFormatter`."""
    from flywheel import TodoFormatter

    # Verify the class is properly exported
    assert hasattr(TodoFormatter, "format_todo")
    assert hasattr(TodoFormatter, "format_list")


def test_all_exports_in_dunder_all() -> None:
    """Verify all public API names are listed in __all__."""
    import flywheel

    expected_exports = {"__version__", "Todo", "TodoApp", "TodoStorage", "TodoFormatter"}
    actual_exports = set(flywheel.__all__)

    assert expected_exports.issubset(actual_exports), (
        f"Missing exports in __all__: {expected_exports - actual_exports}"
    )


def test_deep_imports_still_work() -> None:
    """Verify that existing deep import paths remain functional (backward compatibility)."""
    from flywheel.cli import TodoApp
    from flywheel.formatter import TodoFormatter
    from flywheel.storage import TodoStorage
    from flywheel.todo import Todo

    # Verify the classes work correctly
    todo = Todo(id=1, text="test")
    assert todo.text == "test"

    storage = TodoStorage()
    assert storage is not None

    assert TodoFormatter.format_todo(todo).startswith("[ ]")

    # Verify TodoApp can be instantiated
    _ = TodoApp  # Verify the class is accessible
