"""Regression tests for Issue #5365: TodoApp class lacks rename() method.

This test file ensures that TodoApp has a rename() method that loads,
finds, renames, and saves the todo - following the same pattern as mark_done()
and mark_undone() methods.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_rename_todo_with_valid_id_and_text(tmp_path) -> None:
    """rename() should successfully rename a todo with valid ID and text.

    When a todo with the given ID exists, it should be renamed and saved
    to storage. The method should use the same explicit iteration pattern
    consistent with mark_done() and mark_undone().
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original text")
    assert todo.id == 1
    assert todo.text == "original text"

    # Rename it - should succeed
    renamed = app.rename(todo.id, "new text")

    # Verify the rename worked
    assert renamed.text == "new text"
    assert renamed.id == todo.id

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_rename_todo_raises_valueerror_for_invalid_id(tmp_path) -> None:
    """rename() should raise ValueError when todo ID doesn't exist.

    When no todo with the given ID exists, the method should raise ValueError
    with appropriate message, consistent with mark_done() and mark_undone().
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("test todo")

    # Try to rename non-existent todo - should raise ValueError
    with pytest.raises(ValueError, match=r"Todo #999 not found"):
        app.rename(999, "new text")

    # Original todo should still exist unchanged
    remaining = app.list()
    assert len(remaining) == 1
    assert remaining[0].id == todo.id
    assert remaining[0].text == "test todo"


def test_rename_strips_whitespace_from_text(tmp_path) -> None:
    """rename() should strip whitespace from the new text.

    Following Todo.rename() behavior, the text should be stripped.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")

    # Rename with padded text
    renamed = app.rename(todo.id, "  padded text  ")

    # Verify whitespace was stripped
    assert renamed.text == "padded text"


def test_rename_raises_valueerror_for_empty_text(tmp_path) -> None:
    """rename() should raise ValueError for empty text after strip.

    Following Todo.rename() behavior, empty strings should raise ValueError.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")

    # Try to rename with empty text - should raise ValueError
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        app.rename(todo.id, "")

    # Try with whitespace-only text
    with pytest.raises(ValueError, match=r"Todo text cannot be empty"):
        app.rename(todo.id, "   ")

    # Original todo should still exist unchanged
    remaining = app.list()
    assert len(remaining) == 1
    assert remaining[0].text == "original"


def test_rename_updates_persisted_state(tmp_path) -> None:
    """rename() should persist the updated todo to storage.

    The method should call _save() after renaming, similar to mark_done()
    and mark_undone().
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")

    # Rename it
    app.rename(todo.id, "updated")

    # Create a new app instance to verify persistence
    app2 = TodoApp(db_path=str(db))
    todos = app2.list()

    assert len(todos) == 1
    assert todos[0].text == "updated"
