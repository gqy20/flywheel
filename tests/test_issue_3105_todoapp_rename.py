"""Tests for issue #3105: TodoApp.rename() method."""

from __future__ import annotations

import time

import pytest

from flywheel.cli import TodoApp


def test_app_rename_success(tmp_path) -> None:
    """TodoApp.rename() should successfully rename a todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original text")
    original_updated_at = added.updated_at

    # Small delay to ensure updated_at changes
    time.sleep(0.01)

    renamed = app.rename(added.id, "new text")

    assert renamed.text == "new text"
    assert renamed.id == added.id
    assert renamed.updated_at > original_updated_at

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_app_rename_not_found(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    app.add("some todo")

    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "new text")


def test_app_rename_strips_whitespace(tmp_path) -> None:
    """TodoApp.rename() should strip whitespace from text."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")
    renamed = app.rename(added.id, "  padded text  ")

    assert renamed.text == "padded text"


def test_app_rename_propagates_empty_validation(tmp_path) -> None:
    """TodoApp.rename() should propagate empty text validation from Todo.rename()."""
    app = TodoApp(str(tmp_path / "db.json"))

    added = app.add("original")

    # Todo.rename raises ValueError for empty text
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(added.id, "")
