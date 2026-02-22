"""Regression tests for Issue #5256: TodoApp missing rename method.

This test file ensures that TodoApp.rename() exists and works correctly,
following the same pattern as mark_done/mark_undone methods.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_todoapp_rename_successfully_renames_todo(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should rename a todo and return it."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original text")

    renamed = app.rename(added.id, "new text")

    assert renamed.id == added.id
    assert renamed.text == "new text"

    # Verify the change is persisted
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_todoapp_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent todo ID."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("existing todo")

    with pytest.raises(ValueError, match="not found"):
        app.rename(999, "new text")


def test_todoapp_rename_raises_for_empty_text(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for empty text via Todo.rename."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(added.id, "")

    # Verify state is unchanged
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "original"


def test_todoapp_rename_raises_for_whitespace_only_text(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for whitespace-only text."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(added.id, "   ")

    # Verify state is unchanged
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "original"


def test_todoapp_rename_strips_whitespace(tmp_path) -> None:
    """TodoApp.rename should strip whitespace from text (via Todo.rename)."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original")

    renamed = app.rename(added.id, "  padded text  ")

    assert renamed.text == "padded text"
