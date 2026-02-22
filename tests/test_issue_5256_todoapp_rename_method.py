"""Regression tests for Issue #5256: TodoApp class missing rename method.

This test file ensures that TodoApp exposes a rename method that follows
the same pattern as mark_done/mark_undone: calls todo.rename(text) and saves.
"""

from __future__ import annotations

from flywheel.cli import TodoApp


def test_todoapp_rename_success(tmp_path) -> None:
    """TodoApp.rename should successfully rename an existing todo."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo first
    todo = app.add("Original text")
    assert todo.text == "Original text"

    # Rename it
    renamed = app.rename(todo.id, "New text")
    assert renamed.text == "New text"
    assert renamed.id == todo.id


def test_todoapp_rename_nonexistent_id_raises_value_error(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for non-existent ID."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo so the list isn't empty
    app.add("Some todo")

    # Try to rename non-existent ID
    try:
        app.rename(999, "New text")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not found" in str(e).lower()


def test_todoapp_rename_empty_text_raises_value_error(tmp_path) -> None:
    """TodoApp.rename should raise ValueError for empty text.

    The ValueError should be raised by Todo.rename when text is empty.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo first
    todo = app.add("Original text")

    # Try to rename with empty text
    try:
        app.rename(todo.id, "")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e).lower()


def test_todoapp_rename_persists_to_storage(tmp_path) -> None:
    """TodoApp.rename should persist the renamed todo to storage."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo first
    todo = app.add("Original text")

    # Rename it
    app.rename(todo.id, "Renamed text")

    # Verify persistence by creating a new app instance
    new_app = TodoApp(db_path=str(db))
    todos = new_app.list()
    assert len(todos) == 1
    assert todos[0].text == "Renamed text"
