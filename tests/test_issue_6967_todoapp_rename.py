"""Regression tests for Issue #6967: TodoApp class has no rename() method.

This test file ensures that TodoApp exposes the Todo.rename() functionality
at the app level, consistent with the existing mark_done, mark_undone, and
remove methods.

Issue #6967 acceptance criteria:
- TodoApp.rename(todo_id, text) method exists
- Method raises ValueError if todo_id not found (consistent with mark_done/mark_undone)
- Method calls todo.rename(text) which validates text is not empty
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_todoapp_rename_updates_todo_text(tmp_path) -> None:
    """TodoApp.rename(todo_id, text) should update todo text.

    Issue #6967: TodoApp should expose Todo.rename() at the app level.
    """
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("original text")
    assert added.id == 1
    assert app.list()[0].text == "original text"

    # Rename the todo
    renamed = app.rename(1, "new text")
    assert renamed.id == 1
    assert renamed.text == "new text"

    # Verify persistence
    assert app.list()[0].text == "new text"


def test_todoapp_rename_raises_valueerror_for_nonexistent_id(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for non-existent todo ID.

    Issue #6967: Consistent with mark_done/mark_undone behavior.
    """
    app = TodoApp(str(tmp_path / "db.json"))

    # No todos exist, rename should raise ValueError
    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.rename(999, "new text")


def test_todoapp_rename_propagates_empty_text_validation(tmp_path) -> None:
    """TodoApp.rename() should propagate Todo.rename() validation.

    Issue #6967: Method calls todo.rename(text) which validates text is not empty.
    """
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original text")

    # Empty text should raise ValueError via todo.rename()
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(1, "")


def test_todoapp_rename_strips_whitespace(tmp_path) -> None:
    """TodoApp.rename() should strip whitespace like Todo.rename() does."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("original text")

    # Whitespace should be stripped
    renamed = app.rename(1, "  padded text  ")
    assert renamed.text == "padded text"
