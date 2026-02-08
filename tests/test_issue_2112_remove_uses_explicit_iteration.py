"""Tests for TodoApp.remove() explicit iteration pattern (Issue #2112).

These tests verify that:
1. TodoApp.remove() uses explicit iteration pattern consistent with mark_done()/mark_undone()
2. remove() correctly removes todos with valid IDs
3. remove() raises ValueError with proper message for non-existent IDs
4. The implementation is consistent across all todo modification methods
"""

from __future__ import annotations

import pytest

from flywheel.cli import TodoApp


def test_remove_with_valid_todo_id_succeeds(tmp_path) -> None:
    """remove() should successfully remove a todo with valid ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    added = app.add("buy milk")
    assert added.id == 1
    assert len(app.list()) == 1

    # Remove it
    app.remove(1)
    assert len(app.list()) == 0


def test_remove_with_multiple_todos_removes_correct_one(tmp_path) -> None:
    """remove() should only remove the todo with matching ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add multiple todos
    todo1 = app.add("first")
    todo2 = app.add("second")
    todo3 = app.add("third")

    assert len(app.list()) == 3

    # Remove middle one
    app.remove(todo2.id)

    # Verify correct removal
    remaining = app.list()
    assert len(remaining) == 2
    assert any(t.id == todo1.id for t in remaining)
    assert any(t.id == todo3.id for t in remaining)
    assert not any(t.id == todo2.id for t in remaining)


def test_remove_with_nonexistent_todo_id_raises_value_error(tmp_path) -> None:
    """remove() should raise ValueError with proper message for non-existent ID."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Add a todo
    app.add("existing todo")

    # Try to remove non-existent todo
    with pytest.raises(ValueError, match="Todo #999 not found"):
        app.remove(999)


def test_remove_from_empty_list_raises_value_error(tmp_path) -> None:
    """remove() should raise ValueError when called on empty todo list."""
    app = TodoApp(str(tmp_path / "db.json"))

    with pytest.raises(ValueError, match="Todo #1 not found"):
        app.remove(1)


def test_remove_error_message_format_consistent_with_mark_done(tmp_path) -> None:
    """remove() error message should match mark_done() error message format."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Both methods should raise the same error message format
    with pytest.raises(ValueError, match="Todo #42 not found"):
        app.mark_done(42)

    with pytest.raises(ValueError, match="Todo #42 not found"):
        app.remove(42)


def test_remove_uses_explicit_iteration_pattern(tmp_path) -> None:
    """Verify remove() implementation matches mark_done()/mark_undone() pattern.

    This test verifies code consistency by checking that remove() follows
    the same explicit iteration pattern as mark_done() and mark_undone().
    """
    import inspect

    # Get source code for the methods
    remove_source = inspect.getsource(TodoApp.remove)
    mark_done_source = inspect.getsource(TodoApp.mark_done)
    mark_undone_source = inspect.getsource(TodoApp.mark_undone)

    # Verify remove() uses explicit iteration (not list comprehension)
    assert "for " in remove_source and " todo in " in remove_source, (
        "remove() should use explicit iteration pattern with 'for ... in todos'"
    )

    # Verify remove() has early return after finding the todo
    # The pattern should be similar to mark_done/mark_undone
    assert "break" in remove_source or "return" in remove_source, (
        "remove() should have early return/break after finding the todo"
    )

    # Verify all three methods use similar pattern structure
    # They should all have explicit iteration, not list comprehension
    for method_source in [remove_source, mark_done_source, mark_undone_source]:
        assert "[todo for todo in" not in method_source, (
            f"{method_source} should not use list comprehension for iteration"
        )


def test_remove_behavior_preserved_after_refactor(tmp_path) -> None:
    """Ensure remove() behavior is identical before/after refactor."""
    app = TodoApp(str(tmp_path / "db.json"))

    # Test normal removal
    todo = app.add("test todo")
    app.remove(todo.id)
    assert len(app.list()) == 0

    # Test error case
    app.add("another")
    with pytest.raises(ValueError):
        app.remove(999)

    # Verify the todo is still there after failed removal
    assert len(app.list()) == 1
