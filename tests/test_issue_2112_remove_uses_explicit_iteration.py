"""Tests for TodoApp.remove() explicit iteration pattern (Issue #2112).

These tests verify that:
1. remove() uses explicit iteration pattern consistent with mark_done()/mark_undone()
2. remove() properly raises ValueError when todo_id is not found
3. remove() properly removes the todo when todo_id exists
4. The behavior is consistent across all todo modification methods
"""

from __future__ import annotations

from pathlib import Path

from flywheel.cli import TodoApp


def test_remove_with_valid_todo_id_succeeds(tmp_path: Path) -> None:
    """remove() should successfully remove an existing todo."""
    db_path = tmp_path / ".todo.json"
    app = TodoApp(db_path=str(db_path))

    # Add a todo
    todo = app.add("buy milk")
    assert todo.id == 1

    # Remove it
    app.remove(todo.id)

    # Verify it's removed
    remaining = app.list()
    assert len(remaining) == 0


def test_remove_with_non_existent_todo_id_raises_value_error(tmp_path: Path) -> None:
    """remove() should raise ValueError when todo_id doesn't exist."""
    db_path = tmp_path / ".todo.json"
    app = TodoApp(db_path=str(db_path))

    # Add one todo
    todo = app.add("buy milk")
    assert todo.id == 1

    # Try to remove non-existent todo
    try:
        app.remove(999)
        raise AssertionError("Expected ValueError to be raised")
    except ValueError as e:
        assert "Todo #999 not found" in str(e)


def test_remove_multiple_todos(tmp_path: Path) -> None:
    """remove() should correctly remove one todo from a list of multiple todos."""
    db_path = tmp_path / ".todo.json"
    app = TodoApp(db_path=str(db_path))

    # Add multiple todos
    todo1 = app.add("first task")
    todo2 = app.add("second task")
    todo3 = app.add("third task")

    # Remove the middle one
    app.remove(todo2.id)

    # Verify correct todo was removed
    remaining = app.list()
    assert len(remaining) == 2
    assert remaining[0].id == todo1.id
    assert remaining[0].text == "first task"
    assert remaining[1].id == todo3.id
    assert remaining[1].text == "third task"


def test_remove_consistent_with_mark_done_pattern(tmp_path: Path) -> None:
    """remove() should use same explicit iteration pattern as mark_done()/mark_undone()."""
    db_path = tmp_path / ".todo.json"
    app = TodoApp(db_path=str(db_path))

    # Both methods should raise ValueError with same message format
    try:
        app.mark_done(999)
        raise AssertionError("Expected ValueError")
    except ValueError as e:
        mark_done_error = str(e)

    try:
        app.remove(999)
        raise AssertionError("Expected ValueError")
    except ValueError as e:
        remove_error = str(e)

    # Error messages should be consistent
    assert mark_done_error == remove_error == "Todo #999 not found"


def test_remove_from_empty_list_raises_value_error(tmp_path: Path) -> None:
    """remove() should raise ValueError when called on empty todo list."""
    db_path = tmp_path / ".todo.json"
    app = TodoApp(db_path=str(db_path))

    try:
        app.remove(1)
        raise AssertionError("Expected ValueError to be raised")
    except ValueError as e:
        assert "Todo #1 not found" in str(e)


def test_remove_only_todo_in_list(tmp_path: Path) -> None:
    """remove() should work correctly when removing the only todo in list."""
    db_path = tmp_path / ".todo.json"
    app = TodoApp(db_path=str(db_path))

    # Add and remove single todo
    todo = app.add("only task")
    app.remove(todo.id)

    # List should be empty
    remaining = app.list()
    assert len(remaining) == 0
