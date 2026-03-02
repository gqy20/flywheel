"""Tests for issue #6842: TodoApp.rename() method to expose Todo.rename() functionality."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_todoapp_rename_updates_todo_text(tmp_path) -> None:
    """TodoApp.rename() should update todo text and persist."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original text")
    assert added.id == 1
    assert added.text == "original text"

    # Rename it
    renamed = app.rename(1, "new text")
    assert renamed.id == 1
    assert renamed.text == "new text"

    # Verify persistence after save/load cycle
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_todoapp_rename_raises_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add one todo
    app.add("test")

    # Try to rename non-existent todo
    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "new text")


def test_todoapp_rename_raises_for_empty_text(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("test")

    # Try to rename with empty text
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "")


def test_todoapp_rename_raises_for_whitespace_only_text(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for whitespace-only text."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("test")

    # Try to rename with whitespace-only text
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "   ")
