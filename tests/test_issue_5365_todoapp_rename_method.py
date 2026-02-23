"""Tests for issue #5365: TodoApp.rename() method.

Regression tests for TodoApp.rename(todo_id, text) method that should:
- Rename a todo by ID and save to storage
- Raise ValueError if todo not found
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_todoapp_rename_updates_todo_text(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should update todo text and save."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
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


def test_todoapp_rename_raises_valueerror_for_nonexistent_todo(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should raise ValueError if todo not found."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "new text")


def test_todoapp_rename_strips_whitespace(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should strip whitespace from text."""
    app = TodoApp(str(tmp_path / "db.json"))

    app.add("original")
    renamed = app.rename(1, "  padded  ")
    assert renamed.text == "padded"


def test_todoapp_rename_rejects_empty_text(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should reject empty text after strip."""
    app = TodoApp(str(tmp_path / "db.json"))

    app.add("original")

    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "")
