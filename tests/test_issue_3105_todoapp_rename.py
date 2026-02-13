"""Tests for issue #3105: TodoApp.rename method."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_todoapp_rename_success(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should successfully rename a todo."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original text")
    original_updated_at = added.updated_at

    # Rename the todo
    renamed = app.rename(added.id, "new text")

    assert renamed.id == added.id
    assert renamed.text == "new text"
    assert renamed.updated_at >= original_updated_at

    # Verify the change persisted
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_todoapp_rename_strips_whitespace(tmp_path) -> None:
    """TodoApp.rename should strip whitespace from the text."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original")

    renamed = app.rename(added.id, "  padded text  ")

    assert renamed.text == "padded text"


def test_todoapp_rename_not_found_raises_error(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))
    app.add("first todo")

    with pytest.raises(ValueError, match=r"Todo #999 not found"):
        app.rename(999, "new text")


def test_todoapp_rename_empty_text_raises_error(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for empty text."""
    app = TodoApp(str(tmp_path / "db.json"))
    added = app.add("original")
    original_text = added.text

    # Should propagate the ValueError from Todo.rename
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(added.id, "")

    # Verify state unchanged after failed validation
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == original_text
