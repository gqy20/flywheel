"""Test for issue #5365: TodoApp lacks rename() method."""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_todoapp_rename_updates_todo(tmp_path) -> None:
    """Test that TodoApp.rename() updates todo text."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original text")

    # Rename it
    renamed = app.rename(1, "new text")

    assert renamed.id == 1
    assert renamed.text == "new text"

    # Verify persistence
    todos = app.list()
    assert todos[0].text == "new text"


def test_todoapp_rename_raises_valueerror_for_nonexistent_todo(tmp_path) -> None:
    """Test that TodoApp.rename() raises ValueError for non-existent todo."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "some text")


def test_todoapp_rename_strips_whitespace(tmp_path) -> None:
    """Test that TodoApp.rename() strips whitespace from text."""
    app = TodoApp(str(tmp_path / "db.json"))

    app.add("original")
    renamed = app.rename(1, "  padded text  ")

    assert renamed.text == "padded text"
