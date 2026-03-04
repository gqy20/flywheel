"""Tests for issue #7276: Export core public APIs to package entry.

Verifies that users can import core types from the top-level flywheel package
without needing to import from submodules directly.
"""

from __future__ import annotations


def test_import_todo_from_top_level() -> None:
    """Verify Todo can be imported from top-level flywheel package."""
    from flywheel import Todo

    todo = Todo(id=1, text="test")
    assert todo.id == 1
    assert todo.text == "test"
    assert todo.done is False


def test_import_todo_app_from_top_level() -> None:
    """Verify TodoApp can be imported from top-level flywheel package."""
    from flywheel import TodoApp

    # TodoApp is a class, just verify it's importable
    assert TodoApp.__name__ == "TodoApp"


def test_import_todo_storage_from_top_level() -> None:
    """Verify TodoStorage can be imported from top-level flywheel package."""
    from flywheel import TodoStorage

    # TodoStorage is a class, just verify it's importable
    assert TodoStorage.__name__ == "TodoStorage"


def test_import_todo_formatter_from_top_level() -> None:
    """Verify TodoFormatter can be imported from top-level flywheel package."""
    from flywheel import TodoFormatter

    # TodoFormatter is a class, just verify it's importable
    assert TodoFormatter.__name__ == "TodoFormatter"


def test_all_exports_defined() -> None:
    """Verify __all__ contains all public API names."""
    import flywheel

    expected_exports = ["__version__", "Todo", "TodoApp", "TodoStorage", "TodoFormatter"]

    for name in expected_exports:
        assert name in flywheel.__all__, f"{name!r} should be in flywheel.__all__"


def test_version_still_exported() -> None:
    """Verify __version__ is still exported."""
    from flywheel import __version__

    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_submodule_imports_still_work() -> None:
    """Verify existing submodule import paths still work (backwards compatibility)."""
    # These should still work
    from flywheel.todo import Todo
    from flywheel.cli import TodoApp
    from flywheel.storage import TodoStorage
    from flywheel.formatter import TodoFormatter

    todo = Todo(id=1, text="test")
    assert todo.text == "test"
