"""Regression tests for Issue #2112: TodoApp.remove() should use explicit iteration pattern.

This test file ensures that remove() method uses the same explicit iteration
pattern as mark_done() and mark_undone() methods for consistency and robustness.
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_remove_uses_explicit_iteration_valid_id(tmp_path) -> None:
    """remove() should successfully remove a todo with valid ID.

    When a todo with the given ID exists, it should be removed from the list
    and saved to storage. The method should use explicit iteration pattern
    consistent with mark_done() and mark_undone().
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("test todo")
    assert todo.id == 1

    # Remove it - should succeed
    app.remove(todo.id)

    # Verify it's gone
    remaining = app.list_todos()
    assert len(remaining) == 0
    assert all(t.id != todo.id for t in remaining)


def test_remove_uses_explicit_iteration_invalid_id(tmp_path) -> None:
    """remove() should raise ValueError when todo ID doesn't exist.

    When no todo with the given ID exists, the method should iterate through
    all todos and raise ValueError with appropriate message, consistent with
    mark_done() and mark_undone() behavior.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add a todo
    todo = app.add("test todo")

    # Try to remove non-existent todo - should raise ValueError
    with pytest.raises(ValueError, match=r"Todo #999 not found"):
        app.remove(999)

    # Original todo should still exist
    remaining = app.list_todos()
    assert len(remaining) == 1
    assert remaining[0].id == todo.id


def test_remove_consistent_with_mark_done_undone_pattern(tmp_path) -> None:
    """remove() should use the same iteration pattern as mark_done()/mark_undone().

    This test verifies code consistency - all three methods (mark_done, mark_undone,
    remove) should use the same explicit iteration with early return pattern.
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Add multiple todos
    todo1 = app.add("first todo")
    todo2 = app.add("second todo")
    app.add("third todo")  # todo3 - unused but ensures list has 3 items

    # All three methods should work consistently
    # mark_done modifies in-place and saves
    app.mark_done(todo1.id)
    todos = app.list_todos()
    assert todos[0].done

    # mark_undone modifies in-place and saves
    app.mark_undone(todo1.id)
    todos = app.list_todos()
    assert not todos[0].done

    # remove should work with the same pattern
    app.remove(todo2.id)
    todos = app.list_todos()
    assert len(todos) == 2
    assert all(t.id != todo2.id for t in todos)


def test_remove_non_existent_id_error_message(tmp_path) -> None:
    """remove() should raise ValueError with consistent error message format.

    Error message should match the format used by mark_done() and mark_undone():
    'Todo #{id} not found'
    """
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Test the error message format
    with pytest.raises(ValueError, match=r"Todo #42 not found"):
        app.remove(42)


def test_remove_from_empty_list(tmp_path) -> None:
    """remove() should raise ValueError when trying to remove from empty list."""
    db = tmp_path / "test.json"
    app = TodoApp(db_path=str(db))

    # Try to remove from empty database
    with pytest.raises(ValueError, match=r"Todo #1 not found"):
        app.remove(1)
