"""Regression tests for Issue #5256: TodoApp.rename() method.

This test file ensures that TodoApp exposes the rename functionality from
the Todo model layer, following the same pattern as mark_done()/mark_undone().
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_rename_success(tmp_path) -> None:
    """TodoApp.rename() should successfully rename a todo with valid ID and text.

    When a todo with the given ID exists, its text should be updated
    and saved to storage. The method should return the updated Todo.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original text")
    assert todo.id == 1
    assert todo.text == "original text"

    # Rename it - should succeed and return updated todo
    updated = app.rename(todo.id, "new text")
    assert updated.id == todo.id
    assert updated.text == "new text"

    # Verify persistence
    todos = app.list()
    assert len(todos) == 1
    assert todos[0].text == "new text"


def test_rename_invalid_id_raises_valueerror(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError when todo ID doesn't exist.

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


def test_rename_empty_text_raises_valueerror(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for empty text.

    The error should be propagated from Todo.rename() which validates
    that the text is not empty after stripping.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")

    # Empty text should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(todo.id, "")

    # Original todo should be unchanged
    todos = app.list()
    assert todos[0].text == "original"


def test_rename_whitespace_only_text_raises_valueerror(tmp_path) -> None:
    """TodoApp.rename() should raise ValueError for whitespace-only text."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")

    # Whitespace-only text should raise ValueError
    with pytest.raises(ValueError, match="Todo text cannot be empty"):
        app.rename(todo.id, "   ")

    # Original todo should be unchanged
    todos = app.list()
    assert todos[0].text == "original"


def test_rename_strips_whitespace(tmp_path) -> None:
    """TodoApp.rename() should strip leading/trailing whitespace from text."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")

    # Rename with padded text
    updated = app.rename(todo.id, "  padded text  ")

    # Text should be stripped
    assert updated.text == "padded text"


def test_rename_updates_timestamp(tmp_path) -> None:
    """TodoApp.rename() should update the updated_at timestamp."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("original")
    original_updated_at = todo.updated_at

    # Small delay to ensure timestamp changes
    import time
    time.sleep(0.01)

    # Rename
    updated = app.rename(todo.id, "new text")

    # Timestamp should be updated
    assert updated.updated_at != original_updated_at


def test_rename_consistent_with_mark_done_pattern(tmp_path) -> None:
    """TodoApp.rename() should use the same iteration pattern as mark_done()/mark_undone().

    This test verifies code consistency - all three methods (mark_done, mark_undone,
    rename) should use the same explicit iteration with early return pattern.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    app.add("third todo")

    # All three methods should work consistently
    # mark_done modifies in-place and saves
    app.mark_done(todo1.id)
    todos = app.list()
    assert todos[0].done

    # mark_undone modifies in-place and saves
    app.mark_undone(todo1.id)
    todos = app.list()
    assert not todos[0].done

    # rename should work with the same pattern
    app.rename(todo2.id, "renamed second")
    todos = app.list()
    assert todos[1].text == "renamed second"
    assert todos[2].text == "third todo"  # todo3 should be unchanged
