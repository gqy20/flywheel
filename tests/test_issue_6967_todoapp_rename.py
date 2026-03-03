"""Regression tests for Issue #6967: TodoApp class has no rename() method.

This test file ensures that TodoApp.rename() exposes Todo.rename() at the
app level, consistent with mark_done(), mark_undone(), and remove() patterns.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_rename_updates_todo_text(tmp_path) -> None:
    """rename() should update todo text via Todo.rename()."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original text")
    assert todo.id == 1
    assert todo.text == "original text"

    # Rename it
    renamed = app.rename(todo.id, "new text")
    assert renamed.text == "new text"
    assert renamed.id == todo.id

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_rename_raises_value_error_for_nonexistent_id(tmp_path) -> None:
    """rename() should raise ValueError if todo_id not found."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    app.add("some todo")

    # Try to rename non-existent todo - should raise ValueError
    with pytest.raises(ValueError, match=r"Todo #999 not found"):
        app.rename(999, "new text")


def test_rename_propagates_empty_text_validation(tmp_path) -> None:
    """rename() should propagate Todo.rename() validation for empty text."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original text")

    # Empty string should raise ValueError (via Todo.rename)
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        app.rename(todo.id, "")

    # Verify original text unchanged
    todos = app.list()
    assert todos[0].text == "original text"


def test_rename_strips_whitespace(tmp_path) -> None:
    """rename() should strip whitespace from text via Todo.rename()."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original text")

    # Rename with padded text - whitespace should be stripped
    renamed = app.rename(todo.id, "  padded text  ")
    assert renamed.text == "padded text"


def test_rename_updates_timestamp(tmp_path) -> None:
    """rename() should update updated_at via Todo.rename()."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original text")
    original_updated_at = todo.updated_at

    # Rename should update timestamp
    renamed = app.rename(todo.id, "new text")
    assert renamed.updated_at >= original_updated_at
