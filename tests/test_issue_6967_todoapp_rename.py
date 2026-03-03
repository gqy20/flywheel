"""Tests for issue #6967: TodoApp.rename() method to expose Todo.rename() at app level."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_app_rename_updates_todo_text(tmp_path) -> None:
    """TodoApp.rename() should update todo text and persist changes."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo first
    added = app.add("original text")
    assert added.id == 1
    assert added.text == "original text"

    # Rename it
    renamed = app.rename(1, "new text")
    assert renamed.id == 1
    assert renamed.text == "new text"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_app_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add one todo
    app.add("some task")

    # Try to rename non-existent todo
    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "new text")


def test_app_rename_propagates_empty_text_validation(tmp_path) -> None:
    """TodoApp.rename() should propagate Todo.rename() validation for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original")

    # Empty text should raise ValueError (via Todo.rename validation)
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "")


def test_app_rename_propagates_whitespace_validation(tmp_path) -> None:
    """TodoApp.rename() should propagate Todo.rename() validation for whitespace-only text."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original")

    # Whitespace-only text should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "   ")
